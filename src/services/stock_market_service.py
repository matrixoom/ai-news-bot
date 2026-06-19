"""Market Data 股票市场页面业务服务。"""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from datetime import UTC, datetime, date
import json
import logging
import os
from pathlib import Path
import threading
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from src.domain.market_monitoring import build_default_market_registry

from .market_history_store import MarketHistoryStore
from .stock_market_repository import (
    StockInstrument,
    StockMarketRepository,
    StockMarketValidationError,
)
from .stock_market_sync_service import StockMarketSyncService, _compact_error_message


STOCK_MARKET_RANGES = {"1m", "3m", "6m", "1y", "3y", "5y", "custom"}
STOCK_FINANCIAL_REPORT_TYPES = {"quarterly", "yearly"}
STOCK_OVERVIEW_INDEX_HISTORY_DAYS = 1830
STOCK_REQUIRED_FINANCIAL_METRICS = {
    "roe",
    "revenue_yoy",
    "net_profit_yoy",
    "debt_asset_ratio",
}
STOCK_OVERVIEW_INDEX_REGISTRY = tuple(build_default_market_registry().values())
STOCK_ALL_REFRESH_TERMINAL_STATUSES = {"completed", "completed_with_warnings", "failed", "skipped"}
STOCK_ALL_REFRESH_SCHEDULE_TIME = "15:30"
STOCK_ALL_REFRESH_TIMEZONE = "Asia/Shanghai"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedStockRange:
    """股票行情查询日期范围。"""

    range_type: str
    start_date: str
    end_date: str


class StockMarketService:
    """组织股票市场搜索、懒加载和详情 payload。"""

    def __init__(
        self,
        repository: StockMarketRepository | None = None,
        sync_service: StockMarketSyncService | None = None,
        market_history_store: MarketHistoryStore | None = None,
        refresh_state_path: str | Path | None = None,
        enable_scheduler: bool = False,
        scheduler_check_seconds: float | None = None,
    ) -> None:
        """初始化股票市场业务服务。

        Args:
            repository: 股票市场仓储。
            sync_service: AkShare 同步服务。
            market_history_store: 宽基指数历史仓储。
            refresh_state_path: 全标的刷新每日限次状态文件路径。
            enable_scheduler: 是否启动 15:30 自动刷新检查线程。
            scheduler_check_seconds: 后台定时检查间隔秒数。

        Returns:
            股票市场服务实例。
        """

        self._repository = repository or StockMarketRepository()
        self._sync_service = sync_service or StockMarketSyncService(repository=self._repository)
        self._market_history_store = market_history_store or MarketHistoryStore()
        self._refresh_state_path = Path(refresh_state_path or ".data/stock_market_refresh_state.json")
        self._all_refresh_lock = threading.Lock()
        self._all_refresh_jobs: dict[str, dict[str, Any]] = {}
        self._latest_all_refresh_job_id: str | None = None
        self._all_refresh_thread: threading.Thread | None = None
        self._scheduler_check_seconds = max(
            5.0,
            float(
                scheduler_check_seconds
                if scheduler_check_seconds is not None
                else os.getenv("STOCK_MARKET_SCHEDULER_CHECK_SECONDS", "20")
            ),
        )
        self._scheduler_stop_event = threading.Event()
        self._scheduler_thread: threading.Thread | None = None
        if enable_scheduler:
            self.start_scheduler()

    def start_scheduler(self) -> None:
        """启动股票市场后台定时刷新检查线程。"""

        if self._scheduler_thread is not None:
            return
        self._scheduler_stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="stock-market-refresh-scheduler",
            daemon=True,
        )
        self._scheduler_thread.start()

    def stop_scheduler(self) -> None:
        """停止股票市场定时器和当前刷新线程。"""

        self._scheduler_stop_event.set()
        if self._scheduler_thread is not None:
            self._scheduler_thread.join(timeout=2.0)
            self._scheduler_thread = None
        if self._all_refresh_thread is not None:
            self._all_refresh_thread.join(timeout=2.0)
            self._all_refresh_thread = None

    def _scheduler_loop(self) -> None:
        """循环检查 15:30 自动刷新触发条件。"""

        while not self._scheduler_stop_event.wait(self._scheduler_check_seconds):
            try:
                self.run_due_scheduled_refresh()
            except Exception as error:  # pragma: no cover - 后台防御日志
                logger.warning("stock market scheduler loop failed: %s", error)

    def run_due_scheduled_refresh(
        self,
        *,
        now: datetime | None = None,
        run_inline: bool = False,
    ) -> list[dict[str, Any]]:
        """在上海时间 15:30 触发全标的刷新。

        Args:
            now: 测试可注入的当前 UTC 时间。
            run_inline: 测试模式下同步执行任务。

        Returns:
            本轮触发的任务结果列表；未到时间返回空列表。
        """

        current_time = now or datetime.now(UTC)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        local_time = current_time.astimezone(ZoneInfo(STOCK_ALL_REFRESH_TIMEZONE))
        if local_time.strftime("%H:%M") != STOCK_ALL_REFRESH_SCHEDULE_TIME:
            return []
        return [self.start_all_instrument_refresh(trigger="scheduled", run_inline=run_inline)]

    def start_all_instrument_refresh(
        self,
        *,
        trigger: str = "manual",
        run_inline: bool = False,
    ) -> dict[str, Any]:
        """启动全标的近一月行情、概况和财务刷新任务。

        Args:
            trigger: `manual` 或 `scheduled`，用于前端展示和状态追踪。
            run_inline: 测试模式下同步执行任务。

        Returns:
            可供前端轮询的任务状态。
        """

        today_text = self._local_today()
        with self._all_refresh_lock:
            for existing_job in self._all_refresh_jobs.values():
                if existing_job["status"] not in STOCK_ALL_REFRESH_TERMINAL_STATUSES:
                    return {"job": self._public_all_refresh_job(existing_job)}
            if self._load_refresh_state().get("last_refresh_date") == today_text:
                job = self._new_all_refresh_job(
                    trigger=trigger,
                    status="skipped",
                    message=f"{today_text} 今日已完成全标的刷新，每天最多执行一次。",
                )
                job["completed"] = job["total"]
                job["percentage"] = 100
                self._all_refresh_jobs[job["id"]] = job
                self._latest_all_refresh_job_id = job["id"]
                return {"job": self._public_all_refresh_job(job)}
            job = self._new_all_refresh_job(trigger=trigger)
            self._all_refresh_jobs[job["id"]] = job
            self._latest_all_refresh_job_id = job["id"]

        if run_inline:
            self._run_all_instrument_refresh(job["id"])
        else:
            self._all_refresh_thread = threading.Thread(
                target=self._run_all_instrument_refresh,
                args=(job["id"],),
                name=f"stock-market-all-refresh-{job['id'][:8]}",
                daemon=True,
            )
            self._all_refresh_thread.start()
        return self.get_all_instrument_refresh(job["id"])

    def get_all_instrument_refresh(self, job_id: str) -> dict[str, Any]:
        """读取指定全标的刷新任务状态。

        Args:
            job_id: 启动接口返回的任务 ID。

        Returns:
            可公开给前端展示的任务状态。

        Raises:
            KeyError: 任务不存在。
        """

        with self._all_refresh_lock:
            job = self._all_refresh_jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return {"job": self._public_all_refresh_job(job)}

    def get_latest_all_instrument_refresh(self) -> dict[str, Any]:
        """读取最近一次全标的刷新任务，供前端复用定时任务进度条。"""

        with self._all_refresh_lock:
            job = self._all_refresh_jobs.get(self._latest_all_refresh_job_id or "")
            return {
                "job": self._public_all_refresh_job(job) if job else None,
                "state": deepcopy(self._load_refresh_state()),
            }

    def _run_all_instrument_refresh(self, job_id: str) -> None:
        """逐标的执行外部数据同步并持续更新进度。"""

        end = date.today()
        start = _shift_months(end, -1)
        instruments = self._load_all_refresh_instruments()
        with self._all_refresh_lock:
            job = self._all_refresh_jobs[job_id]
            job["status"] = "running"
            job["total"] = len(instruments)
            job["message"] = "正在刷新全部标的近 1 个月行情、概况和财务数据。"
            job["started_at"] = _utc_now()
        try:
            for index, instrument in enumerate(instruments, start=1):
                self._update_all_refresh_progress(
                    job_id,
                    completed=index - 1,
                    total=len(instruments),
                    instrument=instrument,
                    message=f"正在刷新 {instrument.name}。",
                )
                errors = self._refresh_single_instrument(instrument, start=start, end=end)
                with self._all_refresh_lock:
                    job = self._all_refresh_jobs[job_id]
                    for error in errors:
                        if error not in job["errors"]:
                            job["errors"].append(error)
                self._update_all_refresh_progress(
                    job_id,
                    completed=index,
                    total=len(instruments),
                    instrument=instrument,
                    message=f"{instrument.name} 刷新完成。",
                )
            with self._all_refresh_lock:
                job = self._all_refresh_jobs[job_id]
                job["completed"] = job["total"]
                job["percentage"] = 100
                job["finished_at"] = _utc_now()
                if job["errors"]:
                    job["status"] = "completed_with_warnings"
                    job["message"] = "全标的刷新完成，部分标的失败，已保留旧数据。"
                else:
                    job["status"] = "completed"
                    job["message"] = "全标的近 1 个月行情、概况和财务数据已刷新。"
                self._save_refresh_state(
                    {
                        "last_refresh_date": self._local_today(),
                        "last_refresh_at": job["finished_at"],
                        "last_trigger": job["trigger"],
                    }
                )
        except Exception as error:  # pragma: no cover - 后台任务兜底
            logger.exception("stock market all refresh failed", extra={"job_id": job_id})
            with self._all_refresh_lock:
                job = self._all_refresh_jobs[job_id]
                job["status"] = "failed"
                job["finished_at"] = _utc_now()
                job["message"] = f"全标的刷新失败：{_compact_error_message(error)}"
                job["errors"].append(str(error))

    def build_overview_payload(self) -> dict[str, Any]:
        """构建股票市场摘要，单项缺失时保留其余可用数据。

        Returns:
            包含 Push Center 默认宽基指数注册表和市场宽度的稳定前端契约。
        """

        indices = [
            self._build_index_overview(index.symbol, index.display_name)
            for index in STOCK_OVERVIEW_INDEX_REGISTRY
        ]
        try:
            breadth = self._repository.load_market_breadth()
        except Exception as error:
            logger.warning("stock market breadth unavailable: %s", error)
            breadth = {
                "trade_date": None,
                "advanced": 0,
                "declined": 0,
                "unchanged": 0,
                "total": 0,
                "status": "unavailable",
            }
        return {
            "generated_at": _utc_now(),
            "indices": indices,
            "breadth": breadth,
        }

    def _build_index_overview(self, symbol: str, display_name: str) -> dict[str, Any]:
        """构建单个宽基指数的最近收盘变化。"""

        try:
            points = self._market_history_store.load_latest_points(symbol=symbol, limit=2)
        except Exception as error:
            logger.warning("stock index overview unavailable for %s: %s", symbol, error)
            points = []
        try:
            history_points = self._market_history_store.load_points(
                symbol=symbol,
                end_date=date.today(),
                window_days=STOCK_OVERVIEW_INDEX_HISTORY_DAYS,
            )
        except Exception as error:
            logger.warning("stock index kline history unavailable for %s: %s", symbol, error)
            history_points = []
        if len(points) < 2:
            return {
                "symbol": symbol,
                "display_name": display_name,
                "close": None,
                "change": None,
                "change_pct": None,
                "trade_date": None,
                "status": "unavailable",
                "daily_bars": self._index_daily_bars(history_points),
            }
        previous, latest = points[-2], points[-1]
        change = latest.close_price - previous.close_price
        change_pct = (change / previous.close_price * 100) if previous.close_price else None
        return {
            "symbol": symbol,
            "display_name": display_name,
            "close": latest.close_price,
            "change": round(change, 4),
            "change_pct": change_pct,
            "trade_date": latest.trade_date.isoformat(),
            "status": "live",
            "daily_bars": self._index_daily_bars(history_points),
        }

    def _index_daily_bars(self, points: list[Any]) -> list[dict[str, Any]]:
        """将 Push Center 收盘历史转换为前端 K 线图可复用的日线结构。

        Args:
            points: MarketHistoryStore 读取的宽基指数收盘历史。

        Returns:
            与股票 K 线组件兼容的日线数组；Push Center 不保存 OHLC 时，开盘价使用前一交易日收盘价。
        """

        closes = [float(point.close_price) for point in points]
        bars: list[dict[str, Any]] = []
        previous_close: float | None = None
        for index, point in enumerate(points):
            close_price = float(point.close_price)
            open_price = previous_close if previous_close is not None else close_price
            bars.append(
                {
                    "date": point.trade_date.isoformat(),
                    "open": open_price,
                    "close": close_price,
                    "high": max(open_price, close_price),
                    "low": min(open_price, close_price),
                    "volume": float(point.volume) if isinstance(point.volume, (int, float)) else 0.0,
                    "ma5": _moving_average(closes, index, 5),
                    "ma10": _moving_average(closes, index, 10),
                    "ma20": _moving_average(closes, index, 20),
                    "ma60": _moving_average(closes, index, 60),
                    "ma120": _moving_average(closes, index, 120),
                    "pe_ttm": None,
                    "pb_mrq": None,
                    "dividend_yield_ttm": None,
                    "total_market_cap": None,
                }
            )
            previous_close = close_price
        return bars

    def sync_universe(self) -> dict[str, Any]:
        """手动同步 A 股和 ETF 标的列表。"""

        counts = self._sync_service.sync_universe()
        return {
            "ok": True,
            "counts": {key: value for key, value in counts.items() if key != "warnings"},
            "warnings": counts.get("warnings", []),
        }

    def build_instruments_payload(
        self,
        *,
        query: str = "",
        instrument_type: str = "all",
        market_board: str = "all",
        listing_status: str = "all",
        limit: int = 100,
        offset: int = 0,
        ensure_universe: bool = True,
    ) -> dict[str, Any]:
        """返回股票列表筛选结果。

        Args:
            query: 股票代码或名称关键字。
            instrument_type: 股票/ETF 类型筛选。
            market_board: 市场板块筛选。
            listing_status: 上市状态筛选。
            limit: 分页条数。
            offset: 分页偏移。
            ensure_universe: 空库时是否尝试拉取全市场标的。

        Returns:
            前端股票列表 payload。
        """

        normalized_limit = max(1, min(limit, 200))
        normalized_offset = max(0, offset)
        universe_warning = ""
        if ensure_universe and self._repository.count_instruments() == 0:
            try:
                sync_result = self._sync_service.sync_universe()
                warnings = sync_result.get("warnings", [])
                if warnings:
                    universe_warning = "；".join(str(item) for item in warnings)
            except Exception as error:
                logger.warning("stock universe sync failed: %s", error)
                universe_warning = f"股票列表同步失败：{error}"
        items, total = self._repository.search_instruments(
            query=query,
            instrument_type=self._validate_filter(instrument_type, {"all", "stock", "etf"}, "invalid stock type"),
            market_board=market_board or "all",
            listing_status=self._validate_filter(listing_status, {"all", "listed"}, "invalid listing status"),
            limit=normalized_limit,
            offset=normalized_offset,
        )
        return {
            "generated_at": _utc_now(),
            "items": [self._instrument_payload(item) for item in items],
            "total": total,
            "limit": normalized_limit,
            "offset": normalized_offset,
            "universe_count": self._repository.count_instruments(),
            "warning_message": universe_warning,
        }

    def build_stock_detail_payload(
        self,
        symbol: str,
        *,
        range_type: str = "1m",
        start_date: str | None = None,
        end_date: str | None = None,
        financial_report_type: str = "quarterly",
    ) -> dict[str, Any]:
        """返回选中股票详情，并在首次无日线数据时懒加载近 1 个月。"""

        instrument = self._require_instrument(symbol)
        resolved_range = self._resolve_range(range_type=range_type, start_date=start_date, end_date=end_date)
        warning = ""
        if not self._repository.has_daily_bars(instrument.symbol):
            default_range = self._resolve_range(range_type="1m", start_date=None, end_date=None)
            try:
                self._sync_service.sync_symbol_window(
                    instrument,
                    start_date=date.fromisoformat(default_range.start_date),
                    end_date=date.fromisoformat(default_range.end_date),
                )
            except Exception as error:
                warning = f"首次行情同步失败：{_compact_error_message(error)}"
                logger.warning("stock lazy daily sync failed for %s: %s", instrument.symbol, warning)
                self._repository.record_sync_warning(instrument.symbol, warning)
        self._ensure_profile_and_financials(instrument)
        return self._build_detail_payload(
            instrument,
            resolved_range=resolved_range,
            financial_report_type=financial_report_type,
            warning_message=warning,
        )

    def refresh_stock_detail(
        self,
        symbol: str,
        *,
        range_type: str = "1m",
        start_date: str | None = None,
        end_date: str | None = None,
        financial_report_type: str = "quarterly",
    ) -> dict[str, Any]:
        """手动刷新选中日期范围内的日线与财务数据并返回详情。"""

        instrument = self._require_instrument(symbol)
        resolved_range = self._resolve_range(range_type=range_type, start_date=start_date, end_date=end_date)
        warnings: list[str] = []
        result = {"daily_bars": 0}
        try:
            result = self._sync_service.sync_symbol_window(
                instrument,
                start_date=date.fromisoformat(resolved_range.start_date),
                end_date=date.fromisoformat(resolved_range.end_date),
            )
        except Exception as error:
            warning = f"行情刷新失败：{_compact_error_message(error)}"
            warnings.append(warning)
            logger.warning("stock daily refresh failed for %s: %s", instrument.symbol, warning)
            self._repository.record_sync_warning(instrument.symbol, warning)
        if instrument.instrument_type == "stock":
            try:
                result.update(self._sync_service.sync_financials(instrument))
            except Exception as error:
                warning = f"财报刷新失败：{_compact_error_message(error)}"
                warnings.append(warning)
                logger.warning("stock financial refresh failed for %s: %s", instrument.symbol, warning)
                self._repository.record_sync_warning(instrument.symbol, warning)
        self._ensure_profile_and_financials(instrument, ensure_financials=False)
        payload = self._build_detail_payload(
            instrument,
            resolved_range=resolved_range,
            financial_report_type=financial_report_type,
            warning_message="；".join(warnings),
        )
        payload["refresh_result"] = result
        return payload

    def _load_all_refresh_instruments(self) -> list[StockInstrument]:
        """按分页读取全部上市标的，避免一次性加载超大结果集。

        Returns:
            当前库内全部上市股票和 ETF 标的。
        """

        instruments: list[StockInstrument] = []
        page_size = 200
        offset = 0
        while True:
            items, total = self._repository.search_instruments(
                query="",
                instrument_type="all",
                market_board="all",
                listing_status="listed",
                limit=page_size,
                offset=offset,
            )
            instruments.extend(items)
            offset += page_size
            if offset >= total or not items:
                break
        return instruments

    def _refresh_single_instrument(
        self,
        instrument: StockInstrument,
        *,
        start: date,
        end: date,
    ) -> list[str]:
        """刷新单只标的的行情、概况和财务数据，单项失败不阻断后续标的。

        Args:
            instrument: 当前股票或 ETF 标的。
            start: 近一月窗口起始日期。
            end: 近一月窗口结束日期。

        Returns:
            本标的刷新过程中产生的短错误信息。
        """

        errors: list[str] = []
        try:
            self._sync_service.sync_symbol_window(instrument, start_date=start, end_date=end)
        except Exception as error:
            warning = f"{instrument.symbol} 行情刷新失败：{_compact_error_message(error)}"
            logger.warning("stock all refresh daily failed for %s: %s", instrument.symbol, warning)
            self._repository.record_sync_warning(instrument.symbol, warning)
            errors.append(warning)
        try:
            self._sync_service.sync_profile(instrument)
        except Exception as error:
            warning = f"{instrument.symbol} 概况刷新失败：{_compact_error_message(error)}"
            logger.warning("stock all refresh profile failed for %s: %s", instrument.symbol, warning)
            self._repository.record_sync_warning(instrument.symbol, warning)
            errors.append(warning)
        if instrument.instrument_type == "stock":
            try:
                self._sync_service.sync_financials(instrument)
            except Exception as error:
                warning = f"{instrument.symbol} 财务刷新失败：{_compact_error_message(error)}"
                logger.warning("stock all refresh financial failed for %s: %s", instrument.symbol, warning)
                self._repository.record_sync_warning(instrument.symbol, warning)
                errors.append(warning)
        return errors

    def _update_all_refresh_progress(
        self,
        job_id: str,
        *,
        completed: int,
        total: int,
        instrument: StockInstrument,
        message: str,
    ) -> None:
        """更新全标的刷新任务的公开进度字段。"""

        safe_total = max(1, total)
        with self._all_refresh_lock:
            job = self._all_refresh_jobs[job_id]
            job["status"] = "running"
            job["completed"] = min(max(0, completed), safe_total)
            job["total"] = total
            job["percentage"] = round((job["completed"] / safe_total) * 100)
            job["current_symbol"] = instrument.symbol
            job["current_label"] = instrument.name
            job["message"] = message

    def _new_all_refresh_job(
        self,
        *,
        trigger: str,
        status: str = "pending",
        message: str = "刷新任务已创建，等待后台执行。",
    ) -> dict[str, Any]:
        """创建全标的刷新任务状态对象。"""

        return {
            "id": uuid4().hex,
            "status": status,
            "trigger": trigger,
            "completed": 0,
            "total": self._repository.count_instruments(),
            "percentage": 0,
            "current_symbol": "",
            "current_label": "",
            "message": message,
            "errors": [],
            "started_at": "",
            "finished_at": "",
        }

    def _public_all_refresh_job(self, job: dict[str, Any] | None) -> dict[str, Any] | None:
        """复制任务字段，避免前端拿到内部可变对象。"""

        return deepcopy(job) if job is not None else None

    def _local_today(self) -> str:
        """返回上海时区当天日期，作为每日限次键。"""

        return date.today().isoformat()

    def _load_refresh_state(self) -> dict[str, Any]:
        """读取全标的刷新每日限次状态文件。"""

        try:
            with self._refresh_state_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError):
            payload = {}
        return dict(payload) if isinstance(payload, dict) else {}

    def _save_refresh_state(self, payload: dict[str, Any]) -> None:
        """原子写入全标的刷新每日限次状态文件。"""

        self._refresh_state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._refresh_state_path.with_suffix(f"{self._refresh_state_path.suffix}.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        temp_path.replace(self._refresh_state_path)

    def _build_detail_payload(
        self,
        instrument: StockInstrument,
        *,
        resolved_range: ResolvedStockRange,
        financial_report_type: str,
        warning_message: str,
    ) -> dict[str, Any]:
        """组装前端股票详情 payload。"""

        report_type = self._validate_filter(
            financial_report_type,
            STOCK_FINANCIAL_REPORT_TYPES,
            "invalid financial report type",
        )
        daily_bars = self._repository.load_daily_bars(
            symbol=instrument.symbol,
            start_date=resolved_range.start_date,
            end_date=resolved_range.end_date,
        )
        profile = self._repository.get_profile(instrument.symbol)
        sync_state = self._repository.get_sync_state(instrument.symbol)
        financial_metrics = self._repository.load_financial_metrics(symbol=instrument.symbol, report_type=report_type)
        return {
            "generated_at": _utc_now(),
            "instrument": self._instrument_payload(instrument),
            "range": {
                "type": resolved_range.range_type,
                "start_date": resolved_range.start_date,
                "end_date": resolved_range.end_date,
            },
            "daily_bars": [
                {
                    "date": bar.trade_date,
                    "open": bar.open_price,
                    "close": bar.close_price,
                    "high": bar.high_price,
                    "low": bar.low_price,
                    "volume": bar.volume,
                    "ma5": bar.ma5,
                    "ma10": bar.ma10,
                    "ma20": bar.ma20,
                    "ma60": bar.ma60,
                    "ma120": bar.ma120,
                    "pe_ttm": bar.pe_ttm,
                    "pb_mrq": bar.pb_mrq,
                    "dividend_yield_ttm": bar.dividend_yield_ttm,
                    "total_market_cap": (
                        round(bar.total_market_cap / 100_000_000, 4)
                        if bar.total_market_cap is not None
                        else None
                    ),
                }
                for bar in daily_bars
            ],
            "profile": {
                "company_name": profile.company_name if profile else instrument.name,
                "industry": profile.industry if profile else "",
                "sector": profile.sector if profile else instrument.market_board,
                "region": profile.region if profile else "",
                "listing_date": profile.listing_date if profile else "",
                "attributes": profile.attributes if profile else [],
                "summary": profile.summary if profile else "",
                "updated_at": profile.updated_at if profile else "",
            },
            "financials": self._financial_payload(financial_metrics, report_type),
            "sync_state": {
                "latest_trade_date": sync_state.latest_trade_date if sync_state else None,
                "earliest_trade_date": sync_state.earliest_trade_date if sync_state else None,
                "daily_point_count": sync_state.daily_point_count if sync_state else 0,
                "profile_status": sync_state.profile_status if sync_state else "unavailable",
                "financial_status": sync_state.financial_status if sync_state else "unavailable",
                "warning_message": warning_message or (sync_state.warning_message if sync_state else ""),
                "synced_at": sync_state.synced_at if sync_state else "",
            },
        }

    def _ensure_profile_and_financials(
        self,
        instrument: StockInstrument,
        *,
        ensure_financials: bool = True,
    ) -> None:
        """按需补齐概况和财报，失败时保留详情主体可用。

        Args:
            instrument: 当前股票或 ETF 标的。
            ensure_financials: 是否检查并补采缺失的股票财务指标。

        Returns:
            无返回值。
        """

        if self._repository.get_profile(instrument.symbol) is None:
            try:
                self._sync_service.sync_profile(instrument)
            except Exception as error:
                warning = f"公司概况同步失败：{_compact_error_message(error)}"
                logger.warning("stock profile sync failed for %s: %s", instrument.symbol, warning)
                self._repository.record_sync_warning(instrument.symbol, warning)
        if (
            ensure_financials
            and instrument.instrument_type == "stock"
            and not self._repository.has_financial_metrics(
                instrument.symbol,
                required_metrics=STOCK_REQUIRED_FINANCIAL_METRICS,
            )
        ):
            try:
                self._sync_service.sync_financials(instrument)
            except Exception as error:
                warning = f"财报同步失败：{_compact_error_message(error)}"
                logger.warning("stock financial sync failed for %s: %s", instrument.symbol, warning)
                self._repository.record_sync_warning(instrument.symbol, warning)

    def _financial_payload(self, metrics: list[Any], report_type: str) -> dict[str, Any]:
        """将财务指标列表按指标分组成图表友好的结构。"""

        metric_order = [
            "revenue",
            "expense",
            "cash_flow",
            "asset",
            "liability",
            "roe",
            "revenue_yoy",
            "net_profit_yoy",
            "debt_asset_ratio",
        ]
        label_by_metric = {
            "revenue": "营业收入",
            "expense": "营业支出",
            "cash_flow": "经营活动现金流",
            "asset": "资产合计",
            "liability": "负债合计",
            "roe": "ROE",
            "revenue_yoy": "营收同比",
            "net_profit_yoy": "净利润同比",
            "debt_asset_ratio": "资产负债率",
        }
        points_by_metric: dict[str, list[dict[str, Any]]] = {metric: [] for metric in metric_order}
        for item in metrics:
            points_by_metric.setdefault(item.metric, []).append({
                "period": item.report_period,
                "value": item.value,
                "unit": item.unit,
            })
        return {
            "report_type": report_type,
            "unit": "亿元",
            "series": [
                {
                    "metric": metric,
                    "label": label_by_metric.get(metric, metric),
                    "points": points_by_metric.get(metric, []),
                }
                for metric in metric_order
            ],
        }

    def _require_instrument(self, symbol: str) -> StockInstrument:
        """校验并读取股票标的。"""

        normalized_symbol = symbol.strip().upper()
        instrument = self._repository.get_instrument(normalized_symbol)
        if instrument is None:
            raise StockMarketValidationError("unknown stock symbol")
        return instrument

    def _resolve_range(
        self,
        *,
        range_type: str,
        start_date: str | None,
        end_date: str | None,
    ) -> ResolvedStockRange:
        """解析股票行情时间范围。"""

        if range_type not in STOCK_MARKET_RANGES:
            raise StockMarketValidationError("invalid stock range")
        today = date.today()
        if range_type == "custom":
            if not start_date or not end_date:
                raise StockMarketValidationError("custom range requires start_date and end_date")
            start = self._parse_date(start_date)
            end = self._parse_date(end_date)
        else:
            end = today
            months_by_range = {"1m": 1, "3m": 3, "6m": 6, "1y": 12, "3y": 36, "5y": 60}
            start = _shift_months(end, -months_by_range[range_type])
        if start > end:
            raise StockMarketValidationError("start date must be before end date")
        return ResolvedStockRange(range_type=range_type, start_date=start.isoformat(), end_date=end.isoformat())

    def _parse_date(self, raw_value: str) -> date:
        """解析 ISO 日期字符串。"""

        try:
            return date.fromisoformat(raw_value)
        except ValueError as error:
            raise StockMarketValidationError("invalid stock date") from error

    def _validate_filter(self, value: str, allowed_values: set[str], message: str) -> str:
        """校验枚举型筛选字段。"""

        normalized = value.strip() if isinstance(value, str) else ""
        if normalized not in allowed_values:
            raise StockMarketValidationError(message)
        return normalized

    def _instrument_payload(self, instrument: StockInstrument) -> dict[str, Any]:
        """转换股票标的为前端 payload。"""

        return {
            "symbol": instrument.symbol,
            "code": instrument.code,
            "exchange": instrument.exchange,
            "name": instrument.name,
            "instrument_type": instrument.instrument_type,
            "market_board": instrument.market_board,
            "listing_status": instrument.listing_status,
            "updated_at": instrument.updated_at,
            "latest_price": instrument.latest_price,
        }


def _utc_now() -> str:
    """返回当前 UTC ISO 字符串。"""

    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _shift_months(value: date, months: int) -> date:
    """按月份偏移日期，保持月底有效性。"""

    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    days_in_month = [31, 29 if _is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(value.day, days_in_month[month - 1]))


def _is_leap_year(year: int) -> bool:
    """判断闰年。"""

    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _moving_average(values: list[float], index: int, window: int) -> float | None:
    """计算指定窗口的简单移动均线。

    Args:
        values: 按日期升序排列的收盘价。
        index: 当前点位下标。
        window: 均线窗口大小。

    Returns:
        窗口不足时返回 None，否则返回四位小数均线。
    """

    if index + 1 < window:
        return None
    window_values = values[index - window + 1:index + 1]
    return round(sum(window_values) / window, 4)
