"""Event Insight 事件抽取服务。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .event_insight_job_service import EventInsightJobService
from .event_insight_repository import EventInsightRepository, decode_job_payload
from .event_insight_migrations import utc_now_iso


class EventExtractionValidationError(Exception):
    """表示模型输出无法通过事件抽取校验。"""


class EventExtractionService:
    """将原始材料抽取为事件、证据和实体。

    Args:
        repository: Event Insight 仓储。
        task_router: 统一 LLM 任务路由。
        job_service: 可选任务服务，用于处理 extract_event job。

    Returns:
        初始化后的事件抽取服务。
    """

    def __init__(
        self,
        *,
        repository: EventInsightRepository,
        task_router: Any,
        job_service: EventInsightJobService | None = None,
    ) -> None:
        self._repository = repository
        self._task_router = task_router
        self._job_service = job_service
        self._prompt = _load_prompt()

    def extract_document(self, raw_document_id: int) -> dict[str, Any]:
        """抽取单篇材料并写入事件事实。

        Args:
            raw_document_id: 原始材料主键。

        Returns:
            包含 analysisRunId 和 eventIds 的结果。
        """

        document = self._repository.get_raw_document(raw_document_id)
        if document is None:
            raise EventExtractionValidationError("raw document not found")

        result = self._task_router.generate(
            "event_extraction",
            [
                {"role": "system", "content": self._prompt},
                {"role": "user", "content": str(document["content_text"])},
            ],
        )
        provider = getattr(result, "provider", {}) or {}
        provider_config_id = self._resolve_provider_config_id(provider.get("id"))
        analysis_run_id = self._repository.create_analysis_run(
            run_type="event_extraction",
            model_provider=str(provider.get("providerType") or provider.get("id") or ""),
            model_name=str(provider.get("modelName") or ""),
        )
        try:
            payload = self._parse_payload(str(result.text))
            event_ids = self._write_events(
                analysis_run_id=analysis_run_id,
                raw_document=document,
                events=payload["events"],
            )
            self._repository.complete_analysis_run(analysis_run_id=analysis_run_id)
            self._repository.create_llm_call_log(
                task_type="event_extraction",
                provider_config_id=provider_config_id,
                model_name=str(provider.get("modelName") or ""),
                status="succeeded",
            )
            return {"analysisRunId": analysis_run_id, "eventIds": event_ids}
        except Exception as exc:
            self._repository.fail_analysis_run(analysis_run_id=analysis_run_id, error_message=str(exc))
            self._repository.create_llm_call_log(
                task_type="event_extraction",
                provider_config_id=provider_config_id,
                model_name=str(provider.get("modelName") or ""),
                status="failed",
                error_message=str(exc),
            )
            raise

    def run_next_job(self, *, lease_owner: str, now: str | None = None) -> dict[str, Any] | None:
        """领取并处理下一条 extract_event job。"""

        if self._job_service is None:
            raise RuntimeError("job service is required")
        job = self._repository.claim_next_processing_job(
            lease_owner=lease_owner,
            now=now or utc_now_iso(),
            lease_seconds=60,
        )
        if job is None:
            return None
        if job["job_type"] != "extract_event":
            return None
        payload = decode_job_payload(job)
        try:
            result = self.extract_document(int(payload["rawDocumentId"]))
            self._repository.complete_processing_job(job_id=int(job["id"]), now=utc_now_iso())
            return {"jobId": int(job["id"]), **result}
        except Exception as exc:
            self._repository.fail_processing_job(
                job_id=int(job["id"]),
                error_message=str(exc),
                now=utc_now_iso(),
                retry_delay_seconds=30,
            )
            raise

    def _parse_payload(self, text: str) -> dict[str, Any]:
        """解析并校验模型 JSON。"""

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise EventExtractionValidationError("model output is not valid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
            raise EventExtractionValidationError("events array is required")
        return payload

    def _write_events(
        self,
        *,
        analysis_run_id: int,
        raw_document: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> list[int]:
        """写入模型输出事件。"""

        event_ids: list[int] = []
        content_text = str(raw_document["content_text"])
        for item in events:
            self._validate_event_item(item)
            event_id = self._repository.create_event(
                title=str(item["title"]),
                summary=str(item["summary"]),
                event_time=str(item["eventTime"]),
                event_type=str(item["eventType"]),
                confidence_score=float(item["confidenceScore"]),
                analysis_run_id=analysis_run_id,
                source_method="llm",
            )
            self._repository.link_event_source(
                event_id=event_id,
                raw_document_id=int(raw_document["id"]),
            )
            for evidence in item["evidence"]:
                excerpt = str(evidence.get("excerpt") or "")
                start_offset = content_text.find(excerpt)
                if not excerpt or start_offset < 0:
                    raise EventExtractionValidationError("evidence excerpt not found in raw material")
                evidence_id = self._repository.create_evidence(
                    raw_document_id=int(raw_document["id"]),
                    excerpt=excerpt,
                    start_offset=start_offset,
                    end_offset=start_offset + len(excerpt),
                    evidence_level=str(evidence.get("evidenceLevel") or "C"),
                    source_title=str(raw_document.get("title") or ""),
                    source_url=str(raw_document.get("url") or ""),
                )
                self._repository.link_event_evidence(event_id=event_id, evidence_id=evidence_id, role="primary")
            for entity in item.get("entities", []):
                entity_id = self._repository.create_entity(
                    name=str(entity.get("name") or ""),
                    entity_type=str(entity.get("entityType") or "other"),
                )
                self._repository.link_event_entity(
                    event_id=event_id,
                    entity_id=entity_id,
                    role=str(entity.get("role") or "mentioned"),
                )
            event_ids.append(event_id)
        return event_ids

    def _validate_event_item(self, item: dict[str, Any]) -> None:
        """校验单条事件输出。"""

        required = ("title", "summary", "eventTime", "eventType", "confidenceScore", "evidence")
        if any(not item.get(field) for field in required):
            raise EventExtractionValidationError("required event fields are missing")
        if not isinstance(item["evidence"], list) or not item["evidence"]:
            raise EventExtractionValidationError("event evidence is required")

    def _resolve_provider_config_id(self, value: Any) -> int | None:
        """只在 provider 配置存在时返回外键 ID。"""

        provider_id = _optional_int(value)
        if provider_id is None:
            return None
        return provider_id if self._repository.get_llm_provider_config(provider_id) is not None else None


def _load_prompt() -> str:
    """读取事件抽取 prompt。"""

    return Path("src/prompts/event_insight/event_extraction.md").read_text(encoding="utf-8")


def _optional_int(value: Any) -> int | None:
    """将可选值转为 int。"""

    try:
        return int(value)
    except (TypeError, ValueError):
        return None
