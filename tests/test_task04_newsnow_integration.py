import os
from datetime import UTC, date, datetime, timedelta
import unittest
from unittest.mock import patch

from src.domain.external_data import NewsCategory, NewsItem
from src.services.dashboard_service import DashboardService
from src.providers.newsnow_provider import (
    CompositeNewsProvider,
    NewsNowAggregatedNewsProvider,
    NewsNowModeProvider,
    NewsNowSourceMode,
)
from src.providers.newsnow_sources import NewsNowSource


class _MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _MockTextResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        raise RuntimeError("json() not supported for text-only response")


class NewsNowModeProviderTests(unittest.TestCase):
    def test_hybrid_mode_falls_back_to_upstream_provider(self):
        class BrokenProvider:
            provider_key = "api"

            def fetch_latest(self, *, category, published_on, limit):
                raise RuntimeError("api down")

            def fetch_source_latest(self, *, source_id, limit=10):
                raise RuntimeError("api down")

            def list_source_ids(self):
                return ("weibo",)

            def healthcheck(self):
                return None

        class WorkingProvider:
            provider_key = "upstream"

            def fetch_latest(self, *, category, published_on, limit):
                return [
                    NewsItem(
                        provider="upstream",
                        source_name="weibo",
                        category=category,
                        title="Upstream native item",
                        url="https://example.com/native",
                        published_at="2026-03-21T08:00:00Z",
                        summary=None,
                    )
                ]

            def fetch_source_latest(self, *, source_id, limit=10):
                return self.fetch_latest(
                    category=NewsCategory.POLICY,
                    published_on=date(2026, 3, 21),
                    limit=limit,
                )

            def list_source_ids(self):
                return ("weibo",)

            def healthcheck(self):
                return None

        provider = NewsNowModeProvider(
            mode=NewsNowSourceMode.HYBRID,
            api_provider=BrokenProvider(),
            upstream_provider=WorkingProvider(),
        )

        items = provider.fetch_latest(
            category=NewsCategory.POLICY,
            published_on=date(2026, 3, 21),
            limit=5,
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Upstream native item")


# class NewsNowAggregatedNewsProviderTests(unittest.TestCase):
#     @patch("src.providers.newsnow_provider.requests.get")
#     def test_source_interval_cache_avoids_redundant_request(self, mock_get):
#         spec = NewsNowSource("tech-source", "tech", "realtime", 600000)
#         clock = [datetime(2026, 3, 21, 8, 0, tzinfo=UTC)]
#         now_ms = int(clock[0].timestamp() * 1000)
#         mock_get.return_value = _MockResponse(
#             {
#                 "status": "success",
#                 "id": "tech-source",
#                 "updatedTime": now_ms,
#                 "items": [
#                     {
#                         "id": "1",
#                         "title": "Tech source item",
#                         "url": "https://example.com/tech/1",
#                         "pubDate": "2026-03-21T08:00:00Z",
#                     }
#                 ],
#             }
#         )
#         provider = NewsNowAggregatedNewsProvider(
#             source_specs=(spec,),
#             max_items_per_source=3,
#             min_source_budget=1,
#             source_budget_multiplier=1,
#             max_workers=1,
#             now_factory=lambda: clock[0],
#         )
#
#         first = provider.fetch_latest(
#             category=NewsCategory.TECHNOLOGY,
#             published_on=date(2026, 3, 21),
#             limit=10,
#         )
#         second = provider.fetch_latest(
#             category=NewsCategory.TECHNOLOGY,
#             published_on=date(2026, 3, 21),
#             limit=10,
#         )
#
#         self.assertEqual(mock_get.call_count, 1)
#         self.assertEqual(len(first), 1)
#         self.assertEqual(len(second), 1)
#         self.assertEqual(first[0].title, "Tech source item")
#         self.assertEqual(provider.list_source_ids(), ("tech-source",))
#
#     @patch("src.providers.newsnow_provider.requests.get")
#     def test_newsnow_realtime_method_returns_clickable_original_url(self, mock_get):
#         spec = NewsNowSource("policy-source", "china", "realtime", 600000)
#         clock = [datetime(2026, 3, 21, 8, 0, tzinfo=UTC)]
#         now_ms = int(clock[0].timestamp() * 1000)
#         mock_get.return_value = _MockResponse(
#             {
#                 "status": "success",
#                 "id": "policy-source",
#                 "updatedTime": now_ms,
#                 "items": [
#                     {
#                         "id": "p-1",
#                         "title": "Policy timeline update",
#                         "url": "https://desktop.example/policy/1",
#                         "mobileUrl": "https://m.example/policy/1",
#                         "pubDate": "2026-03-21T08:00:00Z",
#                     }
#                 ],
#             }
#         )
#         provider = NewsNowAggregatedNewsProvider(
#             source_specs=(spec,),
#             max_items_per_source=3,
#             min_source_budget=1,
#             source_budget_multiplier=1,
#             max_workers=1,
#             now_factory=lambda: clock[0],
#         )
#
#         items = provider.fetch_latest(
#             category=NewsCategory.POLICY,
#             published_on=date(2026, 3, 21),
#             limit=10,
#         )
#
#         self.assertEqual(len(items), 1)
#         self.assertEqual(items[0].url, "https://m.example/policy/1")
#         headers = mock_get.call_args.kwargs.get("headers", {})
#         self.assertIn("Mozilla/5.0", headers.get("User-Agent", ""))
#
#     @patch("src.providers.newsnow_provider.requests.get")
#     def test_fetch_source_latest_supports_source_by_source_probe(self, mock_get):
#         spec = NewsNowSource("probe-source", "tech", "realtime", 600000)
#         now_ms = int(datetime(2026, 3, 21, 8, 0, tzinfo=UTC).timestamp() * 1000)
#         mock_get.return_value = _MockResponse(
#             {
#                 "status": "success",
#                 "id": "probe-source",
#                 "updatedTime": now_ms,
#                 "items": [
#                     {
#                         "id": "1",
#                         "title": "Probe headline A",
#                         "url": "https://example.com/a",
#                         "pubDate": "2026-03-21T08:00:00Z",
#                     },
#                     {
#                         "id": "2",
#                         "title": "Probe headline B",
#                         "url": "https://example.com/b",
#                         "pubDate": "2026-03-21T08:01:00Z",
#                     },
#                 ],
#             }
#         )
#         provider = NewsNowAggregatedNewsProvider(
#             source_specs=(spec,),
#             min_source_budget=1,
#             source_budget_multiplier=1,
#             max_workers=1,
#             max_items_per_source=10,
#             now_factory=lambda: datetime(2026, 3, 21, 8, 2, tzinfo=UTC),
#         )
#
#         items = provider.fetch_source_latest(source_id="probe-source", limit=5)
#
#         self.assertEqual(len(items), 2)
#         self.assertEqual(items[0].title, "Probe headline B")
#         self.assertEqual(items[1].title, "Probe headline A")
#
#     @patch("src.providers.newsnow_provider.requests.get")
#     def test_refresh_failure_uses_stale_cache(self, mock_get):
#         spec = NewsNowSource("finance-source", "finance", "realtime", 1000)
#         clock = [datetime(2026, 3, 21, 8, 0, tzinfo=UTC)]
#         now_ms = int(clock[0].timestamp() * 1000)
#
#         payload = {
#             "status": "success",
#             "id": "finance-source",
#             "updatedTime": now_ms,
#             "items": [
#                 {
#                     "id": "1",
#                     "title": "Finance source item",
#                     "url": "https://example.com/finance/1",
#                     "pubDate": "2026-03-21 08:00:00",
#                 }
#             ],
#         }
#         mock_get.side_effect = [
#             _MockResponse(payload),
#             RuntimeError("network down"),
#             RuntimeError("network down"),
#         ]
#         provider = NewsNowAggregatedNewsProvider(
#             source_specs=(spec,),
#             max_items_per_source=3,
#             min_source_budget=1,
#             source_budget_multiplier=1,
#             max_workers=1,
#             now_factory=lambda: clock[0],
#         )
#
#         first = provider.fetch_latest(
#             category=NewsCategory.FINANCE,
#             published_on=date(2026, 3, 21),
#             limit=10,
#         )
#         clock[0] = clock[0] + timedelta(seconds=3)
#         second = provider.fetch_latest(
#             category=NewsCategory.FINANCE,
#             published_on=date(2026, 3, 21),
#             limit=10,
#         )
#
#         self.assertEqual(mock_get.call_count, 3)
#         self.assertEqual(len(first), 1)
#         self.assertEqual(len(second), 1)
#         self.assertEqual(second[0].title, "Finance source item")
#
#     @patch("src.providers.newsnow_provider.requests.get")
#     def test_native_source_fallback_from_source_code_for_bilibili_hot_video(self, mock_get):
#         class _ErrorResponse:
#             def raise_for_status(self):
#                 raise RuntimeError("500")
#
#         source = NewsNowSource("bilibili-hot-video", "china", "hottest", 600000)
#         now = datetime(2026, 3, 21, 8, 0, tzinfo=UTC)
#
#         bilibili_payload = {
#             "code": 0,
#             "data": {
#                 "list": [
#                     {
#                         "bvid": "BV1xx411c7mD",
#                         "title": "Bilibili Hot Video",
#                         "pubdate": int(now.timestamp()),
#                         "desc": "video summary",
#                     }
#                 ]
#             },
#         }
#         mock_get.side_effect = [
#             _ErrorResponse(),
#             _ErrorResponse(),
#             _MockResponse(bilibili_payload),
#         ]
#
#         provider = NewsNowAggregatedNewsProvider(
#             source_specs=(source,),
#             max_items_per_source=3,
#             min_source_budget=1,
#             source_budget_multiplier=1,
#             max_workers=1,
#             now_factory=lambda: now,
#         )
#
#         items = provider.fetch_source_latest(source_id="bilibili-hot-video", limit=3)
#
#         self.assertEqual(len(items), 1)
#         self.assertEqual(items[0].title, "Bilibili Hot Video")
#         self.assertIn("bilibili.com/video/BV1xx411c7mD", items[0].url)
#
#     @patch("src.providers.newsnow_provider.requests.get")
#     def test_native_source_fallback_from_source_code_for_fastbull_express(self, mock_get):
#         class _ErrorResponse:
#             def raise_for_status(self):
#                 raise RuntimeError("500")
#
#         source = NewsNowSource("fastbull-express", "finance", "realtime", 120000)
#         now = datetime(2026, 3, 21, 8, 0, tzinfo=UTC)
#         now_ms = int(now.timestamp() * 1000)
#         html = (
#             '<div class="news-list content-list-a" data-date="1774058591352">'
#             '<div class="shear_box box_show" data-title="Fastbull headline A" '
#             'data-href="/cn/fastshort/3962699_100_1"></div>'
#             "</div>"
#         )
#         mock_get.side_effect = [
#             _ErrorResponse(),
#             _ErrorResponse(),
#             _MockTextResponse(html),
#         ]
#
#         provider = NewsNowAggregatedNewsProvider(
#             source_specs=(source,),
#             max_items_per_source=3,
#             min_source_budget=1,
#             source_budget_multiplier=1,
#             max_workers=1,
#             now_factory=lambda: now,
#         )
#
#         items = provider.fetch_source_latest(source_id="fastbull-express", limit=3)
#
#         self.assertEqual(len(items), 1)
#         self.assertEqual(items[0].title, "Fastbull headline A")
#         self.assertEqual(items[0].url, "https://www.fastbull.com/cn/fastshort/3962699_100_1")
#         self.assertEqual(items[0].published_at, "2026-03-21T02:03:11Z")
#
#     @patch("src.providers.newsnow_provider.requests.get", side_effect=RuntimeError("network down"))
#     def test_raises_when_newsnow_has_no_data_and_no_cache(self, _mock_get):
#         spec = NewsNowSource("tech-source", "tech", "realtime", 600000)
#         provider = NewsNowAggregatedNewsProvider(
#             source_specs=(spec,),
#             max_items_per_source=3,
#             min_source_budget=1,
#             source_budget_multiplier=1,
#             max_workers=1,
#             now_factory=lambda: datetime(2026, 3, 21, 8, 0, tzinfo=UTC),
#         )
#
#         with self.assertRaises(RuntimeError):
#             provider.fetch_latest(
#                 category=NewsCategory.TECHNOLOGY,
#                 published_on=date(2026, 3, 21),
#                 limit=10,
#             )
#
#
# class CompositeNewsProviderTests(unittest.TestCase):
#     def test_raises_when_all_subproviders_fail(self):
#         class BrokenProvider:
#             provider_key = "broken"
#
#             def fetch_latest(self, *, category, published_on, limit):
#                 raise RuntimeError("failed")
#
#         provider = CompositeNewsProvider((BrokenProvider(), BrokenProvider()))
#         with self.assertRaises(RuntimeError):
#             provider.fetch_latest(
#                 category=NewsCategory.TECHNOLOGY,
#                 published_on=date(2026, 3, 21),
#                 limit=10,
#             )
#
#     def test_merges_successful_subprovider_results(self):
#         class WorkingProvider:
#             provider_key = "ok"
#
#             def fetch_latest(self, *, category, published_on, limit):
#                 return [
#                     NewsItem(
#                         provider="ok",
#                         source_name="ok",
#                         category=category,
#                         title="Merged Item",
#                         url="https://example.com/merged",
#                         published_at="2026-03-21T08:00:00Z",
#                         summary=None,
#                     )
#                 ]
#
#         class BrokenProvider:
#             provider_key = "broken"
#
#             def fetch_latest(self, *, category, published_on, limit):
#                 raise RuntimeError("failed")
#
#         provider = CompositeNewsProvider((BrokenProvider(), WorkingProvider()))
#         items = provider.fetch_latest(
#             category=NewsCategory.TECHNOLOGY,
#             published_on=date(2026, 3, 21),
#             limit=10,
#         )
#
#         self.assertEqual(len(items), 1)
#         self.assertEqual(items[0].title, "Merged Item")
#
#
# class DashboardNewsNowWiringTests(unittest.TestCase):
#     @patch("src.services.dashboard_service.GoogleNewsSearchProvider.search", return_value=())
#     @patch("src.services.dashboard_service.PublicRssNewsProvider.fetch_latest", side_effect=RuntimeError("rss down"))
#     @patch("src.services.dashboard_service.NewsNowAggregatedNewsProvider.fetch_latest")
#     def test_dashboard_live_mode_consumes_newsnow_items(
#         self,
#         mock_newsnow_fetch,
#         *_unused,
#     ):
#         def side_effect(*, category, published_on, limit):
#             title = {
#                 NewsCategory.TECHNOLOGY: "NewsNow tech",
#                 NewsCategory.FINANCE: "NewsNow finance",
#                 NewsCategory.POLICY: "NewsNow policy",
#             }[category]
#             return [
#                 NewsItem(
#                     provider="newsnow",
#                     source_name="newsnow-source",
#                     category=category,
#                     title=title,
#                     url="https://newsnow.example/item",
#                     published_at=f"{published_on.isoformat()}T08:00:00Z",
#                     summary="sample",
#                 )
#             ]
#
#         mock_newsnow_fetch.side_effect = side_effect
#         snapshot = DashboardService(prefer_live_data=True).build_snapshot()
#
#         self.assertEqual(len(snapshot.news_sections), 3)
#         for section in snapshot.news_sections:
#             self.assertGreaterEqual(len(section.items), 1)
#             self.assertTrue(section.items[0].url.startswith("https://"))
#             self.assertIn("NewsNow", section.items[0].title)
#
#
# @unittest.skipUnless(
#     os.getenv("RUN_LIVE_SMOKE") == "1",
#     "Set RUN_LIVE_SMOKE=1 to run optional live NewsNow smoke tests.",
# )
# class NewsNowLiveSmokeTests(unittest.TestCase):
#     def test_newsnow_live_endpoint_returns_items(self):
#         provider = NewsNowAggregatedNewsProvider(
#             source_specs=(NewsNowSource("weibo", "china", "hottest", 120000),),
#             max_items_per_source=5,
#             min_source_budget=1,
#             source_budget_multiplier=1,
#             max_workers=1,
#         )
#
#         items = provider.fetch_latest(
#             category=NewsCategory.POLICY,
#             published_on=date.today(),
#             limit=5,
#         )
#
#         self.assertGreaterEqual(len(items), 1)
#         self.assertTrue(all(item.url.startswith("http") for item in items))


@unittest.skipUnless(
    os.getenv("RUN_LIVE_NEWSNOW_ALL_SOURCES") == "1",
    "Set RUN_LIVE_NEWSNOW_ALL_SOURCES=1 to validate every NewsNow source ID one by one.",
)
class NewsNowAllSourcesLiveMatrixTests(unittest.TestCase):
    def test_every_registered_source_returns_items(self):
        provider = NewsNowAggregatedNewsProvider(
            max_items_per_source=3,
            min_source_budget=1,
            source_budget_multiplier=1,
            max_workers=6,
        )

        for source_id in provider.list_source_ids():
            with self.subTest(source_id=source_id):
                items = provider.fetch_source_latest(source_id=source_id, limit=3)
                for item in items:
                    print(f'{item.title}, {item.source_name}, {item.url}, {item.summary}, {item.published_at}', flush=True)
                self.assertTrue(items, f"{source_id}: empty result")
                self.assertTrue(
                    any(item.url.startswith("http") for item in items),
                    f"{source_id}: no clickable url",
                )


if __name__ == "__main__":
    unittest.main()
