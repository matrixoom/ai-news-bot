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


@dataclass(frozen=True)
class MarketMonitoringSnapshot:
    """Top-level market monitoring snapshot."""

    generated_at: str
    items: List[MarketModelView] = field(default_factory=list)


def build_default_market_registry() -> Dict[str, TrackedIndexDefinition]:
    """Return the default tracked-index registry for Task 06."""
    definitions = (
        TrackedIndexDefinition("CSI300", "CSI 300", "AKShare / Exchange", "CNY"),
        TrackedIndexDefinition("CSI500", "CSI 500", "AKShare / Exchange", "CNY"),
        TrackedIndexDefinition("CSI1000", "CSI 1000", "AKShare / Exchange", "CNY"),
        TrackedIndexDefinition("SSE", "SSE Composite", "AKShare / Exchange", "CNY"),
        TrackedIndexDefinition("CHINEXT", "ChiNext", "AKShare / Exchange", "CNY"),
        TrackedIndexDefinition("HSTECH", "Hang Seng Tech", "AKShare / Exchange", "HKD"),
    )
    return {definition.symbol: definition for definition in definitions}
