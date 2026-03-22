import os
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from contextlib import contextmanager
from uuid import uuid4


class DemoResearchProvider:
    provider_key = "demo-research"

    def collect_outlook(self, *, horizon, topics, as_of):
        _ = topics
        offsets = {
            "7d": 3,
            "30d": 12,
            "90d": 45,
            "180d": 120,
        }
        offset = offsets[horizon.value]
        expected_date = date.fromordinal(as_of.toordinal() + offset).isoformat()
        from src.domain.external_data import ConfidenceLevel, ResearchFinding, SourceReference

        return [
            ResearchFinding(
                self.provider_key,
                horizon,
                f"Demo event {horizon.value}",
                "US",
                expected_date,
                "Demo outlook item for verifying the events service pipeline.",
                ConfidenceLevel.HIGH,
                (SourceReference("Demo source", "https://example.com/demo"),),
            )
        ]

    def healthcheck(self):
        from src.providers.contracts import ProviderAvailability, ProviderStatus

        return ProviderStatus(
            self.provider_key,
            ProviderAvailability.DEGRADED,
            "demo provider",
            "2026-03-22T00:00:00Z",
        )


@contextmanager
def isolated_demo_store():
    from src.services.events_outlook_store import EventsOutlookStore

    base_dir = Path(".data") / ".test-events-demo"
    base_dir.mkdir(exist_ok=True)
    db_path = base_dir / f"events-demo-{uuid4().hex}.db"
    try:
        yield EventsOutlookStore(db_path)
    finally:
        for suffix in ("", "-wal", "-shm"):
            path = Path(f"{db_path}{suffix}")
            if path.exists():
                path.unlink()
        if base_dir.exists():
            try:
                next(base_dir.iterdir())
            except StopIteration:
                base_dir.rmdir()
            except OSError:
                pass


class EventsOutlookDemoTests(unittest.TestCase):
    def test_demo_events_outlook_snapshot(self):
        try:
            from src.domain.external_data import EventHorizon
            from src.services.events_outlook_service import EventsOutlookService
        except ModuleNotFoundError as exc:
            self.skipTest(f"Missing optional dependency for demo: {exc}")

        as_of = date(2026, 3, 22)
        provider = DemoResearchProvider()

        findings = provider.collect_outlook(
            horizon=EventHorizon.NEXT_30_DAYS,
            topics=("policy", "macro", "meeting"),
            as_of=as_of,
        )

        print("DEMO_OUTLOOK_FINDINGS")
        for finding in findings:
            print(
                f"- {finding.expected_date} | {finding.title} | {finding.confidence.value} | "
                f"{finding.sources[0].title if finding.sources else 'no-source'} | {finding.summary}"
        )

        with isolated_demo_store() as store:
            service = EventsOutlookService(
                research_provider=provider,
                store=store,
                now_factory=lambda: datetime(2026, 3, 22, tzinfo=UTC),
            )
            snapshot = service.build_snapshot(as_of=as_of, refresh_store=True)

            print("DEMO_OUTLOOK_SNAPSHOT")
            for window in snapshot.windows:
                print(f"[{window.title}] {len(window.items)} items")
                for item in window.items:
                    print(
                        f"  - {item.expected_date} | {item.title} | {item.confidence.value} | "
                        f"{item.source} | {item.impact_summary}"
                    )

            self.assertTrue(any(window.items for window in snapshot.windows))

    @unittest.skipUnless(
        os.getenv("RUN_LIVE_EVENTS_OUTLOOK_DEMO") == "1",
        "Set RUN_LIVE_EVENTS_OUTLOOK_DEMO=1 to run the live events outlook demo.",
    )
    def test_live_events_outlook_demo(self):
        try:
            from src.domain.external_data import EventHorizon
            from src.providers.live_data import ArkResearchProvider, FallbackResearchProvider, UnavailableResearchProvider
            from src.services.events_outlook_service import EventsOutlookService
        except ModuleNotFoundError as exc:
            self.skipTest(f"Missing optional dependency for live demo: {exc}")

        as_of = date.today()
        provider = FallbackResearchProvider(ArkResearchProvider, UnavailableResearchProvider())

        findings = provider.collect_outlook(
            horizon=EventHorizon.NEXT_30_DAYS,
            topics=("policy", "macro", "meeting"),
            as_of=as_of,
        )

        print("LIVE_OUTLOOK_FINDINGS")
        for finding in findings:
            print(
                f"- {finding.expected_date} | {finding.title} | {finding.confidence.value} | "
                f"{finding.sources[0].title if finding.sources else 'no-source'} | {finding.summary}"
            )

        with isolated_demo_store() as store:
            service = EventsOutlookService(
                research_provider=provider,
                store=store,
                now_factory=lambda: datetime.now(UTC),
            )
            snapshot = service.build_snapshot(as_of=as_of, refresh_store=True)

            print("LIVE_OUTLOOK_SNAPSHOT")
            for window in snapshot.windows:
                print(f"[{window.title}] {len(window.items)} items")
                for item in window.items:
                    print(
                        f"  - {item.expected_date} | {item.title} | {item.confidence.value} | "
                        f"{item.source} | {item.impact_summary}"
                    )

            self.assertIsInstance(snapshot.windows, list)


if __name__ == "__main__":
    unittest.main()
