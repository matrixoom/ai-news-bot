"""Service layer for frontend Macro Data payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from .macro_data_repository import MacroDataPoint, MacroDataRepository, MacroIndicatorDefinition


MACRO_DATA_TABS = {
    "gdp": "GDP",
    "credit": "信贷",
    "climate": "景气",
    "trade": "外贸",
    "prices": "物价",
    "currency": "货币",
    "expectations": "预期",
}

MACRO_DATA_RANGES = {"6m", "1y", "3y", "5y", "10y", "15y", "20y", "25y", "30y", "custom"}
MACRO_DATA_FREQUENCIES = {"monthly", "quarterly", "yearly"}
GDP_GROWTH_CHART_ID = "gdp_growth"
GDP_TOTAL_COMBINED_CHART_ID = "gdp_total_combined"
CURRENCY_SUPPLY_CHART_ID = "currency_supply"
NEW_RMB_LOANS_COMBINED_CHART_ID = "new_rmb_loans"
SOCIAL_FINANCING_CHART_ID = "social_financing"

_NEW_RMB_LOANS_SERIES = [
    {"indicator_id": "new_rmb_loans", "name": "新增人民币贷款总计"},
    {"indicator_id": "household_short_term_loans", "name": "居民新增短期贷款"},
    {"indicator_id": "household_long_term_loans", "name": "居民新增长期贷款"},
    {"indicator_id": "corporate_short_term_loans", "name": "企业新增短期贷款"},
    {"indicator_id": "corporate_long_term_loans", "name": "企业新增长期贷款"},
]

_CREDIT_CHART_ORDER = {
    "new_rmb_loans": 1,
    "social_financing": 2,
    "household_leverage_ratio": 3,
    "corporate_leverage_ratio": 4,
}

_CHART_SYNC_GROUPS: dict[str, str] = {
    "gdp_total_combined": "gdp",
    "gdp_growth": "gdp",
    "currency_supply": "currency",
    "cpi": "prices",
    "ppi": "prices",
    "manufacturing_pmi": "climate",
    "non_manufacturing_pmi": "climate",
    "comprehensive_pmi": "climate",
    "exports": "trade",
    "imports": "trade",
    "new_rmb_loans": "credit_breakdown",
    "social_financing": "credit",
    "household_leverage_ratio": "credit",
    "corporate_leverage_ratio": "credit",
    "china_10y_bond_yield": "expectations",
    "us_10y_bond_yield": "expectations",
    "usd_cny": "expectations",
    "us_credit_spread": "expectations",
}


@dataclass(frozen=True)
class ResolvedDateRange:
    """解析后的图表时间范围。

    Args:
        range_type: 原始范围类型。
        start_date: 起始日期。
        end_date: 结束日期。

    Returns:
        不返回值；该数据类用于 Service 与 Repository 之间传递范围。
    """

    range_type: str
    start_date: str
    end_date: str


class MacroDataValidationError(ValueError):
    """宏观数据参数校验错误。

    Args:
        message: 错误说明。

    Returns:
        异常对象；Controller 捕获后转换为用户安全的 400 响应。
    """


class MacroDataService:
    """组织 Macro Data 前端接口 payload。

    Args:
        repository: 宏观数据 SQLite 仓储；未传入时使用默认本地库。

    Returns:
        Service 实例。
    """

    def __init__(self, repository: MacroDataRepository | None = None) -> None:
        self._repository = repository or MacroDataRepository()

    def sync_chart(self, chart_id: str) -> dict[str, Any]:
        """触发图表对应的数据同步，返回同步结果。

        Args:
            chart_id: 图表指标 ID。

        Returns:
            含 ok 和 point_counts 的同步结果字典。
        """

        group = _CHART_SYNC_GROUPS.get(chart_id)
        if group is None:
            raise MacroDataValidationError("unknown chart id for sync")
        from .macro_data_sync_service import MacroDataSyncService

        syncer = MacroDataSyncService(repository=self._repository)
        sync_methods: dict[str, Any] = {
            "gdp": syncer.sync_gdp_history,
            "currency": syncer.sync_currency_history,
            "prices": syncer.sync_prices_history,
            "climate": syncer.sync_climate_history,
            "trade": syncer.sync_trade_history,
            "credit": syncer.sync_credit_history,
            "credit_breakdown": syncer.sync_credit_breakdown_history,
            "expectations": syncer.sync_expectations_history,
        }
        point_counts = sync_methods[group]()
        return {"ok": True, "point_counts": point_counts}

    def build_module_payload(self, tab: str = "gdp") -> dict[str, Any]:
        """构造模块元数据 payload。

        Args:
            tab: 当前分类标签。

        Returns:
            前端模块元数据与图表定义。
        """

        normalized_tab = self._validate_tab(tab)
        charts = self._repository.list_indicators(normalized_tab)
        chart_payloads = [self._chart_definition_payload(chart) for chart in charts]
        if normalized_tab == "gdp":
            chart_payloads = [c for c in chart_payloads if c["id"] not in ("nominal_gdp", "real_gdp")]
            chart_payloads.append(self._gdp_total_combined_definition_payload())
            chart_payloads.append(self._gdp_growth_definition_payload())
        if normalized_tab == "currency":
            chart_payloads = [c for c in chart_payloads if c["id"] not in ("m0", "m1", "m2")]
            chart_payloads.append(self._currency_supply_definition_payload())
        if normalized_tab == "credit":
            chart_payloads = [
                c for c in chart_payloads
                if c["id"] not in ("new_rmb_loans", "household_short_term_loans", "household_long_term_loans",
                                   "corporate_short_term_loans", "corporate_long_term_loans")
            ]
            chart_payloads = [c for c in chart_payloads if c["id"] != "social_financing"]
            chart_payloads.insert(0, self._new_rmb_loans_combined_definition_payload())
            chart_payloads.insert(1, self._social_financing_wide_definition_payload())
            chart_payloads.sort(key=lambda c: _CREDIT_CHART_ORDER.get(c["id"], 99))
        return {
            "generated_at": _utc_now(),
            "module": {
                "id": "macro-data",
                "label": "Macro Data",
                "description": "GDP, credit, leverage, and inflation indicators",
                "status": "live",
                "loading": False,
            },
            "tabs": [
                {"value": value, "label": label}
                for value, label in MACRO_DATA_TABS.items()
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

    def build_chart_payload(
        self,
        chart_id: str,
        *,
        range_type: str = "1y",
        start_date: str | None = None,
        end_date: str | None = None,
        frequency: str | None = None,
    ) -> dict[str, Any]:
        """构造单张图表数据 payload。

        Args:
            chart_id: 图表指标 ID。
            range_type: 时间范围类型。
            start_date: 自定义范围起始日期。
            end_date: 自定义范围结束日期。
            frequency: 数据频率；未传入时使用指标默认频率。

        Returns:
            前端图表序列数据。
        """

        resolved_range = self._resolve_range(
            range_type=range_type,
            start_date=start_date,
            end_date=end_date,
        )
        if chart_id == GDP_GROWTH_CHART_ID:
            normalized_frequency = self._validate_frequency(frequency or "quarterly")
            return self._build_gdp_growth_payload(resolved_range, normalized_frequency)
        if chart_id == GDP_TOTAL_COMBINED_CHART_ID:
            normalized_frequency = self._validate_frequency(frequency or "quarterly")
            return self._build_gdp_total_combined_payload(resolved_range, normalized_frequency)
        if chart_id == CURRENCY_SUPPLY_CHART_ID:
            return self._build_currency_supply_payload(resolved_range)
        if chart_id == NEW_RMB_LOANS_COMBINED_CHART_ID:
            normalized_frequency = self._validate_frequency(frequency or "monthly")
            return self._build_new_rmb_loans_combined_payload(resolved_range, normalized_frequency)
        if chart_id == SOCIAL_FINANCING_CHART_ID and frequency in (None, "monthly"):
            normalized_frequency = self._validate_frequency(frequency or "monthly")
            return self._build_social_financing_wide_payload(resolved_range, normalized_frequency)

        definition = self._repository.get_indicator(chart_id)
        if definition is None:
            raise MacroDataValidationError("unknown chart id")
        normalized_frequency = self._validate_frequency(frequency or definition.frequency)
        points = self._repository.load_points(
            indicator_id=chart_id,
            start_date=resolved_range.start_date,
            end_date=resolved_range.end_date,
            frequency=normalized_frequency,
        )
        sync_state = self._repository.get_sync_state(chart_id)
        return {
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
            "sync_state": {
                "status": sync_state.status if sync_state else "unavailable",
                "synced_at": sync_state.synced_at if sync_state else "",
                "warning_message": sync_state.warning_message if sync_state else "",
                "point_count": sync_state.point_count if sync_state else 0,
            },
            "series": [
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
            ],
        }

    def _validate_tab(self, tab: str) -> str:
        """校验并归一化分类标签。

        Args:
            tab: 原始分类标签。

        Returns:
            允许的分类标签。
        """

        if tab not in MACRO_DATA_TABS:
            raise MacroDataValidationError("invalid macro data tab")
        return tab

    def _validate_frequency(self, frequency: str) -> str:
        """校验并归一化数据频率。

        Args:
            frequency: 原始频率值。

        Returns:
            允许的频率。
        """

        if frequency not in MACRO_DATA_FREQUENCIES:
            raise MacroDataValidationError("invalid macro data frequency")
        return frequency

    def _default_frequency_for_tab(self, tab: str) -> str:
        """返回标签页默认数据频率。

        Args:
            tab: 分类标签。

        Returns:
            默认频率字符串。
        """

        if tab == "gdp":
            return "quarterly"
        return "monthly"

    def _frequency_options_for_tab(self, tab: str) -> list[dict[str, str]]:
        """返回标签页可用的频率选项。

        Args:
            tab: 分类标签。

        Returns:
            频率选项列表，含 value 和 label。
        """

        if tab == "gdp":
            return [
                {"value": "quarterly", "label": "季度"},
                {"value": "yearly", "label": "年度"},
            ]
        return [
            {"value": "monthly", "label": "月度"},
            {"value": "quarterly", "label": "季度"},
            {"value": "yearly", "label": "年度"},
        ]

    def _resolve_range(
        self,
        *,
        range_type: str,
        start_date: str | None,
        end_date: str | None,
    ) -> ResolvedDateRange:
        """解析预设或自定义日期范围。

        Args:
            range_type: 时间范围类型。
            start_date: 自定义起始日期。
            end_date: 自定义结束日期。

        Returns:
            已解析的日期范围。
        """

        if range_type not in MACRO_DATA_RANGES:
            raise MacroDataValidationError("invalid macro data range")
        today = date.today()
        if range_type == "custom":
            if not start_date or not end_date:
                raise MacroDataValidationError("custom range requires start_date and end_date")
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
            raise MacroDataValidationError("start date must be before end date")
        return ResolvedDateRange(range_type=range_type, start_date=start.isoformat(), end_date=end.isoformat())

    def _parse_date(self, raw_value: str) -> date:
        """解析标准日期字符串。

        Args:
            raw_value: `YYYY-MM-DD` 日期字符串。

        Returns:
            `date` 对象。
        """

        try:
            return date.fromisoformat(raw_value)
        except ValueError as error:
            raise MacroDataValidationError("invalid macro data date") from error

    def _chart_definition_payload(self, definition: MacroIndicatorDefinition) -> dict[str, Any]:
        """将指标定义映射为前端图表定义。

        Args:
            definition: 指标定义。

        Returns:
            前端可直接使用的图表定义字典。
        """

        return {
            "id": definition.indicator_id,
            "title": definition.title,
            "unit": definition.unit,
            "frequency": definition.frequency,
            "status": definition.status,
            "chart_type": "line",
        }

    def _gdp_growth_definition_payload(self) -> dict[str, Any]:
        """构造 GDP 增速派生图表定义。

        Returns:
            前端可直接使用的 GDP 增速图表定义。
        """

        return {
            "id": GDP_GROWTH_CHART_ID,
            "title": "GDP增速",
            "unit": "%",
            "frequency": "quarterly",
            "status": "sample",
            "chart_type": "line",
        }

    def _gdp_total_combined_definition_payload(self) -> dict[str, Any]:
        """构造名义与实际 GDP 总量合并图表定义。

        Returns:
            前端可直接使用的合并图表定义。
        """

        return {
            "id": GDP_TOTAL_COMBINED_CHART_ID,
            "title": "名义与实际GDP总量",
            "unit": "亿元",
            "frequency": "quarterly",
            "status": "sample",
            "chart_type": "line",
        }

    def _build_gdp_total_combined_payload(
        self, resolved_range: ResolvedDateRange, frequency: str
    ) -> dict[str, Any]:
        """合并名义 GDP 和实际 GDP 总量为单张图表。

        Args:
            resolved_range: 已解析的目标展示范围。
            frequency: 数据频率。

        Returns:
            包含名义 GDP 和实际 GDP 两条序列的图表 payload。
        """

        nominal_points = self._repository.load_points(
            indicator_id="nominal_gdp",
            start_date=resolved_range.start_date,
            end_date=resolved_range.end_date,
            frequency=frequency,
        )
        real_points = self._repository.load_points(
            indicator_id="real_gdp",
            start_date=resolved_range.start_date,
            end_date=resolved_range.end_date,
            frequency=frequency,
        )
        nominal_payload_points = self._points_payload(nominal_points, resolved_range)
        real_payload_points = self._points_payload(real_points, resolved_range)
        sync_state = self._combined_gdp_total_sync_state(nominal_payload_points, real_payload_points)

        return {
            **self._gdp_total_combined_definition_payload(),
            "frequency": frequency,
            "range": {
                "type": resolved_range.range_type,
                "start_date": resolved_range.start_date,
                "end_date": resolved_range.end_date,
            },
            "sync_state": sync_state,
            "series": [
                {"name": "名义GDP", "points": nominal_payload_points},
                {"name": "实际GDP", "points": real_payload_points},
            ],
        }

    def _combined_gdp_total_sync_state(
        self,
        nominal_points: list[dict[str, Any]],
        real_points: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """合并名义与实际 GDP 总量图表的源数据同步状态。

        Args:
            nominal_points: 名义 GDP 点位。
            real_points: 实际 GDP 点位。

        Returns:
            前端展示用同步状态。
        """

        nominal_state = self._repository.get_sync_state("nominal_gdp")
        real_state = self._repository.get_sync_state("real_gdp")
        states = [state for state in [nominal_state, real_state] if state is not None]
        warning_messages = [state.warning_message for state in states if state.warning_message]
        return {
            "status": states[0].status if states else "unavailable",
            "synced_at": max((state.synced_at for state in states), default=""),
            "warning_message": "；".join(warning_messages),
            "point_count": len(nominal_points) + len(real_points),
        }

    def _build_gdp_growth_payload(self, resolved_range: ResolvedDateRange, frequency: str) -> dict[str, Any]:
        """基于名义和实际 GDP 总量构造同比增速图表。

        Args:
            resolved_range: 已解析的目标展示范围。

        Returns:
            包含名义 GDP 增速和实际 GDP 增速两条序列的图表 payload。
        """

        range_start = date.fromisoformat(resolved_range.start_date)
        lookback_start = _shift_months(range_start, -12).isoformat()
        nominal_growth_points = self._repository.load_points(
            indicator_id="nominal_gdp_growth",
            start_date=lookback_start,
            end_date=resolved_range.end_date,
            frequency=frequency,
        )
        real_growth_points = self._repository.load_points(
            indicator_id="real_gdp_growth",
            start_date=lookback_start,
            end_date=resolved_range.end_date,
            frequency=frequency,
        )
        if nominal_growth_points:
            nominal_payload_points = self._points_payload(nominal_growth_points, resolved_range)
        else:
            nominal_total_points = self._repository.load_points(
                indicator_id="nominal_gdp",
                start_date=lookback_start,
                end_date=resolved_range.end_date,
                frequency=frequency,
            )
            nominal_payload_points = self._year_over_year_growth_points(nominal_total_points, resolved_range)
        if real_growth_points:
            real_payload_points = self._points_payload(real_growth_points, resolved_range)
        else:
            real_total_points = self._repository.load_points(
                indicator_id="real_gdp",
                start_date=lookback_start,
                end_date=resolved_range.end_date,
                frequency=frequency,
            )
            real_payload_points = self._year_over_year_growth_points(real_total_points, resolved_range)
        sync_state = self._combined_gdp_growth_sync_state(nominal_payload_points, real_payload_points)

        return {
            **self._gdp_growth_definition_payload(),
            "frequency": frequency,
            "range": {
                "type": resolved_range.range_type,
                "start_date": resolved_range.start_date,
                "end_date": resolved_range.end_date,
            },
            "sync_state": sync_state,
            "series": [
                {"name": "名义GDP增速", "points": nominal_payload_points},
                {"name": "实际GDP增速", "points": real_payload_points},
            ],
        }

    def _points_payload(
        self,
        points: list[MacroDataPoint],
        resolved_range: ResolvedDateRange,
    ) -> list[dict[str, Any]]:
        """将已持久化点位限制到目标范围并映射为前端点位。

        Args:
            points: Repository 返回的点位。
            resolved_range: 目标展示范围。

        Returns:
            前端图表点位列表。
        """

        start = date.fromisoformat(resolved_range.start_date)
        end = date.fromisoformat(resolved_range.end_date)
        return [
            {
                "date": point.period_end,
                "period_label": point.period_label,
                "value": point.value,
                "unit": point.unit,
                "released_at": point.released_at,
            }
            for point in points
            if start <= date.fromisoformat(point.period_end) <= end
        ]

    def _year_over_year_growth_points(
        self,
        points: list[MacroDataPoint],
        resolved_range: ResolvedDateRange,
    ) -> list[dict[str, Any]]:
        """按同周期上一年计算同比增速点位。

        Args:
            points: 含目标范围与前置一年窗口的源总量点位。
            resolved_range: 目标展示范围。

        Returns:
            落在目标范围内的同比增速点位列表。
        """

        start = date.fromisoformat(resolved_range.start_date)
        end = date.fromisoformat(resolved_range.end_date)
        point_by_date = {point.period_end: point for point in points}
        growth_points: list[dict[str, Any]] = []
        for point in points:
            current_date = date.fromisoformat(point.period_end)
            if current_date < start or current_date > end:
                continue
            previous_date = _shift_months(current_date, -12).isoformat()
            previous_point = point_by_date.get(previous_date)
            if previous_point is None or previous_point.value == 0:
                continue
            growth_value = round((point.value / previous_point.value - 1) * 100, 2)
            growth_points.append(
                {
                    "date": point.period_end,
                    "period_label": point.period_label,
                    "value": growth_value,
                    "unit": "%",
                    "released_at": point.released_at,
                }
            )
        return growth_points

    def _combined_gdp_growth_sync_state(
        self,
        nominal_growth_points: list[dict[str, Any]],
        real_growth_points: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """合并 GDP 增速派生图表的源数据同步状态。

        Args:
            nominal_growth_points: 名义 GDP 增速点位。
            real_growth_points: 实际 GDP 增速点位。

        Returns:
            前端展示用同步状态。
        """

        nominal_state = self._repository.get_sync_state("nominal_gdp_growth") or self._repository.get_sync_state("nominal_gdp")
        real_state = self._repository.get_sync_state("real_gdp_growth") or self._repository.get_sync_state("real_gdp")
        states = [state for state in [nominal_state, real_state] if state is not None]
        warning_messages = [state.warning_message for state in states if state.warning_message]
        return {
            "status": states[0].status if states else "unavailable",
            "synced_at": max((state.synced_at for state in states), default=""),
            "warning_message": "；".join(warning_messages),
            "point_count": len(nominal_growth_points) + len(real_growth_points),
        }

    def _currency_supply_definition_payload(self) -> dict[str, Any]:
        """构造货币供应量派生图表定义。

        Returns:
            前端可直接使用的货币供应量图表定义。
        """

        return {
            "id": CURRENCY_SUPPLY_CHART_ID,
            "title": "货币供应量",
            "unit": "亿元",
            "frequency": "monthly",
            "status": "sample",
        }

    def _build_currency_supply_payload(
        self, resolved_range: ResolvedDateRange
    ) -> dict[str, Any]:
        """合并 M0、M1、M2 为单张图表。

        Args:
            resolved_range: 已解析的目标展示范围。

        Returns:
            包含 M0、M1、M2 三条序列的图表 payload。
        """

        m0_points = self._repository.load_points(
            indicator_id="m0",
            start_date=resolved_range.start_date,
            end_date=resolved_range.end_date,
            frequency="monthly",
        )
        m1_points = self._repository.load_points(
            indicator_id="m1",
            start_date=resolved_range.start_date,
            end_date=resolved_range.end_date,
            frequency="monthly",
        )
        m2_points = self._repository.load_points(
            indicator_id="m2",
            start_date=resolved_range.start_date,
            end_date=resolved_range.end_date,
            frequency="monthly",
        )
        m0_payload_points = self._points_payload(m0_points, resolved_range)
        m1_payload_points = self._points_payload(m1_points, resolved_range)
        m2_payload_points = self._points_payload(m2_points, resolved_range)
        sync_state = self._combined_currency_sync_state(
            m0_payload_points, m1_payload_points, m2_payload_points
        )

        return {
            **self._currency_supply_definition_payload(),
            "frequency": "monthly",
            "range": {
                "type": resolved_range.range_type,
                "start_date": resolved_range.start_date,
                "end_date": resolved_range.end_date,
            },
            "sync_state": sync_state,
            "series": [
                {"name": "M0", "points": m0_payload_points},
                {"name": "M1", "points": m1_payload_points},
                {"name": "M2", "points": m2_payload_points},
            ],
        }

    def _combined_currency_sync_state(
        self,
        m0_points: list[dict[str, Any]],
        m1_points: list[dict[str, Any]],
        m2_points: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """合并货币供应量图表的源数据同步状态。

        Args:
            m0_points: M0 点位。
            m1_points: M1 点位。
            m2_points: M2 点位。

        Returns:
            前端展示用同步状态。
        """

        m0_state = self._repository.get_sync_state("m0")
        m1_state = self._repository.get_sync_state("m1")
        m2_state = self._repository.get_sync_state("m2")
        states = [state for state in [m0_state, m1_state, m2_state] if state is not None]
        warning_messages = [state.warning_message for state in states if state.warning_message]
        return {
            "status": states[0].status if states else "unavailable",
            "synced_at": max((state.synced_at for state in states), default=""),
            "warning_message": "；".join(warning_messages),
            "point_count": len(m0_points) + len(m1_points) + len(m2_points),
        }

    def _new_rmb_loans_combined_definition_payload(self) -> dict[str, Any]:
        """构造新增人民币贷款合并图表定义（总量虚线 + 4 条堆叠柱）。

        Returns:
            前端可直接使用的图表定义，含 wide 布局标记。
        """

        return {
            "id": NEW_RMB_LOANS_COMBINED_CHART_ID,
            "title": "新增人民币贷款",
            "unit": "亿元",
            "frequency": "monthly",
            "status": "sample",
            "chart_type": "bar_stacked_line",
            "wide": True,
        }

    def _social_financing_wide_definition_payload(self) -> dict[str, Any]:
        """构造社会融资规模宽图表定义。

        Returns:
            前端可直接使用的图表定义，含 wide 布局标记。
        """

        return {
            "id": SOCIAL_FINANCING_CHART_ID,
            "title": "社会融资规模",
            "unit": "亿元",
            "frequency": "monthly",
            "status": "sample",
            "chart_type": "line",
            "wide": True,
        }

    def _build_new_rmb_loans_combined_payload(
        self, resolved_range: ResolvedDateRange, frequency: str
    ) -> dict[str, Any]:
        """合并新增人民币贷款总计及居民/企业短期/长期贷款为单张图表。

        Args:
            resolved_range: 已解析的目标展示范围。
            frequency: 数据频率。

        Returns:
            包含 5 条序列的图表 payload。
        """

        series: list[dict[str, Any]] = []
        all_points: list[dict[str, Any]] = []
        for series_def in _NEW_RMB_LOANS_SERIES:
            points = self._repository.load_points(
                indicator_id=series_def["indicator_id"],
                start_date=resolved_range.start_date,
                end_date=resolved_range.end_date,
                frequency=frequency,
            )
            payload_points = self._points_payload(points, resolved_range)
            series.append({"name": series_def["name"], "points": payload_points})
            all_points.extend(payload_points)

        sync_state = self._combined_credit_breakdown_sync_state()
        return {
            **self._new_rmb_loans_combined_definition_payload(),
            "frequency": frequency,
            "range": {
                "type": resolved_range.range_type,
                "start_date": resolved_range.start_date,
                "end_date": resolved_range.end_date,
            },
            "sync_state": sync_state,
            "series": series,
        }

    def _build_social_financing_wide_payload(
        self, resolved_range: ResolvedDateRange, frequency: str
    ) -> dict[str, Any]:
        """构造社会融资规模宽图表数据。

        Args:
            resolved_range: 已解析的目标展示范围。
            frequency: 数据频率。

        Returns:
            单系列宽图表 payload。
        """

        points = self._repository.load_points(
            indicator_id="social_financing",
            start_date=resolved_range.start_date,
            end_date=resolved_range.end_date,
            frequency=frequency,
        )
        payload_points = self._points_payload(points, resolved_range)
        sync_state = self._repository.get_sync_state("social_financing")
        return {
            **self._social_financing_wide_definition_payload(),
            "frequency": frequency,
            "range": {
                "type": resolved_range.range_type,
                "start_date": resolved_range.start_date,
                "end_date": resolved_range.end_date,
            },
            "sync_state": {
                "status": sync_state.status if sync_state else "unavailable",
                "synced_at": sync_state.synced_at if sync_state else "",
                "warning_message": sync_state.warning_message if sync_state else "",
                "point_count": sync_state.point_count if sync_state else 0,
            },
            "series": [
                {"name": "社会融资规模", "points": payload_points},
            ],
        }

    def _combined_credit_breakdown_sync_state(self) -> dict[str, Any]:
        """合并贷款细分指标四表的同步状态。

        Returns:
            前端展示用同步状态。
        """

        indicator_ids = [s["indicator_id"] for s in _NEW_RMB_LOANS_SERIES]
        states = [
            state
            for iid in indicator_ids
            if (state := self._repository.get_sync_state(iid)) is not None
        ]
        warning_messages = [s.warning_message for s in states if s.warning_message]
        return {
            "status": states[0].status if states else "unavailable",
            "synced_at": max((s.synced_at for s in states), default=""),
            "warning_message": "；".join(warning_messages),
            "point_count": sum(s.point_count for s in states),
        }


def _utc_now() -> str:
    """返回当前 UTC 时间。

    Returns:
        ISO 8601 UTC 时间字符串。
    """

    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _shift_months(value: date, months: int) -> date:
    """按月偏移日期，并处理月底越界。

    Args:
        value: 原始日期。
        months: 月份偏移量，可为负数。

    Returns:
        偏移后的日期。
    """

    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    days_in_month = [31, 29 if _is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(value.day, days_in_month[month - 1]))


def _is_leap_year(year: int) -> bool:
    """判断是否闰年。

    Args:
        year: 年份。

    Returns:
        闰年返回 True，否则返回 False。
    """

    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
