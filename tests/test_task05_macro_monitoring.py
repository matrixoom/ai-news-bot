from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.domain import MacroFrequency, TrendDirection, build_default_macro_registry
from src.domain.external_data import MacroHistoryPoint, MacroIndicatorSeries
from src.providers import ProviderAvailability, ProviderStatus
from src.services.dashboard_service import DashboardService
from src.services.macro_data_factor_store import MacroDataFactorStore
from src.services.macro_history_store import MacroHistoryStore
from src.services.macro_monitoring_service import MacroMonitoringService


class FakeMacroProvider:
    provider_key = "fake-macro"

    def __init__(self, series_items):
        self._series_items = list(series_items)

    def fetch_history_series(self, *, indicator_codes, start_date):
        return [
            item
            for item in self._series_items
            if item.indicator_code in indicator_codes
            and any(point.period_end >= start_date for point in item.points)
        ]

    def fetch_latest_readings(self, *, indicator_codes):
        _ = indicator_codes
        return []

    def healthcheck(self):
        return ProviderStatus(
            provider_key=self.provider_key,
            availability=ProviderAvailability.LIVE,
            detail="ok",
            checked_at="2026-03-15T00:00:00Z",
        )


class Task05DocumentationTests(unittest.TestCase):
    def test_task05_main_doc_links_protocol_and_tests(self):
        content = Path("tasks/05-macro-indicators-monitoring.md").read_text(encoding="utf-8")

        self.assertIn("Completed for implementation phase.", content)
        self.assertIn("05-indicator-registry-and-display-protocol.md", content)
        self.assertIn("tests/test_task05_macro_monitoring.py", content)


class MacroRegistryTests(unittest.TestCase):
    def test_registry_covers_paired_macro_dashboard_indicators(self):
        registry = build_default_macro_registry()

        self.assertEqual(
            set(registry),
            {
                "cpi",
                "copper_gold_ratio",
                "enterprise_leverage",
                "enterprise_new_loans",
                "gdp_nominal",
                "gdp_real",
                "gold_price",
                "household_new_loans",
                "household_leverage",
                "nvidia_stock_price",
                "oil_price",
                "ppi",
                "us_10y_yield",
                "us_credit_spread",
                "usd_cny",
            },
        )
        self.assertEqual(registry["cpi"].frequency, MacroFrequency.MONTHLY)
        self.assertEqual(registry["gdp_real"].frequency, MacroFrequency.QUARTERLY)
        self.assertEqual(registry["enterprise_new_loans"].unit, "tn yuan")
        self.assertEqual(registry["usd_cny"].frequency, MacroFrequency.DAILY)
        self.assertEqual(registry["us_10y_yield"].unit, "pct")


class MacroHistoryStoreTests(unittest.TestCase):
    def test_data_factor_store_seeds_source_matrix(self):
        with TemporaryDirectory() as tmpdir:
            store = MacroDataFactorStore(Path(tmpdir) / "macro_data_factors.db")
            rows = store.list_source_matrix_rows()
            comments = store.get_table_field_comments("macro_housing_price_history")

        self.assertTrue(any(row.factor_code == "housing_price" for row in rows))
        self.assertTrue(
            any(
                row.factor_code == "household_demand_deposit_growth"
                and row.availability_status == "degraded"
                for row in rows
            )
        )
        self.assertEqual(comments["value"], "观测值，无法确认时保持空值")
        self.assertEqual(comments["source_key"], "数据来源编码")

    def test_store_persists_points_and_sync_state(self):
        with TemporaryDirectory() as tmpdir:
            store = MacroHistoryStore(Path(tmpdir) / "macro_history.db")
            store.upsert_indicator_history(
                indicator_code="cpi",
                provider_key="fake-macro",
                source_url="https://example.com/cpi",
                points=[
                    MacroHistoryPoint(
                        period_end=date(2026, 1, 31),
                        period_label="2026-01",
                        value=0.2,
                        unit="%",
                        source_url="https://example.com/cpi",
                        released_at="2026-02-09",
                    ),
                    MacroHistoryPoint(
                        period_end=date(2026, 2, 28),
                        period_label="2026-02",
                        value=0.4,
                        unit="%",
                        source_url="https://example.com/cpi",
                        released_at="2026-03-09",
                    ),
                ],
                status="live",
                warning_message="",
                synced_at="2026-03-15T00:00:00Z",
            )

            points = store.load_points(indicator_code="cpi", start_date=date(2026, 1, 1))
            state = store.get_sync_state("cpi")

        self.assertEqual(len(points), 2)
        self.assertEqual(points[-1].value, 0.4)
        self.assertIsNotNone(state)
        self.assertEqual(state.point_count, 2)
        self.assertEqual(state.latest_period_end, date(2026, 2, 28))


class MacroMonitoringServiceTests(unittest.TestCase):
    def test_service_formats_indicator_and_derives_trend_from_history(self):
        series = MacroIndicatorSeries(
            provider="fake-macro",
            indicator_code="cpi",
            display_name="CPI",
            unit="%",
            source_url="https://example.com/cpi",
            points=(
                MacroHistoryPoint(
                    period_end=date(2026, 1, 31),
                    period_label="2026-01",
                    value=0.2,
                    unit="%",
                    source_url="https://example.com/cpi",
                    released_at="2026-02-09",
                ),
                MacroHistoryPoint(
                    period_end=date(2026, 2, 28),
                    period_label="2026-02",
                    value=0.4,
                    unit="%",
                    source_url="https://example.com/cpi",
                    released_at="2026-03-09",
                ),
            ),
        )
        with TemporaryDirectory() as tmpdir:
            service = MacroMonitoringService(
                macro_provider=FakeMacroProvider([series]),
                store=MacroHistoryStore(Path(tmpdir) / "macro_history.db"),
                registry={"cpi": build_default_macro_registry()["cpi"]},
                now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(["cpi"])

        self.assertEqual(snapshot.indicators[0].value, "0.4%")
        self.assertEqual(snapshot.indicators[0].previous_value, "0.2%")
        self.assertIn("+0.2", snapshot.indicators[0].change_label)
        self.assertEqual(snapshot.indicators[0].trend, TrendDirection.UP)
        self.assertEqual(snapshot.indicators[0].status, "live")
        self.assertEqual(snapshot.indicators[0].numeric_value, 0.4)
        self.assertEqual(len(snapshot.indicators[0].history_points), 2)

    def test_service_keeps_unavailable_card_when_provider_misses_data(self):
        registry = build_default_macro_registry()
        with TemporaryDirectory() as tmpdir:
            service = MacroMonitoringService(
                macro_provider=FakeMacroProvider([]),
                store=MacroHistoryStore(Path(tmpdir) / "macro_history.db"),
                registry={"enterprise_leverage": registry["enterprise_leverage"]},
                now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(["enterprise_leverage"])

        self.assertEqual(snapshot.indicators[0].status, "unavailable")
        self.assertEqual(snapshot.indicators[0].numeric_value, None)
        self.assertEqual(snapshot.indicators[0].history_points, [])


class DashboardMacroIntegrationTests(unittest.TestCase):
    def test_dashboard_snapshot_uses_registry_driven_macro_cards(self):
        snapshot = DashboardService().build_snapshot()

        self.assertGreaterEqual(len(snapshot.macro_sections), 15)
        self.assertTrue(snapshot.macro_sections[0].source_label)
        self.assertTrue(snapshot.macro_sections[0].updated_at)

    def test_frontend_macro_module_exposes_data_factor_payload(self):
        client = TestClient(create_fastapi_app())

        response = client.get("/api/frontend/modules/macro")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data_factors"]["label"], "数据因子")
        self.assertEqual(payload["source_matrix"]["label"], "数据源矩阵")
        self.assertEqual(payload["data_models"]["status"], "reserved")
        self.assertEqual(payload["module"]["details"], [])

    def test_legacy_pair_payload_is_not_exposed_in_macro_module(self):
        client = TestClient(create_fastapi_app())

        response = client.get("/api/frontend/modules/macro")

        self.assertEqual(response.status_code, 200)
        sections = [detail["section"] for detail in response.json()["module"]["details"]]
        self.assertEqual(sections, [])


if __name__ == "__main__":
    unittest.main()
