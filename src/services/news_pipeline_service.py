"""News intelligence pipeline service."""
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
import re
from typing import Callable, Dict, Iterable, List
from urllib.parse import urlparse

from ..domain.external_data import NewsCategory, NewsItem, SearchResultItem
from ..domain.news_pipeline import (
    DomainNewsDigest,
    NewsDomainConfig,
    NewsPipelineItem,
    NewsPipelineSnapshot,
    NewsSourceType,
    build_default_news_domain_configs,
)
from ..providers import NewsProvider, SearchProvider


class NewsPipelineService:
    """Collect, merge, and rank news across domains."""

    def __init__(
        self,
        *,
        news_provider: NewsProvider,
        search_provider: SearchProvider,
        domain_configs: Dict[NewsCategory, NewsDomainConfig] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._news_provider = news_provider
        self._search_provider = search_provider
        self._domain_configs = domain_configs or build_default_news_domain_configs()
        self._now_factory = now_factory or (lambda: datetime.now(UTC))

    def build_snapshot(self, target_date: date | None = None) -> NewsPipelineSnapshot:
        """Build one snapshot spanning all configured domains."""
        current_time = self._now_factory()
        effective_date = target_date or current_time.date()
        domains = [
            self.build_digest_for_category(
                category=category,
                target_date=effective_date,
                fetched_at=current_time,
            )
            for category in self._domain_configs
        ]
        return NewsPipelineSnapshot(
            generated_at=current_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            target_date=effective_date.isoformat(),
            domains=domains,
        )

    def build_digest_for_category(
        self,
        *,
        category: NewsCategory,
        target_date: date | None = None,
        fetched_at: datetime | None = None,
    ) -> DomainNewsDigest:
        """Build one domain digest with filtering, dedupe, and ranking."""
        current_time = fetched_at or self._now_factory()
        effective_date = target_date or current_time.date()
        config = self._domain_configs[category]

        candidates = self._collect_candidates(
            config=config,
            target_date=effective_date,
            fetched_at=current_time,
        )
        items, dropped_outdated_count, merged_duplicate_count = self._merge_candidates(candidates)

        return DomainNewsDigest(
            category=category,
            display_name=config.display_name,
            query_templates=config.search_queries,
            summary_strategy=config.summary_strategy,
            candidate_count=len(candidates),
            dropped_outdated_count=dropped_outdated_count,
            merged_duplicate_count=merged_duplicate_count,
            items=items,
        )

    def _collect_candidates(
        self,
        *,
        config: NewsDomainConfig,
        target_date: date,
        fetched_at: datetime,
    ) -> List[NewsPipelineItem]:
        items: List[NewsPipelineItem] = []
        fetched_at_text = fetched_at.isoformat(timespec="seconds").replace("+00:00", "Z")

        for item in self._news_provider.fetch_latest(
            category=config.category,
            published_on=target_date,
            limit=config.rss_limit,
        ):
            items.append(self._normalize_news_item(item, config, target_date, fetched_at_text))

        for query in config.search_queries:
            for item in self._search_provider.search(
                query=query,
                published_on=target_date,
                limit=config.search_limit,
            ):
                items.append(self._normalize_search_item(item, config, target_date, fetched_at_text))

        return items

    def _normalize_news_item(
        self,
        item: NewsItem,
        config: NewsDomainConfig,
        target_date: date,
        fetched_at_text: str,
    ) -> NewsPipelineItem:
        source_name = item.source_name or item.provider
        return NewsPipelineItem(
            title=item.title.strip(),
            category=item.category,
            source_name=source_name,
            source_type=NewsSourceType.RSS,
            url=item.url,
            published_at=item.published_at or None,
            fetched_at=fetched_at_text,
            raw_summary=item.summary or "",
            is_today=self._is_same_day(item.published_at, target_date),
            dedupe_key=self._build_dedupe_key(item.title, item.url),
            source_weight=config.source_weight_for(source_name, NewsSourceType.RSS),
            corroboration_count=1,
            score=0,
            source_tag=item.source_tag or NewsSourceType.RSS.value,
            supporting_sources=(source_name,),
        )

    def _normalize_search_item(
        self,
        item: SearchResultItem,
        config: NewsDomainConfig,
        target_date: date,
        fetched_at_text: str,
    ) -> NewsPipelineItem:
        source_name = self._source_name_from_url(item.original_url) or item.provider
        return NewsPipelineItem(
            title=item.title.strip(),
            category=config.category,
            source_name=source_name,
            source_type=NewsSourceType.SEARCH,
            url=item.original_url,
            published_at=item.published_at or None,
            fetched_at=fetched_at_text,
            raw_summary=item.snippet or "",
            is_today=self._is_same_day(item.published_at, target_date),
            dedupe_key=self._build_dedupe_key(item.title, item.original_url),
            source_weight=config.source_weight_for(source_name, NewsSourceType.SEARCH),
            corroboration_count=1,
            score=0,
            source_tag=item.source_tag or NewsSourceType.SEARCH.value,
            supporting_sources=(source_name,),
        )

    def _merge_candidates(
        self,
        candidates: Iterable[NewsPipelineItem],
    ) -> tuple[List[NewsPipelineItem], int, int]:
        grouped: Dict[str, List[NewsPipelineItem]] = {}
        for candidate in candidates:
            grouped.setdefault(candidate.dedupe_key, []).append(candidate)

        kept_items: List[NewsPipelineItem] = []
        dropped_outdated_count = 0
        merged_duplicate_count = 0

        for group in grouped.values():
            today_items = [item for item in group if item.is_today]
            if not today_items:
                dropped_outdated_count += len(group)
                continue

            merged_duplicate_count += max(0, len(group) - 1)
            primary = max(today_items, key=self._primary_rank)
            supporting_sources = tuple(sorted({item.source_name for item in group}))
            corroboration_count = len(supporting_sources)
            summary_text = next((item.raw_summary for item in today_items if item.raw_summary), primary.raw_summary)
            published_at = next((item.published_at for item in today_items if item.published_at), primary.published_at)
            score = self._score_item(primary, corroboration_count)

            kept_items.append(
                NewsPipelineItem(
                    title=primary.title,
                    category=primary.category,
                    source_name=primary.source_name,
                    source_type=primary.source_type,
                    url=primary.url,
                    published_at=published_at,
                    fetched_at=primary.fetched_at,
                    raw_summary=summary_text,
                    is_today=True,
                    dedupe_key=primary.dedupe_key,
                    source_weight=primary.source_weight,
                    corroboration_count=corroboration_count,
                    score=score,
                    source_tag=primary.source_tag,
                    supporting_sources=supporting_sources,
                )
            )

        kept_items.sort(
            key=lambda item: (
                -item.score,
                item.source_name.lower(),
                item.title.lower(),
            )
        )
        return kept_items, dropped_outdated_count, merged_duplicate_count

    def _primary_rank(self, item: NewsPipelineItem) -> tuple[int, int, int, int]:
        return (
            item.source_weight,
            1 if item.source_type == NewsSourceType.RSS else 0,
            1 if item.published_at else 0,
            1 if item.raw_summary else 0,
        )

    def _score_item(self, item: NewsPipelineItem, corroboration_count: int) -> int:
        return (
            item.source_weight
            + 120
            + ((corroboration_count - 1) * 20)
            + (10 if item.source_type == NewsSourceType.RSS else 0)
            + (5 if item.raw_summary else 0)
        )

    def _build_dedupe_key(self, title: str, url: str) -> str:
        normalized_title = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        if normalized_title:
            return normalized_title
        normalized_url = re.sub(r"[^a-z0-9]+", " ", url.lower()).strip()
        return normalized_url or "unknown"

    def _is_same_day(self, published_at: str | None, target_date: date) -> bool:
        parsed = self._parse_datetime(published_at)
        return bool(parsed and parsed.date() == target_date)

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None

        text = value.strip()
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass

        try:
            return parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError):
            return None

    def _source_name_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return hostname
