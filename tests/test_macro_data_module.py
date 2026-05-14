import sqlite3
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.services.macro_data_repository import MacroDataRepository
from src.services.macro_data_service import MacroDataService
from src.services.macro_data_sync_service import (
    MacroDataSyncService,
    _parse_credit_balance_sheet,
    _parse_household_deposit_balance_sheet,
)


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
        self.assertIn("macro_household_deposits", table_names)
        self.assertIn("macro_household_demand_deposits", table_names)
        self.assertIn("macro_household_time_deposits", table_names)
        self.assertIn("macro_ppi", table_names)
        self.assertIn("macro_cpi", table_names)
        self.assertIn("macro_nominal_gdp_growth", table_names)
        self.assertIn("macro_real_gdp_growth", table_names)
        self.assertIn("macro_comprehensive_pmi", table_names)
        self.assertIn("macro_unemployment_insurance_fund_expense", table_names)
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

    def test_replace_points_updates_indicator_status_after_live_sync(self) -> None:
        """校验真实同步写入后指标定义状态不再停留在样例状态。"""
        repository = MacroDataRepository(self.db_path)

        repository.replace_points(
            "comprehensive_pmi",
            [
                {
                    "period_end": "2026-03-31",
                    "period_label": "2026-03",
                    "value": 51.5,
                    "unit": "%",
                    "frequency": "monthly",
                    "provider_key": "akshare_comprehensive_pmi",
                    "source_url": "https://akshare.akfamily.xyz/",
                    "released_at": "",
                }
            ],
            status="live",
            warning_message="",
        )

        indicator = repository.get_indicator("comprehensive_pmi")

        self.assertIsNotNone(indicator)
        self.assertEqual(indicator.status, "live")

        reopened = MacroDataRepository(self.db_path)
        reopened_indicator = reopened.get_indicator("comprehensive_pmi")
        self.assertIsNotNone(reopened_indicator)
        self.assertEqual(reopened_indicator.status, "live")

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

    def test_repository_seeds_twenty_year_unemployment_insurance_expense_history(self) -> None:
        """校验失业保险基金支出默认种子覆盖近二十年官方年度序列。"""
        repository = MacroDataRepository(self.db_path)

        points = repository.load_points(
            indicator_id="unemployment_insurance_fund_expense",
            start_date="2005-01-01",
            end_date="2024-12-31",
            frequency="yearly",
        )
        sync_state = repository.get_sync_state("unemployment_insurance_fund_expense")

        self.assertEqual(len(points), 20)
        self.assertEqual(points[0].period_label, "2005")
        self.assertEqual(points[-1].period_label, "2024")
        self.assertEqual(points[0].value, 206.9)
        self.assertEqual(points[1].value, 198.0)
        self.assertEqual(points[-2].value, 1485.2)
        self.assertEqual(points[-1].value, 1842.21)
        self.assertIsNotNone(sync_state)
        self.assertEqual(sync_state.status, "live")


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

    def test_frontend_macro_data_module_returns_credit_charts(self) -> None:
        """校验模块接口按 信贷 子标签返回贷款、杠杆率和社融图表定义。"""
        response = self.client.get("/api/frontend/modules/macro-data?tab=credit")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tab"], "credit")
        chart_ids = [chart["id"] for chart in payload["charts"]]
        self.assertIn("new_rmb_loans", chart_ids)
        self.assertIn("household_demand_deposits", chart_ids)
        self.assertIn("social_financing", chart_ids)
        self.assertIn("household_leverage_ratio", chart_ids)
        self.assertIn("corporate_leverage_ratio", chart_ids)
        self.assertLess(chart_ids.index("new_rmb_loans"), chart_ids.index("household_demand_deposits"))
        self.assertLess(chart_ids.index("household_demand_deposits"), chart_ids.index("social_financing"))
        social_financing = next(c for c in payload["charts"] if c["id"] == "social_financing")
        self.assertEqual(social_financing["chart_type"], "line")
        self.assertEqual(social_financing["title"], "社会融资规模")
        self.assertEqual(social_financing["unit"], "亿元")
        new_loans = next(c for c in payload["charts"] if c["id"] == "new_rmb_loans")
        self.assertEqual(new_loans["chart_type"], "bar_stacked_line")
        self.assertEqual(new_loans["title"], "新增人民币贷款")
        self.assertEqual(new_loans["unit"], "亿元")
        household_deposits = next(c for c in payload["charts"] if c["id"] == "household_demand_deposits")
        self.assertEqual(household_deposits["chart_type"], "bar_stacked_line")
        self.assertEqual(household_deposits["title"], "居民活期存款")
        self.assertEqual(household_deposits["unit"], "亿元")
        self.assertTrue(household_deposits["wide"])

    def test_frontend_macro_data_module_returns_comprehensive_pmi_chart(self) -> None:
        """校验景气标签包含综合 PMI，且保持 PMI 折线图契约。"""
        response = self.client.get("/api/frontend/modules/macro-data?tab=climate")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        chart_ids = [chart["id"] for chart in payload["charts"]]
        self.assertEqual(chart_ids, ["manufacturing_pmi", "non_manufacturing_pmi", "comprehensive_pmi"])
        comprehensive = payload["charts"][2]
        self.assertEqual(comprehensive["title"], "综合PMI")
        self.assertEqual(comprehensive["chart_type"], "line")

    def test_frontend_macro_data_module_returns_employment_chart(self) -> None:
        """校验就业标签返回失业保险基金支出累计值图表定义。"""
        response = self.client.get("/api/frontend/modules/macro-data?tab=employment")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tab"], "employment")
        self.assertEqual([chart["id"] for chart in payload["charts"]], ["unemployment_insurance_fund_expense"])
        chart = payload["charts"][0]
        self.assertEqual(chart["title"], "中国社会保险基金支出:失业保险:累计值")
        self.assertEqual(chart["unit"], "亿元")
        self.assertEqual(chart["frequency"], "yearly")

    def test_frontend_macro_data_chart_returns_unemployment_insurance_expense_series(self) -> None:
        """校验就业指标图表返回年度失业保险基金支出累计值序列。"""
        self.repository.replace_points(
            "unemployment_insurance_fund_expense",
            [
                {
                    "period_end": "2024-12-31",
                    "period_label": "2024",
                    "value": 1800.0,
                    "unit": "亿元",
                    "frequency": "yearly",
                    "provider_key": "unit_test",
                    "source_url": "",
                    "released_at": "",
                }
            ],
            status="sample",
            warning_message="",
        )

        response = self.client.get(
            "/api/frontend/modules/macro-data/charts/unemployment_insurance_fund_expense"
            "?range=custom&start_date=2024-01-01&end_date=2024-12-31&frequency=yearly"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], "unemployment_insurance_fund_expense")
        self.assertEqual(payload["series"][0]["name"], "中国社会保险基金支出:失业保险:累计值")
        self.assertEqual(payload["series"][0]["points"][0]["period_label"], "2024")
        self.assertEqual(payload["series"][0]["points"][0]["value"], 1800.0)

    def test_frontend_comprehensive_pmi_chart_uses_live_sync_status(self) -> None:
        """校验综合 PMI 图表同步后对外状态为真实数据状态。"""
        self.repository.replace_points(
            "comprehensive_pmi",
            [
                {
                    "period_end": "2026-03-31",
                    "period_label": "2026-03",
                    "value": 51.5,
                    "unit": "%",
                    "frequency": "monthly",
                    "provider_key": "akshare_comprehensive_pmi",
                    "source_url": "https://akshare.akfamily.xyz/",
                    "released_at": "",
                }
            ],
            status="live",
            warning_message="",
        )

        response = self.client.get("/api/frontend/modules/macro-data/charts/comprehensive_pmi?frequency=monthly")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "live")
        self.assertEqual(payload["sync_state"]["status"], "live")

    def test_frontend_macro_data_chart_returns_social_financing_series(self) -> None:
        """校验社融图表返回单系列月度数据。"""
        response = self.client.get(
            "/api/frontend/modules/macro-data/charts/social_financing"
            "?range=custom&start_date=2025-01-01&end_date=2026-12-31"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], "social_financing")
        self.assertEqual(payload["chart_type"], "line")
        self.assertEqual(payload["frequency"], "monthly")
        self.assertEqual(len(payload["series"]), 1)
        self.assertEqual(payload["series"][0]["name"], "社会融资规模")

    def test_frontend_macro_data_chart_returns_household_deposit_series(self) -> None:
        """校验居民活期存款图表返回总量线和活期/定期分项序列。"""
        self.repository.replace_points(
            "household_deposits",
            [
                {
                    "period_end": "2000-01-31",
                    "period_label": "2000-01",
                    "value": 60241.8,
                    "unit": "亿元",
                    "frequency": "monthly",
                    "provider_key": "unit_test",
                    "source_url": "",
                    "released_at": "",
                },
                {
                    "period_end": "2026-03-31",
                    "period_label": "2026-03",
                    "value": 1735889.52,
                    "unit": "亿元",
                    "frequency": "monthly",
                    "provider_key": "unit_test",
                    "source_url": "",
                    "released_at": "",
                },
            ],
            status="live",
            warning_message="",
        )
        self.repository.replace_points(
            "household_demand_deposits",
            [
                {
                    "period_end": "2000-01-31",
                    "period_label": "2000-01",
                    "value": 14975.0,
                    "unit": "亿元",
                    "frequency": "monthly",
                    "provider_key": "unit_test",
                    "source_url": "",
                    "released_at": "",
                },
                {
                    "period_end": "2026-03-31",
                    "period_label": "2026-03",
                    "value": 420190.26,
                    "unit": "亿元",
                    "frequency": "monthly",
                    "provider_key": "unit_test",
                    "source_url": "",
                    "released_at": "",
                },
            ],
            status="live",
            warning_message="",
        )
        self.repository.replace_points(
            "household_time_deposits",
            [
                {
                    "period_end": "2000-01-31",
                    "period_label": "2000-01",
                    "value": 45266.8,
                    "unit": "亿元",
                    "frequency": "monthly",
                    "provider_key": "unit_test",
                    "source_url": "",
                    "released_at": "",
                },
                {
                    "period_end": "2026-03-31",
                    "period_label": "2026-03",
                    "value": 1315699.26,
                    "unit": "亿元",
                    "frequency": "monthly",
                    "provider_key": "unit_test",
                    "source_url": "",
                    "released_at": "",
                },
            ],
            status="live",
            warning_message="",
        )

        response = self.client.get(
            "/api/frontend/modules/macro-data/charts/household_demand_deposits"
            "?range=custom&start_date=2000-01-01&end_date=2026-12-31"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], "household_demand_deposits")
        self.assertEqual(payload["chart_type"], "bar_stacked_line")
        self.assertEqual(payload["frequency"], "monthly")
        self.assertEqual(
            [series["name"] for series in payload["series"]],
            ["居民存款总计", "居民活期存款", "居民定期及其他存款"],
        )
        self.assertEqual(payload["series"][1]["points"][0]["date"], "2000-01-31")
        self.assertEqual(payload["series"][1]["points"][-1]["date"], "2026-03-31")

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

    def test_sync_climate_history_persists_comprehensive_pmi(self) -> None:
        """校验景气同步会同时写入制造业、非制造业和综合 PMI。"""
        repository = MacroDataRepository(self.db_path)
        service = MacroDataSyncService(
            repository=repository,
            pmi_loader=lambda: [{"period_end": "2026-03-31", "value": 50.4}],
            non_man_pmi_loader=lambda: [{"period_end": "2026-03-31", "value": 50.1}],
            comprehensive_pmi_loader=lambda: [{"period_end": "2026-03-31", "value": 51.5}],
        )

        result = service.sync_climate_history()

        self.assertEqual(result["comprehensive_pmi"], 1)
        points = repository.load_points(
            indicator_id="comprehensive_pmi",
            start_date="2026-01-01",
            end_date="2026-12-31",
            frequency="monthly",
        )
        self.assertEqual(points[0].value, 51.5)

    def test_sync_household_deposit_history_persists_near_30_year_points(self) -> None:
        """校验居民存款同步可写入覆盖近 30 年窗口的月度活期存款序列。"""
        repository = MacroDataRepository(self.db_path)
        service = MacroDataSyncService(
            repository=repository,
            household_deposit_loader=lambda: [
                {
                    "period_end": "2000-01-31",
                    "household_total": 60241.8,
                    "household_demand": 14975.0,
                    "household_time": 45266.8,
                },
                {
                    "period_end": "2026-03-31",
                    "household_total": 1735889.52,
                    "household_demand": 420190.26,
                    "household_time": 1315699.26,
                },
            ],
        )

        result = service.sync_household_deposit_history()

        self.assertEqual(result["household_demand_deposits"], 2)
        points = repository.load_points(
            indicator_id="household_demand_deposits",
            start_date="1999-01-01",
            end_date="2026-12-31",
            frequency="monthly",
        )
        self.assertEqual(points[0].period_end, "2000-01-31")
        self.assertEqual(points[-1].period_end, "2026-03-31")
        self.assertEqual(repository.get_sync_state("household_demand_deposits").status, "live")

    def test_parse_household_deposit_balance_sheet_reads_household_demand_rows(self) -> None:
        """校验人民银行信贷收支表可解析住户存款、活期和定期分项余额。"""
        import pandas as pd

        rows = [[""] * 4 for _ in range(15)]
        rows[5][0] = "项目 Item"
        rows[5][1] = "2000.01"
        rows[5][2] = "2000.02"
        rows[5][3] = "2000.03"
        rows[8][0] = "储蓄存款 Household Savings Deposits"
        rows[9][0] = "活期储蓄 Demand deposits"
        rows[10][0] = "定期储蓄 Time Deposits"
        rows[8][1:] = [60241.8, 62270.3, 62492.29]
        rows[9][1:] = [14975.0, 15726.8, 16001.83]
        rows[10][1:] = [45266.8, 46543.4, 46490.46]

        result = _parse_household_deposit_balance_sheet(pd.DataFrame(rows), 2000)

        self.assertEqual(result[(2000, 1)]["household_total"], 60241.8)
        self.assertEqual(result[(2000, 1)]["household_demand"], 14975.0)
        self.assertEqual(result[(2000, 1)]["household_time"], 45266.8)

    def test_parse_household_deposit_balance_sheet_accepts_chinese_only_savings_rows(self) -> None:
        """校验 2000 年前后仅中文行名的储蓄存款表可解析为居民存款。"""
        import pandas as pd

        rows = [[""] * 3 for _ in range(12)]
        rows[2][0] = "项目"
        rows[2][1] = "2001.01"
        rows[2][2] = "2001.02"
        rows[6][0] = "储蓄存款"
        rows[7][0] = "活期储蓄"
        rows[8][0] = "定期储蓄"
        rows[6][1:] = [70000.0, 71000.0]
        rows[7][1:] = [18000.0, 18100.0]
        rows[8][1:] = [52000.0, 52900.0]

        result = _parse_household_deposit_balance_sheet(pd.DataFrame(rows), 2001)

        self.assertEqual(result[(2001, 1)]["household_total"], 70000.0)
        self.assertEqual(result[(2001, 1)]["household_demand"], 18000.0)
        self.assertEqual(result[(2001, 1)]["household_time"], 52000.0)

    def test_parse_household_deposit_balance_sheet_keeps_time_and_other_deposits_row(self) -> None:
        """校验定期及其他存款不会被误判为居民存款分组结束。"""
        import pandas as pd

        rows = [[""] * 3 for _ in range(12)]
        rows[2][0] = "项目 Item"
        rows[2][1] = "2011.01"
        rows[2][2] = "2011.02"
        rows[6][0] = "1.住户存款 Deposits of Households"
        rows[7][0] = "（1）活期及临时性存款 Demand & Temporary Deposits"
        rows[8][0] = "（2）定期及其他存款 Time & Other Deposits"
        rows[9][0] = "2.非金融企业存款 Deposits of Non-financial Enterprises"
        rows[6][1:] = [320000.0, 330000.0]
        rows[7][1:] = [120000.0, 121000.0]
        rows[8][1:] = [200000.0, 209000.0]

        result = _parse_household_deposit_balance_sheet(pd.DataFrame(rows), 2011)

        self.assertEqual(result[(2011, 1)]["household_time"], 200000.0)

    def test_parse_credit_balance_sheet_keeps_october_month_from_truncated_excel_header(self) -> None:
        """校验 Excel 将 10 月显示为 2025.1 时仍能按列序解析为 10 月。"""
        import pandas as pd

        rows = [[""] * 13 for _ in range(40)]
        rows[5][0] = "项目 Item"
        for month in range(1, 13):
            rows[5][month] = f"2025.{month:02d}" if month != 10 else "2025.1"
        rows[28][0] = "1.住户贷款 Loans to Households"
        rows[29][0] = "（1）短期贷款 Short-term Loans"
        rows[32][0] = "（2）中长期贷款 Mid & Long-term Loans"
        rows[35][0] = "2.非金融企业及机关团体贷款 Loans to Non-financial Enterprises"
        rows[36][0] = "（1）短期贷款 Short-term Loans"
        rows[37][0] = "（2）中长期贷款 Mid & Long-term Loans"
        for column in range(1, 13):
            rows[29][column] = 1000 + column
            rows[32][column] = 2000 + column
            rows[36][column] = 3000 + column
            rows[37][column] = 4000 + column

        result = _parse_credit_balance_sheet(pd.DataFrame(rows), 2025)

        self.assertIn((2025, 10), result)
        self.assertEqual(result[(2025, 10)]["hh_short"], 1010.0)
        self.assertNotEqual(result[(2025, 10)]["hh_short"], result[(2025, 1)]["hh_short"])


if __name__ == "__main__":
    unittest.main()
