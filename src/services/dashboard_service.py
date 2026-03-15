"""Dashboard service that provides the first shared contract for web and push layers."""
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import List


@dataclass(frozen=True)
class DashboardSection:
    """A lightweight section contract for the initial dashboard shell."""

    key: str
    title: str
    status: str
    description: str


@dataclass(frozen=True)
class DashboardSnapshot:
    """Structured dashboard data shared across the web and push entrypoints."""

    generated_at: str
    title: str
    summary: str
    sections: List[DashboardSection]


class DashboardService:
    """Provide the initial dashboard snapshot during migration."""

    def build_snapshot(self) -> DashboardSnapshot:
        """Return a minimal but structured dashboard snapshot."""
        sections = [
            DashboardSection(
                key="news",
                title="News Intelligence",
                status="planned",
                description="Tech, finance, and politics news pipeline will be migrated here.",
            ),
            DashboardSection(
                key="macro",
                title="Macro Indicators",
                status="planned",
                description="Macro indicators registry and provider-based ingestion are pending.",
            ),
            DashboardSection(
                key="market",
                title="Market Models",
                status="planned",
                description="Index tracking, MA20, and fishbowl model outputs will live here.",
            ),
            DashboardSection(
                key="events",
                title="Events And Policy Outlook",
                status="planned",
                description="Upcoming meetings and policy outlook will be added after the data layer.",
            ),
            DashboardSection(
                key="push",
                title="Push Automation",
                status="compatible",
                description="Legacy push flow still runs through the new jobs layer.",
            ),
        ]

        return DashboardSnapshot(
            generated_at=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            title="Finance And Policy Intelligence Dashboard",
            summary="Architecture migration is in progress. Web and push will converge on shared services.",
            sections=sections,
        )
