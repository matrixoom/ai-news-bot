from datetime import UTC, date, datetime
import unittest

from src.domain import ConfidenceLevel, EventHorizon
from src.domain.external_data import ResearchFinding, SourceReference
from src.providers import ProviderAvailability, ProviderStatus
from src.services.events_outlook_service import EventsOutlookService


class FakeResearchProvider:
    provider_key = "fake-research"

    def __init__(self, findings_by_horizon):
        self._findings_by_horizon = findings_by_horizon

    def collect_outlook(self, *, horizon, topics, as_of):
        return list(self._findings_by_horizon.get(horizon, ()))

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.LIVE, "ok", "2026-03-15T00:00:00Z")


class Task07DocumentationTests(unittest.TestCase):
    def test_task07_main_doc_links_protocol_and_tests(self):
        with open("TASK/07-events-policy-outlook-and-llm-research.md", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("Completed for implementation phase.", content)
        self.assertIn("07-confidence-and-research-protocol.md", content)
        self.assertIn("tests/test_task07_events_outlook.py", content)


class EventsOutlookServiceTests(unittest.TestCase):
    def test_filters_low_confidence_and_missing_source_items(self):
        service = EventsOutlookService(
            research_provider=FakeResearchProvider(
                {
                    EventHorizon.NEXT_7_DAYS: (
                        ResearchFinding("fake", EventHorizon.NEXT_7_DAYS, "Keep me", "CN", "2026-03-18", "High confidence.", ConfidenceLevel.HIGH, (SourceReference("Official", "https://example.com"),)),
                        ResearchFinding("fake", EventHorizon.NEXT_7_DAYS, "Drop me", "CN", "2026-03-19", "Low confidence.", ConfidenceLevel.LOW, (SourceReference("Weak", "https://weak.example"),)),
                    )
                }
            ),
            now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
        )

        snapshot = service.build_snapshot(as_of=date(2026, 3, 15))

        next_7 = snapshot.windows[0]
        self.assertEqual(next_7.title, "Next 7 Days")
        self.assertEqual(len(next_7.items), 1)
        self.assertEqual(next_7.items[0].title, "Keep me")

    def test_snapshot_contains_all_four_windows(self):
        service = EventsOutlookService(
            research_provider=FakeResearchProvider({}),
            now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
        )

        snapshot = service.build_snapshot(as_of=date(2026, 3, 15))
        self.assertEqual([window.key for window in snapshot.windows], ["7d", "30d", "90d", "180d"])


if __name__ == "__main__":
    unittest.main()
