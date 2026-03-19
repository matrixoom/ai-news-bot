import unittest

from src.app.jobs.push_job import run_push_job
from src.services import DashboardService, PushReportService


class FakeConfig:
    ai_response_languages = ["en"]
    notification_methods = ["email", "slack"]
    log_level = "INFO"
    log_format = "%(message)s"


class SuccessNotifier:
    def send(self, content, **kwargs):
        return True


class FailingNotifier:
    def send(self, content, **kwargs):
        return False


class Task08DocumentationTests(unittest.TestCase):
    def test_task08_main_doc_links_protocol_and_tests(self):
        with open("TASK/08-push-workflow-and-automation.md", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("Completed for implementation phase.", content)
        self.assertIn("08-report-and-automation-design.md", content)
        self.assertIn("tests/test_task08_push_workflow.py", content)


class PushWorkflowTests(unittest.TestCase):
    def test_report_service_builds_unified_markdown(self):
        snapshot = DashboardService().build_snapshot()
        report = PushReportService().build_markdown(snapshot)

        self.assertIn("## 新闻", report)
        self.assertIn("## 宏观指标", report)
        self.assertIn("## 市场模型", report)
        self.assertIn("## 事件展望", report)

    def test_push_job_survives_partial_notifier_failure(self):
        result = run_push_job(
            config=FakeConfig(),
            dashboard_service=DashboardService(),
            report_service=PushReportService(),
            notifier_specs=[
                ("email", SuccessNotifier),
                ("slack", FailingNotifier),
            ],
        )

        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
