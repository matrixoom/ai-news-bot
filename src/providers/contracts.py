"""Provider contracts for external data sources."""
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol, Sequence, runtime_checkable

from ..domain.external_data import (
    EventHorizon,
    MacroIndicatorSeries,
    MacroIndicatorReading,
    MarketIndexSnapshot,
    NewsCategory,
    NewsItem,
    ResearchFinding,
    SearchResultItem,
)


class ProviderAvailability(StrEnum):
    """Availability levels returned by provider health checks."""

    LIVE = "live"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ProviderStatus:
    """Health status shared by all providers."""

    provider_key: str
    availability: ProviderAvailability
    detail: str
    checked_at: str


@runtime_checkable
class NewsProvider(Protocol):
    """Contract for normalized news ingestion providers."""

    provider_key: str

    def fetch_latest(
        self,
        *,
        category: NewsCategory,
        published_on: date,
        limit: int,
    ) -> Sequence[NewsItem]:
        """Fetch normalized news items for one category and target date."""

    def healthcheck(self) -> ProviderStatus:
        """Return current provider availability."""


@runtime_checkable
class SearchProvider(Protocol):
    """Contract for auxiliary search-based enrichment."""

    provider_key: str

    def search(
        self,
        *,
        query: str,
        published_on: date,
        limit: int,
    ) -> Sequence[SearchResultItem]:
        """Return normalized search hits for a query and target date."""

    def healthcheck(self) -> ProviderStatus:
        """Return current provider availability."""


@runtime_checkable
class MarketDataProvider(Protocol):
    """Contract for broad index snapshots."""

    provider_key: str

    def fetch_index_snapshots(
        self,
        *,
        symbols: Sequence[str],
        trade_date: date,
    ) -> Sequence[MarketIndexSnapshot]:
        """Return normalized broad-index snapshots for one trade date."""

    def healthcheck(self) -> ProviderStatus:
        """Return current provider availability."""


@runtime_checkable
class MacroDataProvider(Protocol):
    """Contract for macro-indicator ingestion."""

    provider_key: str

    def fetch_latest_readings(
        self,
        *,
        indicator_codes: Sequence[str],
    ) -> Sequence[MacroIndicatorReading]:
        """Return normalized macro readings for requested indicators."""

    def fetch_history_series(
        self,
        *,
        indicator_codes: Sequence[str],
        start_date: date,
    ) -> Sequence[MacroIndicatorSeries]:
        """Return normalized macro history series for requested indicators."""

    def healthcheck(self) -> ProviderStatus:
        """Return current provider availability."""


@runtime_checkable
class ResearchProvider(Protocol):
    """Contract for upcoming-event and policy research."""

    provider_key: str

    def collect_outlook(
        self,
        *,
        horizon: EventHorizon,
        topics: Sequence[str],
        as_of: date,
    ) -> Sequence[ResearchFinding]:
        """Return structured findings for one future time horizon."""

    def healthcheck(self) -> ProviderStatus:
        """Return current provider availability."""
