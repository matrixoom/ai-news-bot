import os
import unittest
from datetime import date
from unittest.mock import Mock, patch

try:
    from src.domain.external_data import NewsCategory
    from src.providers.live_data import GoogleNewsSearchProvider, PublicRssNewsProvider

    LIVE_PROVIDER_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    NewsCategory = None
    GoogleNewsSearchProvider = None
    PublicRssNewsProvider = None
    LIVE_PROVIDER_IMPORT_ERROR = exc

try:
    from fastapi.testclient import TestClient
    from src.app.web.fastapi_app import create_fastapi_app
    from src.services.dashboard_service import DashboardService

    FASTAPI_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    TestClient = None
    create_fastapi_app = None
    DashboardService = None
    FASTAPI_IMPORT_ERROR = exc


RSS_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample Feed</title>
    <item>
      <title>First headline</title>
      <link>https://example.com/1</link>
      <pubDate>Tue, 17 Mar 2026 10:00:00 +0000</pubDate>
      <description>First summary</description>
    </item>
    <item>
      <title>Second headline</title>
      <link>https://example.com/2</link>
      <pubDate>Tue, 17 Mar 2026 11:00:00 +0000</pubDate>
      <description>Second summary</description>
    </item>
  </channel>
</rss>
"""


@unittest.skipIf(
    LIVE_PROVIDER_IMPORT_ERROR is not None,
    f"Live provider deps missing: {LIVE_PROVIDER_IMPORT_ERROR}",
)
class RealInterfaceUnitTests(unittest.TestCase):
    @patch("src.providers.live_data.requests.get")
    def test_public_rss_provider_invokes_http_and_parses_item(self, mock_get):
        response = Mock()
        response.content = RSS_FIXTURE.encode("utf-8")
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        provider = PublicRssNewsProvider()
        items = provider.fetch_latest(
            category=NewsCategory.TECHNOLOGY,
            published_on=date(2026, 3, 17),
            limit=1,
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "First headline")
        self.assertIn("openai.com/blog/rss", mock_get.call_args.args[0])

    @patch("src.providers.live_data.requests.get")
    def test_google_news_search_provider_invokes_http_and_parses_item(self, mock_get):
        response = Mock()
        response.content = RSS_FIXTURE.encode("utf-8")
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        provider = GoogleNewsSearchProvider()
        items = provider.search(
            query="macro market liquidity today",
            published_on=date(2026, 3, 17),
            limit=1,
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "First headline")
        self.assertIn("news.google.com/rss/search", mock_get.call_args.args[0])
        self.assertIn("macro+market+liquidity+today", mock_get.call_args.args[0])


@unittest.skipUnless(
    os.getenv("RUN_LIVE_SMOKE") == "1",
    "Set RUN_LIVE_SMOKE=1 to run optional live-interface smoke tests.",
)
@unittest.skipIf(
    FASTAPI_IMPORT_ERROR is not None,
    f"FastAPI deps missing: {FASTAPI_IMPORT_ERROR}",
)
class LiveInterfaceSmokeTests(unittest.TestCase):
    def test_removed_frontend_dashboard_api_live_mode_smoke(self):
        app = create_fastapi_app(DashboardService(prefer_live_data=True))
        client = TestClient(app)

        response = client.get("/api/frontend/dashboard")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
