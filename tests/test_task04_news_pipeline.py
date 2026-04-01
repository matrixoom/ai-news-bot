from datetime import UTC, date, datetime
import unittest

from src.domain import NewsCategory, NewsItem, SearchResultItem, build_default_news_domain_configs
from src.providers import ProviderAvailability, ProviderStatus
from src.services.news_pipeline_service import NewsPipelineService


class FakeNewsProvider:
    provider_key = "fake-news"

    def __init__(self, items_by_category):
        self._items_by_category = items_by_category

    def fetch_latest(self, *, category, published_on, limit):
        return list(self._items_by_category.get(category, ()))[:limit]

    def healthcheck(self):
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail="ok",
            checked_at="2026-03-15T00:00:00Z",
        )


class FakeSearchProvider:
    provider_key = "fake-search"

    def __init__(self, items_by_query):
        self._items_by_query = items_by_query

    def search(self, *, query, published_on, limit):
        return list(self._items_by_query.get(query, ()))[:limit]

    def healthcheck(self):
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail="ok",
            checked_at="2026-03-15T00:00:00Z",
        )


class Task04DocumentationTests(unittest.TestCase):
    def test_task04_main_doc_links_protocol_and_tests(self):
        with open("tasks/04-news-intelligence-pipeline.md", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("Completed for implementation phase.", content)
        self.assertIn("04-domain-config-and-summary-protocol.md", content)
        self.assertIn("tests/test_task04_news_pipeline.py", content)


class NewsPipelineConfigTests(unittest.TestCase):
    def test_default_config_covers_three_domains(self):
        configs = build_default_news_domain_configs()

        self.assertEqual(set(configs), {NewsCategory.TECHNOLOGY, NewsCategory.FINANCE, NewsCategory.POLICY})
        for config in configs.values():
            self.assertGreaterEqual(len(config.search_queries), 1)
            self.assertGreater(config.rss_limit, 0)
            self.assertGreater(config.search_limit, 0)


class NewsPipelineServiceTests(unittest.TestCase):
    def test_filters_outdated_groups_by_default(self):
        target_date = date(2026, 3, 15)
        configs = build_default_news_domain_configs()
        config = configs[NewsCategory.TECHNOLOGY]

        service = NewsPipelineService(
            news_provider=FakeNewsProvider(
                {
                    NewsCategory.TECHNOLOGY: (
                        NewsItem(
                            provider="rss",
                            source_name="Tier One",
                            category=NewsCategory.TECHNOLOGY,
                            title="AI operating workflow expands into enterprise teams",
                            url="https://example.com/today",
                            published_at="2026-03-15T08:00:00Z",
                            summary="Today item",
                        ),
                        NewsItem(
                            provider="rss",
                            source_name="Tier One",
                            category=NewsCategory.TECHNOLOGY,
                            title="Yesterday headline should drop",
                            url="https://example.com/yesterday",
                            published_at="2026-03-14T08:00:00Z",
                            summary="Old item",
                        ),
                    ),
                }
            ),
            search_provider=FakeSearchProvider({config.search_queries[0]: ()}),
            domain_configs={NewsCategory.TECHNOLOGY: config},
            now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
        )

        digest = service.build_digest_for_category(category=NewsCategory.TECHNOLOGY, target_date=target_date)

        self.assertEqual(len(digest.items), 1)
        self.assertEqual(digest.items[0].title, "AI operating workflow expands into enterprise teams")
        self.assertEqual(digest.dropped_outdated_count, 1)

    def test_deduplicates_rss_and_search_hits_into_one_card(self):
        target_date = date(2026, 3, 15)
        config = build_default_news_domain_configs()[NewsCategory.POLICY]

        service = NewsPipelineService(
            news_provider=FakeNewsProvider(
                {
                    NewsCategory.POLICY: (
                        NewsItem(
                            provider="rss",
                            source_name="Xinhua",
                            category=NewsCategory.POLICY,
                            title="Policy briefing sets new technology export controls",
                            url="https://official.example/policy",
                            published_at="2026-03-15T09:00:00Z",
                            summary="Official summary",
                        ),
                    ),
                }
            ),
            search_provider=FakeSearchProvider(
                {
                    config.search_queries[0]: (
                        SearchResultItem(
                            provider="search",
                            query=config.search_queries[0],
                            title="Policy briefing sets new technology export controls",
                            snippet="Search corroboration",
                            original_url="https://xinhua.example/policy",
                            published_at=None,
                        ),
                    ),
                }
            ),
            domain_configs={NewsCategory.POLICY: config},
            now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
        )

        digest = service.build_digest_for_category(category=NewsCategory.POLICY, target_date=target_date)

        self.assertEqual(len(digest.items), 1)
        self.assertEqual(digest.items[0].corroboration_count, 2)
        self.assertEqual(digest.merged_duplicate_count, 1)
        self.assertIn("Xinhua", digest.items[0].supporting_sources)
        self.assertIn("xinhua.example", digest.items[0].supporting_sources)

    def test_ranks_corroborated_item_above_generic_item(self):
        target_date = date(2026, 3, 15)
        config = build_default_news_domain_configs()[NewsCategory.FINANCE]

        service = NewsPipelineService(
            news_provider=FakeNewsProvider(
                {
                    NewsCategory.FINANCE: (
                        NewsItem(
                            provider="rss",
                            source_name="Reuters Finance",
                            category=NewsCategory.FINANCE,
                            title="Liquidity window remains the market's central watchpoint",
                            url="https://official.example/liquidity",
                            published_at="2026-03-15T08:00:00Z",
                            summary="Official summary",
                        ),
                        NewsItem(
                            provider="rss",
                            source_name="Local Blog",
                            category=NewsCategory.FINANCE,
                            title="Sector chatter drives speculative pockets",
                            url="https://blog.example/chatter",
                            published_at="2026-03-15T08:10:00Z",
                            summary="Blog summary",
                        ),
                    ),
                }
            ),
            search_provider=FakeSearchProvider(
                {
                    config.search_queries[0]: (
                        SearchResultItem(
                            provider="search",
                            query=config.search_queries[0],
                            title="Liquidity window remains the market's central watchpoint",
                            snippet="Cross-check",
                            original_url="https://markets.example/liquidity",
                            published_at="2026-03-15T08:30:00Z",
                        ),
                    ),
                }
            ),
            domain_configs={NewsCategory.FINANCE: config},
            now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
        )

        digest = service.build_digest_for_category(category=NewsCategory.FINANCE, target_date=target_date)

        self.assertEqual(digest.items[0].title, "Liquidity window remains the market's central watchpoint")
        self.assertGreater(digest.items[0].score, digest.items[1].score)

    def test_snapshot_runs_three_domains_independently(self):
        target_date = date(2026, 3, 15)
        service = NewsPipelineService(
            news_provider=FakeNewsProvider(
                {
                    NewsCategory.TECHNOLOGY: (
                        NewsItem(
                            provider="rss",
                            source_name="TechCrunch AI",
                            category=NewsCategory.TECHNOLOGY,
                            title="Tech domain item",
                            url="https://example.com/tech",
                            published_at="2026-03-15T07:00:00Z",
                            summary="Tech summary",
                        ),
                    ),
                    NewsCategory.FINANCE: (
                        NewsItem(
                            provider="rss",
                            source_name="Reuters Finance",
                            category=NewsCategory.FINANCE,
                            title="Finance domain item",
                            url="https://example.com/finance",
                            published_at="2026-03-15T07:10:00Z",
                            summary="Finance summary",
                        ),
                    ),
                    NewsCategory.POLICY: (
                        NewsItem(
                            provider="rss",
                            source_name="Xinhua",
                            category=NewsCategory.POLICY,
                            title="Policy domain item",
                            url="https://example.com/policy",
                            published_at="2026-03-15T07:20:00Z",
                            summary="Policy summary",
                        ),
                    ),
                }
            ),
            search_provider=FakeSearchProvider({}),
            now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
        )

        snapshot = service.build_snapshot(target_date=target_date)

        self.assertEqual(snapshot.target_date, "2026-03-15")
        self.assertEqual(
            [digest.category for digest in snapshot.domains],
            [NewsCategory.TECHNOLOGY, NewsCategory.FINANCE, NewsCategory.POLICY],
        )
        self.assertEqual([len(digest.items) for digest in snapshot.domains], [1, 1, 1])


if __name__ == "__main__":
    unittest.main()
