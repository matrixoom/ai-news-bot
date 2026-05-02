import sqlite3
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.services.macro_data_repository import MacroDataRepository
from src.services.macro_data_service import MacroDataService
from src.services.macro_data_sync_service import MacroDataSyncService


class MacroDataRepositoryTests(unittest.TestCase):
    """校验宏观数据模块按每指标一表写入和读取 SQLite。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "macro-data" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()

    def test_repository_initializes_one_table_per_indicator(self) -> None:
        """校验初始化会创建指标事实表和共享注册/同步状态表。"""
        repository = MacroDataRepository(self.db_path)

        table_names = repository.list_table_names()

        self.assertIn("macro_nominal_gdp", table_names)
        self.assertIn("macro_real_gdp", table_names)
        self.assertIn("macro_household_new_loans", table_names)
        self.assertIn("macro_corporate_new_loans", table_names)
        self.assertIn("macro_household_leverage_ratio", table_names)
        self.assertIn("macro_corporate_leverage_ratio", table_names)
        self.assertIn("macro_ppi", table_names)
        self.assertIn("macro_cpi", table_names)
        self.assertIn("macro_nominal_gdp_growth", table_names)
        self.assertIn("macro_real_gdp_growth", table_names)
        self.assertIn("macro_data_indicator_registry", table_names)
        self.assertIn("macro_data_sync_state", table_names)

    def test_repository_reads_chart_points_from_own_indicator_table(self) -> None:
        """校验单图表查询只读取该指标独立事实表。"""
        repository = MacroDataRepository(self.db_path)
        repository.upsert_points(
            "nominal_gdp",
            [
                {
                    "period_end": "2025-03-31",
                    "period_label": "2025Q1",
                    "value": 100.0,
                    "unit": "亿元",
                    "frequency": "quarterly",
                    "provider_key": "unit_test",
                    "source_url": "https://example.com/nominal-gdp",
                    "released_at": "2025-04-15T00:00:00Z",
                }
            ],
            status="success",
            warning_message="",
        )
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO macro_real_gdp (
                    period_end, period_label, value, unit, frequency, provider_key, source_url, released_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2025-03-31",
                    "2025Q1",
                    999.0,
                    "亿元",
                    "quarterly",
                    "unit_test",
                    "https://example.com/real-gdp",
                    "2025-04-15T00:00:00Z",
                    "2026-05-01T00:00:00Z",
                ),
            )

        points = repository.load_points(
            indicator_id="nominal_gdp",
            start_date="2025-01-01",
            end_date="2025-12-31",
        )

        values = [point.value for point in points]
        self.assertIn(100.0, values)
        self.assertNotIn(999.0, values)

    def test_repository_keeps_yearly_and_quarterly_points_for_same_period_end(self) -> None:
        """校验同一日期的年度与季度点位不会互相覆盖。"""
        repository = MacroDataRepository(self.db_path)
        repository.replace_points(
            "nominal_gdp",
            [
                {
                    "period_end": "2024-12-31",
                    "period_label": "2024",
                    "value": 700.0,
                    "unit": "亿元",
                    "frequency": "yearly",
                    "provider_key": "unit_test",
                    "source_url": "https://example.com/yearly",
                    "released_at": "2025-01-01T00:00:00Z",
                },
                {
                    "period_end": "2024-12-31",
                    "period_label": "2024Q4",
                    "value": 250.0,
                    "unit": "亿元",
                    "frequency": "quarterly",
                    "provider_key": "unit_test",
                    "source_url": "https://example.com/quarterly",
                    "released_at": "2025-01-01T00:00:00Z",
                },
            ],
            status="success",
            warning_message="",
        )

        yearly_points = repository.load_points(
            indicator_id="nominal_gdp",
            start_date="2024-01-01",
            end_date="2024-12-31",
            frequency="yearly",
        )
        quarterly_points = repository.load_points(
            indicator_id="nominal_gdp",
            start_date="2024-01-01",
            end_date="2024-12-31",
            frequency="quarterly",
        )

        self.assertEqual([point.value for point in yearly_points], [700.0])
        self.assertEqual([point.value for point in quarterly_points], [250.0])


class MacroDataApiTests(unittest.TestCase):
    """校验前端 Macro Data API 契约。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "macro-data-api" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()
        self.repository = MacroDataRepository(self.db_path)
        service = MacroDataService(repository=self.repository)
        self.client = TestClient(create_fastapi_app(macro_data_service=service))

    def test_frontend_macro_data_module_returns_gdp_charts(self) -> None:
        """校验模块接口按 GDP 子标签返回总量与增速图定义。"""
        response = self.client.get("/api/frontend/modules/macro-data?tab=gdp")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module"]["id"], "macro-data")
        self.assertEqual(payload["tab"], "gdp")
        self.assertEqual([chart["id"] for chart in payload["charts"]], ["gdp_total_combined", "gdp_growth"])
        self.assertEqual(
            [option["value"] for option in payload["range_options"]],
            ["6m", "1y", "3y", "5y", "10y", "15y", "20y", "25y", "30y", "custom"],
        )
        self.assertIn({"value": "1y", "label": "1年"}, payload["range_options"])
        self.assertIn({"value": "3y", "label": "3年"}, payload["range_options"])
        self.assertEqual(payload["frequency_options"], [{"value": "quarterly", "label": "季度"}, {"value": "yearly", "label": "年度"}])

    def test_frontend_macro_data_chart_returns_gdp_growth_series(self) -> None:
        """校验 GDP 增速图按名义和实际 GDP 总量派生两条同比序列。"""
        response = self.client.get(
            "/api/frontend/modules/macro-data/charts/gdp_growth"
            "?range=custom&start_date=2025-01-01&end_date=2026-12-31"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], "gdp_growth")
        self.assertEqual(payload["title"], "GDP增速")
        self.assertEqual(payload["unit"], "%")
        self.assertEqual(payload["range"]["type"], "custom")
        self.assertEqual([series["name"] for series in payload["series"]], ["名义GDP增速", "实际GDP增速"])
        self.assertEqual(payload["series"][0]["points"][0]["date"], "2026-03-31")
        self.assertAlmostEqual(payload["series"][0]["points"][0]["value"], 3.87)
        self.assertAlmostEqual(payload["series"][1]["points"][0]["value"], 4.75)

    def test_frontend_macro_data_chart_supports_30_year_range(self) -> None:
        """校验单图接口支持新增 30 年预设范围。"""
        response = self.client.get("/api/frontend/modules/macro-data/charts/nominal_gdp?range=30y")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["range"]["type"], "30y")

    def test_frontend_macro_data_chart_filters_by_frequency(self) -> None:
        """校验 GDP 图表可按年度或季度频率分别查询。"""
        self.repository.replace_points(
            "nominal_gdp",
            [
                {
                    "period_end": "2024-12-31",
                    "period_label": "2024",
                    "value": 700.0,
                    "unit": "亿元",
                    "frequency": "yearly",
                    "provider_key": "unit_test",
                    "source_url": "",
                    "released_at": "",
                },
                {
                    "period_end": "2024-12-31",
                    "period_label": "2024Q4",
                    "value": 250.0,
                    "unit": "亿元",
                    "frequency": "quarterly",
                    "provider_key": "unit_test",
                    "source_url": "",
                    "released_at": "",
                },
            ],
            status="success",
            warning_message="",
        )

        response = self.client.get(
            "/api/frontend/modules/macro-data/charts/nominal_gdp"
            "?range=custom&start_date=2024-01-01&end_date=2024-12-31&frequency=yearly"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["frequency"], "yearly")
        self.assertEqual(payload["series"][0]["points"][0]["period_label"], "2024")
        self.assertEqual(payload["series"][0]["points"][0]["value"], 700.0)

    def test_frontend_macro_data_chart_supports_custom_range(self) -> None:
        """校验单图接口支持自定义起止日期并返回点位序列。"""
        response = self.client.get(
            "/api/frontend/modules/macro-data/charts/nominal_gdp"
            "?range=custom&start_date=2025-01-01&end_date=2026-12-31"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], "nominal_gdp")
        self.assertEqual(payload["range"]["type"], "custom")
        self.assertEqual(payload["range"]["start_date"], "2025-01-01")
        self.assertEqual(payload["range"]["end_date"], "2026-12-31")
        self.assertGreater(len(payload["series"][0]["points"]), 0)

    def test_frontend_macro_data_chart_rejects_invalid_custom_range(self) -> None:
        """校验自定义起止日期倒置时快速失败。"""
        response = self.client.get(
            "/api/frontend/modules/macro-data/charts/nominal_gdp"
            "?range=custom&start_date=2026-12-31&end_date=2025-01-01"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_macro_data_range")


class MacroDataSyncServiceTests(unittest.TestCase):
    """校验宏观数据历史同步服务会写入本地 SQLite。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "macro-data-sync" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()

    def test_sync_gdp_history_persists_totals_and_growth_points(self) -> None:
        """校验 GDP 同步会写入名义/实际总量和两条增速序列。"""
        repository = MacroDataRepository(self.db_path)
        service = MacroDataSyncService(
            repository=repository,
            world_bank_loader=lambda indicator: [
                {"year": 2024, "value_yuan": 1_349_083_546_278_00 if indicator.endswith(".CN") else 1_282_315_896_159_00},
            ],
            eastmoney_loader=lambda: [
                {"label": "2024年第1季度", "nominal_value": 304761.8, "real_growth": 5.3},
                {"label": "2025年第1季度", "nominal_value": 318466.4, "real_growth": 5.4},
            ],
            constant_price_loader=lambda: [
                {"period_end": "2024-03-31", "period_label": "2024Q1", "value": 290845.8},
                {"period_end": "2025-03-31", "period_label": "2025Q1", "value": 306551.47},
            ],
            historical_loader=lambda: [],
        )

        result = service.sync_gdp_history()

        self.assertEqual(result["nominal_gdp"], 3)
        self.assertEqual(result["real_gdp"], 3)
        nominal_points = repository.load_points(
            indicator_id="nominal_gdp",
            start_date="2024-01-01",
            end_date="2025-12-31",
        )
        real_points = repository.load_points(
            indicator_id="real_gdp",
            start_date="2024-01-01",
            end_date="2025-12-31",
        )
        growth_points = repository.load_points(
            indicator_id="real_gdp_growth",
            start_date="2025-01-01",
            end_date="2025-12-31",
        )
        self.assertEqual(nominal_points[-1].value, 318466.4)
        self.assertAlmostEqual(real_points[-1].value, 306551.47)
        self.assertEqual(growth_points[-1].value, 5.4)
        self.assertEqual(repository.get_sync_state("nominal_gdp").status, "live")

    def test_sync_gdp_history_derives_quarter_values_and_matching_yearly_totals(self) -> None:
        """校验季度图使用当季值，完整年度图与四个季度之和一致。"""
        repository = MacroDataRepository(self.db_path)
        service = MacroDataSyncService(
            repository=repository,
            world_bank_loader=lambda indicator: [],
            eastmoney_loader=lambda: [
                {"label": "2024年第1季度", "nominal_value": 100.0, "real_growth": 5.0},
                {"label": "2024年第1-2季度", "nominal_value": 250.0, "real_growth": 5.0},
                {"label": "2024年第1-3季度", "nominal_value": 450.0, "real_growth": 5.0},
                {"label": "2024年第1-4季度", "nominal_value": 700.0, "real_growth": 5.0},
            ],
            constant_price_loader=lambda: [],
            historical_loader=lambda: [],
        )

        service.sync_gdp_history()

        quarterly_points = repository.load_points(
            indicator_id="nominal_gdp",
            start_date="2024-01-01",
            end_date="2024-12-31",
            frequency="quarterly",
        )
        yearly_points = repository.load_points(
            indicator_id="nominal_gdp",
            start_date="2024-01-01",
            end_date="2024-12-31",
            frequency="yearly",
        )

        self.assertEqual([point.value for point in quarterly_points], [100.0, 150.0, 200.0, 250.0])
        self.assertEqual(yearly_points[0].value, sum(point.value for point in quarterly_points))


if __name__ == "__main__":
    unittest.main()
