"""Domain models for market models and daily dashboard output."""
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Dict, List


class FishbowlState(StrEnum):
    """Simple, reproducible fishbowl states."""

    BREAKOUT = "breakout"
    CONSTRUCTIVE = "constructive"
    NEUTRAL = "neutral"
    PRESSURED = "pressured"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class TrackedIndexDefinition:
    """Registry definition for one tracked market index."""

    symbol: str
    display_name: str
    source_label: str
    currency: str


@dataclass(frozen=True)
class MarketChartPoint:
    """日报图表可直接使用的市场历史点。"""

    trade_date: str
    close_price: float
    ma20_price: float | None
    deviation_pct: float | None
    volume: float | None = None


@dataclass(frozen=True)
class MarketModelView:
    """Dashboard-facing market model card."""

    key: str
    label: str
    trade_date: str
    close_value: str
    ma20_value: str
    deviation_pct: str
    fishbowl_state: FishbowlState
    explanation: str
    source_label: str
    status: str
    data_window_label: str = ""
    history_warning: str = ""
    chart_points: List[MarketChartPoint] = field(default_factory=list)


@dataclass(frozen=True)
class MarketMonitoringSnapshot:
    """Top-level market monitoring snapshot."""

    generated_at: str
    items: List[MarketModelView] = field(default_factory=list)


def build_default_market_registry() -> Dict[str, TrackedIndexDefinition]:
    """Return the default tracked-index registry for Task 06."""
    definitions = (
        TrackedIndexDefinition("CSI300", "沪深 300", "AKShare / 交易所", "CNY"),
        TrackedIndexDefinition("CSI500", "中证 500", "AKShare / 交易所", "CNY"),
        TrackedIndexDefinition("CSI1000", "中证 1000", "AKShare / 交易所", "CNY"),
        TrackedIndexDefinition("SSE", "上证综指", "AKShare / 交易所", "CNY"),
        TrackedIndexDefinition("SZSE", "深证成指", "AKShare / 交易所", "CNY"),
        TrackedIndexDefinition("CHINEXT", "创业板指", "AKShare / 交易所", "CNY"),
        TrackedIndexDefinition("HSTECH", "恒生科技指数", "AKShare / 交易所", "HKD"),
    )
    return {definition.symbol: definition for definition in definitions}
