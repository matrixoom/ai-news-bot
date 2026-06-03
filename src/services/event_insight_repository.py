"""Event Insight SQLite repository."""

from __future__ import annotations

from contextlib import contextmanager
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
    ) -> int:
        """新增证据片段。

        Args:
            raw_document_id: 原始材料主键。
            excerpt: 证据原文片段。
            start_offset: 片段开始位置。
            end_offset: 片段结束位置。
            evidence_level: 证据等级。

        Returns:
            新增证据主键。
        """

        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO evidence (
                    raw_document_id, excerpt, start_offset, end_offset, evidence_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (raw_document_id, excerpt, start_offset, end_offset, evidence_level, utc_now_iso()),
            )
            return int(cursor.lastrowid)

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
