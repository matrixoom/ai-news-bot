"""Service layer for frontend Market Data payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import logging
import os
import threading
from typing import Any
from zoneinfo import ZoneInfo

from .market_data_repository import (
    MarketDataPoint,
    MarketDataRepository,
    MarketDataValidationError,
    MarketIndicatorDefinition,
)

MARKET_DATA_TABS = {
    "commodities": "商品",
    "precious_metals": "贵金属",
    "stock_market": "股票市场",
    "real_estate": "房地产",
}

MARKET_DATA_RANGES = {"6m", "1y", "3y", "5y", "10y", "15y", "20y", "25y", "30y", "custom"}
MARKET_DATA_FREQUENCIES = {"daily", "monthly", "yearly"}
MARKET_DATA_REFRESH_SCHEDULE_TIMES = ("08:00", "20:00")
MARKET_DATA_REFRESH_TIMEZONE = "Asia/Shanghai"
logger = logging.getLogger(__name__)

_CHART_SYNC_GROUPS: dict[str, str] = {
    "wti_crude_oil": "commodities",
    "brent_crude_oil": "commodities",
    "gold_spot": "precious_metals",
    "silver_spot": "precious_metals",
    "copper": "precious_metals",
    "second_hand_housing": "real_estate",
}


@dataclass(frozen=True)
class ResolvedDateRange:
    range_type: str
    start_date: str
    end_date: str


class MarketDataService:
    """组织 Market Data 前端接口 payload。"""

    def __init__(
        self,
        repository: MarketDataRepository | None = None,
        *,
        sync_service: Any | None = None,
        enable_scheduler: bool = False,
        scheduler_check_seconds: float | None = None,
    ) -> None:
        """初始化 Market Data 服务。

        Args:
            repository: Market Data 本地仓储。
            sync_service: 商品、贵金属历史同步服务，测试可注入。
            enable_scheduler: 是否启动商品和贵金属自动刷新线程。
            scheduler_check_seconds: 后台定时检查间隔秒数。

        Returns:
            Market Data 服务实例。
        """

        self._repository = repository or MarketDataRepository()
        self._sync_service = sync_service
        self._scheduled_refresh_lock = threading.Lock()
        self._completed_scheduled_slots: set[str] = set()
        self._scheduler_check_seconds = max(
            5.0,
            float(
                scheduler_check_seconds
                if scheduler_check_seconds is not None
                else os.getenv("MARKET_DATA_SCHEDULER_CHECK_SECONDS", "20")
            ),
        )
        self._scheduler_stop_event = threading.Event()
        self._scheduler_thread: threading.Thread | None = None
        if enable_scheduler:
            self.start_scheduler()

    def sync_chart(self, chart_id: str) -> dict[str, Any]:
        """同步指定 Market Data 图表。

        Args:
            chart_id: 图表指标 ID。

        Returns:
            同步成功标记和本次写入点位数量。
        """

        if chart_id not in _CHART_SYNC_GROUPS:
            raise MarketDataValidationError("unknown chart id for sync")

        syncer = self._syncer()
        point_counts = syncer.sync_indicator_history(chart_id)
        return {"ok": True, "point_counts": point_counts}

    def start_scheduler(self) -> None:
        """启动商品与贵金属后台自动刷新检查线程。"""

        if self._scheduler_thread is not None:
            return
        self._scheduler_stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="market-data-refresh-scheduler",
            daemon=True,
        )
        self._scheduler_thread.start()

    def stop_scheduler(self) -> None:
        """停止商品与贵金属后台自动刷新检查线程。"""

        self._scheduler_stop_event.set()
        if self._scheduler_thread is not None:
            self._scheduler_thread.join(timeout=2.0)
            self._scheduler_thread = None

    def run_due_scheduled_refresh(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        """在上海时间 08:00 和 20:00 自动刷新商品、贵金属数据。

        Args:
            now: 测试可注入的当前 UTC 时间。

        Returns:
            本轮触发的刷新结果；未到时间或时间槽已执行时返回空列表。
        """

        current_time = now or datetime.now(UTC)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        local_time = current_time.astimezone(ZoneInfo(MARKET_DATA_REFRESH_TIMEZONE))
        current_slot_time = local_time.strftime("%H:%M")
        if current_slot_time not in MARKET_DATA_REFRESH_SCHEDULE_TIMES:
            return []

        slot_key = f"{local_time.strftime('%Y-%m-%d')}T{current_slot_time}"
        with self._scheduled_refresh_lock:
            if slot_key in self._completed_scheduled_slots:
                return []
            self._completed_scheduled_slots.add(slot_key)
            self._trim_completed_scheduled_slots(local_time.date().isoformat())

        syncer = self._syncer()
        try:
            commodities_result = syncer.sync_commodities_history()
            metals_result = syncer.sync_precious_metals_history()
        except Exception:
            with self._scheduled_refresh_lock:
                self._completed_scheduled_slots.discard(slot_key)
            logger.exception("market data scheduled refresh failed", extra={"slot": slot_key})
            raise
        logger.info("market data scheduled refresh completed", extra={"slot": slot_key})
        return [
            {
                "slot": slot_key,
                "commodities": commodities_result,
                "precious_metals": metals_result,
            }
        ]

    def _scheduler_loop(self) -> None:
        """循环检查商品与贵金属自动刷新触发条件。"""

        while not self._scheduler_stop_event.wait(self._scheduler_check_seconds):
            try:
                self.run_due_scheduled_refresh()
            except Exception as error:  # pragma: no cover - 后台防御日志
                logger.warning("market data scheduler loop failed: %s", error)

    def _syncer(self) -> Any:
        """延迟创建 Market Data 同步服务，避免测试和轻量接口提前加载外部依赖。

        Returns:
            可执行 Market Data 历史同步的服务实例。
        """

        if self._sync_service is None:
            from .market_data_sync_service import MarketDataSyncService

            self._sync_service = MarketDataSyncService(repository=self._repository)
        return self._sync_service

    def _trim_completed_scheduled_slots(self, current_day: str) -> None:
        """保留当天已执行时间槽，避免长期运行进程内存持续增长。

        Args:
            current_day: 当前上海日期，格式为 `YYYY-MM-DD`。

        Returns:
            无返回值；直接清理内部集合。
        """

        self._completed_scheduled_slots = {
            slot for slot in self._completed_scheduled_slots if slot.startswith(f"{current_day}T")
        }

    def build_module_payload(self, tab: str = "commodities") -> dict[str, Any]:
        normalized_tab = self._validate_tab(tab)
        charts = self._repository.list_indicators(normalized_tab)
        chart_payloads = [self._chart_definition_payload(chart) for chart in charts]
        payload: dict[str, Any] = {
            "generated_at": _utc_now(),
            "module": {
                "id": "market-data",
                "label": "Market Data",
                "description": "Commodities, precious metals, and stock indices",
                "status": "live",
                "loading": False,
            },
            "tabs": [
                {"value": value, "label": label}
                for value, label in MARKET_DATA_TABS.items()
            ],
            "tab": normalized_tab,
            "default_range": "1y",
            "default_frequency": self._default_frequency_for_tab(normalized_tab),
            "frequency_options": self._frequency_options_for_tab(normalized_tab),
            "range_options": [
                {"value": "6m", "label": "半年"},
                {"value": "1y", "label": "1年"},
                {"value": "3y", "label": "3年"},
                {"value": "5y", "label": "5年"},
                {"value": "10y", "label": "10年"},
                {"value": "15y", "label": "15年"},
                {"value": "20y", "label": "20年"},
                {"value": "25y", "label": "25年"},
                {"value": "30y", "label": "30年"},
                {"value": "custom", "label": "自定义"},
            ],
            "charts": chart_payloads,
        }
        if normalized_tab == "real_estate":
            try:
                payload["housing_cities"] = self._repository.list_housing_cities("second_hand_housing")
            except Exception:
                payload["housing_cities"] = []
        return payload

    def build_chart_payload(
        self,
        chart_id: str,
        *,
        range_type: str = "1y",
        start_date: str | None = None,
        end_date: str | None = None,
        frequency: str | None = None,
        cities: list[str] | None = None,
    ) -> dict[str, Any]:
        resolved_range = self._resolve_range(
            range_type=range_type,
            start_date=start_date,
            end_date=end_date,
        )
        definition = self._repository.get_indicator(chart_id)
        if definition is None:
            raise MarketDataValidationError("unknown chart id")
        normalized_frequency = self._validate_frequency(frequency or definition.frequency)

        payload: dict[str, Any] = {
            "id": definition.indicator_id,
            "title": definition.title,
            "unit": definition.unit,
            "frequency": normalized_frequency,
            "status": definition.status,
            "chart_type": "line",
            "range": {
                "type": resolved_range.range_type,
                "start_date": resolved_range.start_date,
                "end_date": resolved_range.end_date,
            },
        }

        # 房地产图表：按城市返回多个 series
        if chart_id == "second_hand_housing":
            available_cities = self._repository.list_housing_cities(chart_id)
            payload["housing_cities"] = available_cities
            payload["chart_type"] = "housing_multi_metric"
            payload["unit"] = "% / 指数"
            selected_cities = cities or available_cities[:2]
            raw_series = self._repository.load_housing_points(
                indicator_id=chart_id,
                cities=selected_cities,
                start_date=resolved_range.start_date,
                end_date=resolved_range.end_date,
            )
            metric_labels = {
                "yoy": "同比",
                "mom": "环比",
                "global_index": "全局走势",
            }
            payload["series"] = []
            for city, city_points in raw_series.items():
                points_by_metric: dict[str, list[Any]] = {metric: [] for metric in metric_labels}
                for point in city_points:
                    if point.metric in points_by_metric:
                        points_by_metric[point.metric].append(point)
                for metric, label in metric_labels.items():
                    metric_points = points_by_metric[metric]
                    if not metric_points:
                        continue
                    payload["series"].append({
                        "name": f"{city} {label}",
                        "metric": metric,
                        "points": [
                            {
                                "date": point.period_end,
                                "period_label": point.period_label,
                                "value": point.value,
                                "unit": point.unit,
                                "released_at": point.released_at,
                            }
                            for point in metric_points
                        ],
                    })
            sync_state = self._repository.get_sync_state(chart_id)
            payload["sync_state"] = {
                "status": sync_state.status if sync_state else "unavailable",
                "synced_at": sync_state.synced_at if sync_state else "",
                "warning_message": sync_state.warning_message if sync_state else "",
                "point_count": sync_state.point_count if sync_state else 0,
            }
            return payload

        points = self._repository.load_points(
            indicator_id=chart_id,
            start_date=resolved_range.start_date,
            end_date=resolved_range.end_date,
            frequency=normalized_frequency,
        )
        sync_state = self._repository.get_sync_state(chart_id)
        payload["sync_state"] = {
            "status": sync_state.status if sync_state else "unavailable",
            "synced_at": sync_state.synced_at if sync_state else "",
            "warning_message": sync_state.warning_message if sync_state else "",
            "point_count": sync_state.point_count if sync_state else 0,
        }
        payload["series"] = [
            {
                "name": definition.title,
                "points": [
                    {
                        "date": point.period_end,
                        "period_label": point.period_label,
                        "value": point.value,
                        "unit": point.unit,
                        "released_at": point.released_at,
                    }
                    for point in points
                ],
            }
        ]
        return payload

    def _validate_tab(self, tab: str) -> str:
        if tab not in MARKET_DATA_TABS:
            raise MarketDataValidationError("invalid market data tab")
        return tab

    def _validate_frequency(self, frequency: str) -> str:
        if frequency not in MARKET_DATA_FREQUENCIES:
            raise MarketDataValidationError("invalid market data frequency")
        return frequency

    def _default_frequency_for_tab(self, tab: str) -> str:
        if tab in {"stock_market", "real_estate"}:
            return "monthly"
        return "daily"

    def _frequency_options_for_tab(self, tab: str) -> list[dict[str, str]]:
        return [
            {"value": "daily", "label": "日度"},
            {"value": "monthly", "label": "月度"},
            {"value": "yearly", "label": "年度"},
        ]

    def _resolve_range(
        self,
        *,
        range_type: str,
        start_date: str | None,
        end_date: str | None,
    ) -> ResolvedDateRange:
        if range_type not in MARKET_DATA_RANGES:
            raise MarketDataValidationError("invalid market data range")
        today = date.today()
        if range_type == "custom":
            if not start_date or not end_date:
                raise MarketDataValidationError("custom range requires start_date and end_date")
            start = self._parse_date(start_date)
            end = self._parse_date(end_date)
        else:
            end = today
            months_by_range = {
                "6m": 6,
                "1y": 12,
                "3y": 36,
                "5y": 60,
                "10y": 120,
                "15y": 180,
                "20y": 240,
                "25y": 300,
                "30y": 360,
            }
            start = _shift_months(end, -months_by_range[range_type])
        if start > end:
            raise MarketDataValidationError("start date must be before end date")
        return ResolvedDateRange(range_type=range_type, start_date=start.isoformat(), end_date=end.isoformat())

    def _parse_date(self, raw_value: str) -> date:
        try:
            return date.fromisoformat(raw_value)
        except ValueError as error:
            raise MarketDataValidationError("invalid market data date") from error

    def _chart_definition_payload(self, definition: MarketIndicatorDefinition) -> dict[str, Any]:
        return {
            "id": definition.indicator_id,
            "title": definition.title,
            "unit": definition.unit,
            "frequency": definition.frequency,
            "status": definition.status,
            "chart_type": "line",
        }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _shift_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    days_in_month = [31, 29 if _is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(value.day, days_in_month[month - 1]))


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
