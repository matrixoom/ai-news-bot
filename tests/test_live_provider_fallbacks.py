from datetime import date
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.domain.external_data import EventHorizon


try:
    from src.providers.live_data import (
        FallbackMacroProvider,
        FallbackMarketDataProvider,
        FallbackResearchProvider,
        UnavailableResearchProvider,
    )
    from src.providers.sample_data import (
        SampleMacroProvider,
        SampleMarketDataProvider,
    )
    from src.services import DashboardService
    _IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    FallbackMacroProvider = None
    FallbackMarketDataProvider = None
    FallbackResearchProvider = None
    UnavailableResearchProvider = None
    SampleMacroProvider = None
    SampleMarketDataProvider = None
    DashboardService = None
    _IMPORT_ERROR = exc


class RaisingMacroProvider:
    provider_key = "raising-macro"

    def fetch_latest_readings(self, *, indicator_codes):
        raise RuntimeError("akshare unavailable")


class PartialMarketProvider:
    provider_key = "partial-market"

    def fetch_index_snapshots(self, *, symbols, trade_date):
        fallback = SampleMarketDataProvider()
        return fallback.fetch_index_snapshots(symbols=["CSI300"], trade_date=trade_date)


class RaisingResearchProvider:
    provider_key = "raising-research"

    def collect_outlook(self, *, horizon, topics, as_of):
        raise RuntimeError("missing ark key")


@unittest.skipIf(_IMPORT_ERROR is not None, f"Missing optional dependency: {_IMPORT_ERROR}")
class LiveProviderFallbackTests(unittest.TestCase):
    def test_macro_provider_falls_back_to_sample_on_exception(self):
        provider = FallbackMacroProvider(RaisingMacroProvider(), SampleMacroProvider())

        readings = provider.fetch_latest_readings(indicator_codes=["cpi", "ppi"])

        self.assertEqual(len(readings), 2)
        self.assertEqual(provider.healthcheck().availability.value, "degraded")
        self.assertIn("实时宏观数据不可用", provider.healthcheck().detail)

    def test_market_provider_backfills_missing_symbols_from_sample(self):
        provider = FallbackMarketDataProvider(PartialMarketProvider(), SampleMarketDataProvider())

        snapshots = provider.fetch_index_snapshots(
            symbols=["CSI300", "HSTECH"],
            trade_date=date(2026, 3, 15),
        )

        self.assertEqual({item.symbol for item in snapshots}, {"CSI300", "HSTECH"})
        self.assertEqual(next(item for item in snapshots if item.symbol == "HSTECH").currency, "HKD")
        self.assertEqual(provider.healthcheck().availability.value, "degraded")
        self.assertIn("HSTECH", provider.healthcheck().detail)

    def test_research_provider_falls_back_to_empty_on_exception(self):
        provider = FallbackResearchProvider(lambda: RaisingResearchProvider(), UnavailableResearchProvider())

        findings = provider.collect_outlook(
            horizon=EventHorizon.NEXT_7_DAYS,
            topics=("policy",),
            as_of=date(2026, 3, 15),
        )

        self.assertEqual(findings, [])
        self.assertEqual(provider.healthcheck().availability.value, "degraded")
        self.assertIn("实时事件研究不可用", provider.healthcheck().detail)

    @patch("src.providers.live_data.PublicRssNewsProvider.fetch_latest", side_effect=RuntimeError("rss down"))
    @patch("src.providers.live_data.GoogleNewsSearchProvider.search", side_effect=RuntimeError("search down"))
    @patch("src.providers.live_data.AkshareMacroDataProvider.fetch_latest_readings", side_effect=RuntimeError("akshare missing"))
    @patch("src.providers.live_data.AkshareMarketDataProvider.fetch_index_snapshots", side_effect=RuntimeError("akshare missing"))
    @patch("src.providers.live_data.ArkResearchProvider.__init__", side_effect=RuntimeError("ark key missing"))
    def test_dashboard_live_mode_keeps_events_empty_when_research_provider_fails(
        self,
        *_mocks,
    ):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ,
            {"EVENTS_OUTLOOK_DB_PATH": str(Path(tmpdir) / "events_outlook.db")},
            clear=False,
        ):
            snapshot = DashboardService(
                prefer_live_data=True,
                enable_background_refresh=False,
            ).build_snapshot(force_refresh=True)

        self.assertEqual(len(snapshot.news_sections), 3)
        self.assertEqual(len(snapshot.market_sections), 6)
        self.assertEqual(len(snapshot.event_sections), 4)
        self.assertTrue(any(section.items for section in snapshot.news_sections))
        self.assertTrue(all(not section.items for section in snapshot.event_sections))
        self.assertTrue(any(item.status == "degraded" for item in snapshot.data_status))
        self.assertEqual(snapshot.dashboard_summary.coverage_note, "")


if __name__ == "__main__":
    unittest.main()
