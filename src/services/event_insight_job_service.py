"""Event Insight durable local job service."""

from __future__ import annotations

import json
from typing import Any

from .event_insight_migrations import utc_now_iso
from .event_insight_repository import EventInsightRepository, decode_job_payload


class EventInsightJobNotFoundError(KeyError):
    """任务不存在错误。"""


class EventInsightJobService:
    """封装 Event Insight 本地任务队列行为。

    Args:
        repository: Event Insight Repository。

    Returns:
        初始化后的任务服务。
    """

    def __init__(self, repository: EventInsightRepository | None = None) -> None:
        self._repository = repository or EventInsightRepository()

    @property
    def repository(self) -> EventInsightRepository:
        """返回底层 Repository。

        Returns:
            Event Insight Repository。
        """

        return self._repository

    def create_job(
        self,
        *,
        job_type: str,
        idempotency_key: str,
        payload: dict[str, Any],
        now: str | None = None,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        """创建幂等处理任务。

        Args:
            job_type: 任务类型。
            idempotency_key: 幂等键。
            payload: 任务 payload。
            now: 当前时间；测试可传固定值。
            max_attempts: 最大尝试次数。

        Returns:
            任务状态 payload。
        """

        timestamp = now or utc_now_iso()
        row = self._repository.create_processing_job(
            job_type=job_type,
            idempotency_key=idempotency_key,
            payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            next_run_at=timestamp,
            max_attempts=max_attempts,
        )
        return self._to_status_payload(row)

    def get_job(self, job_id: int) -> dict[str, Any]:
        """读取任务状态。

        Args:
            job_id: 任务主键。

        Returns:
            任务状态 payload。

        Raises:
            EventInsightJobNotFoundError: 任务不存在。
        """

        row = self._repository.get_processing_job(job_id)
        if row is None:
            raise EventInsightJobNotFoundError(str(job_id))
        return self._to_status_payload(row)

    def claim_next_job(self, *, lease_owner: str, now: str | None = None, lease_seconds: int = 300) -> dict[str, Any] | None:
        """领取下一条可运行任务。

        Args:
            lease_owner: worker 标识。
            now: 当前时间；测试可传固定值。
            lease_seconds: 租约秒数。

        Returns:
            running 任务字段字典；无可领取任务时返回 None。
        """

        return self._repository.claim_next_processing_job(
            lease_owner=lease_owner,
            now=now or utc_now_iso(),
            lease_seconds=lease_seconds,
        )

    def complete_job(self, *, job_id: int, now: str | None = None) -> dict[str, Any]:
        """标记任务成功。

        Args:
            job_id: 任务主键。
            now: 完成时间。

        Returns:
            任务状态 payload。
        """

        row = self._repository.complete_processing_job(job_id=job_id, now=now or utc_now_iso())
        if row is None:
            raise EventInsightJobNotFoundError(str(job_id))
        return self._to_status_payload(row)

    def fail_job(
        self,
        *,
        job_id: int,
        error_message: str,
        now: str | None = None,
        retry_delay_seconds: int = 60,
    ) -> dict[str, Any]:
        """记录任务失败并按剩余次数决定是否重试。

        Args:
            job_id: 任务主键。
            error_message: 失败原因。
            now: 失败时间。
            retry_delay_seconds: 重试延迟秒数。

        Returns:
            任务状态 payload。
        """

        row = self._repository.fail_processing_job(
            job_id=job_id,
            error_message=error_message,
            now=now or utc_now_iso(),
            retry_delay_seconds=retry_delay_seconds,
        )
        if row is None:
            raise EventInsightJobNotFoundError(str(job_id))
        return self._to_status_payload(row)

    def _to_status_payload(self, row: dict[str, Any]) -> dict[str, Any]:
        """把数据库任务行转换为 API payload。

        Args:
            row: processing_job 字段字典。

        Returns:
            前端可轮询的任务状态。
        """

        payload = decode_job_payload(row)
        return {
            "id": int(row["id"]),
            "jobId": int(row["id"]),
            "jobType": str(row["job_type"]),
            "status": str(row["status"]),
            "attemptCount": int(row["attempt_count"]),
            "maxAttempts": int(row["max_attempts"]),
            "error": str(row["error_message"] or ""),
            "payload": payload,
            "rawDocumentId": payload.get("rawDocumentId"),
            "traceId": f"event-insight-job-{row['id']}",
        }
