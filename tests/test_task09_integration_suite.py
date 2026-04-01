import unittest

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.services import DashboardService, PushReportService


class Task09DocumentationTests(unittest.TestCase):
    def test_task09_main_doc_links_matrix_and_tests(self):
        with open("tasks/09-testing-strategy-and-delivery-gates.md", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("Completed for implementation phase.", content)
        self.assertIn("09-test-matrix-and-delivery-gates.md", content)
        self.assertIn("tests/test_task09_integration_suite.py", content)


class IntegrationSuiteTests(unittest.TestCase):
    def test_dashboard_api_exposes_all_major_modules(self):
        client = TestClient(create_fastapi_app())
        response = client.get("/api/dashboard")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["news_sections"]), 3)
        self.assertGreaterEqual(len(payload["macro_sections"]), 7)
        self.assertGreaterEqual(len(payload["market_sections"]), 6)
        self.assertEqual(len(payload["event_sections"]), 4)

    def test_push_report_reuses_dashboard_snapshot(self):
        snapshot = DashboardService().build_snapshot()
        report = PushReportService().build_markdown(snapshot)
        html = PushReportService().build_email_html(snapshot)

        self.assertIn(snapshot.title, report)
        self.assertIn("| 指标 | 当前值 | 前值 | 趋势 | 更新时间 |", report)
        self.assertIn("| 指数 | 收盘 | MA20 | 偏离 | 信号 |", report)
        self.assertIn("Close", html)
        self.assertIn("M20", html)
        self.assertIn("Deviation", html)


if __name__ == "__main__":
    unittest.main()
