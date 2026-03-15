"""Primary, fallback, and degradation strategy for external data providers."""
from dataclasses import dataclass
from enum import StrEnum


class StrategyCategory(StrEnum):
    """Top-level data categories tracked in the dashboard roadmap."""

    TECHNOLOGY_NEWS = "technology_news"
    FINANCE_NEWS = "finance_news"
    POLICY_NEWS = "policy_news"
    SEARCH_HOTSPOTS = "search_hotspots"
    MACRO_INDICATORS = "macro_indicators"
    BROAD_MARKET_INDICES = "broad_market_indices"
    EVENT_OUTLOOK = "event_outlook"


class FeasibilityLevel(StrEnum):
    """Design-time assessment of whether a free strategy is workable."""

    VIABLE = "viable"
    VIABLE_WITH_GUARDRAILS = "viable_with_guardrails"


@dataclass(frozen=True)
class SourcePlan:
    """A concrete source option used by one strategy category."""

    provider_key: str
    provider_contract: str
    source_name: str
    access_mode: str
    is_free: bool
    rationale: str
    risks: tuple[str, ...]


@dataclass(frozen=True)
class CategoryStrategy:
    """Primary, fallback, and degradation plan for one data category."""

    category: StrategyCategory
    provider_contract: str
    primary_source: SourcePlan
    fallback_sources: tuple[SourcePlan, ...]
    degradation_mode: str
    free_feasibility: FeasibilityLevel


def build_provider_strategy() -> tuple[CategoryStrategy, ...]:
    """Return the design-phase strategy for all critical data categories."""

    return (
        CategoryStrategy(
            category=StrategyCategory.TECHNOLOGY_NEWS,
            provider_contract="NewsProvider",
            primary_source=SourcePlan(
                provider_key="news_rss_primary",
                provider_contract="NewsProvider",
                source_name="Public RSS feeds from tech media and official AI blogs",
                access_mode="rss",
                is_free=True,
                rationale="Low integration cost and already compatible with the legacy RSS fetcher.",
                risks=(
                    "published_at formats vary",
                    "duplicate content across syndication feeds",
                ),
            ),
            fallback_sources=(
                SourcePlan(
                    provider_key="news_rss_search_fallback",
                    provider_contract="NewsProvider",
                    source_name="Topic and query-based news RSS feeds",
                    access_mode="rss_search",
                    is_free=True,
                    rationale="Improves recall when a curated feed misses a major story.",
                    risks=("topic feeds can be noisy",),
                ),
            ),
            degradation_mode="Show the latest successful snapshot or an empty section with freshness metadata.",
            free_feasibility=FeasibilityLevel.VIABLE,
        ),
        CategoryStrategy(
            category=StrategyCategory.FINANCE_NEWS,
            provider_contract="NewsProvider",
            primary_source=SourcePlan(
                provider_key="finance_rss_primary",
                provider_contract="NewsProvider",
                source_name="Public finance-media RSS and market newsroom feeds",
                access_mode="rss",
                is_free=True,
                rationale="Finance headlines are widely available through RSS or newsroom pages.",
                risks=(
                    "paywalled articles can reduce body availability",
                    "same-wire stories appear across multiple outlets",
                ),
            ),
            fallback_sources=(
                SourcePlan(
                    provider_key="finance_search_fallback",
                    provider_contract="SearchProvider",
                    source_name="Search-based finance hotspot enrichment",
                    access_mode="search",
                    is_free=True,
                    rationale="Useful when RSS coverage misses intraday topics.",
                    risks=("search hits need original-link backfill",),
                ),
            ),
            degradation_mode="Disable hotspot enrichment first and keep the curated finance headline stream running.",
            free_feasibility=FeasibilityLevel.VIABLE,
        ),
        CategoryStrategy(
            category=StrategyCategory.POLICY_NEWS,
            provider_contract="NewsProvider",
            primary_source=SourcePlan(
                provider_key="policy_official_primary",
                provider_contract="NewsProvider",
                source_name="Official release pages and trusted policy-news RSS feeds",
                access_mode="html_or_rss",
                is_free=True,
                rationale="Policy coverage needs higher-trust sources than generic media aggregation.",
                risks=(
                    "release pages are less standardized than RSS",
                    "source quality varies more than tech or finance media",
                ),
            ),
            fallback_sources=(
                SourcePlan(
                    provider_key="policy_search_fallback",
                    provider_contract="SearchProvider",
                    source_name="Search enrichment constrained by source allowlist",
                    access_mode="search",
                    is_free=True,
                    rationale="Search can help surface same-day policy headlines outside the allowlist.",
                    risks=("search results cannot be used without source validation",),
                ),
            ),
            degradation_mode="Keep only allowlisted official and top-tier sources when enrichment is unavailable.",
            free_feasibility=FeasibilityLevel.VIABLE_WITH_GUARDRAILS,
        ),
        CategoryStrategy(
            category=StrategyCategory.SEARCH_HOTSPOTS,
            provider_contract="SearchProvider",
            primary_source=SourcePlan(
                provider_key="search_primary",
                provider_contract="SearchProvider",
                source_name="Generic search provider wrapper for hotspot recall",
                access_mode="search",
                is_free=True,
                rationale="Search helps recover topics not covered by fixed RSS inputs.",
                risks=(
                    "ranking is opaque",
                    "results may omit publish timestamps",
                ),
            ),
            fallback_sources=(
                SourcePlan(
                    provider_key="search_rss_fallback",
                    provider_contract="NewsProvider",
                    source_name="Topic RSS feeds used as a weak hotspot substitute",
                    access_mode="rss_search",
                    is_free=True,
                    rationale="RSS-based topic feeds are less flexible but still usable when search fails.",
                    risks=("lower recall for broad hotspot discovery",),
                ),
            ),
            degradation_mode="Turn off hotspot enrichment entirely; main dashboard sections must continue without it.",
            free_feasibility=FeasibilityLevel.VIABLE_WITH_GUARDRAILS,
        ),
        CategoryStrategy(
            category=StrategyCategory.MACRO_INDICATORS,
            provider_contract="MacroDataProvider",
            primary_source=SourcePlan(
                provider_key="macro_official_primary",
                provider_contract="MacroDataProvider",
                source_name="Official macro pages from NBS, PBOC, and other authorities",
                access_mode="html_or_open_data",
                is_free=True,
                rationale="Official pages provide the authoritative release cadence and metric definitions.",
                risks=(
                    "page structures differ by institution",
                    "release schedules vary across indicators",
                ),
            ),
            fallback_sources=(
                SourcePlan(
                    provider_key="macro_akshare_fallback",
                    provider_contract="MacroDataProvider",
                    source_name="AKShare macro endpoints",
                    access_mode="python_sdk",
                    is_free=True,
                    rationale="AKShare is fast to integrate and good for backfill or initial validation.",
                    risks=("some AKShare endpoints depend on third-party sites",),
                ),
            ),
            degradation_mode="Serve the last successful reading with a stale-data badge until the next official release is collected.",
            free_feasibility=FeasibilityLevel.VIABLE_WITH_GUARDRAILS,
        ),
        CategoryStrategy(
            category=StrategyCategory.BROAD_MARKET_INDICES,
            provider_contract="MarketDataProvider",
            primary_source=SourcePlan(
                provider_key="market_akshare_primary",
                provider_contract="MarketDataProvider",
                source_name="AKShare broad-index market endpoints",
                access_mode="python_sdk",
                is_free=True,
                rationale="AKShare offers high coverage for A-share, Hong Kong, and related index snapshots.",
                risks=(
                    "stability depends on upstream pages for some endpoints",
                    "rate limits and action-runner compatibility need verification",
                ),
            ),
            fallback_sources=(
                SourcePlan(
                    provider_key="market_exchange_fallback",
                    provider_contract="MarketDataProvider",
                    source_name="Official exchange index pages and lightweight parsers",
                    access_mode="html",
                    is_free=True,
                    rationale="Exchange pages provide a direct fallback for core closing values.",
                    risks=("HTML parsing cost is higher than SDK access",),
                ),
            ),
            degradation_mode="Expose the last completed trade-date snapshot and clearly mark it as delayed.",
            free_feasibility=FeasibilityLevel.VIABLE,
        ),
        CategoryStrategy(
            category=StrategyCategory.EVENT_OUTLOOK,
            provider_contract="ResearchProvider",
            primary_source=SourcePlan(
                provider_key="events_official_primary",
                provider_contract="ResearchProvider",
                source_name="Official calendars, policy agendas, and public meeting schedules",
                access_mode="html_or_calendar",
                is_free=True,
                rationale="Upcoming events need traceable, forward-looking sources before any model enrichment is applied.",
                risks=(
                    "calendar formats are inconsistent",
                    "important events may appear across multiple agencies",
                ),
            ),
            fallback_sources=(
                SourcePlan(
                    provider_key="events_doubao_fallback",
                    provider_contract="ResearchProvider",
                    source_name="Doubao research with source-constrained JSON output",
                    access_mode="llm_api",
                    is_free=True,
                    rationale="Model-assisted research can organize event leads that are scattered across sources.",
                    risks=(
                        "model output is not a fact source",
                        "records without citations must be discarded",
                    ),
                ),
            ),
            degradation_mode="Hide low-confidence findings and keep only source-backed events in the public dashboard.",
            free_feasibility=FeasibilityLevel.VIABLE_WITH_GUARDRAILS,
        ),
    )
