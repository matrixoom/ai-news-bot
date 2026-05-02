import sqlite3
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.services.macro_data_repository import MacroDataRepository
from src.services.macro_data_service import MacroDataService


class MacroDataRepositoryTests(unittest.TestCase):
    """校验宏观数据模块按每指标一表写入和读取 SQLite。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "macro-data" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()

    def test_repository_initializes_one_table_per_indicator(self) -> None:
        """校验初始化会创建八张指标事实表和共享注册/同步状态表。"""
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


class MacroDataApiTests(unittest.TestCase):
    """校验前端 Macro Data API 契约。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "macro-data-api" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()
        service = MacroDataService(repository=MacroDataRepository(self.db_path))
        self.client = TestClient(create_fastapi_app(macro_data_service=service))

    def test_frontend_macro_data_module_returns_gdp_charts(self) -> None:
        """校验模块接口按 GDP 子标签返回总量与增速图定义。"""
        response = self.client.get("/api/frontend/modules/macro-data?tab=gdp")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module"]["id"], "macro-data")
        self.assertEqual(payload["tab"], "gdp")
        self.assertEqual([chart["id"] for chart in payload["charts"]], ["nominal_gdp", "real_gdp", "gdp_growth"])

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


if __name__ == "__main__":
    unittest.main()
