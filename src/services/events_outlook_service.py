"""Events and policy outlook service."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import os
from pathlib import Path
from typing import Callable, Sequence

from ..domain.events_outlook import (
    EventsOutlookSnapshot,
    OutlookEventView,
    OutlookWindowView,
    build_default_outlook_horizons,
    build_default_outlook_official_links,
)
from ..domain.external_data import ConfidenceLevel, EventHorizon
from ..providers.contracts import ProviderAvailability
from ..providers import ResearchProvider
from .events_outlook_store import EventsOutlookStore


class EventsOutlookService:
    """Collect and filter source-backed events for dashboard display."""

    def __init__(
        self,
        *,
        research_provider: ResearchProvider,
        store: EventsOutlookStore | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._research_provider = research_provider
        default_db_path = Path(os.getenv("EVENTS_OUTLOOK_DB_PATH", ".data/events_outlook.db"))
        self._store = store or EventsOutlookStore(default_db_path)
        self._now_factory = now_factory or (lambda: datetime.now(UTC))

    def build_snapshot(
        self,
        *,
        as_of: date | None = None,
        topics: Sequence[str] | None = None,
        refresh_store: bool = False,
    ) -> EventsOutlookSnapshot:
        """Build one outlook snapshot across all configured time windows."""
        current_time = self._now_factory()
        effective_as_of = as_of or current_time.date()
        effective_topics = tuple(topics or ("policy", "macro", "meeting"))
        provider_not_live = self._provider_is_not_live()
        if refresh_store:
            refreshed = self.refresh_store(as_of=effective_as_of, topics=effective_topics)
            has_stored_records = self._store.has_records()
            if refreshed == 0 and not has_stored_records and provider_not_live:
                return self._empty_snapshot(current_time=current_time)
        elif not self._store.has_records():
            return self._empty_snapshot(current_time=current_time)

        max_expected_date = effective_as_of + timedelta(days=self._days_for_horizon(EventHorizon.NEXT_180_DAYS))
        stored_findings = self._store.load_future_findings(
            as_of=effective_as_of,
            max_expected_date=max_expected_date,
        )
        grouped_findings = {horizon: [] for horizon in build_default_outlook_horizons()}
        for finding in stored_findings:
            horizon = self._horizon_for_expected_date(finding.expected_date, as_of=effective_as_of)
            if horizon is None:
                continue
            if finding.confidence not in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}:
                continue
            grouped_findings[horizon].append(finding)

        official_links = list(build_default_outlook_official_links())
        windows = []
        for horizon in build_default_outlook_horizons():
            filtered = sorted(
                grouped_findings[horizon],
                key=lambda finding: self._sort_key_for_date(finding.expected_date),
            )
            windows.append(
                OutlookWindowView(
                    key=horizon.value,
                    title=self._title_for_horizon(horizon),
                    status="degraded" if provider_not_live else ("live" if filtered else "degraded"),
                    items=[
                        OutlookEventView(
                            title=finding.title,
                            category="policy_outlook",
                            region=finding.region,
                            expected_date=finding.expected_date,
                            time_window=self._title_for_horizon(horizon),
                            confidence=finding.confidence,
                            impact_summary=finding.summary,
                            source=finding.source_title or finding.provider,
                        )
                        for finding in filtered
                    ],
                    official_links=list(official_links),
                )
            )

        return EventsOutlookSnapshot(
            generated_at=current_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            windows=windows,
            official_links=official_links,
        )

    def refresh_store(self, *, as_of: date | None = None, topics: Sequence[str] | None = None) -> int:
        current_time = self._now_factory()
        effective_as_of = as_of or current_time.date()
        effective_topics = tuple(topics or ("policy", "macro", "meeting"))
        collected_at = current_time.isoformat(timespec="seconds").replace("+00:00", "Z")
        findings = []
        for horizon in build_default_outlook_horizons():
            findings.extend(
                self._research_provider.collect_outlook(
                    horizon=horizon,
                    topics=effective_topics,
                    as_of=effective_as_of,
                )
            )
        return self._store.upsert_findings(findings, collected_at=collected_at)

    def _title_for_horizon(self, horizon: EventHorizon) -> str:
        titles = {
            EventHorizon.NEXT_7_DAYS: "\u672a\u6765 7 \u5929",
            EventHorizon.NEXT_30_DAYS: "\u672a\u6765 30 \u5929",
            EventHorizon.NEXT_90_DAYS: "\u672a\u6765 90 \u5929",
            EventHorizon.NEXT_180_DAYS: "\u672a\u6765 180 \u5929",
        }
        return titles[horizon]

    def _horizon_for_expected_date(self, expected_date: str, *, as_of: date) -> EventHorizon | None:
        parsed = self._parse_expected_date(expected_date)
        if parsed is None:
            return None
        delta_days = (parsed - as_of).days
        if delta_days < 0:
            return None
        if delta_days <= self._days_for_horizon(EventHorizon.NEXT_7_DAYS):
            return EventHorizon.NEXT_7_DAYS
        if delta_days <= self._days_for_horizon(EventHorizon.NEXT_30_DAYS):
            return EventHorizon.NEXT_30_DAYS
        if delta_days <= self._days_for_horizon(EventHorizon.NEXT_90_DAYS):
            return EventHorizon.NEXT_90_DAYS
        if delta_days <= self._days_for_horizon(EventHorizon.NEXT_180_DAYS):
            return EventHorizon.NEXT_180_DAYS
        return None

    def _sort_key_for_date(self, expected_date: str) -> tuple[int, str]:
        parsed = self._parse_expected_date(expected_date)
        if parsed is None:
            return (1, expected_date or "")
        return (0, parsed.isoformat())

    def _parse_expected_date(self, value: str) -> date | None:
        try:
            return date.fromisoformat((value or "").strip())
        except ValueError:
            return None

    def _days_for_horizon(self, horizon: EventHorizon) -> int:
        days = {
            EventHorizon.NEXT_7_DAYS: 7,
            EventHorizon.NEXT_30_DAYS: 30,
            EventHorizon.NEXT_90_DAYS: 90,
            EventHorizon.NEXT_180_DAYS: 180,
        }
        return days[horizon]

    def _provider_is_not_live(self) -> bool:
        try:
            status = self._research_provider.healthcheck()
        except Exception:
            return False
        availability = getattr(status, "availability", None)
        return availability != ProviderAvailability.LIVE and str(availability) != ProviderAvailability.LIVE.value

    def _empty_snapshot(self, *, current_time: datetime) -> EventsOutlookSnapshot:
        official_links = list(build_default_outlook_official_links())
        windows = [
            OutlookWindowView(
                key=horizon.value,
                title=self._title_for_horizon(horizon),
                status="degraded",
                items=[],
                official_links=list(official_links),
            )
            for horizon in build_default_outlook_horizons()
        ]
        return EventsOutlookSnapshot(
            generated_at=current_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            windows=windows,
            official_links=official_links,
        )
