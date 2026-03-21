"""Domain models for the news intelligence pipeline."""
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Dict, List, Tuple

from .external_data import NewsCategory


class NewsSourceType(StrEnum):
    """Supported collection channels for news records."""

    RSS = "rss"
    SEARCH = "search"


@dataclass(frozen=True)
class NewsDomainConfig:
    """Configuration for one monitored news domain."""

    category: NewsCategory
    display_name: str
    search_queries: Tuple[str, ...]
    rss_limit: int
    search_limit: int
    summary_strategy: str
    official_sources: Tuple[str, ...] = ()
    priority_sources: Tuple[str, ...] = ()
    default_rss_weight: int = 60
    default_search_weight: int = 35

    def source_weight_for(self, source_name: str, source_type: NewsSourceType) -> int:
        """Resolve source weight based on domain policy and source type."""
        if source_name in self.official_sources:
            return 100
        if source_name in self.priority_sources:
            return 80
        if source_type == NewsSourceType.RSS:
            return self.default_rss_weight
        return self.default_search_weight


@dataclass(frozen=True)
class NewsPipelineItem:
    """Normalized output item from the news pipeline."""

    title: str
    category: NewsCategory
    source_name: str
    source_type: NewsSourceType
    url: str
    published_at: str | None
    fetched_at: str
    raw_summary: str
    is_today: bool
    dedupe_key: str
    source_weight: int
    corroboration_count: int
    score: int
    supporting_sources: Tuple[str, ...] = ()


@dataclass(frozen=True)
class DomainNewsDigest:
    """Collected and ranked news for one domain."""

    category: NewsCategory
    display_name: str
    query_templates: Tuple[str, ...]
    summary_strategy: str
    candidate_count: int
    dropped_outdated_count: int
    merged_duplicate_count: int
    items: List[NewsPipelineItem] = field(default_factory=list)


@dataclass(frozen=True)
class NewsPipelineSnapshot:
    """Top-level snapshot spanning all news domains."""

    generated_at: str
    target_date: str
    domains: List[DomainNewsDigest] = field(default_factory=list)


def build_default_news_domain_configs() -> Dict[NewsCategory, NewsDomainConfig]:
    """Return the default domain configuration for Task 04."""
    configs = (
        NewsDomainConfig(
            category=NewsCategory.TECHNOLOGY,
            display_name="Technology",
            search_queries=(
                "AI platform release today",
                "AI infrastructure chip news today",
            ),
            rss_limit=30,
            search_limit=6,
            summary_strategy="card_summary",
            official_sources=("OpenAI Blog", "Google AI Blog", "Microsoft AI Blog"),
            priority_sources=("MIT Technology Review", "TechCrunch AI", "The Verge AI"),
        ),
        NewsDomainConfig(
            category=NewsCategory.FINANCE,
            display_name="Finance",
            search_queries=(
                "macro market liquidity today",
                "A-share Hong Kong market close today",
            ),
            rss_limit=30,
            search_limit=6,
            summary_strategy="card_summary",
            official_sources=("SSE Newsroom", "HKEX Newsroom"),
            priority_sources=("Caixin Finance", "Reuters Finance", "Bloomberg Markets"),
        ),
        NewsDomainConfig(
            category=NewsCategory.POLICY,
            display_name="Policy",
            search_queries=(
                "policy briefing today",
                "regulatory announcement today",
            ),
            rss_limit=30,
            search_limit=6,
            summary_strategy="card_summary",
            official_sources=("State Council", "PBOC", "NDRC"),
            priority_sources=("Xinhua", "People's Daily"),
        ),
    )

    return {config.category: config for config in configs}
