"""Events and policy outlook service."""
from datetime import UTC, date, datetime
from typing import Callable, Sequence

from ..domain.events_outlook import EventsOutlookSnapshot, OutlookEventView, OutlookWindowView, build_default_outlook_horizons
from ..domain.external_data import ConfidenceLevel, EventHorizon
from ..providers import ResearchProvider


class EventsOutlookService:
    """Collect and filter source-backed events for dashboard display."""

    def __init__(
        self,
        *,
        research_provider: ResearchProvider,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._research_provider = research_provider
        self._now_factory = now_factory or (lambda: datetime.now(UTC))

    def build_snapshot(self, *, as_of: date | None = None, topics: Sequence[str] | None = None) -> EventsOutlookSnapshot:
        """Build one outlook snapshot across all configured time windows."""
        current_time = self._now_factory()
        effective_as_of = as_of or current_time.date()
        effective_topics = tuple(topics or ("policy", "macro", "meeting"))

        windows = []
        for horizon in build_default_outlook_horizons():
            findings = self._research_provider.collect_outlook(
                horizon=horizon,
                topics=effective_topics,
                as_of=effective_as_of,
            )
            filtered = [
                finding
                for finding in findings
                if finding.sources and finding.confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}
            ]
            windows.append(
                OutlookWindowView(
                    key=horizon.value,
                    title=self._title_for_horizon(horizon),
                    status="live" if filtered else "degraded",
                    items=[
                        OutlookEventView(
                            title=finding.title,
                            category="policy_outlook",
                            region=finding.region,
                            expected_date=finding.expected_date,
                            time_window=self._title_for_horizon(horizon),
                            confidence=finding.confidence,
                            impact_summary=finding.summary,
                            source=finding.sources[0].title,
                        )
                        for finding in filtered
                    ],
                )
            )

        return EventsOutlookSnapshot(
            generated_at=current_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            windows=windows,
        )

    def _title_for_horizon(self, horizon: EventHorizon) -> str:
        titles = {
            EventHorizon.NEXT_7_DAYS: "Next 7 Days",
            EventHorizon.NEXT_30_DAYS: "Next 30 Days",
            EventHorizon.NEXT_90_DAYS: "Next 90 Days",
            EventHorizon.NEXT_180_DAYS: "Next 180 Days",
        }
        return titles[horizon]
