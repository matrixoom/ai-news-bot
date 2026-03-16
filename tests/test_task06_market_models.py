from datetime import UTC, date, datetime
import unittest

from src.domain import FishbowlState, build_default_market_registry
from src.domain.external_data import MarketIndexSnapshot
from src.providers import ProviderAvailability, ProviderStatus
from src.services.market_monitoring_service import MarketMonitoringService


class FakeMarketProvider:
    provider_key = "fake-market"

    def __init__(self, snapshots):
        self._snapshots = snapshots

    def fetch_index_snapshots(self, *, symbols, trade_date):
        return [snapshot for snapshot in self._snapshots if snapshot.symbol in symbols]

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.LIVE, "ok", "2026-03-15T00:00:00Z")


class Task06DocumentationTests(unittest.TestCase):
    def test_task06_main_doc_links_protocol_and_tests(self):
        with open("TASK/06-market-models-and-daily-dashboard.md", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("Completed for implementation phase.", content)
        self.assertIn("06-fishbowl-rules-and-panel-protocol.md", content)
        self.assertIn("tests/test_task06_market_models.py", content)


class MarketMonitoringServiceTests(unittest.TestCase):
    def test_registry_covers_default_indices(self):
        registry = build_default_market_registry()
        self.assertEqual(set(registry), {"CSI300", "CSI500", "CSI1000", "SSE", "CHINEXT", "HSTECH"})

    def test_service_computes_ma20_and_fishbowl_state(self):
        service = MarketMonitoringService(
            market_provider=FakeMarketProvider(
                [
                    MarketIndexSnapshot(
                        provider="fake-market",
                        symbol="CSI300",
                        display_name="CSI 300",
                        trade_date=date(2026, 3, 15),
                        close_price=110.0,
                        currency="CNY",
                        source_url="https://example.com",
                        lookback_closes=tuple([100.0] * 19),
                    )
                ]
            ),
            registry={"CSI300": build_default_market_registry()["CSI300"]},
            now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
        )

        snapshot = service.build_snapshot(["CSI300"], date(2026, 3, 15))

        self.assertEqual(snapshot.items[0].ma20_value, "100.5")
        self.assertEqual(snapshot.items[0].fishbowl_state, FishbowlState.BREAKOUT)
        self.assertIn("%", snapshot.items[0].deviation_pct)

    def test_missing_symbol_does_not_break_other_cards(self):
        service = MarketMonitoringService(
            market_provider=FakeMarketProvider([]),
            registry={
                "CSI300": build_default_market_registry()["CSI300"],
                "HSTECH": build_default_market_registry()["HSTECH"],
            },
            now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
        )

        snapshot = service.build_snapshot(["CSI300", "HSTECH"], date(2026, 3, 15))

        self.assertEqual(len(snapshot.items), 2)
        self.assertEqual(snapshot.items[0].status, "unavailable")


if __name__ == "__main__":
    unittest.main()
