"""RSS 源配置与 Event Insight 入库服务。"""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
import re
from typing import Any

from ..news.fetcher import NewsFetcher
from .event_insight_migrations import utc_now_iso
from .event_insight_repository import EventInsightRepository


class RssConfigNotFoundError(Exception):
    """表示 RSS 源不存在。"""


class RssConfigValidationError(Exception):
    """表示 RSS 配置请求不合法。"""


class RssConfigService:
    """封装 RSS 源配置、调度设置和抓取入库规则。

    Args:
        repository: Event Insight SQLite 仓储。
        fetcher: RSS 抓取器；测试可注入假实现。

    Returns:
        初始化后的 RSS 配置服务。
    """

    def __init__(self, *, repository: EventInsightRepository | None = None, fetcher: Any | None = None) -> None:
        self._repository = repository or EventInsightRepository()
        self._fetcher = fetcher or NewsFetcher()

    def list_sources(self) -> dict[str, Any]:
        """返回 RSS 源和全局调度配置。"""

        sources = [self._present_source(row) for row in self._repository.list_rss_sources()]
        return {"sources": sources, "scheduler": self._present_scheduler(self._repository.get_rss_scheduler_config())}

    def create_source(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        """创建 RSS 源配置。"""

        row = self._repository.create_rss_source(self._parse_source_payload(payload))
        return {"source": self._present_source(row)}

    def update_source(self, source_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
        """更新 RSS 源配置。"""

        row = self._repository.update_rss_source(source_id, self._parse_source_payload(payload))
        if row is None:
            raise RssConfigNotFoundError()
        return {"source": self._present_source(row)}

    def disable_source(self, source_id: int) -> dict[str, Any]:
        """禁用 RSS 源配置。"""

        row = self._repository.disable_rss_source(source_id)
        if row is None:
            raise RssConfigNotFoundError()
        return {"source": self._present_source(row)}

    def update_scheduler(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        """保存 RSS 每日抓取调度设置。"""

        body = payload or {}
        daily_fetch_time = _validate_hhmm(str(body.get("dailyFetchTime") or "06:30"))
        timezone = str(body.get("timezone") or "Asia/Shanghai").strip()
        if not timezone:
            raise RssConfigValidationError("timezone is required")
        row = self._repository.update_rss_scheduler_config(
            {
                "enabled": bool(body.get("enabled", True)),
                "timezone": timezone,
                "daily_fetch_time": daily_fetch_time,
            }
        )
        return {"scheduler": self._present_scheduler(row)}

    def fetch_source(self, source_id: int) -> dict[str, Any]:
        """手动抓取单个 RSS 源并写入 Event Insight 事件列表。

        Args:
            source_id: RSS 源主键。

        Returns:
            导入统计和抓取时间。
        """

        source = self._repository.get_rss_source(source_id)
        if source is None:
            raise RssConfigNotFoundError()
        items = self._fetcher.fetch_rss_feed(str(source["url"]), max_items=int(source.get("max_items") or 20))
        imported_count = 0
        skipped_count = 0
        for item in items:
            if self._import_rss_item(source, item):
                imported_count += 1
            else:
                skipped_count += 1
        fetched_at = utc_now_iso()
        self._repository.mark_rss_source_fetched(source_id, fetched_at)
        return {
            "source": self._present_source(self._repository.get_rss_source(source_id) or source),
            "importedCount": imported_count,
            "skippedCount": skipped_count,
            "fetchedAt": fetched_at,
        }

    def _import_rss_item(self, source: dict[str, Any], item: dict[str, str]) -> bool:
        """将单条 RSS 新闻写为 raw_document、event 和 evidence。"""

        title = str(item.get("title") or "").strip()
        if not title:
            return False
        link = str(item.get("link") or "").strip()
        description = str(item.get("description") or "").strip()
        published_at = _normalize_published_at(str(item.get("published") or ""))
        fingerprint = link or f"{title}|{published_at}|{description}"
        content_hash = f"rss:{sha256(fingerprint.encode('utf-8')).hexdigest()}"
        if self._repository.get_raw_document_by_hash(content_hash) is not None:
            return False

        document_id = self._repository.create_raw_document(
            source_type="news",
            title=title,
            content_text=description,
            content_hash=content_hash,
            url=link,
            published_at=published_at,
        )
        event_id = self._repository.create_event(
            title=title,
            summary=description or title,
            event_time=published_at or utc_now_iso(),
            published_at=published_at,
            event_type="other",
            confidence_score=0.6,
            source_method="rss",
        )
        evidence_id = self._repository.create_evidence(
            raw_document_id=document_id,
            excerpt=description or title,
            evidence_level="C",
            source_title=str(source.get("name") or ""),
            source_url=link,
        )
        self._repository.link_event_source(event_id=event_id, raw_document_id=document_id)
        self._repository.link_event_evidence(event_id=event_id, evidence_id=evidence_id, role="primary")
        self._repository.create_event_operation_log(
            event_id=event_id,
            operation_type="rss_import",
            before_json="{}",
            after_json=f'{{"rss_source_id": {int(source["id"])}, "raw_document_id": {document_id}}}',
            reason="rss fetch",
            operator="system",
        )
        return True

    def _parse_source_payload(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        """解析 RSS 源请求体。"""

        body = payload or {}
        name = str(body.get("name") or "").strip()
        url = str(body.get("url") or "").strip()
        if not name or not (url.startswith("http://") or url.startswith("https://")):
            raise RssConfigValidationError("name and http url are required")
        try:
            max_items = int(body.get("maxItems") or 20)
        except (TypeError, ValueError):
            raise RssConfigValidationError("maxItems must be integer") from None
        if max_items < 1 or max_items > 100:
            raise RssConfigValidationError("maxItems out of range")
        return {
            "name": name,
            "url": url,
            "language": str(body.get("language") or "zh").strip() or "zh",
            "category": str(body.get("category") or "finance").strip() or "finance",
            "enabled": bool(body.get("enabled", True)),
            "fetch_time": _validate_hhmm(str(body.get("fetchTime") or "06:30")),
            "max_items": max_items,
        }

    def _present_source(self, row: dict[str, Any]) -> dict[str, Any]:
        """将 RSS 源行转换为前端契约。"""

        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "url": str(row["url"]),
            "language": str(row.get("language") or "zh"),
            "category": str(row.get("category") or "finance"),
            "enabled": bool(row.get("enabled")),
            "fetchTime": str(row.get("fetch_time") or "06:30"),
            "maxItems": int(row.get("max_items") or 20),
            "lastFetchedAt": row.get("last_fetched_at"),
            "updatedAt": str(row.get("updated_at") or ""),
        }

    def _present_scheduler(self, row: dict[str, Any]) -> dict[str, Any]:
        """将 RSS 调度行转换为前端契约。"""

        return {
            "enabled": bool(row.get("enabled")),
            "timezone": str(row.get("timezone") or "Asia/Shanghai"),
            "dailyFetchTime": str(row.get("daily_fetch_time") or "06:30"),
            "updatedAt": str(row.get("updated_at") or ""),
        }


def _validate_hhmm(value: str) -> str:
    """校验 HH:mm 时间文本。"""

    if not re.match(r"^\d{2}:\d{2}$", value):
        raise RssConfigValidationError("time must be HH:mm")
    hour, minute = [int(part) for part in value.split(":", 1)]
    if hour > 23 or minute > 59:
        raise RssConfigValidationError("time out of range")
    return value


def _normalize_published_at(value: str) -> str:
    """把 RSS 发布时间解析为 UTC ISO；解析失败时返回当前时间。"""

    if not value:
        return utc_now_iso()
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return utc_now_iso()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
