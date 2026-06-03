import unittest
from pathlib import Path

from src.services.event_insight_job_service import EventInsightJobService
from src.services.event_insight_repository import EventInsightRepository


class EventInsightJobServiceTests(unittest.TestCase):
    """校验 Event Insight 本地任务队列的幂等、租约和重试行为。"""

    def setUp(self) -> None:
        self.db_path = Path(".tmp-events-tests") / "event-insight-jobs" / f"{self.id().split('.')[-1]}.db"
        if self.db_path.exists():
            self.db_path.unlink()
        self.repository = EventInsightRepository(self.db_path)
        self.service = EventInsightJobService(self.repository)

    def test_create_job_is_idempotent_by_key(self) -> None:
        """校验相同幂等键不会创建重复任务。"""
        first = self.service.create_job(
            job_type="parse_document",
            idempotency_key="parse:doc:1",
            payload={"rawDocumentId": 1},
            now="2026-06-03T09:00:00Z",
        )
        second = self.service.create_job(
            job_type="parse_document",
            idempotency_key="parse:doc:1",
            payload={"rawDocumentId": 1},
            now="2026-06-03T09:00:01Z",
        )

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["status"], "pending")

    def test_claim_next_job_marks_running_and_records_attempt(self) -> None:
        """校验领取任务会设置租约并记录 attempt。"""
        created = self.service.create_job(
            job_type="parse_document",
            idempotency_key="parse:doc:2",
            payload={"rawDocumentId": 2},
            now="2026-06-03T09:00:00Z",
        )

        claimed = self.service.claim_next_job(
            lease_owner="worker-a",
            now="2026-06-03T09:01:00Z",
            lease_seconds=60,
        )

        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["id"], created["id"])
        self.assertEqual(claimed["status"], "running")
        self.assertEqual(claimed["lease_owner"], "worker-a")
        self.assertEqual(claimed["attempt_count"], 1)
        self.assertEqual(len(self.repository.list_processing_job_attempts(created["id"])), 1)

    def test_active_lease_is_not_claimed_twice(self) -> None:
        """校验未过期租约不会被其他 worker 重复领取。"""
        self.service.create_job(
            job_type="parse_document",
            idempotency_key="parse:doc:3",
            payload={"rawDocumentId": 3},
            now="2026-06-03T09:00:00Z",
        )
        self.service.claim_next_job(
            lease_owner="worker-a",
            now="2026-06-03T09:01:00Z",
            lease_seconds=60,
        )

        claimed = self.service.claim_next_job(
            lease_owner="worker-b",
            now="2026-06-03T09:01:30Z",
            lease_seconds=60,
        )

        self.assertIsNone(claimed)

    def test_expired_lease_can_be_recovered(self) -> None:
        """校验过期 running 任务可被重新领取并增加 attempt。"""
        created = self.service.create_job(
            job_type="parse_document",
            idempotency_key="parse:doc:4",
            payload={"rawDocumentId": 4},
            now="2026-06-03T09:00:00Z",
        )
        self.service.claim_next_job(
            lease_owner="worker-a",
            now="2026-06-03T09:01:00Z",
            lease_seconds=30,
        )

        recovered = self.service.claim_next_job(
            lease_owner="worker-b",
            now="2026-06-03T09:02:00Z",
            lease_seconds=60,
        )

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered["id"], created["id"])
        self.assertEqual(recovered["lease_owner"], "worker-b")
        self.assertEqual(recovered["attempt_count"], 2)
        self.assertEqual(len(self.repository.list_processing_job_attempts(created["id"])), 2)

    def test_fail_job_retries_then_marks_failed_after_max_attempts(self) -> None:
        """校验失败任务在次数未耗尽时重试，达到上限后进入 failed。"""
        created = self.service.create_job(
            job_type="parse_document",
            idempotency_key="parse:doc:5",
            payload={"rawDocumentId": 5},
            now="2026-06-03T09:00:00Z",
            max_attempts=2,
        )
        self.service.claim_next_job(
            lease_owner="worker-a",
            now="2026-06-03T09:01:00Z",
            lease_seconds=30,
        )

        retried = self.service.fail_job(
            job_id=created["id"],
            error_message="parse failed once",
            now="2026-06-03T09:01:10Z",
            retry_delay_seconds=30,
        )

        self.assertEqual(retried["status"], "pending")
        self.assertEqual(retried["error"], "parse failed once")

        self.service.claim_next_job(
            lease_owner="worker-b",
            now="2026-06-03T09:02:00Z",
            lease_seconds=30,
        )
        failed = self.service.fail_job(
            job_id=created["id"],
            error_message="parse failed twice",
            now="2026-06-03T09:02:10Z",
            retry_delay_seconds=30,
        )

        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error"], "parse failed twice")


if __name__ == "__main__":
    unittest.main()
