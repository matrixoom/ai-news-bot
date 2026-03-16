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
            f"Generated at: {snapshot.generated_at}",
            "",
            "## News",
        ]

        for section in snapshot.news_sections:
            lines.append(f"### {section.title}")
            for item in section.items:
                lines.append(f"- {item.title} | {item.source} | {item.published_at} | {item.tag}")
            lines.append("")

        lines.extend(
            [
                "## Macro Indicators",
                "",
                "| Indicator | Value | Previous | Trend | Updated |",
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
                "## Market Models",
                "",
                "| Index | Close | MA20 | Deviation | Fishbowl |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for card in snapshot.market_sections:
            lines.append(
                f"| {card.label} | {card.close_value} | {card.ma20_value} | {card.deviation_pct} | {card.signal} |"
            )

        lines.extend(["", "## Events Outlook", ""])
        for section in snapshot.event_sections:
            lines.append(f"### {section.title}")
            for item in section.items:
                lines.append(f"- {item.title} | {item.time_window} | {item.confidence} | {item.source}")
            lines.append("")

        lines.extend(["## Data Status", ""])
        for item in snapshot.data_status:
            lines.append(f"- {item.label}: {item.status} - {item.detail}")

        return "\n".join(lines)
