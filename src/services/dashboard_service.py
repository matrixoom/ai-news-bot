"""Dashboard service that provides shared view models for web and push layers."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import List

from ..domain.external_data import NewsCategory
from ..providers import (
    AkshareMacroDataProvider,
    AkshareMarketDataProvider,
    ArkResearchProvider,
    FallbackMacroProvider,
    FallbackMarketDataProvider,
    FallbackNewsProvider,
    FallbackResearchProvider,
    FallbackSearchProvider,
    GoogleNewsSearchProvider,
    ProviderAvailability,
    PublicRssNewsProvider,
    SampleMacroProvider,
    SampleMarketDataProvider,
    SampleNewsProvider,
    SampleResearchProvider,
    SampleSearchProvider,
)
from .events_outlook_service import EventsOutlookService
from .macro_monitoring_service import MacroMonitoringService
from .market_monitoring_service import MarketMonitoringService
from .news_pipeline_service import NewsPipelineService


@dataclass(frozen=True)
class DashboardSection:
    """Legacy-compatible summary section retained for early migration tests."""

    key: str
    title: str
    status: str
    description: str


@dataclass(frozen=True)
class SummaryBlock:
    """Top summary content for the homepage."""

    title: str
    subtitle: str
    as_of_label: str
    coverage_note: str
    highlights: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class NewsItemView:
    """Headline item rendered in a news column."""

    title: str
    source: str
    published_at: str
    tag: str


@dataclass(frozen=True)
class NewsSectionView:
    """A category-specific news section for the homepage."""

    key: str
    title: str
    status: str
    description: str
    items: List[NewsItemView] = field(default_factory=list)


@dataclass(frozen=True)
class MetricCard:
    """Macro indicator card rendered in the dashboard shell."""

    key: str
    label: str
    value: str
    context: str
    status: str
    previous_value: str = "Unavailable"
    change_label: str = "Change unavailable"
    trend: str = "unavailable"
    source_label: str = "Unavailable"
    updated_at: str = "Unavailable"
    frequency: str = "unavailable"


@dataclass(frozen=True)
class MarketCard:
    """Market model card rendered in the dashboard shell."""

    key: str
    label: str
    close_value: str
    ma20_value: str
    signal: str
    status: str
    trade_date: str = "Unavailable"
    deviation_pct: str = "Unavailable"
    source_label: str = "Unavailable"
    explanation: str = "Unavailable"


@dataclass(frozen=True)
class EventItemView:
    """Single upcoming event row."""

    title: str
    time_window: str
    confidence: str
    source: str


@dataclass(frozen=True)
class EventSectionView:
    """Grouped future events for one horizon bucket."""

    key: str
    title: str
    status: str
    items: List[EventItemView] = field(default_factory=list)


@dataclass(frozen=True)
class DataStatusItem:
    """Operational status for one data domain."""

    key: str
    label: str
    status: str
    detail: str


@dataclass(frozen=True)
class DashboardSnapshot:
    """Structured dashboard data shared across the web and push entrypoints."""

    generated_at: str
    title: str
    summary: str
    sections: List[DashboardSection]
    dashboard_summary: SummaryBlock
    news_sections: List[NewsSectionView]
    macro_sections: List[MetricCard]
    market_sections: List[MarketCard]
    event_sections: List[EventSectionView]
    data_status: List[DataStatusItem]


class DashboardService:
    """Compose the dashboard from news, macro, market, and events services."""

    def __init__(
        self,
        news_service: NewsPipelineService | None = None,
        macro_service: MacroMonitoringService | None = None,
        market_service: MarketMonitoringService | None = None,
        events_service: EventsOutlookService | None = None,
        *,
        prefer_live_data: bool = False,
    ) -> None:
        self._prefer_live_data = prefer_live_data
        self._news_provider = None
        self._search_provider = None
        self._macro_provider = None
        self._market_provider = None
        self._research_provider = None

        if news_service is None:
            news_provider, search_provider = self._build_news_providers(prefer_live_data=prefer_live_data)
            self._news_provider = news_provider
            self._search_provider = search_provider
            self._news_service = NewsPipelineService(
                news_provider=news_provider,
                search_provider=search_provider,
            )
        else:
            self._news_service = news_service

        if macro_service is None:
            macro_provider = self._build_macro_provider(prefer_live_data=prefer_live_data)
            self._macro_provider = macro_provider
            self._macro_service = MacroMonitoringService(macro_provider=macro_provider)
        else:
            self._macro_service = macro_service

        if market_service is None:
            market_provider = self._build_market_provider(prefer_live_data=prefer_live_data)
            self._market_provider = market_provider
            self._market_service = MarketMonitoringService(market_provider=market_provider)
        else:
            self._market_service = market_service

        if events_service is None:
            research_provider = self._build_research_provider(prefer_live_data=prefer_live_data)
            self._research_provider = research_provider
            self._events_service = EventsOutlookService(research_provider=research_provider)
        else:
            self._events_service = events_service

    def build_snapshot(self) -> DashboardSnapshot:
        """Return a structured dashboard snapshot composed from service outputs."""
        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        news_snapshot = self._news_service.build_snapshot()
        macro_snapshot = self._macro_service.build_snapshot()
        market_snapshot = self._market_service.build_snapshot()
        events_snapshot = self._events_service.build_snapshot()
        data_status = self._build_data_status()

        summary = SummaryBlock(
            title="Finance And Policy Intelligence Dashboard",
            subtitle="A compact homepage for finance, policy, macro, and market monitoring.",
            as_of_label=generated_at,
            coverage_note=self._coverage_note(data_status),
            highlights=self._summary_highlights(data_status),
        )

        title_by_category = {
            NewsCategory.TECHNOLOGY: "Technology News",
            NewsCategory.FINANCE: "Finance News",
            NewsCategory.POLICY: "Policy News",
        }
        news_sections = [
            NewsSectionView(
                key=digest.category.value,
                title=title_by_category[digest.category],
                status="live" if digest.items else "degraded",
                description=(
                    f"{digest.candidate_count} candidates, "
                    f"{digest.merged_duplicate_count} merges, "
                    f"{digest.dropped_outdated_count} outdated drops."
                ),
                items=[
                    NewsItemView(
                        title=item.title,
                        source=item.source_name,
                        published_at=item.published_at or "Unavailable",
                        tag=item.source_type.value,
                    )
                    for item in digest.items[:3]
                ],
            )
            for digest in news_snapshot.domains
        ]

        macro_sections = [
            MetricCard(
                key=item.key,
                label=item.label,
                value=item.value,
                context=item.context,
                status=item.status,
                previous_value=item.previous_value,
                change_label=item.change_label,
                trend=item.trend.value,
                source_label=item.source_label,
                updated_at=item.updated_at,
                frequency=item.frequency.value,
            )
            for item in macro_snapshot.indicators
        ]

        market_sections = [
            MarketCard(
                key=item.key,
                label=item.label,
                close_value=item.close_value,
                ma20_value=item.ma20_value,
                signal=item.fishbowl_state.value,
                status=item.status,
                trade_date=item.trade_date,
                deviation_pct=item.deviation_pct,
                source_label=item.source_label,
                explanation=item.explanation,
            )
            for item in market_snapshot.items
        ]

        event_sections = [
            EventSectionView(
                key=window.key,
                title=window.title,
                status=window.status,
                items=[
                    EventItemView(
                        title=item.title,
                        time_window=item.time_window,
                        confidence=item.confidence.value,
                        source=item.source,
                    )
                    for item in window.items
                ],
            )
            for window in events_snapshot.windows
        ]

        sections = [
            DashboardSection("news", "News Intelligence", data_status[0].status, "Three-domain news pipeline is now service-backed."),
            DashboardSection("macro", "Macro Indicators", data_status[1].status, "Registry-driven macro cards include source and freshness metadata."),
            DashboardSection("market", "Market Models", data_status[2].status, "Fishbowl and MA20 outputs are reproducible and independent per symbol."),
            DashboardSection("events", "Events And Policy Outlook", data_status[3].status, "Outlook windows filter out low-confidence, weak-source findings."),
            DashboardSection("push", "Push Automation", "compatible", "Push report now consumes the shared dashboard snapshot."),
        ]

        return DashboardSnapshot(
            generated_at=generated_at,
            title=summary.title,
            summary=summary.subtitle,
            sections=sections,
            dashboard_summary=summary,
            news_sections=news_sections,
            macro_sections=macro_sections,
            market_sections=market_sections,
            event_sections=event_sections,
            data_status=data_status,
        )

    def _build_news_providers(self, *, prefer_live_data: bool):
        if not prefer_live_data:
            return SampleNewsProvider(), SampleSearchProvider()
        return (
            FallbackNewsProvider(PublicRssNewsProvider(), SampleNewsProvider()),
            FallbackSearchProvider(GoogleNewsSearchProvider(), SampleSearchProvider()),
        )

    def _build_macro_provider(self, *, prefer_live_data: bool):
        if not prefer_live_data:
            return SampleMacroProvider()
        return FallbackMacroProvider(AkshareMacroDataProvider(), SampleMacroProvider())

    def _build_market_provider(self, *, prefer_live_data: bool):
        if not prefer_live_data:
            return SampleMarketDataProvider()
        return FallbackMarketDataProvider(AkshareMarketDataProvider(), SampleMarketDataProvider())

    def _build_research_provider(self, *, prefer_live_data: bool):
        if not prefer_live_data:
            return SampleResearchProvider()
        return FallbackResearchProvider(ArkResearchProvider, SampleResearchProvider())

    def _build_data_status(self) -> List[DataStatusItem]:
        if not self._prefer_live_data:
            return [
                DataStatusItem("news", "News Pipeline", "sample", "Sample RSS and search data are rendered for local development."),
                DataStatusItem("macro", "Macro Monitoring", "sample", "Sample macro cards are rendered because live mode is disabled."),
                DataStatusItem("market", "Market Models", "sample", "Sample market snapshots are rendered because live mode is disabled."),
                DataStatusItem("events", "Events Outlook", "sample", "Sample events outlook is rendered because live mode is disabled."),
            ]

        news_status = self._combine_statuses(
            key="news",
            label="News Pipeline",
            statuses=[
                self._news_provider.healthcheck() if self._news_provider else None,
                self._search_provider.healthcheck() if self._search_provider else None,
            ],
        )
        macro_status = self._single_status("macro", "Macro Monitoring", self._macro_provider)
        market_status = self._single_status("market", "Market Models", self._market_provider)
        events_status = self._single_status("events", "Events Outlook", self._research_provider)
        return [news_status, macro_status, market_status, events_status]

    def _single_status(self, key: str, label: str, provider) -> DataStatusItem:
        if provider is None:
            return DataStatusItem(key, label, "unknown", "No provider status is available.")
        status = provider.healthcheck()
        return DataStatusItem(key, label, status.availability.value, status.detail)

    def _combine_statuses(self, *, key: str, label: str, statuses) -> DataStatusItem:
        available = [status for status in statuses if status is not None]
        if not available:
            return DataStatusItem(key, label, "unknown", "No provider status is available.")

        if any(status.availability == ProviderAvailability.DEGRADED for status in available):
            final_status = ProviderAvailability.DEGRADED.value
        elif all(status.availability == ProviderAvailability.LIVE for status in available):
            final_status = ProviderAvailability.LIVE.value
        else:
            final_status = available[0].availability.value

        detail = " | ".join(dict.fromkeys(status.detail for status in available))
        return DataStatusItem(key, label, final_status, detail)

    def _coverage_note(self, data_status: List[DataStatusItem]) -> str:
        if not self._prefer_live_data:
            return "The dashboard is running in sample-data mode for stable local development and tests."
        if any(item.status == ProviderAvailability.DEGRADED.value for item in data_status):
            return "The dashboard is running in live-first mode with automatic sample fallback for providers that are missing keys, dependencies, or reachable data."
        return "The dashboard is running in live-first mode and all configured providers reported live status on the latest fetch."

    def _summary_highlights(self, data_status: List[DataStatusItem]) -> List[str]:
        base = [
            "News, macro, market, and events are composed from dedicated services instead of hardcoded sections.",
            "The same dashboard snapshot powers both the homepage and the push report.",
        ]
        if not self._prefer_live_data:
            base.append("Runtime entrypoints can switch to live-first providers; tests continue to use deterministic sample data.")
            return base

        degraded = [item.label for item in data_status if item.status == ProviderAvailability.DEGRADED.value]
        if degraded:
            base.append("Automatic sample fallback is active for: " + ", ".join(degraded) + ".")
        else:
            base.append("All provider groups reported live status on the latest refresh.")
        return base
