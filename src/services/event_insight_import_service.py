"""Event Insight material import service."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .event_insight_job_service import EventInsightJobService
from .event_insight_repository import EventInsightRepository, decode_job_payload


class EventInsightImportValidationError(ValueError):
    """材料导入请求校验失败。"""


@dataclass(frozen=True)
class _FilePolicy:
    """受控文件上传策略。"""

    content_type: str
    bucket: str


_ALLOWED_FILE_POLICIES: dict[str, _FilePolicy] = {
    ".txt": _FilePolicy("text/plain", "txt"),
    ".md": _FilePolicy("text/markdown", "markdown"),
    ".json": _FilePolicy("application/json", "json"),
    ".html": _FilePolicy("text/html", "html"),
    ".htm": _FilePolicy("text/html", "html"),
    ".pdf": _FilePolicy("application/pdf", "pdf"),
}


class EventInsightImportService:
    """处理 Event Insight 材料导入。

    Args:
        repository: Event Insight Repository。
        job_service: 本地任务服务。
        storage_root: 受控文件存储根目录。
        max_content_bytes: 单个导入内容最大字节数。

    Returns:
        初始化后的导入服务。
    """

    def __init__(
        self,
        *,
        repository: EventInsightRepository | None = None,
        job_service: EventInsightJobService | None = None,
        storage_root: str | Path = ".data/event_insight",
        max_content_bytes: int = 5 * 1024 * 1024,
    ) -> None:
        self._repository = repository or EventInsightRepository()
        self._job_service = job_service or EventInsightJobService(self._repository)
        self._storage_root = Path(storage_root)
        self._max_content_bytes = max_content_bytes
        self._storage_root.mkdir(parents=True, exist_ok=True)

    def import_document(self, payload: dict[str, Any] | None, *, idempotency_key: str | None = None) -> dict[str, Any]:
        """导入材料并创建 parse_document 任务。

        Args:
            payload: HTTP JSON payload。
            idempotency_key: 可选请求幂等键。

        Returns:
            202 响应 payload。

        Raises:
            EventInsightImportValidationError: payload 无效。
        """

        if not isinstance(payload, dict):
            raise EventInsightImportValidationError("payload must be an object")
        mode = str(payload.get("mode", "")).strip().lower()
        if mode == "text":
            document_id, computed_key = self._import_text(payload)
        elif mode == "url":
            document_id, computed_key = self._import_url(payload)
        elif mode == "file":
            document_id, computed_key = self._import_file(payload)
        else:
            raise EventInsightImportValidationError("mode must be text, url or file")

        effective_key = idempotency_key.strip() if idempotency_key and idempotency_key.strip() else computed_key
        existing_job = self._repository.get_processing_job_by_idempotency_key(effective_key)
        if existing_job is not None:
            return self._accepted_payload(existing_job)

        job = self._job_service.create_job(
            job_type="parse_document",
            idempotency_key=effective_key,
            payload={"rawDocumentId": document_id},
        )
        return {
            "jobId": job["id"],
            "jobType": job["jobType"],
            "status": job["status"],
            "rawDocumentId": document_id,
            "traceId": job["traceId"],
        }

    def _import_text(self, payload: dict[str, Any]) -> tuple[int, str]:
        """导入粘贴文本。"""

        title = self._required_text(payload, "title")
        content = self._required_text(payload, "content")
        self._validate_content_size(content.encode("utf-8"))
        content_hash = f"text:{sha256(content.encode('utf-8')).hexdigest()}"
        document = self._repository.get_raw_document_by_hash(content_hash)
        if document is None:
            document_id = self._repository.create_raw_document(
                source_type=str(payload.get("sourceType") or "other"),
                title=title,
                content_text=content,
                content_hash=content_hash,
            )
        else:
            document_id = int(document["id"])
        return document_id, f"event-insight-import:{content_hash}"

    def _import_url(self, payload: dict[str, Any]) -> tuple[int, str]:
        """导入 URL 元信息。"""

        title = self._required_text(payload, "title")
        url = self._required_text(payload, "url")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise EventInsightImportValidationError("url must be http or https")
        content_hash = f"url:{sha256(url.encode('utf-8')).hexdigest()}"
        document = self._repository.get_raw_document_by_hash(content_hash)
        if document is None:
            document_id = self._repository.create_raw_document(
                source_type=str(payload.get("sourceType") or "news"),
                title=title,
                content_text="",
                content_hash=content_hash,
                url=url,
            )
        else:
            document_id = int(document["id"])
        return document_id, f"event-insight-import:{content_hash}"

    def _import_file(self, payload: dict[str, Any]) -> tuple[int, str]:
        """导入受控 JSON 文件内容。"""

        title = self._required_text(payload, "title")
        file_name = self._required_text(payload, "fileName")
        content_type = self._required_text(payload, "contentType")
        content = self._required_text(payload, "content")
        self._validate_file_name(file_name)
        suffix = Path(file_name).suffix.lower()
        policy = _ALLOWED_FILE_POLICIES.get(suffix)
        if policy is None or content_type != policy.content_type:
            raise EventInsightImportValidationError("unsupported file type")
        raw_bytes = content.encode("utf-8")
        self._validate_content_size(raw_bytes)
        digest = sha256(raw_bytes).hexdigest()
        # Windows worktree 路径可能较长；文件名使用 hash 前缀，完整 hash 仍保存在 content_hash。
        relative_path = Path("raw") / policy.bucket / f"{digest[:16]}{suffix}"
        target_path = self._storage_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(raw_bytes)
        local_file_path = relative_path.as_posix()
        content_hash = f"file:{digest}"
        document = self._repository.get_raw_document_by_hash(content_hash)
        if document is None:
            document_id = self._repository.create_raw_document(
                source_type=str(payload.get("sourceType") or "other"),
                title=title,
                content_text=content if suffix != ".pdf" else "",
                content_hash=content_hash,
                local_file_path=local_file_path,
            )
        else:
            document_id = int(document["id"])
        return document_id, f"event-insight-import:{content_hash}"

    def _accepted_payload(self, job_row: dict[str, Any]) -> dict[str, Any]:
        """把已有幂等任务转换为导入响应。"""

        payload = decode_job_payload(job_row)
        return {
            "jobId": int(job_row["id"]),
            "jobType": str(job_row["job_type"]),
            "status": str(job_row["status"]),
            "rawDocumentId": payload.get("rawDocumentId"),
            "traceId": f"event-insight-job-{job_row['id']}",
        }

    def _required_text(self, payload: dict[str, Any], field_name: str) -> str:
        """读取必填文本字段。"""

        value = payload.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise EventInsightImportValidationError(f"{field_name} is required")
        return value.strip()

    def _validate_content_size(self, content: bytes) -> None:
        """校验导入内容大小。"""

        if len(content) > self._max_content_bytes:
            raise EventInsightImportValidationError("content is too large")

    def _validate_file_name(self, file_name: str) -> None:
        """校验文件名不包含路径穿越。"""

        normalized = Path(file_name)
        if normalized.name != file_name or ".." in normalized.parts or "/" in file_name or "\\" in file_name:
            raise EventInsightImportValidationError("file name must not contain paths")
