"""Event Insight 事件工作台业务服务。"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from .event_insight_repository import EventInsightRepository


class EventInsightNotFoundError(Exception):
    """表示 Event Insight 资源不存在。"""


class EventInsightValidationError(Exception):
    """表示 Event Insight 请求参数不合法。"""


class EventInsightService:
    """封装 Event Insight 事件列表工作台业务规则。

    Args:
        repository: Event Insight SQLite 仓储。

    Returns:
        初始化后的业务服务实例。
    """

    def __init__(self, repository: EventInsightRepository) -> None:
        self._repository = repository

    def list_events(
        self,
        *,
        keyword: str = "",
        status: str = "active",
        topic_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "event_time",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """构建事件列表分页响应。

        Args:
            keyword: 标题或摘要关键字。
            status: 人工状态筛选，默认仅 active。
            topic_id: 可选主题 ID。
            page: 页码，从 1 开始。
            page_size: 每页数量，最大 100。
            sort_by: 排序字段。
            sort_order: 排序方向。

        Returns:
            前端事件列表响应。
        """

        normalized_page = max(1, page)
        normalized_size = min(max(1, page_size), 100)
        normalized_status = status if status in {"active", "ignored", "archived", "all"} else "active"
        normalized_order = "asc" if sort_order == "asc" else "desc"
        result = self._repository.list_events_for_workbench(
            keyword=keyword.strip(),
            status=normalized_status,
            topic_id=topic_id,
            page=normalized_page,
            page_size=normalized_size,
            sort_by=sort_by,
            sort_order=normalized_order,
        )
        return {
            "traceId": _trace_id("event-insight-events"),
            "items": [self._present_event(row) for row in result["items"]],
            "page": normalized_page,
            "pageSize": normalized_size,
            "total": result["total"],
        }

    def get_event_detail(self, event_id: int) -> dict[str, Any]:
        """构建事件详情响应。

        Args:
            event_id: 事件主键。

        Returns:
            包含事件、证据链和主题归属的响应。
        """

        row = self._require_event(event_id)
        event = self._present_event(row)
        event["topics"] = [self._present_topic(topic) for topic in self._repository.list_event_topics(event_id)]
        event["evidence"] = [
            self._present_evidence(evidence) for evidence in self._repository.list_event_evidence(event_id)
        ]
        event["entities"] = [
            self._present_entity(entity) for entity in self._repository.list_event_entities(event_id)
        ]
        return {"traceId": _trace_id("event-insight-event"), "event": event}

    def update_event(self, event_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
        """写入人工字段覆盖并返回更新后的展示事件。

        Args:
            event_id: 事件主键。
            payload: 前端提交的可编辑字段。

        Returns:
            更新后的事件展示响应。
        """

        original = self._require_event(event_id)
        body = payload or {}
        allowed_fields = {
            "title": "title",
            "summary": "summary",
            "eventType": "event_type",
            "confidenceScore": "confidence_score",
        }
        reason = str(body.get("reason") or "manual update")
        changed: dict[str, Any] = {}
        for request_field, storage_field in allowed_fields.items():
            if request_field in body:
                changed[storage_field] = body[request_field]

        if not changed:
            raise EventInsightValidationError("no editable fields")

        for field_name, value in changed.items():
            self._repository.create_event_field_override(
                event_id=event_id,
                field_name=field_name,
                override_value=json.dumps(value, ensure_ascii=False),
                reason=reason,
                operator="frontend",
            )
        self._repository.create_event_operation_log(
            event_id=event_id,
            operation_type="update_fields",
            before_json=json.dumps(_json_safe(original), ensure_ascii=False),
            after_json=json.dumps(changed, ensure_ascii=False),
            reason=reason,
            operator="frontend",
        )
        return self.get_event_detail(event_id)

    def ignore_event(self, event_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
        """将事件标记为 ignored。

        Args:
            event_id: 事件主键。
            payload: 忽略原因。

        Returns:
            更新后的事件展示响应。
        """

        original = self._require_event(event_id)
        reason = str((payload or {}).get("reason") or "manual ignore")
        if not self._repository.set_event_manual_status(event_id=event_id, manual_status="ignored", reason=reason):
            raise EventInsightNotFoundError(f"event {event_id} not found")
        self._repository.create_event_operation_log(
            event_id=event_id,
            operation_type="ignore",
            before_json=json.dumps(_json_safe(original), ensure_ascii=False),
            after_json=json.dumps({"manual_status": "ignored"}, ensure_ascii=False),
            reason=reason,
            operator="frontend",
        )
        return self.get_event_detail(event_id)

    def create_topic(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        """创建主题。

        Args:
            payload: 主题名称和摘要。

        Returns:
            新建或同名复用的主题响应。
        """

        body = payload or {}
        name = str(body.get("name") or "").strip()
        if not name:
            raise EventInsightValidationError("topic name is required")
        topic = self._repository.create_topic(name=name, summary=str(body.get("summary") or ""))
        self._repository.create_event_operation_log(
            event_id=None,
            operation_type="create_topic",
            before_json="{}",
            after_json=json.dumps({"topic_id": topic["id"], "name": topic["name"]}, ensure_ascii=False),
            reason="manual topic create",
            operator="frontend",
        )
        return {"traceId": _trace_id("event-insight-topic"), "topic": self._present_topic(topic)}

    def link_event_topic(self, event_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
        """关联事件到主题。

        Args:
            event_id: 事件主键。
            payload: 主题 ID 和主题内角色。

        Returns:
            更新后的事件详情响应。
        """

        self._require_event(event_id)
        body = payload or {}
        try:
            topic_id = int(body.get("topicId"))
        except (TypeError, ValueError):
            raise EventInsightValidationError("topicId is required") from None
        role = str(body.get("roleInTopic") or "supporting_event")
        if not self._repository.link_event_topic(event_id=event_id, topic_id=topic_id, role_in_topic=role):
            raise EventInsightNotFoundError("event or topic not found")
        self._repository.create_event_operation_log(
            event_id=event_id,
            operation_type="link_topic",
            before_json="{}",
            after_json=json.dumps({"topic_id": topic_id, "role_in_topic": role}, ensure_ascii=False),
            reason="manual topic link",
            operator="frontend",
        )
        return self.get_event_detail(event_id)

    def get_topic_trace(self, topic_id: int) -> dict[str, Any]:
        """构建主题溯源响应。

        Args:
            topic_id: 主题主键。

        Returns:
            包含主题、指标、阶段、时间线和当前判断的响应。
        """

        topic = self._repository.get_topic(topic_id)
        if topic is None:
            raise EventInsightNotFoundError(f"topic {topic_id} not found")

        event_rows = self._repository.list_topic_trace_events(topic_id)
        event_ids = [int(row["id"]) for row in event_rows]
        evidence_by_event_id = self._repository.list_evidence_for_events(event_ids)
        timeline = [
            self._present_topic_timeline_entry(row, evidence_by_event_id.get(int(row["id"]), []))
            for row in event_rows
        ]
        stages = _build_topic_stages(event_rows)
        current = timeline[0] if timeline else None
        current_judgement = {
            "title": f"{stages[-1]['label'].replace(' · 当前', '')}：{stages[-1]['title']}" if stages else "暂无阶段判断",
            "summary": str(topic.get("summary") or (current or {}).get("summary") or "暂无关联事件。"),
            "clues": _build_trace_clues(topic, timeline),
        }

        return {
            "traceId": _trace_id("event-insight-topic-trace"),
            "topic": self._present_topic(topic),
            "metrics": _build_topic_metrics(event_rows, evidence_by_event_id),
            "stages": stages,
            "timeline": timeline,
            "currentJudgement": current_judgement,
        }

    def run_batch_action(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        """执行事件批量操作。

        Args:
            payload: 批量事件 ID、动作和动作参数。

        Returns:
            包含成功 ID 与失败项的部分成功响应。
        """

        body = payload or {}
        event_ids = body.get("eventIds")
        if not isinstance(event_ids, list) or not event_ids:
            raise EventInsightValidationError("eventIds is required")
        action = str(body.get("action") or "")
        params = body.get("params") if isinstance(body.get("params"), dict) else {}
        succeeded: list[int] = []
        failed: list[dict[str, Any]] = []

        for raw_event_id in event_ids:
            try:
                event_id = int(raw_event_id)
                if action == "ignore":
                    self.ignore_event(event_id, {"reason": params.get("reason") or "batch ignore"})
                elif action == "link_topic":
                    self.link_event_topic(event_id, params)
                else:
                    raise EventInsightValidationError("unsupported batch action")
                succeeded.append(event_id)
            except EventInsightNotFoundError:
                failed.append({"eventId": raw_event_id, "error": "event_not_found"})
            except EventInsightValidationError as exc:
                failed.append({"eventId": raw_event_id, "error": str(exc)})

        return {
            "traceId": _trace_id("event-insight-batch"),
            "succeededEventIds": succeeded,
            "failedItems": failed,
        }

    def _require_event(self, event_id: int) -> dict[str, Any]:
        """读取事件，不存在时抛出业务异常。

        Args:
            event_id: 事件主键。

        Returns:
            事件字段字典。
        """

        event = self._repository.get_event(event_id)
        if event is None:
            raise EventInsightNotFoundError(f"event {event_id} not found")
        return event

    def _present_event(self, row: dict[str, Any]) -> dict[str, Any]:
        """将数据库事件行转换为前端契约。

        Args:
            row: 事件数据库字段。

        Returns:
            camelCase 前端展示字段。
        """

        projected = dict(row)
        for override in self._repository.list_event_field_overrides(int(row["id"])):
            projected[str(override["field_name"])] = _decode_override_value(str(override["override_value"]))

        return {
            "id": int(projected["id"]),
            "title": str(projected["title"]),
            "summary": str(projected["summary"]),
            "eventTime": str(projected["event_time"]),
            "publishedAt": projected.get("published_at"),
            "eventType": str(projected["event_type"]),
            "importanceScore": float(projected.get("importance_score") or 0),
            "noveltyScore": float(projected.get("novelty_score") or 0),
            "marketRelevanceScore": float(projected.get("market_relevance_score") or 0),
            "confidenceScore": float(projected.get("confidence_score") or 0),
            "evidenceLevel": str(projected.get("evidence_level") or "C"),
            "analysisStatus": str(projected.get("analysis_status") or ""),
            "graphStatus": str(projected.get("graph_status") or ""),
            "manualStatus": str(projected.get("manual_status") or ""),
            "sourceMethod": str(projected.get("source_method") or ""),
            "createdAt": str(projected.get("created_at") or ""),
            "updatedAt": str(projected.get("updated_at") or ""),
        }

    def _present_topic(self, row: dict[str, Any]) -> dict[str, Any]:
        """将主题行转换为前端契约。

        Args:
            row: 主题或 topic_event 联表字段。

        Returns:
            camelCase 主题字段。
        """

        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "summary": str(row.get("summary") or ""),
            "lifecycleStage": str(row.get("lifecycle_stage") or "noise"),
            "heatScore": float(row.get("heat_score") or 0),
            "roleInTopic": str(row.get("role_in_topic") or ""),
            "relevanceScore": float(row.get("relevance_score") or 0),
            "manualLocked": bool(row.get("manual_locked") or 0),
        }

    def _present_evidence(self, row: dict[str, Any]) -> dict[str, Any]:
        """将证据行转换为前端契约。

        Args:
            row: evidence 与 raw_document 联表字段。

        Returns:
            camelCase 证据字段。
        """

        return {
            "id": int(row["id"]),
            "rawDocumentId": int(row["raw_document_id"]),
            "excerpt": str(row["excerpt"]),
            "role": str(row.get("role") or "primary"),
            "evidenceLevel": str(row.get("evidence_level") or "C"),
            "sourceTitle": str(row.get("source_title") or row.get("document_title") or ""),
            "sourceUrl": str(row.get("source_url") or row.get("document_url") or ""),
            "startOffset": int(row.get("start_offset") or 0),
            "endOffset": int(row.get("end_offset") or 0),
        }

    def _present_entity(self, row: dict[str, Any]) -> dict[str, Any]:
        """将实体行转换为前端契约。

        Args:
            row: entity 与 event_entity 联表字段。

        Returns:
            camelCase 实体字段。
        """

        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "entityType": str(row.get("entity_type") or ""),
            "canonicalName": str(row.get("canonical_name") or ""),
            "role": str(row.get("role") or ""),
            "relevanceScore": float(row.get("relevance_score") or 0),
        }

    def _present_topic_timeline_entry(
        self,
        row: dict[str, Any],
        evidence_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """将主题事件行转换为溯源时间线节点。

        Args:
            row: 事件与 topic_event 联表字段。
            evidence_rows: 当前事件证据行列表。

        Returns:
            前端主题溯源时间线节点。
        """

        evidence = [self._present_evidence(evidence_row) for evidence_row in evidence_rows]
        return {
            "id": f"event-{int(row['id'])}",
            "eventId": int(row["id"]),
            "happenedAt": str(row["event_time"]),
            "title": str(row["title"]),
            "summary": str(row["summary"]),
            "roleInTopic": str(row.get("role_in_topic") or "supporting_event"),
            "relevanceScore": float(row.get("relevance_score") or 0),
            "evidenceCount": int(row.get("evidence_count") or len(evidence)),
            "evidence": evidence,
        }


def _trace_id(prefix: str) -> str:
    """生成响应 traceId。

    Args:
        prefix: traceId 前缀。

    Returns:
        可定位单次请求的 traceId 字符串。
    """

    return f"{prefix}-{uuid4().hex[:12]}"


def _decode_override_value(value: str) -> Any:
    """解析人工覆盖值。

    Args:
        value: JSON 字符串或兼容旧值的普通字符串。

    Returns:
        解析后的 Python 值。
    """

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    """复制 SQLite 行字典，确保可 JSON 序列化。

    Args:
        row: 数据库字段。

    Returns:
        可序列化字典。
    """

    return {key: value for key, value in row.items()}


def _build_topic_metrics(
    event_rows: list[dict[str, Any]],
    evidence_by_event_id: dict[int, list[dict[str, Any]]],
) -> list[dict[str, str]]:
    """基于主题事件生成展示指标。

    Args:
        event_rows: 主题关联事件行列表。
        evidence_by_event_id: 事件证据映射。

    Returns:
        前端指标卡列表。
    """

    evidence_count = sum(len(items) for items in evidence_by_event_id.values())
    document_ids = {
        int(evidence["raw_document_id"])
        for items in evidence_by_event_id.values()
        for evidence in items
        if evidence.get("raw_document_id") is not None
    }
    key_nodes = min(len(event_rows), 4)
    missing_evidence = sum(1 for row in event_rows if int(row.get("evidence_count") or 0) == 0)
    return [
        {"label": "主题事件", "value": str(len(event_rows)), "note": "按时间倒序展示", "noteTone": "green"},
        {"label": "有效证据", "value": str(evidence_count), "note": f"覆盖 {len(document_ids)} 份材料", "noteTone": "green"},
        {"label": "关键节点", "value": str(key_nodes), "note": "由关联事件生成", "noteTone": "green"},
        {"label": "待验证线索", "value": str(missing_evidence), "note": "缺少证据的事件数", "noteTone": "amber"},
    ]


def _build_topic_stages(event_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """基于主题事件生成阶段条。

    Args:
        event_rows: 主题关联事件行列表，按时间倒序排列。

    Returns:
        按时间正序排列的阶段列表，最后一项标记为当前阶段。
    """

    chronological_rows = list(reversed(event_rows))[-4:]
    stages: list[dict[str, Any]] = []
    for index, row in enumerate(chronological_rows, start=1):
        is_current = index == len(chronological_rows)
        stages.append(
            {
                "id": f"stage-{index}",
                "label": f"阶段 {index:02d}{' · 当前' if is_current else ''}",
                "title": str(row["title"]),
                "active": is_current,
            }
        )
    return stages


def _build_trace_clues(topic: dict[str, Any], timeline: list[dict[str, Any]]) -> list[str]:
    """生成主题溯源待验证线索。

    Args:
        topic: 主题字段。
        timeline: 时间线节点列表。

    Returns:
        待验证线索文案列表。
    """

    if not timeline:
        return ["先关联事件到该主题"]
    clues = ["继续补充交叉证据"]
    if str(topic.get("lifecycle_stage") or "noise") == "noise":
        clues.append("确认主题是否具备持续跟踪价值")
    if any(int(item.get("evidenceCount") or 0) == 0 for item in timeline):
        clues.append("为缺少证据的节点补充材料")
    return clues
