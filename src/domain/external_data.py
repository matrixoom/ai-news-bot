"""Canonical external-data models shared by provider contracts and services."""
from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class NewsCategory(StrEnum):
    """Supported news domains for the first dashboard iteration."""

    TECHNOLOGY = "technology"
    FINANCE = "finance"
    POLICY = "policy"


class EventHorizon(StrEnum):
    """Supported event windows for policy and meeting outlook."""

    NEXT_7_DAYS = "7d"
    NEXT_30_DAYS = "30d"
    NEXT_90_DAYS = "90d"
    NEXT_180_DAYS = "180d"


class ConfidenceLevel(StrEnum):
    """Confidence tiers for research-backed event findings."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class SourceReference:
    """A source pointer that keeps provider outputs traceable."""

    title: str
    url: str
    published_at: str | None = None


@dataclass(frozen=True)
class NewsItem:
    """Normalized news item returned by a news provider."""

    provider: str
    source_name: str
    category: NewsCategory
    title: str
    url: str
    published_at: str
    summary: str | None = None


@dataclass(frozen=True)
class SearchResultItem:
    """Candidate news hit returned by a search provider."""

    provider: str
    query: str
    title: str
    snippet: str
    original_url: str
    published_at: str | None = None


@dataclass(frozen=True)
class MarketIndexSnapshot:
    """Raw market snapshot for a broad index on a trading day."""

    provider: str
    symbol: str
    display_name: str
    trade_date: date
    close_price: float
    currency: str
    source_url: str
    lookback_closes: tuple[float, ...] = ()


@dataclass(frozen=True)
class MacroIndicatorReading:
    """Normalized macro reading returned by a macro provider."""

    provider: str
    indicator_code: str
    display_name: str
    value: float
    unit: str
    period_label: str
    released_at: str
    source_url: str
    previous_value: float | None = None
    change_value: float | None = None
    change_kind: str | None = None
    trend_summary: str | None = None


@dataclass(frozen=True)
class ResearchFinding:
    """Structured event or policy finding backed by sources."""

    provider: str
    horizon: EventHorizon
    title: str
    region: str
    expected_date: str
    summary: str
    confidence: ConfidenceLevel
    sources: tuple[SourceReference, ...]
