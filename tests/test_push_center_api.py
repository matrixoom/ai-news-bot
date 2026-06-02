import json
import logging
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app.web import create_fastapi_app
from src.services import DashboardService
from src.services.dashboard_service import MarketCard
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

    def build_markdown(self, snapshot, module_ids=None, language="en", market_chart_range="1y"):
        _ = (module_ids, language, market_chart_range)
        return f"text-{snapshot.generated_at}"

    def build_email_html(self, snapshot, module_ids=None, layout="newspaper", market_chart_range="1y"):
        _ = (module_ids, layout, market_chart_range)
        return f"<p>{snapshot.generated_at}</p>"


class ModuleOnlyDashboardService:
    def __init__(self):
        self.build_snapshot_calls = []
        self.build_market_module_calls = []

    def build_snapshot(self, *, force_refresh=False):
        self.build_snapshot_calls.append(force_refresh)
        raise AssertionError("full dashboard snapshot should not be used for module-scoped push preview")

    def build_market_module(self, *, force_refresh=False):
        self.build_market_module_calls.append(force_refresh)
        return (
            "2026-03-24T08:00:00Z",
            [
                MarketCard(
                    key="csi300",
                    label="娌繁300",
                    close_value="3900",
                    ma20_value="3850",
                    signal="neutral",
                    status="live",
                    trade_date="2026-03-24",
                    deviation_pct="+1.3%",
                    source_label="akshare",
                    explanation="璇存槑",
                    chart_points=[],
                )
            ],
        )

    def stop_background_refresh(self):
        return None


class ChartRefreshDashboardService(ModuleOnlyDashboardService):
    """模拟逐指数刷新，并记录推送中心是否使用专用重建入口。"""

    def __init__(self):
        super().__init__()
        self.rebuild_market_module_calls = 0

    def rebuild_market_module(self, *, progress_callback=None):
        """汇报两项进度后返回刷新后的市场模块。"""
        self.rebuild_market_module_calls += 1
        if progress_callback is not None:
            progress_callback(
                {
                    "symbol": "CSI300",
                    "label": "沪深300",
                    "status": "completed",
                    "completed": 1,
                    "total": 2,
                    "message": "沪深300 刷新完成。",
                }
            )
            progress_callback(
                {
                    "symbol": "CSI500",
                    "label": "中证500",
                    "status": "completed",
                    "completed": 2,
                    "total": 2,
                    "message": "中证500 刷新完成。",
                }
            )
        return self.build_market_module(force_refresh=True)


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

    def test_push_config_defaults_market_chart_range_to_one_year(self):
        """校验旧配置缺少范围字段时自动兼容为近一年。"""
        saved = self._read_json(self.config_path)
        saved.pop("market_chart_range")
        self.config_path.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")

        payload = self.client.get("/api/frontend/modules/push").json()

        config = payload["module"]["details"][0]["section"]["config"]

        self.assertEqual(config["market_chart_range"], "1y")

    def test_push_config_defaults_blank_market_chart_range_to_one_year(self):
        """校验空白范围按兼容规则回退为近一年。"""
        response = self.client.put(
            "/api/push/config",
            json={"config": {"market_chart_range": "   "}},
        )

        self.assertEqual(response.status_code, 200)
        saved = self._read_json(self.config_path)
        self.assertEqual(saved["market_chart_range"], "1y")

    def test_push_config_persists_market_chart_range(self):
        """校验合法范围会写入配置文件并返回给前端。"""
        response = self.client.put(
            "/api/push/config",
            json={"config": {"market_chart_range": "3y"}},
        )

        self.assertEqual(response.status_code, 200)
        saved = self._read_json(self.config_path)
        self.assertEqual(saved["market_chart_range"], "3y")

    def test_push_config_rejects_invalid_market_chart_range(self):
        """校验非法范围快速失败，避免静默回退到错误推送区间。"""
        for invalid_range in ("5y", False, 0):
            with self.subTest(invalid_range=invalid_range):
                response = self.client.put(
                    "/api/push/config",
                    json={"config": {"market_chart_range": invalid_range}},
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"error": "push_config_update_failed"})

    def test_push_config_invalid_market_chart_range_does_not_leak_into_logs(self):
        """校验非法范围不会通过异常链污染 API 日志。"""
        marker = "push_range_log_injection_marker"
        invalid_range = f"5y\n{marker}"

        with self.assertLogs("src.app.web.fastapi_app", level="ERROR") as captured:
            response = self.client.put(
                "/api/push/config",
                json={"config": {"market_chart_range": invalid_range}},
            )

        logs = "\n".join(logging.Formatter().format(record) for record in captured.records)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "push_config_update_failed"})
        self.assertNotIn(marker, logs)
        self.assertNotIn(invalid_range, logs)

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

    def test_frontend_push_module_can_skip_preview_for_history_tab(self):
        dashboard_service = ModuleOnlyDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "history-payload.json",
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
            response = client.get("/api/frontend/modules/push?include_preview=0")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertFalse(payload["module"]["details"][0]["section"]["preview"]["ok"])
            self.assertEqual(
                payload["module"]["details"][0]["section"]["preview"]["error"],
                "preview_not_requested",
            )
            self.assertEqual(dashboard_service.build_snapshot_calls, [])
        finally:
            client.close()
            push_service.stop_scheduler()

    def test_preview_response_uses_selected_module_snapshot_when_available(self):
        dashboard_service = ModuleOnlyDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "module-preview.json",
            enable_scheduler=False,
            email_notifier_factory=RecordingEmailNotifier,
        )

        try:
            result = push_service.build_preview_response(
                {
                    "selected_module_ids": ["market"],
                    "report_style": "newspaper",
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

            self.assertTrue(result["preview"]["ok"])
            self.assertEqual(dashboard_service.build_snapshot_calls, [])
            self.assertEqual(dashboard_service.build_market_module_calls, [True])
        finally:
            push_service.stop_scheduler()

    def test_preview_response_keeps_module_snapshot_title_readable(self):
        class ReadableDashboardService:
            def __init__(self):
                self.build_snapshot_calls = []
                self.build_market_module_calls = []

            def build_snapshot(self, *, force_refresh=False):
                self.build_snapshot_calls.append(force_refresh)
                raise AssertionError("full dashboard snapshot should not be used for readable-title preview")

            def build_market_module(self, *, force_refresh=False):
                self.build_market_module_calls.append(force_refresh)
                return (
                    "2026-03-24T08:00:00Z",
                    [
                        MarketCard(
                            key="csi300",
                            label="\u6caa\u6df1300",
                            close_value="3900",
                            ma20_value="3850",
                            signal="neutral",
                            status="live",
                            trade_date="2026-03-24",
                            deviation_pct="+1.3%",
                            source_label="akshare",
                            explanation="\u8bf4\u660e",
                            chart_points=[],
                        )
                    ],
                )

            def stop_background_refresh(self):
                return None

        dashboard_service = ReadableDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            config_path=self.temp_dir / "module-preview-readable.json",
            enable_scheduler=False,
            email_notifier_factory=RecordingEmailNotifier,
        )

        try:
            result = push_service.build_preview_response(
                {
                    "selected_module_ids": ["market"],
                    "report_style": "newspaper",
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

            self.assertTrue(result["preview"]["ok"])
            self.assertIn(
                "\u8d22\u7ecf\u4e0e\u653f\u7b56\u60c5\u62a5\u4eea\u8868\u76d8",
                result["preview"]["subject"],
            )
            self.assertIn(
                "\u63a8\u9001\u9884\u89c8\u4ec5\u6784\u5efa\u5df2\u9009\u6a21\u5757",
                result["preview"]["html_body"],
            )
            self.assertEqual(dashboard_service.build_snapshot_calls, [])
            self.assertEqual(dashboard_service.build_market_module_calls, [True])
        finally:
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
                        "times": ["08:00", "12:05", "17:00"],
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
        self.assertEqual(saved_config["schedules"][0]["times"], ["08:00", "12:05", "17:00"])

        preview_response = self.client.post("/api/push/preview", json=payload)
        self.assertEqual(preview_response.status_code, 200)
        preview_json = preview_response.json()
        self.assertTrue(preview_json["preview"]["ok"])
        self.assertEqual(preview_json["preview"]["market_chart_range"], "1y")
        self.assertIn("市场日报", preview_json["preview"]["html_body"])
        self.assertIn("Fishbowl Summary", preview_json["preview"]["html_body"])
        self.assertIn("1Y Trend", preview_json["preview"]["html_body"])
        self.assertIn("Close", preview_json["preview"]["html_body"])
        self.assertIn("M20", preview_json["preview"]["html_body"])
        self.assertIn("偏离", preview_json["preview"]["html_body"])
        self.assertIn("Volume", preview_json["preview"]["html_body"])
        self.assertIn('role="presentation"', preview_json["preview"]["html_body"])
        self.assertIn('style="display:block;max-width:100%;min-height:126', preview_json["preview"]["html_body"])
        self.assertIn("@media only screen and (max-width: 480px)", preview_json["preview"]["html_body"])
        self.assertIn("email-two-up-col", preview_json["preview"]["html_body"])
        self.assertIn("max-width:50%", preview_json["preview"]["html_body"])
        self.assertNotIn("组合图与市场模型保持一致", preview_json["preview"]["html_body"])
        self.assertIn("## 市场模型", preview_json["preview"]["text_body"])
        self.assertIn("### 近1年趋势", preview_json["preview"]["text_body"])

    def test_market_chart_refresh_endpoint_reports_progress_and_returns_redrawn_preview(self):
        """校验专用图表刷新任务会异步返回进度与刷新后的预览。"""
        dashboard_service = ChartRefreshDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "chart-refresh.json",
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
            start_response = client.post(
                "/api/push/market-chart-refresh",
                json={"config": {"selected_module_ids": ["market"], "schedules": []}},
            )

            self.assertEqual(start_response.status_code, 202)
            job_id = start_response.json()["job"]["id"]
            result = None
            for _ in range(30):
                result = client.get(f"/api/push/market-chart-refresh/{job_id}").json()["job"]
                if result["status"] == "completed":
                    break
                time.sleep(0.01)

            self.assertIsNotNone(result)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["completed"], 2)
            self.assertEqual(result["total"], 2)
            self.assertTrue(result["preview"]["ok"])
            self.assertEqual(dashboard_service.rebuild_market_module_calls, 1)
        finally:
            client.close()
            push_service.stop_scheduler()

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

    def test_manual_trigger_sends_same_preview_payload_as_email_body(self):
        push_service = PushCenterService(
            dashboard_service=RecordingDashboardService(),
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "manual-preview-sync.json",
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
            self.assertEqual(len(RecordingEmailNotifier.sent_messages), 1)
            self.assertEqual(
                RecordingEmailNotifier.sent_messages[0]["html_content"],
                result["preview"]["html_body"],
            )
            self.assertEqual(
                RecordingEmailNotifier.sent_messages[0]["content"],
                result["preview"]["text_body"],
            )
        finally:
            push_service.stop_scheduler()

    def test_manual_trigger_reuses_matching_preview_payload_from_request(self):
        """校验手动发送在预览与当前配置一致时复用页面已展示的内容。"""
        push_service = PushCenterService(
            dashboard_service=RecordingDashboardService(),
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "manual-preview-request-sync.json",
            enable_scheduler=False,
            email_notifier_factory=RecordingEmailNotifier,
        )
        try:
            preview_payload = {
                "ok": True,
                "generated_at": "2026-03-24T09:00:00Z",
                "subject": "preview-subject",
                "text_body": "preview-text",
                "html_body": "<p>preview-html</p>",
                "style": "newspaper",
                "market_chart_range": "1y",
                "selected_module_ids": ["market"],
            }
            result = push_service.trigger_push(
                {
                    "config": {
                        "selected_module_ids": ["market"],
                        "report_style": "newspaper",
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
                    },
                    "preview": preview_payload,
                }
            )

            self.assertTrue(result["ok"])
            self.assertEqual(len(RecordingEmailNotifier.sent_messages), 1)
            self.assertEqual(
                RecordingEmailNotifier.sent_messages[0]["html_content"],
                preview_payload["html_body"],
            )
            self.assertEqual(
                RecordingEmailNotifier.sent_messages[0]["content"],
                preview_payload["text_body"],
            )
            self.assertEqual(result["preview"]["subject"], preview_payload["subject"])
            self.assertEqual(result["preview"]["market_chart_range"], "1y")
        finally:
            push_service.stop_scheduler()

    def test_manual_trigger_rebuilds_preview_when_market_chart_range_does_not_match(self):
        """校验预览范围与当前配置不一致时放弃复用并重新构建。"""
        dashboard_service = RecordingDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "manual-preview-range-mismatch.json",
            enable_scheduler=False,
            email_notifier_factory=RecordingEmailNotifier,
        )
        try:
            preview_payload = {
                "ok": True,
                "generated_at": "2026-03-24T09:00:00Z",
                "subject": "stale-preview-subject",
                "text_body": "stale-preview-text",
                "html_body": "<p>stale-preview-html</p>",
                "style": "newspaper",
                "market_chart_range": "3y",
                "selected_module_ids": ["market"],
            }
            result = push_service.trigger_push(
                {
                    "config": {
                        "selected_module_ids": ["market"],
                        "report_style": "newspaper",
                        "market_chart_range": "1y",
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
                    },
                    "preview": preview_payload,
                }
            )

            self.assertTrue(result["ok"])
            self.assertEqual(dashboard_service.force_refresh_calls, [True])
            self.assertNotEqual(
                RecordingEmailNotifier.sent_messages[0]["html_content"],
                preview_payload["html_body"],
            )
            self.assertEqual(result["preview"]["market_chart_range"], "1y")
        finally:
            push_service.stop_scheduler()

    def test_manual_trigger_rebuilds_preview_when_market_chart_range_is_invalid(self):
        """校验损坏的可选预览范围只会触发重建，不会阻断正常发送。"""
        dashboard_service = RecordingDashboardService()
        push_service = PushCenterService(
            dashboard_service=dashboard_service,
            report_service=StubPushReportService(),
            config_path=self.temp_dir / "manual-preview-range-invalid.json",
            enable_scheduler=False,
            email_notifier_factory=RecordingEmailNotifier,
        )
        try:
            marker = "push_preview_range_log_injection_marker"
            invalid_range = f"5y\n{marker}"
            preview_payload = {
                "ok": True,
                "generated_at": "2026-03-24T09:00:00Z",
                "subject": "broken-preview-subject",
                "text_body": "broken-preview-text",
                "html_body": "<p>broken-preview-html</p>",
                "style": "newspaper",
                "market_chart_range": invalid_range,
                "selected_module_ids": ["market"],
            }
            with self.assertLogs("src.services.push_center_service", level="WARNING") as captured:
                result = push_service.trigger_push(
                    {
                        "config": {
                            "selected_module_ids": ["market"],
                            "report_style": "newspaper",
                            "market_chart_range": "1y",
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
                        },
                        "preview": preview_payload,
                    }
                )

            logs = "\n".join(logging.Formatter().format(record) for record in captured.records)
            self.assertTrue(result["ok"])
            self.assertEqual(dashboard_service.force_refresh_calls, [True])
            self.assertNotEqual(
                RecordingEmailNotifier.sent_messages[0]["html_content"],
                preview_payload["html_body"],
            )
            self.assertEqual(result["preview"]["market_chart_range"], "1y")
            self.assertIn("ignored requested preview with invalid market_chart_range", logs)
            self.assertNotIn(marker, logs)
            self.assertNotIn(invalid_range, logs)
        finally:
            push_service.stop_scheduler()

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
