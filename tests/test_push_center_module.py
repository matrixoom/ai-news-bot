import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.services import DashboardService
from src.services.push_center_service import PushCenterService


class RecordingEmailNotifier:
    sent_messages = []
    init_kwargs = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        type(self).init_kwargs.append(kwargs)

    def send(self, content, subject=None, language="en", html_content=None):
        type(self).sent_messages.append(
            {
                "content": content,
                "subject": subject,
                "language": language,
                "html_content": html_content,
                "config": self.kwargs,
            }
        )
        return True


class RecordingDashboardService:
    def __init__(self):
        self.force_refresh_calls = []

    def build_snapshot(self, *, force_refresh=False):
        self.force_refresh_calls.append(force_refresh)
        return type("Snapshot", (), {"generated_at": "2026-03-24T08:00:00Z"})()

    def stop_background_refresh(self):
        return None


class LoadingDashboardService(RecordingDashboardService):
    def should_serve_loading_module(self, module_id):
        return module_id == "market"

    def get_module_bootstrap_state(self, module_id):
        _ = module_id
        return "refreshing", "后台正在拉取最新数据。"


class StubPushReportService:
    def build_subject(self, snapshot, language="en"):
        _ = language
        return f"subject-{snapshot.generated_at}"

    def build_markdown(self, snapshot, module_ids=None, language="en"):
        _ = (module_ids, language)
        return f"text-{snapshot.generated_at}"

    def build_email_html(self, snapshot, module_ids=None, layout="newspaper"):
        _ = (module_ids, layout)
        return f"<p>{snapshot.generated_at}</p>"


class PushCenterModuleTests(unittest.TestCase):
    def setUp(self):
        RecordingEmailNotifier.sent_messages = []
        RecordingEmailNotifier.init_kwargs = []
        self.temp_dir = Path(".tmp-push-tests") / uuid4().hex
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.temp_dir / "push-center.json"
        self.dashboard_service = DashboardService(enable_background_refresh=False)
        self.push_service = PushCenterService(
            dashboard_service=self.dashboard_service,
            config_path=self.config_path,
            enable_scheduler=False,
            email_notifier_factory=RecordingEmailNotifier,
        )
        self.client = TestClient(
            create_fastapi_app(
                dashboard_service=self.dashboard_service,
                push_center_service=self.push_service,
            )
        )

    def tearDown(self):
        self.client.close()
        self.push_service.stop_scheduler()
        self.dashboard_service.stop_background_refresh()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _read_json(self, path: Path):
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_frontend_push_module_endpoint_returns_workspace_payload(self):
        response = self.client.get("/api/frontend/modules/push")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["refresh_after_ms"], self.push_service.frontend_auto_refresh_ms)
        self.assertEqual(payload["module"]["id"], "push")
        detail = payload["module"]["details"][0]
        self.assertEqual(detail["kind"], "push")
        self.assertIn("config", detail["section"])
        self.assertIn("preview", detail["section"])
        self.assertIn("schedules", detail["section"]["config"])
        self.assertIn("recent_runs", detail["section"])
        self.assertEqual(detail["section"]["recent_runs"], [])
        self.assertTrue(self.config_path.with_name("push-center.template.json").exists())

    def test_frontend_push_module_refresh_forces_latest_preview(self):
        dashboard_service = RecordingDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "refresh-preview.json",
            enable_scheduler=False,
            email_notifier_factory=RecordingEmailNotifier,
        )
        client = TestClient(
            create_fastapi_app(
                dashboard_service=dashboard_service,
                push_center_service=push_service,
            )
        )
        try:
            response = client.get("/api/frontend/modules/push?refresh=1")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(dashboard_service.force_refresh_calls, [True])
        finally:
            client.close()
            push_service.stop_scheduler()

    def test_frontend_push_module_returns_loading_during_selected_module_refresh(self):
        dashboard_service = LoadingDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "loading-preview.json",
            enable_scheduler=False,
            email_notifier_factory=RecordingEmailNotifier,
        )
        client = TestClient(
            create_fastapi_app(
                dashboard_service=dashboard_service,
                push_center_service=push_service,
            )
        )
        try:
            response = client.get("/api/frontend/modules/push")

            self.assertEqual(response.status_code, 202)
            payload = response.json()
            self.assertTrue(payload["module"]["loading"])
            self.assertEqual(payload["module"]["note"], "后台正在拉取最新数据。")
            self.assertEqual(payload["refresh_after_ms"], 2000)
        finally:
            client.close()
            push_service.stop_scheduler()

    def test_push_config_and_preview_endpoints_roundtrip(self):
        payload = {
            "config": {
                "selected_module_ids": ["market"],
                "report_style": "newspaper",
                "email": {
                    "smtp_server": "smtp.example.com",
                    "smtp_port": 2525,
                    "username": "bot@example.com",
                    "password": "secret",
                    "from_address": "bot@example.com",
                    "to_addresses": "desk@example.com",
                    "use_tls": True,
                },
                "schedules": [
                    {
                        "id": "market-am",
                        "name": "市场晨报",
                        "enabled": True,
                        "module_ids": ["market"],
                        "channel_types": ["email"],
                        "times": ["08:00", "12:00", "17:00"],
                        "timezone": "Asia/Shanghai",
                    }
                ],
            }
        }

        config_response = self.client.put("/api/push/config", json=payload)
        self.assertEqual(config_response.status_code, 200)
        config_json = config_response.json()
        self.assertEqual(
            config_json["module"]["details"][0]["section"]["config_path"],
            str(self.config_path),
        )
        email_config = config_json["module"]["details"][0]["section"]["config"]["email"]
        self.assertEqual(email_config["smtp_server"], "smtp.example.com")
        self.assertEqual(email_config["smtp_port"], 2525)
        saved_config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(saved_config["schedules"][0]["times"], ["08:00", "12:00", "17:00"])

        preview_response = self.client.post("/api/push/preview", json=payload)
        self.assertEqual(preview_response.status_code, 200)
        preview_json = preview_response.json()
        self.assertTrue(preview_json["preview"]["ok"])
        self.assertIn("市场日报", preview_json["preview"]["html_body"])
        self.assertIn("Fishbowl Summary", preview_json["preview"]["html_body"])
        self.assertIn("3M Trend", preview_json["preview"]["html_body"])
        self.assertIn("Close", preview_json["preview"]["html_body"])
        self.assertIn("M20", preview_json["preview"]["html_body"])
        self.assertIn("Deviation", preview_json["preview"]["html_body"])
        self.assertIn('role="presentation"', preview_json["preview"]["html_body"])
        self.assertIn('style="display:block;width:100%;max-width:344px;height:auto;"', preview_json["preview"]["html_body"])
        self.assertIn("@media only screen and (max-width: 480px)", preview_json["preview"]["html_body"])
        self.assertIn("email-two-up-col", preview_json["preview"]["html_body"])
        self.assertIn("max-width:50%", preview_json["preview"]["html_body"])
        self.assertNotIn("组合图与市场模型保持一致", preview_json["preview"]["html_body"])
        self.assertIn("## 市场模型", preview_json["preview"]["text_body"])
        self.assertIn("### 近3个月趋势", preview_json["preview"]["text_body"])

    def test_manual_trigger_uses_email_notifier_and_records_run(self):
        payload = {
            "config": {
                "selected_module_ids": ["market"],
                "email": {
                    "smtp_server": "smtp.example.com",
                    "smtp_port": 587,
                    "username": "bot@example.com",
                    "password": "secret",
                    "from_address": "bot@example.com",
                    "to_addresses": "desk@example.com",
                    "use_tls": True,
                },
                "schedules": [],
            }
        }

        response = self.client.post("/api/push/trigger", json=payload)

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["status"], "success")
        self.assertEqual(result["result"]["timezone"], "Asia/Shanghai")
        self.assertTrue(result["result"]["executed_at"].endswith("+08:00"))
        self.assertEqual(len(RecordingEmailNotifier.sent_messages), 1)
        self.assertIn("市场日报", RecordingEmailNotifier.sent_messages[0]["html_content"])
        self.assertEqual(result["recent_runs"][0]["trigger"], "manual")
        self.assertEqual(result["recent_runs"][0]["timezone"], "Asia/Shanghai")
        self.assertTrue(result["recent_runs"][0]["executed_at"].endswith("+08:00"))
        config_json = self._read_json(self.config_path)
        self.assertNotIn("recent_runs", config_json)
        self.assertNotIn("scheduler_history", config_json)
        manual_log_path = self.temp_dir / "logs" / "push-center" / "manual" / result["result"]["executed_at"][:7] / f"{result['result']['executed_at'][:10]}.jsonl"
        self.assertTrue(manual_log_path.exists())

    def test_scheduler_runs_once_per_slot(self):
        self.push_service.update_config(
            {
                "selected_module_ids": ["market"],
                "email": {
                    "smtp_server": "smtp.example.com",
                    "smtp_port": 587,
                    "username": "bot@example.com",
                    "password": "secret",
                    "from_address": "bot@example.com",
                    "to_addresses": "desk@example.com",
                    "use_tls": True,
                },
                "schedules": [
                    {
                        "id": "market-daily",
                        "name": "市场日报",
                        "enabled": True,
                        "module_ids": ["market"],
                        "channel_types": ["email"],
                        "times": ["08:00"],
                        "timezone": "Asia/Shanghai",
                    }
                ],
            }
        )

        slot_time = datetime(2026, 3, 22, 0, 0, tzinfo=UTC)
        first = self.push_service.run_due_jobs(now=slot_time)
        second = self.push_service.run_due_jobs(now=slot_time)

        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["result"]["status"], "success")
        self.assertEqual(first[0]["result"]["timezone"], "Asia/Shanghai")
        self.assertEqual(first[0]["result"]["executed_at"], "2026-03-22T08:00:00+08:00")
        self.assertEqual(first[0]["recent_runs"][0]["executed_at"], "2026-03-22T08:00:00+08:00")
        self.assertEqual(second, [])
        state_json = self._read_json(self.config_path.with_name("push-center.state.json"))
        self.assertIn("market-daily@2026-03-22T08:00", state_json["scheduler_history"])
        config_json = self._read_json(self.config_path)
        self.assertNotIn("scheduler_history", config_json)

    def test_manual_trigger_forces_snapshot_refresh_before_send(self):
        dashboard_service = RecordingDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "refresh-manual.json",
            enable_scheduler=False,
            email_notifier_factory=RecordingEmailNotifier,
        )
        try:
            result = push_service.trigger_push(
                {
                    "selected_module_ids": ["market"],
                    "email": {
                        "smtp_server": "smtp.example.com",
                        "smtp_port": 587,
                        "username": "bot@example.com",
                        "password": "secret",
                        "from_address": "bot@example.com",
                        "to_addresses": "desk@example.com",
                        "use_tls": True,
                    },
                    "schedules": [],
                }
            )

            self.assertTrue(result["ok"])
            self.assertEqual(dashboard_service.force_refresh_calls, [True])
        finally:
            push_service.stop_scheduler()

    def test_scheduled_trigger_forces_snapshot_refresh_before_send(self):
        dashboard_service = RecordingDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "refresh-scheduled.json",
            enable_scheduler=False,
            email_notifier_factory=RecordingEmailNotifier,
        )
        try:
            push_service.update_config(
                {
                    "selected_module_ids": ["market"],
                    "email": {
                        "smtp_server": "smtp.example.com",
                        "smtp_port": 587,
                        "username": "bot@example.com",
                        "password": "secret",
                        "from_address": "bot@example.com",
                        "to_addresses": "desk@example.com",
                        "use_tls": True,
                    },
                    "schedules": [
                        {
                            "id": "market-daily",
                            "name": "Market Daily",
                            "enabled": True,
                            "module_ids": ["market"],
                            "channel_types": ["email"],
                            "times": ["08:00"],
                            "timezone": "Asia/Shanghai",
                        }
                    ],
                }
            )
            dashboard_service.force_refresh_calls.clear()

            results = push_service.run_due_jobs(now=datetime(2026, 3, 24, 0, 0, tzinfo=UTC))

            self.assertEqual(len(results), 1)
            self.assertEqual(dashboard_service.force_refresh_calls, [True])
        finally:
            push_service.stop_scheduler()

    def test_legacy_runtime_data_is_migrated_out_of_config(self):
        legacy_config_path = self.temp_dir / "legacy-push-center.json"
        legacy_payload = {
            "selected_module_ids": ["market"],
            "report_style": "newspaper",
            "email": {
                "enabled": True,
                "label": "Primary Email",
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "use_tls": True,
                "username": "bot@example.com",
                "password": "secret",
                "from_address": "bot@example.com",
                "to_addresses": "desk@example.com",
            },
            "schedules": [],
            "recent_runs": [
                {
                    "executed_at": "2026-03-23T08:00:00+08:00",
                    "timezone": "Asia/Shanghai",
                    "trigger": "manual",
                    "job_name": "手动触发",
                    "status": "success",
                    "detail": "发送完成",
                    "subject": "测试主题",
                    "channel_types": ["email"],
                    "module_ids": ["market"],
                }
            ],
            "scheduler_history": {
                "market-daily@2026-03-23T08:00": "2026-03-23T08:00:00+08:00"
            },
        }
        legacy_config_path.write_text(json.dumps(legacy_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        migrated_service = PushCenterService(
            dashboard_service=self.dashboard_service,
            config_path=legacy_config_path,
            enable_scheduler=False,
            email_notifier_factory=RecordingEmailNotifier,
        )
        try:
            payload = migrated_service.build_module_payload()
            self.assertEqual(len(payload["module"]["details"][0]["section"]["recent_runs"]), 1)
            migrated_config = self._read_json(legacy_config_path)
            self.assertNotIn("recent_runs", migrated_config)
            self.assertNotIn("scheduler_history", migrated_config)
            migrated_state = self._read_json(legacy_config_path.with_name("legacy-push-center.state.json"))
            self.assertIn("market-daily@2026-03-23T08:00", migrated_state["scheduler_history"])
            migrated_log = legacy_config_path.parent / "logs" / "legacy-push-center" / "manual" / "2026-03" / "2026-03-23.jsonl"
            self.assertTrue(migrated_log.exists())
        finally:
            migrated_service.stop_scheduler()


if __name__ == "__main__":
    unittest.main()
