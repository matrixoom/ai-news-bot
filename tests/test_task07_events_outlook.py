from datetime import UTC, date, datetime
import gc
from pathlib import Path
import sqlite3
import time
import unittest
from contextlib import closing, contextmanager
from types import SimpleNamespace
from uuid import uuid4

from src.domain import ConfidenceLevel, EventHorizon
from src.domain.external_data import ResearchFinding, SourceReference
from src.services.events_outlook_service import EventsOutlookService
from src.services.events_outlook_store import EventsOutlookStore


@contextmanager
def isolated_events_store():
    base_dir = Path(".data") / ".test-events-outlook"
    base_dir.mkdir(exist_ok=True)
    db_path = base_dir / f"events-outlook-{uuid4().hex}.db"
    try:
        yield EventsOutlookStore(db_path), db_path
    finally:
        gc.collect()
        for suffix in ("", "-wal", "-shm"):
            path = Path(f"{db_path}{suffix}")
            for _ in range(5):
                if not path.exists():
                    break
                try:
                    path.unlink()
                    break
                except PermissionError:
                    time.sleep(0.05)
                    gc.collect()
        if base_dir.exists():
            try:
                next(base_dir.iterdir())
            except StopIteration:
                base_dir.rmdir()
            except OSError:
                pass


class FakeResearchProvider:
    provider_key = "fake-research"

    def __init__(self, findings_by_horizon):
        self._findings_by_horizon = findings_by_horizon
        self.calls = 0

    def collect_outlook(self, *, horizon, topics, as_of):
        self.calls += 1
        return list(self._findings_by_horizon.get(horizon, ()))

    def healthcheck(self):
        return SimpleNamespace(
            provider_key=self.provider_key,
            availability="live",
            detail="ok",
            checked_at="2026-03-15T00:00:00Z",
        )


class RelativeSampleResearchProvider:
    provider_key = "sample-research"

    def collect_outlook(self, *, horizon, topics, as_of):
        by_horizon = {
            EventHorizon.NEXT_7_DAYS: 2,
            EventHorizon.NEXT_30_DAYS: 14,
            EventHorizon.NEXT_90_DAYS: 45,
            EventHorizon.NEXT_180_DAYS: 120,
        }
        expected_date = date.fromordinal(as_of.toordinal() + by_horizon[horizon]).isoformat()
        return [
            ResearchFinding(
                self.provider_key,
                horizon,
                f"Event {horizon.value}",
                "CN",
                expected_date,
                "Future scheduled event.",
                ConfidenceLevel.HIGH,
                (SourceReference("Official", "https://example.com/calendar"),),
            )
        ]

    def healthcheck(self):
        return SimpleNamespace(
            provider_key=self.provider_key,
            availability="degraded",
            detail="sample",
            checked_at="2026-03-15T00:00:00Z",
        )


class UnavailableResearchProvider:
    provider_key = "unavailable-research"

    def collect_outlook(self, *, horizon, topics, as_of):
        _ = horizon, topics, as_of
        return []

    def healthcheck(self):
        return SimpleNamespace(
            provider_key=self.provider_key,
            availability="unavailable",
            detail="no research provider",
            checked_at="2026-03-15T00:00:00Z",
        )


class Task07DocumentationTests(unittest.TestCase):
    def test_task07_main_doc_links_protocol_and_tests(self):
        with open("TASK/07-events-policy-outlook-and-llm-research.md", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("Completed for implementation phase.", content)
        self.assertIn("07-confidence-and-research-protocol.md", content)
        self.assertIn("tests/test_task07_events_outlook.py", content)


class EventsOutlookServiceTests(unittest.TestCase):
    def test_filters_low_confidence_items(self):
        with isolated_events_store() as (store, _db_path):
            service = EventsOutlookService(
                research_provider=FakeResearchProvider(
                    {
                        EventHorizon.NEXT_7_DAYS: (
                            ResearchFinding(
                                "fake",
                                EventHorizon.NEXT_7_DAYS,
                                "Keep me",
                                "CN",
                                "2026-03-18",
                                "High confidence.",
                                ConfidenceLevel.HIGH,
                                (SourceReference("Official", "https://example.com"),),
                            ),
                            ResearchFinding(
                                "fake",
                                EventHorizon.NEXT_7_DAYS,
                                "Drop me",
                                "CN",
                                "2026-03-19",
                                "Low confidence.",
                                ConfidenceLevel.LOW,
                                (SourceReference("Weak", "https://weak.example"),),
                            ),
                        )
                    }
                ),
                store=store,
                now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(as_of=date(2026, 3, 15))

            next_7 = snapshot.windows[0]
            self.assertEqual(next_7.title, "未来 7 天")
            self.assertEqual(len(next_7.items), 1)
            self.assertEqual(next_7.items[0].title, "Keep me")

    def test_snapshot_contains_all_four_windows(self):
        with isolated_events_store() as (store, _db_path):
            service = EventsOutlookService(
                research_provider=FakeResearchProvider({}),
                store=store,
                now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(as_of=date(2026, 3, 15))

            self.assertEqual([window.key for window in snapshot.windows], ["7d", "30d", "90d", "180d"])

    def test_filters_past_or_out_of_horizon_findings(self):
        with isolated_events_store() as (store, _db_path):
            service = EventsOutlookService(
                research_provider=FakeResearchProvider(
                    {
                        EventHorizon.NEXT_7_DAYS: (
                            ResearchFinding(
                                "fake",
                                EventHorizon.NEXT_7_DAYS,
                                "Past item",
                                "CN",
                                "2026-03-14",
                                "Already happened.",
                                ConfidenceLevel.HIGH,
                                (SourceReference("Official", "https://example.com/past"),),
                            ),
                            ResearchFinding(
                                "fake",
                                EventHorizon.NEXT_7_DAYS,
                                "Too far",
                                "CN",
                                "2026-03-25",
                                "Outside 7d horizon.",
                                ConfidenceLevel.HIGH,
                                (SourceReference("Official", "https://example.com/far"),),
                            ),
                            ResearchFinding(
                                "fake",
                                EventHorizon.NEXT_7_DAYS,
                                "Valid event",
                                "CN",
                                "2026-03-18",
                                "Should remain.",
                                ConfidenceLevel.MEDIUM,
                                (SourceReference("Official", "https://example.com/ok"),),
                            ),
                        )
                    }
                ),
                store=store,
                now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(as_of=date(2026, 3, 15))

            self.assertEqual([item.title for item in snapshot.windows[0].items], ["Valid event"])

    def test_sample_provider_generates_future_dates_relative_to_as_of(self):
        with isolated_events_store() as (store, _db_path):
            service = EventsOutlookService(
                research_provider=RelativeSampleResearchProvider(),
                store=store,
                now_factory=lambda: datetime(2026, 3, 22, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(as_of=date(2026, 3, 22))

            self.assertEqual(snapshot.windows[0].items[0].expected_date, "2026-03-24")
            self.assertEqual(snapshot.windows[1].items[0].expected_date, "2026-04-05")

    def test_build_snapshot_persists_findings_once_then_reuses_store(self):
        provider = FakeResearchProvider(
            {
                EventHorizon.NEXT_7_DAYS: (
                    ResearchFinding(
                        "fake",
                        EventHorizon.NEXT_7_DAYS,
                        "FOMC window",
                        "US",
                        "2026-03-18",
                        "Upcoming Fed communication window.",
                        ConfidenceLevel.HIGH,
                        (SourceReference("Fed calendar", "https://example.com/fed"),),
                    ),
                )
            }
        )
        with isolated_events_store() as (store, _db_path):
            service = EventsOutlookService(
                research_provider=provider,
                store=store,
                now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
            )

            first = service.build_snapshot(as_of=date(2026, 3, 15))
            second = service.build_snapshot(as_of=date(2026, 3, 15))

            self.assertTrue(store.has_records())
            self.assertEqual(provider.calls, 4)
            self.assertEqual(len(first.windows[0].items), 1)
            self.assertEqual(len(second.windows[0].items), 1)
            self.assertEqual(first.windows[0].items[0].title, "FOMC window")

    def test_unavailable_provider_returns_empty_windows_even_if_store_has_records(self):
        with isolated_events_store() as (store, _db_path):
            store.upsert_findings(
                (
                    ResearchFinding(
                        "fake",
                        EventHorizon.NEXT_7_DAYS,
                        "Stale stored event",
                        "US",
                        "2026-03-18",
                        "Old persisted event.",
                        ConfidenceLevel.HIGH,
                        (SourceReference("Fed", "https://example.com/fed"),),
                    ),
                ),
                collected_at="2026-03-15T08:00:00Z",
            )
            service = EventsOutlookService(
                research_provider=UnavailableResearchProvider(),
                store=store,
                now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
            )

            snapshot = service.build_snapshot(as_of=date(2026, 3, 15))

            self.assertTrue(all(not window.items for window in snapshot.windows))

    def test_refresh_store_deduplicates_duplicate_events_across_refreshes(self):
        provider = FakeResearchProvider(
            {
                EventHorizon.NEXT_30_DAYS: (
                    ResearchFinding(
                        "fake",
                        EventHorizon.NEXT_30_DAYS,
                        "US CPI release",
                        "US",
                        "2026-03-28",
                        "Inflation release that can reprice rate expectations.",
                        ConfidenceLevel.HIGH,
                        (SourceReference("BLS", "https://example.com/bls"),),
                    ),
                )
            }
        )
        with isolated_events_store() as (store, _db_path):
            service = EventsOutlookService(
                research_provider=provider,
                store=store,
                now_factory=lambda: datetime(2026, 3, 15, tzinfo=UTC),
            )

            service.refresh_store(as_of=date(2026, 3, 15))
            service.refresh_store(as_of=date(2026, 3, 15))

            stored = store.load_future_findings(
                as_of=date(2026, 3, 15),
                max_expected_date=date(2026, 9, 11),
            )
            snapshot = service.build_snapshot(as_of=date(2026, 3, 15))

            self.assertEqual(len(stored), 1)
            self.assertEqual([item.title for item in snapshot.windows[1].items], ["US CPI release"])


class EventsOutlookStoreTests(unittest.TestCase):
    def test_upsert_deduplicates_normalized_titles_and_updates_seen_count(self):
        with isolated_events_store() as (store, db_path):
            first = ResearchFinding(
                "fake",
                EventHorizon.NEXT_30_DAYS,
                "US CPI Release",
                "US",
                "2026-03-28",
                "First summary.",
                ConfidenceLevel.MEDIUM,
                (SourceReference("BLS", "https://example.com/bls"),),
            )
            duplicate = ResearchFinding(
                "fake",
                EventHorizon.NEXT_30_DAYS,
                "  us   cpi release  ",
                "us",
                "2026-03-28",
                "Updated summary.",
                ConfidenceLevel.HIGH,
                (SourceReference("BLS", "https://example.com/bls"),),
            )

            written = store.upsert_findings((first, duplicate), collected_at="2026-03-15T08:00:00Z")
            loaded = store.load_future_findings(
                as_of=date(2026, 3, 15),
                max_expected_date=date(2026, 4, 30),
            )

            self.assertEqual(written, 2)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].title, "US CPI Release")
            self.assertEqual(loaded[0].summary, "Updated summary.")
            self.assertEqual(loaded[0].confidence, ConfidenceLevel.HIGH)

            with closing(sqlite3.connect(db_path)) as connection:
                row = connection.execute(
                    "SELECT seen_count FROM outlook_findings WHERE expected_date = ?",
                    ("2026-03-28",),
                ).fetchone()

            self.assertEqual(row[0], 2)

    def test_upsert_preserves_existing_source_when_duplicate_has_empty_source(self):
        with isolated_events_store() as (store, _db_path):
            with_source = ResearchFinding(
                "fake",
                EventHorizon.NEXT_90_DAYS,
                "ECB meeting window",
                "EA",
                "2026-05-01",
                "Initial source-backed summary.",
                ConfidenceLevel.MEDIUM,
                (SourceReference("ECB", "https://example.com/ecb"),),
            )
            without_source = ResearchFinding(
                "fake",
                EventHorizon.NEXT_90_DAYS,
                "ECB meeting window",
                "EA",
                "2026-05-01",
                "Refreshed summary without source.",
                ConfidenceLevel.HIGH,
                (),
            )

            store.upsert_findings((with_source,), collected_at="2026-03-15T08:00:00Z")
            store.upsert_findings((without_source,), collected_at="2026-03-15T09:00:00Z")
            loaded = store.load_future_findings(
                as_of=date(2026, 3, 15),
                max_expected_date=date(2026, 7, 1),
            )

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].source_title, "ECB")
            self.assertEqual(loaded[0].source_url, "https://example.com/ecb")
            self.assertEqual(loaded[0].summary, "Refreshed summary without source.")
            self.assertEqual(loaded[0].confidence, ConfidenceLevel.HIGH)

    def test_load_future_findings_filters_range_and_orders_by_date_then_region(self):
        with isolated_events_store() as (store, _db_path):
            findings = (
                ResearchFinding(
                    "fake",
                    EventHorizon.NEXT_180_DAYS,
                    "Japan event",
                    "JP",
                    "2026-04-02",
                    "Japan update.",
                    ConfidenceLevel.HIGH,
                    (SourceReference("BOJ", "https://example.com/boj"),),
                ),
                ResearchFinding(
                    "fake",
                    EventHorizon.NEXT_30_DAYS,
                    "US event",
                    "US",
                    "2026-03-20",
                    "US update.",
                    ConfidenceLevel.HIGH,
                    (SourceReference("Fed", "https://example.com/fed"),),
                ),
                ResearchFinding(
                    "fake",
                    EventHorizon.NEXT_30_DAYS,
                    "China event",
                    "CN",
                    "2026-03-20",
                    "China update.",
                    ConfidenceLevel.HIGH,
                    (SourceReference("Gov", "https://example.com/gov"),),
                ),
                ResearchFinding(
                    "fake",
                    EventHorizon.NEXT_7_DAYS,
                    "Past event",
                    "CN",
                    "2026-03-10",
                    "Past update.",
                    ConfidenceLevel.HIGH,
                    (SourceReference("Gov", "https://example.com/gov"),),
                ),
            )

            store.upsert_findings(findings, collected_at="2026-03-15T08:00:00Z")
            loaded = store.load_future_findings(
                as_of=date(2026, 3, 15),
                max_expected_date=date(2026, 3, 31),
            )

            self.assertEqual(
                [(item.expected_date, item.region, item.title) for item in loaded],
                [
                    ("2026-03-20", "CN", "China event"),
                    ("2026-03-20", "US", "US event"),
                ],
            )


if __name__ == "__main__":
    unittest.main()
