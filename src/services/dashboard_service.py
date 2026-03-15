"""Dashboard service that provides shared view models for web and push layers."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import List


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
    """Macro indicator or similar metric card."""

    key: str
    label: str
    value: str
    context: str
    status: str


@dataclass(frozen=True)
class MarketCard:
    """Market model card rendered in the dashboard shell."""

    key: str
    label: str
    close_value: str
    ma20_value: str
    signal: str
    status: str


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
    """Provide the dashboard snapshot for the Task 03 homepage shell."""

    def build_snapshot(self) -> DashboardSnapshot:
        """Return a richer structured dashboard snapshot for Task 03."""
        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        summary = SummaryBlock(
            title="Finance And Policy Intelligence Dashboard",
            subtitle="A compact homepage for finance, policy, macro, and market monitoring.",
            as_of_label=generated_at,
            coverage_note="Task 03 uses structured sample data while Task 04-07 connect live providers.",
            highlights=[
                "Shared ViewModel now powers both HTML and JSON outputs.",
                "News, macro, market, and event panels already have stable section keys.",
                "Data-source health and freshness are visible in the shell.",
            ],
        )

        news_sections = [
            NewsSectionView(
                key="technology",
                title="Technology News",
                status="sample-data",
                description="Initial headlines placeholder for the future news intelligence pipeline.",
                items=[
                    NewsItemView(
                        title="Model platform releases move from demos to operating workflows",
                        source="Sample feed",
                        published_at="Today",
                        tag="AI tooling",
                    ),
                    NewsItemView(
                        title="Chip and cloud vendors keep AI infrastructure spending elevated",
                        source="Sample feed",
                        published_at="Today",
                        tag="Compute",
                    ),
                ],
            ),
            NewsSectionView(
                key="finance",
                title="Finance News",
                status="sample-data",
                description="Finance headlines will converge on the same normalized provider contract.",
                items=[
                    NewsItemView(
                        title="Risk appetite stays selective as macro prints and policy signals diverge",
                        source="Sample feed",
                        published_at="Today",
                        tag="Macro risk",
                    ),
                    NewsItemView(
                        title="Market participants focus on liquidity, growth, and sector rotation",
                        source="Sample feed",
                        published_at="Today",
                        tag="Allocation",
                    ),
                ],
            ),
            NewsSectionView(
                key="policy",
                title="Policy News",
                status="sample-data",
                description="Policy coverage is modeled separately because it requires higher-trust source controls.",
                items=[
                    NewsItemView(
                        title="Upcoming policy communication windows remain the key watchpoint",
                        source="Sample feed",
                        published_at="Today",
                        tag="Policy outlook",
                    ),
                    NewsItemView(
                        title="Official releases and top-tier media will anchor future policy monitoring",
                        source="Sample feed",
                        published_at="Today",
                        tag="Source quality",
                    ),
                ],
            ),
        ]

        macro_sections = [
            MetricCard(
                key="cpi",
                label="CPI",
                value="Sample 0.3%",
                context="Official source planned as primary; AKShare reserved as fallback.",
                status="provider-planned",
            ),
            MetricCard(
                key="ppi",
                label="PPI",
                value="Sample -1.2%",
                context="Release cadence and revision handling will be normalized in Task 05.",
                status="provider-planned",
            ),
            MetricCard(
                key="gdp",
                label="Nominal GDP",
                value="Sample Q/Q",
                context="Macro cards keep units and period labels in the view model.",
                status="provider-planned",
            ),
        ]

        market_sections = [
            MarketCard(
                key="csi300",
                label="CSI 300 Fishbowl",
                close_value="Sample 3,620",
                ma20_value="Sample 3,580",
                signal="Above MA20",
                status="model-placeholder",
            ),
            MarketCard(
                key="hsi",
                label="Hang Seng Trend",
                close_value="Sample 18,420",
                ma20_value="Sample 18,610",
                signal="Below MA20",
                status="model-placeholder",
            ),
        ]

        event_sections = [
            EventSectionView(
                key="next_7_days",
                title="Next 7 Days",
                status="research-planned",
                items=[
                    EventItemView(
                        title="Central-bank communication window",
                        time_window="Next 7 days",
                        confidence="medium",
                        source="Official calendar placeholder",
                    ),
                ],
            ),
            EventSectionView(
                key="next_30_days",
                title="Next 30 Days",
                status="research-planned",
                items=[
                    EventItemView(
                        title="Macro release cluster and policy briefing watchlist",
                        time_window="Next 30 days",
                        confidence="medium",
                        source="Official agenda placeholder",
                    ),
                ],
            ),
        ]

        data_status = [
            DataStatusItem(
                key="news",
                label="News Providers",
                status="sample",
                detail="Task 04 will replace sample headlines with normalized RSS and search data.",
            ),
            DataStatusItem(
                key="macro",
                label="Macro Providers",
                status="planned",
                detail="Official sources defined as primary with stale-cache fallback.",
            ),
            DataStatusItem(
                key="market",
                label="Market Providers",
                status="planned",
                detail="AKShare-backed snapshots will feed model calculations after Task 06.",
            ),
            DataStatusItem(
                key="events",
                label="Research Providers",
                status="planned",
                detail="Only source-backed events will be promoted into the dashboard.",
            ),
        ]

        sections = [
            DashboardSection(
                key="news",
                title="News Intelligence",
                status="sample-data",
                description="Tech, finance, and policy sections are now visible in the homepage shell.",
            ),
            DashboardSection(
                key="macro",
                title="Macro Indicators",
                status="provider-planned",
                description="Macro cards already use a stable shape for future official-source ingestion.",
            ),
            DashboardSection(
                key="market",
                title="Market Models",
                status="model-placeholder",
                description="Market cards expose close, MA20, and signal fields for future calculations.",
            ),
            DashboardSection(
                key="events",
                title="Events And Policy Outlook",
                status="research-planned",
                description="Event windows now have a dedicated section contract and source-confidence slots.",
            ),
            DashboardSection(
                key="push",
                title="Push Automation",
                status="compatible",
                description="Legacy push flow remains isolated under the jobs layer.",
            ),
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
