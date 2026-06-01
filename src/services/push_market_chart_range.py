"""Push Center 宽基指数图表时间范围定义。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PushMarketChartRange:
    """描述一个可用于推送图表展示和刷新的时间范围。"""

    value: str
    label: str
    short_label: str
    window_days: int


PUSH_MARKET_CHART_RANGES = {
    "3m": PushMarketChartRange("3m", "近3个月", "3M", 92),
    "6m": PushMarketChartRange("6m", "近6个月", "6M", 183),
    "1y": PushMarketChartRange("1y", "近1年", "1Y", 366),
    "2y": PushMarketChartRange("2y", "近2年", "2Y", 731),
    "3y": PushMarketChartRange("3y", "近3年", "3Y", 1096),
}
DEFAULT_PUSH_MARKET_CHART_RANGE = "1y"


def resolve_push_market_chart_range(value: object) -> PushMarketChartRange:
    """返回合法范围；非法值直接失败，避免推送区间静默漂移。"""
    if value is None:
        normalized = DEFAULT_PUSH_MARKET_CHART_RANGE
    else:
        normalized = str(value).strip().lower()
        if isinstance(value, str) and not normalized:
            normalized = DEFAULT_PUSH_MARKET_CHART_RANGE
    try:
        return PUSH_MARKET_CHART_RANGES[normalized]
    except KeyError as error:
        raise ValueError(f"unsupported market_chart_range: {normalized}") from error
