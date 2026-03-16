"""Domain models for events and policy outlook."""
from dataclasses import dataclass, field
from typing import List

from .external_data import ConfidenceLevel, EventHorizon


@dataclass(frozen=True)
class OutlookEventView:
    """Dashboard-facing outlook event row."""

    title: str
    category: str
    region: str
    expected_date: str
    time_window: str
    confidence: ConfidenceLevel
    impact_summary: str
    source: str


@dataclass(frozen=True)
class OutlookWindowView:
    """Windowed collection of upcoming events."""

    key: str
    title: str
    status: str
    items: List[OutlookEventView] = field(default_factory=list)


@dataclass(frozen=True)
class EventsOutlookSnapshot:
    """Top-level outlook snapshot."""

    generated_at: str
    windows: List[OutlookWindowView] = field(default_factory=list)


def build_default_outlook_horizons() -> tuple[EventHorizon, ...]:
    """Return the fixed outlook windows for Task 07."""
    return (
        EventHorizon.NEXT_7_DAYS,
        EventHorizon.NEXT_30_DAYS,
        EventHorizon.NEXT_90_DAYS,
        EventHorizon.NEXT_180_DAYS,
    )
