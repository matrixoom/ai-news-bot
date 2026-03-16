from datetime import UTC, datetime
import unittest

from src.app.web import create_fastapi_app
from src.domain import MacroFrequency, TrendDirection, build_default_macro_registry
from src.domain.external_data import MacroIndicatorReading
from src.providers import ProviderAvailability, ProviderStatus
from src.services.dashboard_service import DashboardService
from src.services.macro_monitoring_service import MacroMonitoringService
from fastapi.testclient import TestClient


class FakeMacroProvider:
    provider_key = "fake-macro"

    def __init__(self, readings):
        self._readings = readings

    def fetch_latest_readings(self, *, indicator_codes):
        return [reading for reading in self._readings if reading.indicator_code in indicator_codes]

    def healthcheck(self):
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail="ok",
            checked_at="2026-03-15T00:00:00Z",
        )


class Task05DocumentationTests(unittest.TestCase):
    def test_task05_main_doc_links_protocol_and_tests(self):
        with open("TASK/05-macro-indicators-monitoring.md", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("Completed for implementation phase.", content)
        self.assertIn("05-indicator-registry-and-display-protocol.md", content)
        self.assertIn("tests/test_task05_macro_monitoring.py", content)


class MacroRegistryTests(unittest.TestCase):
    def test_registry_covers_first_batch_indicators(self):
        registry = build_default_macro_registry()

        self.assertEqual(
            set(registry),
            {
                "cpi",
                "ppi",
                "gdp_nominal",
                "gdp_real",
                "social_financing",
                "household_leverage",
                "government_leverage",
            },
        )
        self.assertEqual(registry["cpi"].frequency, MacroFrequency.MONTHLY)
        self.assertEqual(registry["gdp_real"].frequency, MacroFrequency.QUARTERLY)


class MacroMonitoringServiceTests(unittest.TestCase):
    def test_service_formats_indicator_and_derives_trend(self):
        service = MacroMonitoringService(
            macro_provider=FakeMacroProvider(
                [
                    MacroIndicatorReading(
                        provider="fake-macro",
                        indicator_code="cpi",
                        display_name="CPI",
                        value=0.4,
                        unit="%",
                        period_label="2026-02",
                        released_at="2026-03-09",
                        source_url="https://example.com/cpi",
                        previous_value=0.2,
                        change_value=0.2,
                        change_kind="MoM",
                    )
                ]
            ),
            registry={"cpi": build_default_macro_registry()["cpi"]},
            now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
        )

        snapshot = service.build_snapshot(["cpi"])

        self.assertEqual(snapshot.indicators[0].value, "0.4%")
        self.assertEqual(snapshot.indicators[0].previous_value, "0.2%")
        self.assertEqual(snapshot.indicators[0].change_label, "MoM: +0.2 pct")
        self.assertEqual(snapshot.indicators[0].trend, TrendDirection.UP)
        self.assertEqual(snapshot.indicators[0].status, "live")

    def test_service_keeps_unavailable_card_when_provider_misses_data(self):
        registry = build_default_macro_registry()
        service = MacroMonitoringService(
            macro_provider=FakeMacroProvider([]),
            registry={"government_leverage": registry["government_leverage"]},
            now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
        )

        snapshot = service.build_snapshot(["government_leverage"])

        self.assertEqual(snapshot.indicators[0].status, "unavailable")
        self.assertEqual(snapshot.indicators[0].value, "Unavailable")
        self.assertEqual(snapshot.indicators[0].updated_at, "Unavailable")


class DashboardMacroIntegrationTests(unittest.TestCase):
    def test_dashboard_snapshot_uses_registry_driven_macro_cards(self):
        snapshot = DashboardService().build_snapshot()

        self.assertGreaterEqual(len(snapshot.macro_sections), 7)
        self.assertEqual(snapshot.macro_sections[0].source_label, "National Bureau of Statistics")
        self.assertNotEqual(snapshot.macro_sections[0].updated_at, "Unavailable")

    def test_dashboard_api_exposes_macro_source_and_frequency(self):
        client = TestClient(create_fastapi_app())

        response = client.get("/api/dashboard")

        self.assertEqual(response.status_code, 200)
        first_card = response.json()["macro_sections"][0]
        self.assertIn("source_label", first_card)
        self.assertIn("updated_at", first_card)
        self.assertIn("frequency", first_card)


if __name__ == "__main__":
    unittest.main()
