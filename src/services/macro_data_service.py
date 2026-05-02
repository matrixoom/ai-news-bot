"""Service layer for frontend Macro Data payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from .macro_data_repository import MacroDataPoint, MacroDataRepository, MacroIndicatorDefinition


MACRO_DATA_TABS = {
    "gdp": "GDP",
    "credit": "信贷",
    "leverage": "杠杆率",
    "prices": "物价",
}

MACRO_DATA_RANGES = {"6m", "1y", "3y", "5y", "10y", "custom"}
GDP_GROWTH_CHART_ID = "gdp_growth"


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
            chart_payloads.append(self._gdp_growth_definition_payload())
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
            "range_options": [
                {"value": "6m", "label": "半年"},
                {"value": "1y", "label": "一年"},
                {"value": "3y", "label": "三年"},
                {"value": "5y", "label": "5年"},
                {"value": "10y", "label": "10年"},
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
    ) -> dict[str, Any]:
        """构造单张图表数据 payload。

        Args:
            chart_id: 图表指标 ID。
            range_type: 时间范围类型。
            start_date: 自定义范围起始日期。
            end_date: 自定义范围结束日期。

        Returns:
            前端图表序列数据。
        """

        resolved_range = self._resolve_range(
            range_type=range_type,
            start_date=start_date,
            end_date=end_date,
        )
        if chart_id == GDP_GROWTH_CHART_ID:
            return self._build_gdp_growth_payload(resolved_range)

        definition = self._repository.get_indicator(chart_id)
        if definition is None:
            raise MacroDataValidationError("unknown chart id")
        points = self._repository.load_points(
            indicator_id=chart_id,
            start_date=resolved_range.start_date,
            end_date=resolved_range.end_date,
        )
        sync_state = self._repository.get_sync_state(chart_id)
        return {
            "id": definition.indicator_id,
            "title": definition.title,
            "unit": definition.unit,
            "frequency": definition.frequency,
            "status": definition.status,
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
            months_by_range = {"6m": 6, "1y": 12, "3y": 36, "5y": 60, "10y": 120}
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
        }

    def _build_gdp_growth_payload(self, resolved_range: ResolvedDateRange) -> dict[str, Any]:
        """基于名义和实际 GDP 总量构造同比增速图表。

        Args:
            resolved_range: 已解析的目标展示范围。

        Returns:
            包含名义 GDP 增速和实际 GDP 增速两条序列的图表 payload。
        """

        range_start = date.fromisoformat(resolved_range.start_date)
        lookback_start = _shift_months(range_start, -12).isoformat()
        nominal_points = self._repository.load_points(
            indicator_id="nominal_gdp",
            start_date=lookback_start,
            end_date=resolved_range.end_date,
        )
        real_points = self._repository.load_points(
            indicator_id="real_gdp",
            start_date=lookback_start,
            end_date=resolved_range.end_date,
        )
        nominal_growth_points = self._year_over_year_growth_points(nominal_points, resolved_range)
        real_growth_points = self._year_over_year_growth_points(real_points, resolved_range)
        sync_state = self._combined_gdp_growth_sync_state(nominal_growth_points, real_growth_points)

        return {
            **self._gdp_growth_definition_payload(),
            "range": {
                "type": resolved_range.range_type,
                "start_date": resolved_range.start_date,
                "end_date": resolved_range.end_date,
            },
            "sync_state": sync_state,
            "series": [
                {"name": "名义GDP增速", "points": nominal_growth_points},
                {"name": "实际GDP增速", "points": real_growth_points},
            ],
        }

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

        nominal_state = self._repository.get_sync_state("nominal_gdp")
        real_state = self._repository.get_sync_state("real_gdp")
        states = [state for state in [nominal_state, real_state] if state is not None]
        warning_messages = [state.warning_message for state in states if state.warning_message]
        return {
            "status": states[0].status if states else "unavailable",
            "synced_at": max((state.synced_at for state in states), default=""),
            "warning_message": "；".join(warning_messages),
            "point_count": len(nominal_growth_points) + len(real_growth_points),
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
