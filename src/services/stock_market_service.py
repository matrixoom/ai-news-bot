"""Market Data 股票市场页面业务服务。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
from typing import Any

from .stock_market_repository import (
    StockInstrument,
    StockMarketRepository,
    StockMarketValidationError,
)
from .stock_market_sync_service import StockMarketSyncService


STOCK_MARKET_RANGES = {"1m", "3m", "6m", "1y", "3y", "5y", "custom"}
STOCK_FINANCIAL_REPORT_TYPES = {"quarterly", "yearly"}
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
    ) -> None:
        """初始化股票市场业务服务。

        Args:
            repository: 股票市场仓储。
            sync_service: AkShare 同步服务。

        Returns:
            股票市场服务实例。
        """

        self._repository = repository or StockMarketRepository()
        self._sync_service = sync_service or StockMarketSyncService(repository=self._repository)

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
        range_type: str = "3m",
        start_date: str | None = None,
        end_date: str | None = None,
        financial_report_type: str = "quarterly",
    ) -> dict[str, Any]:
        """返回选中股票详情，并在首次无日线数据时懒加载近 3 个月。"""

        instrument = self._require_instrument(symbol)
        resolved_range = self._resolve_range(range_type=range_type, start_date=start_date, end_date=end_date)
        warning = ""
        if not self._repository.has_daily_bars(instrument.symbol):
            default_range = self._resolve_range(range_type="3m", start_date=None, end_date=None)
            try:
                self._sync_service.sync_symbol_window(
                    instrument,
                    start_date=date.fromisoformat(default_range.start_date),
                    end_date=date.fromisoformat(default_range.end_date),
                )
            except Exception as error:
                logger.exception("stock lazy daily sync failed", extra={"symbol": instrument.symbol})
                warning = f"首次行情同步失败：{error}"
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
        range_type: str = "3m",
        start_date: str | None = None,
        end_date: str | None = None,
        financial_report_type: str = "quarterly",
    ) -> dict[str, Any]:
        """手动刷新选中日期范围内的日线数据并返回详情。"""

        instrument = self._require_instrument(symbol)
        resolved_range = self._resolve_range(range_type=range_type, start_date=start_date, end_date=end_date)
        result = self._sync_service.sync_symbol_window(
            instrument,
            start_date=date.fromisoformat(resolved_range.start_date),
            end_date=date.fromisoformat(resolved_range.end_date),
        )
        self._ensure_profile_and_financials(instrument)
        payload = self._build_detail_payload(
            instrument,
            resolved_range=resolved_range,
            financial_report_type=financial_report_type,
            warning_message="",
        )
        payload["refresh_result"] = result
        return payload

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

    def _ensure_profile_and_financials(self, instrument: StockInstrument) -> None:
        """按需补齐概况和财报，失败时保留详情主体可用。"""

        if self._repository.get_profile(instrument.symbol) is None:
            try:
                self._sync_service.sync_profile(instrument)
            except Exception as error:
                logger.exception("stock profile sync failed", extra={"symbol": instrument.symbol})
                self._repository.record_sync_warning(instrument.symbol, f"公司概况同步失败：{error}")
        if instrument.instrument_type == "stock" and not self._repository.has_financial_metrics(instrument.symbol):
            try:
                self._sync_service.sync_financials(instrument)
            except Exception as error:
                logger.exception("stock financial sync failed", extra={"symbol": instrument.symbol})
                self._repository.record_sync_warning(instrument.symbol, f"财报同步失败：{error}")

    def _financial_payload(self, metrics: list[Any], report_type: str) -> dict[str, Any]:
        """将财务指标列表按指标分组成图表友好的结构。"""

        metric_order = ["revenue", "expense", "cash_flow", "asset", "liability"]
        label_by_metric = {
            "revenue": "营业收入",
            "expense": "营业支出",
            "cash_flow": "经营活动现金流",
            "asset": "资产合计",
            "liability": "负债合计",
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
