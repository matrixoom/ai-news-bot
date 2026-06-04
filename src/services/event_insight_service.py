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

    def list_topics(self) -> dict[str, Any]:
        """构建主题列表响应。

        Args:
            无。

        Returns:
            前端可选择主题列表。
        """

        topics = [self._present_topic(topic) for topic in self._repository.list_topics()]
        return {
            "traceId": _trace_id("event-insight-topics"),
            "items": topics,
            "total": len(topics),
        }

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

    def get_event_graph(self, *, topic_id: int | None = None) -> dict[str, Any]:
        """构建事件关系图投影。

        Args:
            topic_id: 可选主题主键，传入时只展示主题内事件关系。

        Returns:
            包含节点、边和默认选中节点的图谱响应。
        """

        if topic_id is not None and self._repository.get_topic(topic_id) is None:
            raise EventInsightNotFoundError(f"topic {topic_id} not found")

        if topic_id is None:
            self._grow_event_network()

        event_rows = self._repository.list_event_graph_events(topic_id=topic_id)
        event_ids = [int(row["id"]) for row in event_rows]
        relation_rows = self._repository.list_event_graph_relations(event_ids)
        node_positions = _build_graph_positions(len(event_rows))
        nodes = [
            _present_graph_node(row, node_positions[index])
            for index, row in enumerate(event_rows)
        ]
        node_id_by_event_id = {int(node["eventId"]): str(node["id"]) for node in nodes}
        edges = [
            _present_graph_edge(row, node_id_by_event_id, index)
            for index, row in enumerate(relation_rows)
            if int(row["source_event_id"]) in node_id_by_event_id and int(row["target_event_id"]) in node_id_by_event_id
        ]

        return {
            "traceId": _trace_id("event-insight-graph"),
            "nodes": nodes,
            "edges": edges,
            "selectedNodeId": nodes[0]["id"] if nodes else None,
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

    def create_relation(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        """创建事件到事件的关系边。

        Args:
            payload: 关系源事件、目标事件、类型和评分。

        Returns:
            新增关系的前端响应。
        """

        body = payload or {}
        try:
            source_event_id = int(body.get("sourceEventId"))
            target_event_id = int(body.get("targetEventId"))
        except (TypeError, ValueError):
            raise EventInsightValidationError("sourceEventId and targetEventId are required") from None
        self._require_event(source_event_id)
        self._require_event(target_event_id)
        relation_type = str(body.get("relationType") or "").strip()
        if relation_type not in {"same_topic", "cause", "support", "contradict", "follow_up"}:
            raise EventInsightValidationError("unsupported relationType")
        relation_summary = str(body.get("relationSummary") or "").strip()
        relation_id = self._repository.create_event_relation(
            source_event_id=source_event_id,
            target_event_id=target_event_id,
            relation_type=relation_type,
            relation_summary=relation_summary,
            strength_score=float(body.get("strengthScore") or 0),
            confidence_score=float(body.get("confidenceScore") or 0),
            generation_method="manual",
        )
        self._repository.create_event_operation_log(
            event_id=source_event_id,
            operation_type="create_relation",
            before_json="{}",
            after_json=json.dumps({"relation_id": relation_id, "target_event_id": target_event_id}, ensure_ascii=False),
            reason="manual relation create",
            operator="frontend",
        )
        return {
            "traceId": _trace_id("event-insight-relation"),
            "relation": {
                "id": relation_id,
                "sourceEventId": source_event_id,
                "targetEventId": target_event_id,
                "relationType": relation_type,
                "relationSummary": relation_summary,
                "strengthScore": float(body.get("strengthScore") or 0),
                "confidenceScore": float(body.get("confidenceScore") or 0),
            },
        }

    def _grow_event_network(self) -> None:
        """将通过质量审核的事件自动投入事件关系网络。"""

        event_rows = self._repository.list_event_graph_events(topic_id=None, limit=80)
        for event in event_rows:
            event_id = int(event["id"])
            if str(event.get("graph_status") or "pending") not in {"pending", "failed"}:
                continue
            relation_created = False
            for candidate in event_rows:
                candidate_id = int(candidate["id"])
                if candidate_id == event_id:
                    continue
                decision = _judge_event_relation(event, candidate)
                if decision is None:
                    continue
                source_event_id, target_event_id = _order_relation_direction(event, candidate)
                if self._repository.event_relation_exists(
                    source_event_id=source_event_id,
                    target_event_id=target_event_id,
                ):
                    continue
                self._repository.create_event_relation(
                    source_event_id=source_event_id,
                    target_event_id=target_event_id,
                    relation_type=decision["relation_type"],
                    relation_summary=decision["relation_summary"],
                    strength_score=decision["strength_score"],
                    confidence_score=decision["confidence_score"],
                    generation_method="rule",
                )
                relation_created = True
            self._repository.update_event_graph_status(
                event_id=event_id,
                graph_status="relation_built" if relation_created else "clustered",
            )

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


def _judge_event_relation(event: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any] | None:
    """基于事件文本和类型判断是否应自动建立关系边。

    Args:
        event: 待入网事件。
        candidate: 网络中已有或同批候选事件。

    Returns:
        达到阈值时返回关系字段，否则返回 None。
    """

    event_tokens = _event_tokens(event)
    candidate_tokens = _event_tokens(candidate)
    overlap = event_tokens & candidate_tokens
    if not overlap:
        return None
    same_type = str(event.get("event_type") or "") == str(candidate.get("event_type") or "")
    score = len(overlap) / max(1, min(len(event_tokens), len(candidate_tokens)))
    if not same_type and score < 0.18:
        return None
    if same_type and score < 0.08 and len(overlap) < 2:
        return None

    relation_type = "same_topic" if same_type else "support"
    if not same_type and str(event.get("event_time") or "") > str(candidate.get("event_time") or ""):
        relation_type = "follow_up"
    clue = "、".join(sorted(overlap)[:4])
    return {
        "relation_type": relation_type,
        "relation_summary": f"事件网络自动聚类：两个事件共享 {clue} 等线索。",
        "strength_score": round(min(0.92, 0.55 + score), 2),
        "confidence_score": round(min(0.9, 0.62 + score / 2), 2),
    }


def _order_relation_direction(event: dict[str, Any], candidate: dict[str, Any]) -> tuple[int, int]:
    """按事件时间确定关系边方向。

    Args:
        event: 当前事件。
        candidate: 候选事件。

    Returns:
        source_event_id 与 target_event_id。
    """

    event_time = str(event.get("event_time") or "")
    candidate_time = str(candidate.get("event_time") or "")
    if candidate_time <= event_time:
        return int(candidate["id"]), int(event["id"])
    return int(event["id"]), int(candidate["id"])


def _event_tokens(row: dict[str, Any]) -> set[str]:
    """提取事件聚类用的轻量文本 token。

    Args:
        row: 事件字段。

    Returns:
        去停用词后的 token 集合。
    """

    text = f"{row.get('title') or ''} {row.get('summary') or ''}".lower()
    import re

    ascii_tokens = {token for token in re.findall(r"[a-z0-9]{2,}", text) if token not in _GRAPH_STOP_WORDS}
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    cjk_tokens = {"".join(cjk_chars[index : index + 2]) for index in range(max(0, len(cjk_chars) - 1))}
    return {token for token in [*ascii_tokens, *cjk_tokens] if token and token not in _GRAPH_STOP_WORDS}


_GRAPH_STOP_WORDS = {
    "ai",
    "和",
    "的",
    "了",
    "在",
    "与",
    "及",
    "或",
    "等",
    "继续",
    "维持",
}


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


def _build_graph_positions(count: int) -> list[dict[str, str]]:
    """生成确定性的图谱节点坐标。

    Args:
        count: 节点数量。

    Returns:
        百分比坐标列表。
    """

    seeds = [
        ("12%", "22%"),
        ("58%", "46%"),
        ("32%", "64%"),
        ("70%", "18%"),
        ("18%", "52%"),
        ("76%", "68%"),
    ]
    return [{"left": seeds[index % len(seeds)][0], "top": seeds[index % len(seeds)][1]} for index in range(count)]


def _present_graph_node(row: dict[str, Any], position: dict[str, str]) -> dict[str, Any]:
    """将事件行转换为关系图节点。

    Args:
        row: 事件数据库字段。
        position: 前端画布百分比坐标。

    Returns:
        前端图谱节点。
    """

    confidence_score = float(row.get("confidence_score") or 0)
    return {
        "id": f"event-{int(row['id'])}",
        "eventId": int(row["id"]),
        "kind": str(row.get("event_type") or "event"),
        "title": str(row["title"]),
        "happenedAt": str(row["event_time"]),
        "confidence": f"{_confidence_label(confidence_score)} · {int(round(confidence_score * 100))}",
        "confidenceTone": _confidence_tone(confidence_score),
        "summary": str(row["summary"]),
        "left": position["left"],
        "top": position["top"],
    }


def _present_graph_edge(
    row: dict[str, Any],
    node_id_by_event_id: dict[int, str],
    index: int,
) -> dict[str, Any]:
    """将事件关系行转换为关系图边。

    Args:
        row: event_relation 数据库字段。
        node_id_by_event_id: event_id 到前端 node id 的映射。
        index: 边序号，用于生成稳定布局。

    Returns:
        前端图谱边。
    """

    edge_layouts = [
        ("25%", "35%", "34%", "18deg"),
        ("38%", "58%", "28%", "-12deg"),
        ("20%", "48%", "42%", "42deg"),
        ("54%", "30%", "30%", "65deg"),
    ]
    left, top, width, rotate = edge_layouts[index % len(edge_layouts)]
    return {
        "id": f"relation-{int(row['id'])}",
        "sourceNodeId": node_id_by_event_id[int(row["source_event_id"])],
        "targetNodeId": node_id_by_event_id[int(row["target_event_id"])],
        "type": _present_relation_type(str(row["relation_type"])),
        "summary": str(row.get("relation_summary") or ""),
        "strengthScore": float(row.get("strength_score") or 0),
        "confidenceScore": float(row.get("confidence_score") or 0),
        "left": left,
        "top": top,
        "width": width,
        "rotate": rotate,
    }


def _present_relation_type(relation_type: str) -> str:
    """映射后端关系类型到前端绘制类型。

    Args:
        relation_type: event_relation.relation_type。

    Returns:
        前端边类型。
    """

    mapping = {
        "cause": "cause",
        "same_topic": "parallel",
        "support": "parallel",
        "contradict": "risk",
        "follow_up": "follow",
    }
    return mapping.get(relation_type, "parallel")


def _confidence_label(score: float) -> str:
    """生成置信度中文标签。

    Args:
        score: 0 到 1 的置信度。

    Returns:
        中文可信度标签。
    """

    if score >= 0.8:
        return "高可信"
    if score >= 0.6:
        return "中可信"
    return "低可信"


def _confidence_tone(score: float) -> str:
    """生成置信度色调。

    Args:
        score: 0 到 1 的置信度。

    Returns:
        前端 InsightTone。
    """

    if score >= 0.8:
        return "green"
    if score >= 0.6:
        return "amber"
    return "rose"
