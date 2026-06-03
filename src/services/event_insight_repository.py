"""Event Insight SQLite repository."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from .event_insight_migrations import EventInsightMigrationService, utc_now_iso


class EventInsightRepository:
    """管理 Event Insight 独立 SQLite 事实库。

    Args:
        db_path: SQLite 数据库路径，默认写入 `.data/event_insight.db`。

    Returns:
        初始化后的仓储实例；构造时会应用 Event Insight migration。
    """

    def __init__(self, db_path: str | Path = ".data/event_insight.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        EventInsightMigrationService(self._db_path).apply()

    @property
    def db_path(self) -> Path:
        """返回当前数据库路径。

        Returns:
            Event Insight SQLite 数据库路径。
        """

        return self._db_path

    def list_table_names(self) -> set[str]:
        """列出当前数据库全部表名。

        Returns:
            SQLite schema 中的表名集合。
        """

        with self._session() as connection:
            rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        return {str(row["name"]) for row in rows}

    def list_applied_migrations(self) -> list[str]:
        """列出已应用 migration 版本。

        Returns:
            按版本排序的 migration 名称。
        """

        with self._session() as connection:
            rows = connection.execute("SELECT version FROM schema_migration ORDER BY version ASC").fetchall()
        return [str(row["version"]) for row in rows]

    def inspect_pragmas(self) -> dict[str, Any]:
        """读取关键 SQLite PRAGMA 状态。

        Returns:
            包含 `foreign_keys` 和 `journal_mode` 的字典。
        """

        with self._session() as connection:
            foreign_keys = int(connection.execute("PRAGMA foreign_keys").fetchone()[0])
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
        return {"foreign_keys": foreign_keys, "journal_mode": journal_mode}

    def create_raw_document(
        self,
        *,
        source_type: str,
        title: str,
        content_text: str,
        content_hash: str,
        url: str = "",
        local_file_path: str = "",
        published_at: str | None = None,
        scan_batch_id: int | None = None,
    ) -> int:
        """新增原始研究材料。

        Args:
            source_type: 材料来源类型。
            title: 材料标题。
            content_text: 解析后的正文。
            content_hash: 内容哈希，用于幂等识别。
            url: 来源 URL。
            local_file_path: 受控本地文件相对路径。
            published_at: 材料发布时间。
            scan_batch_id: 可选扫描批次 ID。

        Returns:
            新增材料主键。
        """

        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO raw_document (
                    scan_batch_id, source_type, title, url, local_file_path,
                    content_text, content_hash, published_at, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_batch_id,
                    source_type,
                    title,
                    url,
                    local_file_path,
                    content_text,
                    content_hash,
                    published_at,
                    utc_now_iso(),
                ),
            )
            return int(cursor.lastrowid)

    def get_raw_document(self, document_id: int) -> dict[str, Any] | None:
        """按主键读取原始材料。

        Args:
            document_id: 原始材料主键。

        Returns:
            找到时返回材料字段字典，否则返回 None。
        """

        with self._session() as connection:
            row = connection.execute("SELECT * FROM raw_document WHERE id = ?", (document_id,)).fetchone()
        return dict(row) if row else None

    def get_raw_document_by_hash(self, content_hash: str) -> dict[str, Any] | None:
        """按内容哈希读取原始材料。

        Args:
            content_hash: 材料内容哈希。

        Returns:
            找到时返回材料字段字典，否则返回 None。
        """

        with self._session() as connection:
            row = connection.execute("SELECT * FROM raw_document WHERE content_hash = ?", (content_hash,)).fetchone()
        return dict(row) if row else None

    def update_raw_document_content(self, *, document_id: int, title: str, content_text: str) -> None:
        """更新原始材料标题和正文。

        Args:
            document_id: 原始材料主键。
            title: 新标题。
            content_text: 新正文。

        Returns:
            无返回值；FTS 由触发器同步。
        """

        with self._session() as connection:
            connection.execute(
                """
                UPDATE raw_document
                SET title = ?, content_text = ?
                WHERE id = ?
                """,
                (title, content_text, document_id),
            )

    def archive_raw_document(self, *, document_id: int, reason: str) -> None:
        """软归档原始材料。

        Args:
            document_id: 原始材料主键。
            reason: 归档原因。

        Returns:
            无返回值；归档后材料会从 FTS 中移除。
        """

        with self._session() as connection:
            connection.execute(
                """
                UPDATE raw_document
                SET archived_at = ?, archive_reason = ?
                WHERE id = ?
                """,
                (utc_now_iso(), reason, document_id),
            )

    def search_raw_documents(self, query: str) -> list[int]:
        """通过 FTS 查询原始材料。

        Args:
            query: FTS5 MATCH 查询词。

        Returns:
            命中的 raw_document ID 列表。
        """

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT raw_document_id
                FROM raw_document_fts
                WHERE raw_document_fts MATCH ?
                ORDER BY rank
                """,
                (query,),
            ).fetchall()
        return [int(row["raw_document_id"]) for row in rows]

    def create_event(
        self,
        *,
        title: str,
        summary: str,
        event_time: str,
        event_type: str,
        confidence_score: float,
        published_at: str | None = None,
        analysis_run_id: int | None = None,
        source_method: str = "manual",
    ) -> int:
        """新增结构化事件事实。

        Args:
            title: 事件标题。
            summary: 事件摘要。
            event_time: 事件发生时间。
            event_type: 事件类型。
            confidence_score: 置信度分数。
            published_at: 事件发布时间。
            analysis_run_id: 可选分析批次 ID。
            source_method: 事件生成方式。

        Returns:
            新增事件主键。
        """

        timestamp = utc_now_iso()
        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO event (
                    analysis_run_id, title, summary, event_time, published_at,
                    event_type, confidence_score, source_method, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_run_id,
                    title,
                    summary,
                    event_time,
                    published_at,
                    event_type,
                    confidence_score,
                    source_method,
                    timestamp,
                    timestamp,
                ),
            )
            return int(cursor.lastrowid)

    def create_analysis_run(
        self,
        *,
        run_type: str,
        model_provider: str = "",
        model_name: str = "",
        prompt_version: str = "event_extraction.v1",
    ) -> int:
        """创建分析运行记录。"""

        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO analysis_run (
                    run_type, status, model_provider, model_name, prompt_version, started_at
                ) VALUES (?, 'running', ?, ?, ?, ?)
                """,
                (run_type, model_provider, model_name, prompt_version, utc_now_iso()),
            )
        return int(cursor.lastrowid)

    def complete_analysis_run(self, *, analysis_run_id: int) -> None:
        """标记分析运行成功。"""

        with self._session() as connection:
            connection.execute(
                "UPDATE analysis_run SET status = 'succeeded', completed_at = ? WHERE id = ?",
                (utc_now_iso(), analysis_run_id),
            )

    def fail_analysis_run(self, *, analysis_run_id: int, error_message: str) -> None:
        """标记分析运行失败。"""

        with self._session() as connection:
            connection.execute(
                """
                UPDATE analysis_run
                SET status = 'failed', completed_at = ?, error_message = ?
                WHERE id = ?
                """,
                (utc_now_iso(), error_message, analysis_run_id),
            )

    def get_event(self, event_id: int) -> dict[str, Any] | None:
        """按主键读取事件事实。

        Args:
            event_id: 事件主键。

        Returns:
            找到时返回事件字段字典，否则返回 None。
        """

        with self._session() as connection:
            row = connection.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
        return dict(row) if row else None

    def update_event_summary(self, *, event_id: int, title: str, summary: str) -> None:
        """更新事件标题和摘要。

        Args:
            event_id: 事件主键。
            title: 新标题。
            summary: 新摘要。

        Returns:
            无返回值；FTS 由触发器同步。
        """

        with self._session() as connection:
            connection.execute(
                """
                UPDATE event
                SET title = ?, summary = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, summary, utc_now_iso(), event_id),
            )

    def archive_event(self, *, event_id: int, reason: str) -> None:
        """软归档事件。

        Args:
            event_id: 事件主键。
            reason: 归档原因。

        Returns:
            无返回值；归档后事件会从 FTS 中移除。
        """

        with self._session() as connection:
            connection.execute(
                """
                UPDATE event
                SET manual_status = 'archived', archived_at = ?, archive_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (utc_now_iso(), reason, utc_now_iso(), event_id),
            )

    def search_events(self, query: str) -> list[int]:
        """通过 FTS 查询事件。

        Args:
            query: FTS5 MATCH 查询词。

        Returns:
            命中的 event ID 列表。
        """

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT event_id
                FROM event_fts
                WHERE event_fts MATCH ?
                ORDER BY rank
                """,
                (query,),
            ).fetchall()
        return [int(row["event_id"]) for row in rows]

    def create_evidence(
        self,
        *,
        raw_document_id: int,
        excerpt: str,
        start_offset: int = 0,
        end_offset: int = 0,
        evidence_level: str = "C",
        source_title: str = "",
        source_url: str = "",
    ) -> int:
        """新增证据片段。

        Args:
            raw_document_id: 原始材料主键。
            excerpt: 证据原文片段。
            start_offset: 片段开始位置。
            end_offset: 片段结束位置。
            evidence_level: 证据等级。
            source_title: 证据来源标题。
            source_url: 证据来源 URL。

        Returns:
            新增证据主键。
        """

        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO evidence (
                    raw_document_id, excerpt, start_offset, end_offset,
                    evidence_level, source_title, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_document_id,
                    excerpt,
                    start_offset,
                    end_offset,
                    evidence_level,
                    source_title,
                    source_url,
                    utc_now_iso(),
                ),
            )
            return int(cursor.lastrowid)

    def link_event_source(self, *, event_id: int, raw_document_id: int, source_role: str = "primary") -> None:
        """关联事件和原始材料。"""

        with self._session() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO event_source(event_id, raw_document_id, source_role, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_id, raw_document_id, source_role, utc_now_iso()),
            )

    def link_event_evidence(self, *, event_id: int, evidence_id: int, role: str) -> None:
        """关联事件和证据。

        Args:
            event_id: 事件主键。
            evidence_id: 证据主键。
            role: 证据角色。

        Returns:
            无返回值；无效外键由 SQLite 拒绝。
        """

        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO event_evidence(event_id, evidence_id, role, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_id, evidence_id, role, utc_now_iso()),
            )

    def create_entity(self, *, name: str, entity_type: str, canonical_name: str = "") -> int:
        """创建或复用实体。"""

        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO entity(name, entity_type, canonical_name, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name, entity_type) DO NOTHING
                """,
                (name, entity_type, canonical_name, utc_now_iso()),
            )
            row = connection.execute(
                "SELECT id FROM entity WHERE name = ? AND entity_type = ?",
                (name, entity_type),
            ).fetchone()
        return int(row["id"])

    def link_event_entity(
        self,
        *,
        event_id: int,
        entity_id: int,
        role: str = "mentioned",
        relevance_score: float = 1.0,
    ) -> None:
        """关联事件和实体。"""

        with self._session() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO event_entity(event_id, entity_id, role, relevance_score, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_id, entity_id, role, relevance_score, utc_now_iso()),
            )

    def list_event_entities(self, event_id: int) -> list[dict[str, Any]]:
        """读取事件关联实体。"""

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT e.id, e.name, e.entity_type, e.canonical_name, ee.role, ee.relevance_score
                FROM event_entity ee
                JOIN entity e ON e.id = ee.entity_id
                WHERE ee.event_id = ?
                ORDER BY ee.relevance_score DESC, e.id ASC
                """,
                (event_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_llm_call_log(
        self,
        *,
        task_type: str,
        provider_config_id: int | None,
        model_name: str,
        status: str,
        error_message: str = "",
    ) -> int:
        """记录一次 LLM 调用摘要。"""

        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO llm_call_log (
                    task_type, provider_config_id, model_name, status, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_type, provider_config_id, model_name, status, error_message, utc_now_iso()),
            )
        return int(cursor.lastrowid)

    def get_llm_provider_config(self, provider_id: int) -> dict[str, Any] | None:
        """读取 LLM provider 配置，用于校验 call log 外键。"""

        with self._session() as connection:
            row = connection.execute("SELECT * FROM llm_provider_config WHERE id = ?", (provider_id,)).fetchone()
        return dict(row) if row else None

    def create_event_field_override(
        self,
        *,
        event_id: int,
        field_name: str,
        override_value: str,
        reason: str,
        operator: str,
    ) -> int:
        """新增人工字段覆盖记录。

        Args:
            event_id: 事件主键。
            field_name: 被覆盖字段名。
            override_value: 人工覆盖值。
            reason: 覆盖原因。
            operator: 操作人。

        Returns:
            新增覆盖记录主键。
        """

        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO event_field_override (
                    event_id, field_name, override_value, reason, operator, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, field_name, override_value, reason, operator, utc_now_iso()),
            )
            return int(cursor.lastrowid)

    def list_event_field_overrides(self, event_id: int) -> list[dict[str, Any]]:
        """读取事件的未归档人工覆盖记录。

        Args:
            event_id: 事件主键。

        Returns:
            覆盖记录字典列表。
        """

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM event_field_override
                WHERE event_id = ? AND archived_at IS NULL
                ORDER BY id ASC
                """,
                (event_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_duplicate_event_candidate(
        self,
        *,
        source_event_id: int,
        candidate_event_id: int,
        score: float,
        method: str,
    ) -> int:
        """新增或更新重复事件候选。

        Args:
            source_event_id: 来源事件主键。
            candidate_event_id: 候选重复事件主键。
            score: 相似度分数。
            method: 生成方法。

        Returns:
            候选记录主键。
        """

        timestamp = utc_now_iso()
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO duplicate_event_candidate (
                    source_event_id, candidate_event_id, score, method, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_event_id, candidate_event_id, method) DO UPDATE SET
                    score = excluded.score,
                    updated_at = excluded.updated_at
                """,
                (source_event_id, candidate_event_id, score, method, timestamp, timestamp),
            )
            row = connection.execute(
                """
                SELECT id
                FROM duplicate_event_candidate
                WHERE source_event_id = ? AND candidate_event_id = ? AND method = ?
                """,
                (source_event_id, candidate_event_id, method),
            ).fetchone()
        return int(row["id"])

    def list_duplicate_event_candidates(self, source_event_id: int) -> list[dict[str, Any]]:
        """读取某个事件的重复候选。

        Args:
            source_event_id: 来源事件主键。

        Returns:
            候选记录字典列表。
        """

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM duplicate_event_candidate
                WHERE source_event_id = ?
                ORDER BY score DESC, id ASC
                """,
                (source_event_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def enqueue_graph_sync(
        self,
        *,
        aggregate_type: str,
        aggregate_id: int,
        operation: str,
        payload_json: str,
        idempotency_key: str,
    ) -> int:
        """写入图谱同步 outbox。

        Args:
            aggregate_type: 聚合类型，例如 event。
            aggregate_id: 聚合主键。
            operation: 投影操作类型。
            payload_json: 投影 payload。
            idempotency_key: 幂等键。

        Returns:
            outbox 记录主键；重复幂等键返回已有记录。
        """

        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO graph_sync_outbox (
                    aggregate_type, aggregate_id, operation, payload_json, idempotency_key, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(idempotency_key) DO NOTHING
                """,
                (aggregate_type, aggregate_id, operation, payload_json, idempotency_key, utc_now_iso()),
            )
            row = connection.execute(
                "SELECT id FROM graph_sync_outbox WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        return int(row["id"])

    def list_graph_outbox(self) -> list[dict[str, Any]]:
        """读取图谱同步 outbox。

        Returns:
            outbox 记录字典列表。
        """

        with self._session() as connection:
            rows = connection.execute("SELECT * FROM graph_sync_outbox ORDER BY id ASC").fetchall()
        return [dict(row) for row in rows]

    def list_events_for_workbench(
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
        """分页读取事件工作台列表。

        Args:
            keyword: 标题或摘要关键字；SQLite FTS5 中文分词较弱，因此列表检索先使用 LIKE。
            status: 人工状态筛选；`all` 表示不过滤人工状态。
            topic_id: 可选主题 ID 筛选。
            page: 页码，从 1 开始。
            page_size: 每页数量。
            sort_by: 排序字段白名单键。
            sort_order: 排序方向。

        Returns:
            包含 `items` 和 `total` 的分页结果。
        """

        sort_columns = {
            "event_time": "e.event_time",
            "created_at": "e.created_at",
            "confidence_score": "e.confidence_score",
        }
        order_column = sort_columns.get(sort_by, "e.event_time")
        order_direction = "ASC" if sort_order == "asc" else "DESC"
        where_clauses = ["e.archived_at IS NULL"]
        params: list[Any] = []
        if status != "all":
            where_clauses.append("e.manual_status = ?")
            params.append(status)
        if keyword:
            where_clauses.append("(e.title LIKE ? OR e.summary LIKE ?)")
            like_keyword = f"%{keyword}%"
            params.extend([like_keyword, like_keyword])
        join_sql = ""
        if topic_id is not None:
            join_sql = "JOIN topic_event te_filter ON te_filter.event_id = e.id"
            where_clauses.append("te_filter.topic_id = ?")
            params.append(topic_id)

        where_sql = " AND ".join(where_clauses)
        offset = (page - 1) * page_size
        with self._session() as connection:
            total_row = connection.execute(
                f"""
                SELECT COUNT(DISTINCT e.id) AS total
                FROM event e
                {join_sql}
                WHERE {where_sql}
                """,
                params,
            ).fetchone()
            rows = connection.execute(
                f"""
                SELECT DISTINCT e.*
                FROM event e
                {join_sql}
                WHERE {where_sql}
                ORDER BY {order_column} {order_direction}, e.id {order_direction}
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return {"items": [dict(row) for row in rows], "total": int(total_row["total"])}

    def list_event_topics(self, event_id: int) -> list[dict[str, Any]]:
        """读取事件关联主题。

        Args:
            event_id: 事件主键。

        Returns:
            主题关联字段列表。
        """

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT
                    t.id, t.name, t.summary, t.lifecycle_stage, t.heat_score,
                    te.role_in_topic, te.relevance_score, te.manual_locked
                FROM topic_event te
                JOIN topic t ON t.id = te.topic_id
                WHERE te.event_id = ? AND t.archived_at IS NULL
                ORDER BY te.updated_at DESC, t.id ASC
                """,
                (event_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_event_evidence(self, event_id: int) -> list[dict[str, Any]]:
        """读取事件证据链。

        Args:
            event_id: 事件主键。

        Returns:
            证据及来源材料字段列表。
        """

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT
                    ev.id, ev.raw_document_id, ev.excerpt, ev.start_offset, ev.end_offset,
                    ev.evidence_level, ev.source_title, ev.source_url, ee.role,
                    rd.title AS document_title, rd.url AS document_url
                FROM event_evidence ee
                JOIN evidence ev ON ev.id = ee.evidence_id
                JOIN raw_document rd ON rd.id = ev.raw_document_id
                WHERE ee.event_id = ?
                ORDER BY ee.created_at ASC, ev.id ASC
                """,
                (event_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_event_operation_log(
        self,
        *,
        event_id: int | None,
        operation_type: str,
        before_json: str,
        after_json: str,
        reason: str,
        operator: str,
    ) -> int:
        """记录事件人工操作日志。

        Args:
            event_id: 事件主键；批量或主题操作可为空。
            operation_type: 操作类型。
            before_json: 操作前快照 JSON。
            after_json: 操作后快照 JSON。
            reason: 操作原因。
            operator: 操作人。

        Returns:
            新增日志主键。
        """

        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO event_operation_log (
                    event_id, operation_type, before_json, after_json, reason, operator, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, operation_type, before_json, after_json, reason, operator, utc_now_iso()),
            )
        return int(cursor.lastrowid)

    def set_event_manual_status(self, *, event_id: int, manual_status: str, reason: str) -> bool:
        """更新事件人工状态。

        Args:
            event_id: 事件主键。
            manual_status: 新人工状态。
            reason: 状态变更原因。

        Returns:
            更新成功返回 True；事件不存在返回 False。
        """

        timestamp = utc_now_iso()
        archived_at = timestamp if manual_status == "archived" else None
        with self._session() as connection:
            cursor = connection.execute(
                """
                UPDATE event
                SET manual_status = ?, archived_at = ?, archive_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (manual_status, archived_at, reason, timestamp, event_id),
            )
        return cursor.rowcount > 0

    def create_topic(self, *, name: str, summary: str = "") -> dict[str, Any]:
        """创建或返回同名主题。

        Args:
            name: 主题名称。
            summary: 主题摘要。

        Returns:
            主题字段字典。
        """

        timestamp = utc_now_iso()
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO topic (name, summary, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    summary = CASE WHEN excluded.summary <> '' THEN excluded.summary ELSE topic.summary END,
                    updated_at = excluded.updated_at
                """,
                (name, summary, timestamp, timestamp),
            )
            row = connection.execute("SELECT * FROM topic WHERE name = ?", (name,)).fetchone()
        return dict(row)

    def get_topic(self, topic_id: int) -> dict[str, Any] | None:
        """按主键读取主题。

        Args:
            topic_id: 主题主键。

        Returns:
            找到时返回主题字段字典，否则返回 None。
        """

        with self._session() as connection:
            row = connection.execute("SELECT * FROM topic WHERE id = ? AND archived_at IS NULL", (topic_id,)).fetchone()
        return dict(row) if row else None

    def link_event_topic(
        self,
        *,
        event_id: int,
        topic_id: int,
        role_in_topic: str,
        relevance_score: float = 1.0,
        manual_locked: bool = True,
    ) -> bool:
        """关联事件和主题。

        Args:
            event_id: 事件主键。
            topic_id: 主题主键。
            role_in_topic: 事件在主题中的角色。
            relevance_score: 相关度分数。
            manual_locked: 是否由人工锁定。

        Returns:
            事件和主题都存在时返回 True，否则返回 False。
        """

        if self.get_event(event_id) is None or self.get_topic(topic_id) is None:
            return False

        timestamp = utc_now_iso()
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO topic_event (
                    topic_id, event_id, role_in_topic, relevance_score, manual_locked, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(topic_id, event_id) DO UPDATE SET
                    role_in_topic = excluded.role_in_topic,
                    relevance_score = excluded.relevance_score,
                    manual_locked = excluded.manual_locked,
                    updated_at = excluded.updated_at
                """,
                (topic_id, event_id, role_in_topic, relevance_score, int(manual_locked), timestamp, timestamp),
            )
        return True

    def create_processing_job(
        self,
        *,
        job_type: str,
        idempotency_key: str,
        payload_json: str,
        next_run_at: str,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        """创建本地处理任务，幂等键重复时返回已有任务。

        Args:
            job_type: 任务类型。
            idempotency_key: 幂等键。
            payload_json: 任务 payload JSON 字符串。
            next_run_at: 最早可运行时间。
            max_attempts: 最大尝试次数。

        Returns:
            任务字段字典。
        """

        timestamp = utc_now_iso()
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO processing_job (
                    job_type, status, idempotency_key, payload_json,
                    max_attempts, next_run_at, created_at, updated_at
                ) VALUES (?, 'pending', ?, ?, ?, ?, ?, ?)
                ON CONFLICT(idempotency_key) DO NOTHING
                """,
                (job_type, idempotency_key, payload_json, max_attempts, next_run_at, timestamp, timestamp),
            )
            row = connection.execute(
                "SELECT * FROM processing_job WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        return dict(row)

    def get_processing_job(self, job_id: int) -> dict[str, Any] | None:
        """按主键读取处理任务。

        Args:
            job_id: 任务主键。

        Returns:
            找到时返回任务字段字典，否则返回 None。
        """

        with self._session() as connection:
            row = connection.execute("SELECT * FROM processing_job WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def get_processing_job_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        """按幂等键读取处理任务。

        Args:
            idempotency_key: 任务幂等键。

        Returns:
            找到时返回任务字段字典，否则返回 None。
        """

        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM processing_job WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        return dict(row) if row else None

    def claim_next_processing_job(self, *, lease_owner: str, now: str, lease_seconds: int) -> dict[str, Any] | None:
        """原子领取下一条可运行任务。

        Args:
            lease_owner: 当前 worker 标识。
            now: 当前时间。
            lease_seconds: 租约秒数。

        Returns:
            成功时返回 running 任务，否则返回 None。
        """

        lease_expires_at = _add_seconds(now, lease_seconds)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT *
                FROM processing_job
                WHERE
                    (status = 'pending' AND next_run_at <= ?)
                    OR (status = 'running' AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?)
                ORDER BY id ASC
                LIMIT 1
                """,
                (now, now),
            ).fetchone()
            if row is None:
                connection.commit()
                return None

            attempt_no = int(row["attempt_count"]) + 1
            if attempt_no > int(row["max_attempts"]):
                connection.execute(
                    """
                    UPDATE processing_job
                    SET status = 'failed', lease_owner = NULL, lease_expires_at = NULL,
                        updated_at = ?, error_message = ?
                    WHERE id = ?
                    """,
                    (now, "max attempts exhausted before claim", int(row["id"])),
                )
                connection.commit()
                return None

            connection.execute(
                """
                UPDATE processing_job
                SET status = 'running',
                    lease_owner = ?,
                    lease_expires_at = ?,
                    attempt_count = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (lease_owner, lease_expires_at, attempt_no, now, int(row["id"])),
            )
            connection.execute(
                """
                INSERT INTO processing_job_attempt(job_id, attempt_no, status, started_at)
                VALUES (?, ?, 'running', ?)
                """,
                (int(row["id"]), attempt_no, now),
            )
            claimed = connection.execute("SELECT * FROM processing_job WHERE id = ?", (int(row["id"]),)).fetchone()
            connection.commit()
            return dict(claimed)
        finally:
            connection.close()

    def complete_processing_job(self, *, job_id: int, now: str) -> dict[str, Any] | None:
        """标记任务成功完成。

        Args:
            job_id: 任务主键。
            now: 完成时间。

        Returns:
            更新后的任务；不存在时返回 None。
        """

        with self._session() as connection:
            job = connection.execute("SELECT * FROM processing_job WHERE id = ?", (job_id,)).fetchone()
            if job is None:
                return None
            connection.execute(
                """
                UPDATE processing_job
                SET status = 'succeeded', lease_owner = NULL, lease_expires_at = NULL,
                    updated_at = ?, error_message = ''
                WHERE id = ?
                """,
                (now, job_id),
            )
            connection.execute(
                """
                UPDATE processing_job_attempt
                SET status = 'succeeded', finished_at = ?
                WHERE job_id = ? AND attempt_no = ?
                """,
                (now, job_id, int(job["attempt_count"])),
            )
        return self.get_processing_job(job_id)

    def fail_processing_job(
        self,
        *,
        job_id: int,
        error_message: str,
        now: str,
        retry_delay_seconds: int,
    ) -> dict[str, Any] | None:
        """记录任务失败，并在次数未耗尽时重新排队。

        Args:
            job_id: 任务主键。
            error_message: 失败原因。
            now: 失败时间。
            retry_delay_seconds: 下一次重试延迟。

        Returns:
            更新后的任务；不存在时返回 None。
        """

        with self._session() as connection:
            job = connection.execute("SELECT * FROM processing_job WHERE id = ?", (job_id,)).fetchone()
            if job is None:
                return None
            attempt_count = int(job["attempt_count"])
            max_attempts = int(job["max_attempts"])
            next_status = "pending" if attempt_count < max_attempts else "failed"
            next_run_at = _add_seconds(now, retry_delay_seconds) if next_status == "pending" else now
            connection.execute(
                """
                UPDATE processing_job
                SET status = ?,
                    lease_owner = NULL,
                    lease_expires_at = NULL,
                    next_run_at = ?,
                    updated_at = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (next_status, next_run_at, now, error_message, job_id),
            )
            if attempt_count > 0:
                connection.execute(
                    """
                    UPDATE processing_job_attempt
                    SET status = 'failed', finished_at = ?, error_message = ?
                    WHERE job_id = ? AND attempt_no = ?
                    """,
                    (now, error_message, job_id, attempt_count),
                )
        return self.get_processing_job(job_id)

    def list_processing_job_attempts(self, job_id: int) -> list[dict[str, Any]]:
        """读取任务尝试日志。

        Args:
            job_id: 任务主键。

        Returns:
            attempt 记录字典列表。
        """

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM processing_job_attempt
                WHERE job_id = ?
                ORDER BY attempt_no ASC
                """,
                (job_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        """打开带 PRAGMA 的 SQLite 连接。

        Returns:
            已启用外键和 WAL 的 SQLite 连接。
        """

        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        """打开 Repository 会话并在退出时提交。

        Returns:
            SQLite 连接上下文。
        """

        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


def decode_job_payload(row: dict[str, Any]) -> dict[str, Any]:
    """解析任务 payload JSON。

    Args:
        row: processing_job 字段字典。

    Returns:
        payload 字典；非法 JSON 返回空字典。
    """

    try:
        payload = json.loads(str(row.get("payload_json") or "{}"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _add_seconds(timestamp: str, seconds: int) -> str:
    """给 UTC ISO 时间增加秒数。

    Args:
        timestamp: 形如 `2026-06-03T09:00:00Z` 的时间。
        seconds: 增加秒数。

    Returns:
        增加后的 UTC ISO 时间。
    """

    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return (parsed + timedelta(seconds=seconds)).astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
