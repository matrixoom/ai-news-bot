"""Build unified push reports from the dashboard snapshot."""
from typing import List

from .dashboard_service import DashboardSnapshot


class PushReportService:
    """Render dashboard data into a compact markdown report."""

    def build_subject(self, snapshot: DashboardSnapshot, language: str = "en") -> str:
        suffix = f" [{language.upper()}]" if language != "en" else ""
        return f"{snapshot.title} - {snapshot.generated_at[:10]}{suffix}"

    def build_markdown(self, snapshot: DashboardSnapshot, language: str = "en") -> str:
        lines: List[str] = [
            f"# {snapshot.title}",
            "",
            f"生成时间：{snapshot.generated_at}",
            "",
            "## 新闻",
        ]

        for section in snapshot.news_sections:
            lines.append(f"### {section.title}")
            for item in section.items:
                lines.append(f"- {item.title} | {item.source} | {item.published_at} | {item.tag}")
            lines.append("")

        lines.extend(
            [
                "## 宏观指标",
                "",
                "| 指标 | 当前值 | 前值 | 趋势 | 更新时间 |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for card in snapshot.macro_sections:
            lines.append(
                f"| {card.label} | {card.value} | {card.previous_value} | {card.trend} | {card.updated_at} |"
            )

        lines.extend(
            [
                "",
                "## 市场模型",
                "",
                "| 指数 | 收盘 | MA20 | 偏离 | Fishbowl |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for card in snapshot.market_sections:
            lines.append(
                f"| {card.label} | {card.close_value} | {card.ma20_value} | {card.deviation_pct} | {card.signal} |"
            )

        lines.extend(["", "## 事件展望", ""])
        for section in snapshot.event_sections:
            lines.append(f"### {section.title}")
            for item in section.items:
                lines.append(f"- {item.title} | {item.time_window} | {item.confidence} | {item.source}")
            lines.append("")

        lines.extend(["## 数据状态", ""])
        for item in snapshot.data_status:
            lines.append(f"- {item.label}: {item.status} - {item.detail}")

        return "\n".join(lines)
