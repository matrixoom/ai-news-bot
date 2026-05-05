import unittest

from src.app.jobs.push_job import run_push_job
from src.services import DashboardService, PushReportService
from src.services.dashboard_service import (
    DashboardSection,
    DashboardSnapshot,
    DataStatusItem,
    MarketCard,
    SummaryBlock,
)


class FakeConfig:
    ai_response_languages = ["en"]
    notification_methods = ["email", "slack"]
    log_level = "INFO"
    log_format = "%(message)s"


class SuccessNotifier:
    sent_payloads = []

    def send(self, content, **kwargs):
        type(self).sent_payloads.append({"content": content, "kwargs": kwargs})
        return True


class FailingNotifier:
    def send(self, content, **kwargs):
        return False


class RecordingDashboardService:
    def __init__(self):
        self.force_refresh_calls = []

    def build_snapshot(self, *, force_refresh=False):
        self.force_refresh_calls.append(force_refresh)
        return type("Snapshot", (), {"generated_at": "2026-03-24T08:00:00Z"})()


class StubReportService:
    def build_subject(self, snapshot, language="en"):
        return f"{language}:{snapshot.generated_at}"

    def build_markdown(self, snapshot, language="en", module_ids=None):
        _ = module_ids
        return f"report-{language}-{snapshot.generated_at}"

    def build_email_html(self, snapshot, module_ids=None, layout="newspaper"):
        _ = (module_ids, layout)
        return f"<p>html-{snapshot.generated_at}</p>"

class PushWorkflowTests(unittest.TestCase):
    def setUp(self):
        SuccessNotifier.sent_payloads = []

    def test_report_service_builds_unified_markdown(self):
        snapshot = DashboardService().build_snapshot()
        report = PushReportService().build_markdown(snapshot)

        self.assertIn("## 新闻", report)
        self.assertIn("## 宏观指标", report)
        self.assertIn("## 市场模型", report)
        self.assertIn("## 事件展望", report)

    def test_report_service_renders_market_signal_in_chinese(self):
        snapshot = DashboardSnapshot(
            generated_at="2026-03-26T08:00:00Z",
            news_mode="hybrid",
            title="日报",
            summary="概览",
            sections=[DashboardSection("market", "市场模型", "live", "desc")],
            dashboard_summary=SummaryBlock(
                title="日报",
                subtitle="概览",
                as_of_label="2026-03-26",
                coverage_note="",
                highlights=[],
            ),
            news_sections=[],
            macro_sections=[],
            market_sections=[
                MarketCard(
                    key="csi300",
                    label="沪深300",
                    close_value="3900",
                    ma20_value="3850",
                    signal="neutral",
                    status="live",
                    trade_date="2026-03-26",
                    deviation_pct="+1.3%",
                    source_label="akshare",
                    explanation="说明",
                    chart_points=[],
                )
            ],
            event_sections=[],
            data_status=[DataStatusItem("market", "市场模型", "live", "ok")],
        )

        report = PushReportService().build_markdown(snapshot, module_ids=["market"])
        html = PushReportService().build_email_html(snapshot, module_ids=["market"])

        self.assertIn("中性", report)
        self.assertNotIn("neutral", report)
        self.assertIn("中性", html)
        self.assertNotIn(">neutral<", html)
        self.assertIn("信号 ", html)
        self.assertIn(">?</span>", html)
        self.assertIn("信号定义: 基于最新收盘价相对 MA20 的位置与乖离率生成", html)
        self.assertIn("计算公式: 乖离率 = (收盘价 - MA20) / MA20 * 100%", html)
        self.assertIn("前提: 至少需要 20 个交易日数据才能计算 MA20 和信号", html)
        self.assertIn("突破: 标准: 最新乖离率 >= +3.0%", html)
        self.assertIn("偏强: 标准: 0.0% <= 最新乖离率 < +3.0%", html)
        self.assertIn("中性: 标准: -3.0% <= 最新乖离率 < 0.0%", html)
        self.assertIn("承压: 标准: 最新乖离率 < -3.0%", html)

    def test_report_service_keeps_chart_tail_aligned_with_market_table(self):
        service = PushReportService()
        card = MarketCard(
            key="csi300",
            label="娌繁300",
            close_value="3900",
            ma20_value="3850",
            signal="neutral",
            status="live",
            trade_date="2026-03-26",
            deviation_pct="+1.3%",
            source_label="akshare",
            explanation="璇存槑",
            chart_points=[
                {
                    "trade_date": "2026-03-24",
                    "close_price": 3810.0,
                    "ma20_price": 3790.0,
                    "deviation_pct": 0.5,
                },
                {
                    "trade_date": "2026-03-25",
                    "close_price": 3825.0,
                    "ma20_price": 3801.0,
                    "deviation_pct": 0.6,
                },
            ],
        )

        trend = service._build_market_trend_summary(card)

        self.assertEqual(trend["latest_label"], "3900.0")
        self.assertEqual(trend["chart_points"][-1]["trade_date"], "2026-03-26")
        self.assertEqual(trend["chart_points"][-1]["close_price"], 3900.0)
        self.assertEqual(trend["chart_points"][-1]["ma20_price"], 3850.0)
        self.assertEqual(trend["chart_points"][-1]["deviation_pct"], 1.3)

    def test_report_service_renders_mobile_scalable_svg_charts(self):
        """校验邮件图表不用固定像素宽度，避免手机邮箱裁切 SVG。"""
        snapshot = DashboardSnapshot(
            generated_at="2026-03-26T08:00:00Z",
            news_mode="hybrid",
            title="日报",
            summary="概览",
            sections=[DashboardSection("market", "市场模型", "live", "desc")],
            dashboard_summary=SummaryBlock(
                title="日报",
                subtitle="概览",
                as_of_label="2026-03-26",
                coverage_note="",
                highlights=[],
            ),
            news_sections=[],
            macro_sections=[],
            market_sections=[
                MarketCard(
                    key="csi300",
                    label="沪深300",
                    close_value="3900",
                    ma20_value="3850",
                    signal="neutral",
                    status="live",
                    trade_date="2026-03-26",
                    deviation_pct="+1.3%",
                    source_label="akshare",
                    explanation="说明",
                    chart_points=[
                        {"trade_date": "2026-03-24", "close_price": 3810.0, "ma20_price": 3790.0, "deviation_pct": 0.5},
                        {"trade_date": "2026-03-25", "close_price": 3825.0, "ma20_price": 3801.0, "deviation_pct": 0.6},
                    ],
                )
            ],
            event_sections=[],
            data_status=[DataStatusItem("market", "市场模型", "live", "ok")],
        )

        html = PushReportService().build_email_html(snapshot, module_ids=["market"])

        self.assertIn('max-width:344px;width:100%;', html)
        self.assertIn("max-width:100%", html)
        self.assertIn('width="344"', html)

    def test_report_service_shrinks_market_summary_table_on_mobile(self):
        """校验手机端市场日报指数表格使用更小字号，降低横向拥挤感。"""
        snapshot = DashboardSnapshot(
            generated_at="2026-03-26T08:00:00Z",
            news_mode="hybrid",
            title="日报",
            summary="概览",
            sections=[DashboardSection("market", "市场模型", "live", "desc")],
            dashboard_summary=SummaryBlock(
                title="日报",
                subtitle="概览",
                as_of_label="2026-03-26",
                coverage_note="",
                highlights=[],
            ),
            news_sections=[],
            macro_sections=[],
            market_sections=[
                MarketCard(
                    key="csi300",
                    label="沪深300",
                    close_value="3900",
                    ma20_value="3850",
                    signal="neutral",
                    status="live",
                    trade_date="2026-03-26",
                    deviation_pct="+1.3%",
                    source_label="akshare",
                    explanation="说明",
                    chart_points=[],
                )
            ],
            event_sections=[],
            data_status=[DataStatusItem("market", "市场模型", "live", "ok")],
        )

        html = PushReportService().build_email_html(snapshot, module_ids=["market"])

        self.assertIn('class="email-market-summary-table"', html)
        self.assertIn(".email-market-summary-table", html)
        self.assertIn("font-size: 8px !important", html)

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

    def test_push_job_forces_snapshot_refresh_before_sending(self):
        dashboard_service = RecordingDashboardService()

        result = run_push_job(
            config=FakeConfig(),
            dashboard_service=dashboard_service,
            report_service=StubReportService(),
            notifier_specs=[
                ("email", SuccessNotifier),
            ],
        )

        self.assertEqual(result, 0)
        self.assertEqual(dashboard_service.force_refresh_calls, [True])

    def test_push_job_uses_html_report_for_email_delivery(self):
        dashboard_service = RecordingDashboardService()

        result = run_push_job(
            config=FakeConfig(),
            dashboard_service=dashboard_service,
            report_service=StubReportService(),
            notifier_specs=[
                ("email", SuccessNotifier),
            ],
        )

        self.assertEqual(result, 0)
        self.assertEqual(len(SuccessNotifier.sent_payloads), 1)
        self.assertEqual(
            SuccessNotifier.sent_payloads[0]["kwargs"]["html_content"],
            "<p>html-2026-03-24T08:00:00Z</p>",
        )


if __name__ == "__main__":
    unittest.main()
