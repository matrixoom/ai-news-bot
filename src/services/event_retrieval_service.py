"""Event Insight 事件检索、重复候选与规则聚类服务。"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from .event_insight_repository import EventInsightRepository
from .sqlite_vec_loader import SqliteVecStatus, probe_sqlite_vec


class EventRetrievalService:
    """提供 Event Insight 检索和非破坏性归类能力。

    Args:
        repository: Event Insight SQLite 仓储。

    Returns:
        初始化后的检索服务实例。
    """

    def __init__(self, repository: EventInsightRepository) -> None:
        self._repository = repository

    def inspect_vector_runtime(self) -> dict[str, Any]:
        """探测向量检索扩展状态。

        Args:
            无。

        Returns:
            包含 sqlite-vec 可用性和说明的状态字典。
        """

        with sqlite3.connect(self._repository.db_path) as connection:
            status = probe_sqlite_vec(connection)
        return _present_vec_status(status)

    def search_events(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        """按关键词检索事件，中文短词使用 n-gram fallback。

        Args:
            query: 用户输入的检索词。
            limit: 返回条数上限。

        Returns:
            包含命中事件和分数字段的检索响应。
        """

        normalized_query = query.strip()
        normalized_limit = min(max(1, limit), 100)
        if not normalized_query:
            return {"items": [], "total": 0, "query": normalized_query}

        scored_items = self._score_events(normalized_query)
        items = [
            {**_present_event(row), "retrievalScore": round(score, 4)}
            for row, score in scored_items[:normalized_limit]
        ]
        return {"items": items, "total": len(scored_items), "query": normalized_query}

    def generate_duplicate_candidates(self, source_event_id: int, *, threshold: float = 0.35) -> dict[str, Any]:
        """生成重复事件候选，不自动合并、不修改事件状态。

        Args:
            source_event_id: 来源事件主键。
            threshold: 候选写入的最低相似度分数。

        Returns:
            包含来源事件和候选列表的响应。
        """

        source = self._repository.get_event(source_event_id)
        if source is None:
            return {"sourceEventId": source_event_id, "candidates": []}

        normalized_threshold = min(max(0.0, threshold), 1.0)
        source_text = _event_text(source)
        candidates: list[dict[str, Any]] = []
        for event in self._list_active_events():
            candidate_id = int(event["id"])
            if candidate_id == source_event_id:
                continue
            score = _similarity(source_text, _event_text(event))
            if score < normalized_threshold:
                continue
            self._repository.create_duplicate_event_candidate(
                source_event_id=source_event_id,
                candidate_event_id=candidate_id,
                score=score,
                method="chinese_ngram_v1",
            )
            candidates.append(
                {
                    "candidateEventId": candidate_id,
                    "score": round(score, 4),
                    "method": "chinese_ngram_v1",
                    "event": _present_event(event),
                }
            )

        candidates.sort(key=lambda item: (-float(item["score"]), int(item["candidateEventId"])))
        return {"sourceEventId": source_event_id, "candidates": candidates}

    def cluster_events(self, *, keyword: str, topic_name: str) -> dict[str, Any]:
        """按规则关键词创建主题并关联匹配事件。

        Args:
            keyword: 事件检索关键词。
            topic_name: 目标主题名称。

        Returns:
            包含主题和已关联事件 ID 的响应。
        """

        normalized_keyword = keyword.strip()
        normalized_topic_name = topic_name.strip()
        if not normalized_keyword or not normalized_topic_name:
            return {"topic": None, "linkedEventIds": []}

        topic = self._repository.create_topic(
            name=normalized_topic_name,
            summary=f"规则聚类：{normalized_keyword}",
        )
        matches = self.search_events(normalized_keyword, limit=100)["items"]
        linked_event_ids: list[int] = []
        for item in matches:
            event_id = int(item["id"])
            linked = self._repository.link_event_topic(
                event_id=event_id,
                topic_id=int(topic["id"]),
                role_in_topic="supporting_event",
                relevance_score=float(item["retrievalScore"]),
                manual_locked=False,
            )
            if linked:
                linked_event_ids.append(event_id)

        return {"topic": _present_topic(topic), "linkedEventIds": linked_event_ids}

    def _score_events(self, query: str) -> list[tuple[dict[str, Any], float]]:
        """计算活跃事件与查询词的文本相关度。

        Args:
            query: 已清理的查询词。

        Returns:
            按分数倒序排列的事件和分数元组。
        """

        scored: list[tuple[dict[str, Any], float]] = []
        for event in self._list_active_events():
            score = _query_score(query, _event_text(event))
            if score > 0:
                scored.append((event, score))
        scored.sort(key=lambda item: (-item[1], str(item[0].get("event_time") or ""), int(item[0]["id"])))
        return scored

    def _list_active_events(self) -> list[dict[str, Any]]:
        """读取可参与检索的活跃事件。

        Args:
            无。

        Returns:
            活跃事件数据库行列表。
        """

        result = self._repository.list_events_for_workbench(status="active", page=1, page_size=500)
        return list(result["items"])


def _event_text(event: dict[str, Any]) -> str:
    """拼接事件标题和摘要。

    Args:
        event: 事件数据库行。

    Returns:
        用于检索和相似度计算的文本。
    """

    return f"{event.get('title') or ''} {event.get('summary') or ''}"


def _query_score(query: str, text: str) -> float:
    """计算查询词命中文本的相关度。

    Args:
        query: 用户查询词。
        text: 候选事件文本。

    Returns:
        0 到 1.5 左右的召回分数，越高越相关。
    """

    normalized_query = _normalize(query)
    normalized_text = _normalize(text)
    if not normalized_query or not normalized_text:
        return 0.0

    substring_bonus = 1.0 if normalized_query in normalized_text else 0.0
    overlap = _overlap_score(_grams(normalized_query), _grams(normalized_text))
    return substring_bonus + overlap


def _similarity(left: str, right: str) -> float:
    """计算两个事件文本的 n-gram Jaccard 相似度。

    Args:
        left: 来源事件文本。
        right: 候选事件文本。

    Returns:
        0 到 1 之间的相似度分数。
    """

    return _overlap_score(_grams(_normalize(left)), _grams(_normalize(right)))


def _overlap_score(left: set[str], right: set[str]) -> float:
    """计算两个 token 集合的交集占比。

    Args:
        left: 左侧 token 集合。
        right: 右侧 token 集合。

    Returns:
        Jaccard 相似度。
    """

    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _grams(text: str) -> set[str]:
    """生成中英文混合 n-gram token。

    Args:
        text: 已归一化文本。

    Returns:
        适合中文短词召回的 token 集合。
    """

    compact = re.sub(r"\s+", "", text)
    grams: set[str] = set()
    for size in (2, 3, 4):
        if len(compact) >= size:
            grams.update(compact[index : index + size] for index in range(0, len(compact) - size + 1))
    grams.update(token for token in re.split(r"\W+", text) if token)
    return grams


def _normalize(text: str) -> str:
    """归一化检索文本。

    Args:
        text: 原始文本。

    Returns:
        小写并压缩空白后的文本。
    """

    return re.sub(r"\s+", " ", text.casefold()).strip()


def _present_event(row: dict[str, Any]) -> dict[str, Any]:
    """将事件数据库行转换为检索响应字段。

    Args:
        row: 事件数据库字段。

    Returns:
        camelCase 事件摘要。
    """

    return {
        "id": int(row["id"]),
        "title": str(row["title"]),
        "summary": str(row["summary"]),
        "eventTime": str(row["event_time"]),
        "eventType": str(row["event_type"]),
        "confidenceScore": float(row.get("confidence_score") or 0),
        "manualStatus": str(row.get("manual_status") or ""),
    }


def _present_topic(row: dict[str, Any]) -> dict[str, Any]:
    """将主题数据库行转换为响应字段。

    Args:
        row: 主题数据库字段。

    Returns:
        camelCase 主题摘要。
    """

    return {
        "id": int(row["id"]),
        "name": str(row["name"]),
        "summary": str(row.get("summary") or ""),
        "lifecycleStage": str(row.get("lifecycle_stage") or "noise"),
        "heatScore": float(row.get("heat_score") or 0),
    }


def _present_vec_status(status: SqliteVecStatus) -> dict[str, Any]:
    """将 sqlite-vec 状态转换为响应字段。

    Args:
        status: sqlite-vec 探测状态。

    Returns:
        可序列化状态字典。
    """

    return {"available": status.available, "reason": status.reason}
