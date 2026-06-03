"""Event Insight SQLite migration service."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Iterator


CORE_MIGRATION_VERSION = "001_event_insight_core"


def utc_now_iso() -> str:
    """返回 UTC ISO 时间字符串。

    Returns:
        形如 `2026-06-03T00:00:00Z` 的时间字符串。
    """

    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class EventInsightMigrationService:
    """管理 Event Insight SQLite schema migration。

    Args:
        db_path: Event Insight 独立 SQLite 数据库路径。

    Returns:
        初始化后的迁移服务实例。
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def apply(self) -> None:
        """幂等应用所有 Event Insight migration。

        Returns:
            无返回值；迁移失败时抛出 SQLite 异常。
        """

        with self._session() as connection:
            self._ensure_migration_table(connection)
            applied = self._applied_versions(connection)
            if CORE_MIGRATION_VERSION not in applied:
                connection.executescript(_core_schema_sql())
                connection.execute(
                    """
                    INSERT INTO schema_migration(version, applied_at)
                    VALUES (?, ?)
                    """,
                    (CORE_MIGRATION_VERSION, utc_now_iso()),
                )

    def _ensure_migration_table(self, connection: sqlite3.Connection) -> None:
        """确保 migration 记录表存在。

        Args:
            connection: 当前 SQLite 连接。

        Returns:
            无返回值。
        """

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migration (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )

    def _applied_versions(self, connection: sqlite3.Connection) -> set[str]:
        """读取已应用 migration 版本。

        Args:
            connection: 当前 SQLite 连接。

        Returns:
            已应用版本集合。
        """

        rows = connection.execute("SELECT version FROM schema_migration").fetchall()
        return {str(row["version"]) for row in rows}

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
        """打开迁移会话并在退出时提交。

        Returns:
            SQLite 连接上下文。
        """

        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


def _core_schema_sql() -> str:
    """返回 001_event_insight_core 的建表 SQL。

    Returns:
        可传给 `executescript` 的完整 SQL。
    """

    return """
    CREATE TABLE IF NOT EXISTS scan_batch (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_key TEXT NOT NULL UNIQUE,
        source_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        started_at TEXT NOT NULL,
        completed_at TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'canceled'))
    );

    CREATE TABLE IF NOT EXISTS analysis_run (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        model_provider TEXT NOT NULL DEFAULT '',
        model_name TEXT NOT NULL DEFAULT '',
        prompt_version TEXT NOT NULL DEFAULT '',
        started_at TEXT NOT NULL,
        completed_at TEXT,
        error_message TEXT NOT NULL DEFAULT '',
        CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'canceled'))
    );

    CREATE TABLE IF NOT EXISTS raw_document (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_batch_id INTEGER REFERENCES scan_batch(id) ON DELETE SET NULL,
        source_type TEXT NOT NULL,
        title TEXT NOT NULL,
        url TEXT NOT NULL DEFAULT '',
        local_file_path TEXT NOT NULL DEFAULT '',
        content_text TEXT NOT NULL,
        content_hash TEXT NOT NULL UNIQUE,
        published_at TEXT,
        imported_at TEXT NOT NULL,
        archived_at TEXT,
        archive_reason TEXT NOT NULL DEFAULT '',
        CHECK (source_type IN (
            'news', 'announcement', 'earnings_report', 'meeting_minutes',
            'research_report', 'policy', 'industry_report', 'macro_data',
            'market_move', 'other'
        ))
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS raw_document_fts USING fts5(
        raw_document_id UNINDEXED,
        title,
        content_text,
        tokenize='unicode61'
    );

    CREATE TRIGGER IF NOT EXISTS raw_document_ai
    AFTER INSERT ON raw_document
    WHEN NEW.archived_at IS NULL
    BEGIN
        INSERT INTO raw_document_fts(raw_document_id, title, content_text)
        VALUES (NEW.id, NEW.title, NEW.content_text);
    END;

    CREATE TRIGGER IF NOT EXISTS raw_document_au
    AFTER UPDATE ON raw_document
    BEGIN
        DELETE FROM raw_document_fts WHERE raw_document_id = OLD.id;
        INSERT INTO raw_document_fts(raw_document_id, title, content_text)
        SELECT NEW.id, NEW.title, NEW.content_text
        WHERE NEW.archived_at IS NULL;
    END;

    CREATE TRIGGER IF NOT EXISTS raw_document_ad
    AFTER DELETE ON raw_document
    BEGIN
        DELETE FROM raw_document_fts WHERE raw_document_id = OLD.id;
    END;

    CREATE TABLE IF NOT EXISTS event (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_event_id INTEGER REFERENCES event(id) ON DELETE SET NULL,
        analysis_run_id INTEGER REFERENCES analysis_run(id) ON DELETE SET NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        event_time TEXT NOT NULL,
        published_at TEXT,
        event_type TEXT NOT NULL,
        importance_score REAL NOT NULL DEFAULT 0,
        novelty_score REAL NOT NULL DEFAULT 0,
        market_relevance_score REAL NOT NULL DEFAULT 0,
        confidence_score REAL NOT NULL DEFAULT 0,
        evidence_level TEXT NOT NULL DEFAULT 'C',
        analysis_status TEXT NOT NULL DEFAULT 'extracted',
        graph_status TEXT NOT NULL DEFAULT 'pending',
        manual_status TEXT NOT NULL DEFAULT 'active',
        source_method TEXT NOT NULL DEFAULT 'manual',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        archived_at TEXT,
        archive_reason TEXT NOT NULL DEFAULT '',
        CHECK (event_type IN (
            'policy', 'price_change', 'supply_demand', 'order_contract',
            'capacity', 'earnings', 'technology', 'capital_market',
            'institution_view', 'macro', 'risk', 'other'
        )),
        CHECK (evidence_level IN ('A', 'B', 'C', 'D')),
        CHECK (manual_status IN ('active', 'ignored', 'archived')),
        CHECK (confidence_score >= 0 AND confidence_score <= 1)
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS event_fts USING fts5(
        event_id UNINDEXED,
        title,
        summary,
        tokenize='unicode61'
    );

    CREATE TRIGGER IF NOT EXISTS event_ai
    AFTER INSERT ON event
    WHEN NEW.archived_at IS NULL AND NEW.manual_status = 'active'
    BEGIN
        INSERT INTO event_fts(event_id, title, summary)
        VALUES (NEW.id, NEW.title, NEW.summary);
    END;

    CREATE TRIGGER IF NOT EXISTS event_au
    AFTER UPDATE ON event
    BEGIN
        DELETE FROM event_fts WHERE event_id = OLD.id;
        INSERT INTO event_fts(event_id, title, summary)
        SELECT NEW.id, NEW.title, NEW.summary
        WHERE NEW.archived_at IS NULL AND NEW.manual_status = 'active';
    END;

    CREATE TRIGGER IF NOT EXISTS event_ad
    AFTER DELETE ON event
    BEGIN
        DELETE FROM event_fts WHERE event_id = OLD.id;
    END;

    CREATE TABLE IF NOT EXISTS event_source (
        event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
        raw_document_id INTEGER NOT NULL REFERENCES raw_document(id) ON DELETE CASCADE,
        source_role TEXT NOT NULL DEFAULT 'primary',
        created_at TEXT NOT NULL,
        PRIMARY KEY (event_id, raw_document_id, source_role)
    );

    CREATE TABLE IF NOT EXISTS evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_document_id INTEGER NOT NULL REFERENCES raw_document(id) ON DELETE CASCADE,
        excerpt TEXT NOT NULL,
        start_offset INTEGER NOT NULL DEFAULT 0,
        end_offset INTEGER NOT NULL DEFAULT 0,
        evidence_level TEXT NOT NULL DEFAULT 'C',
        source_title TEXT NOT NULL DEFAULT '',
        source_url TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        CHECK (evidence_level IN ('A', 'B', 'C', 'D'))
    );

    CREATE TABLE IF NOT EXISTS event_evidence (
        event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
        evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
        role TEXT NOT NULL DEFAULT 'primary',
        created_at TEXT NOT NULL,
        PRIMARY KEY (event_id, evidence_id, role)
    );

    CREATE TABLE IF NOT EXISTS entity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        canonical_name TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        UNIQUE (name, entity_type)
    );

    CREATE TABLE IF NOT EXISTS entity_alias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
        alias TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (entity_id, alias)
    );

    CREATE TABLE IF NOT EXISTS event_entity (
        event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
        entity_id INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
        role TEXT NOT NULL DEFAULT 'mentioned',
        relevance_score REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        PRIMARY KEY (event_id, entity_id, role)
    );

    CREATE TABLE IF NOT EXISTS topic (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        summary TEXT NOT NULL DEFAULT '',
        lifecycle_stage TEXT NOT NULL DEFAULT 'noise',
        heat_score REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        archived_at TEXT
    );

    CREATE TABLE IF NOT EXISTS topic_event (
        topic_id INTEGER NOT NULL REFERENCES topic(id) ON DELETE CASCADE,
        event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
        role_in_topic TEXT NOT NULL DEFAULT 'supporting_event',
        relevance_score REAL NOT NULL DEFAULT 0,
        manual_locked INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (topic_id, event_id)
    );

    CREATE TABLE IF NOT EXISTS event_relation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
        target_event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
        relation_type TEXT NOT NULL,
        relation_summary TEXT NOT NULL DEFAULT '',
        strength_score REAL NOT NULL DEFAULT 0,
        confidence_score REAL NOT NULL DEFAULT 0,
        generation_method TEXT NOT NULL DEFAULT 'manual',
        manual_confirmed INTEGER NOT NULL DEFAULT 0,
        analysis_run_id INTEGER REFERENCES analysis_run(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        archived_at TEXT,
        CHECK (relation_type IN ('same_topic', 'cause', 'support', 'contradict', 'follow_up')),
        CHECK (generation_method IN ('rule', 'llm', 'manual', 'hybrid'))
    );

    CREATE TABLE IF NOT EXISTS relation_evidence (
        relation_id INTEGER NOT NULL REFERENCES event_relation(id) ON DELETE CASCADE,
        evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL,
        PRIMARY KEY (relation_id, evidence_id)
    );

    CREATE TABLE IF NOT EXISTS event_operation_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER REFERENCES event(id) ON DELETE SET NULL,
        operation_type TEXT NOT NULL,
        before_json TEXT NOT NULL DEFAULT '{}',
        after_json TEXT NOT NULL DEFAULT '{}',
        reason TEXT NOT NULL DEFAULT '',
        operator TEXT NOT NULL DEFAULT 'system',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS event_field_override (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
        field_name TEXT NOT NULL,
        override_value TEXT NOT NULL,
        reason TEXT NOT NULL DEFAULT '',
        operator TEXT NOT NULL DEFAULT 'system',
        created_at TEXT NOT NULL,
        archived_at TEXT,
        UNIQUE (event_id, field_name, archived_at)
    );

    CREATE TABLE IF NOT EXISTS duplicate_event_candidate (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
        candidate_event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
        score REAL NOT NULL,
        method TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        analysis_run_id INTEGER REFERENCES analysis_run(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        CHECK (status IN ('pending', 'confirmed', 'rejected')),
        CHECK (source_event_id <> candidate_event_id),
        UNIQUE (source_event_id, candidate_event_id, method)
    );

    CREATE TABLE IF NOT EXISTS processing_job (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        idempotency_key TEXT NOT NULL UNIQUE,
        payload_json TEXT NOT NULL DEFAULT '{}',
        lease_owner TEXT,
        lease_expires_at TEXT,
        attempt_count INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        next_run_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        error_message TEXT NOT NULL DEFAULT '',
        CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'canceled'))
    );

    CREATE TABLE IF NOT EXISTS processing_job_attempt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL REFERENCES processing_job(id) ON DELETE CASCADE,
        attempt_no INTEGER NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        error_message TEXT NOT NULL DEFAULT '',
        UNIQUE (job_id, attempt_no)
    );

    CREATE TABLE IF NOT EXISTS graph_sync_outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aggregate_type TEXT NOT NULL,
        aggregate_id INTEGER NOT NULL,
        operation TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        idempotency_key TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        processed_at TEXT,
        error_message TEXT NOT NULL DEFAULT '',
        CHECK (status IN ('pending', 'running', 'succeeded', 'failed'))
    );

    CREATE TABLE IF NOT EXISTS graph_projection_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projection_key TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'pending',
        last_rebuild_started_at TEXT,
        last_rebuild_completed_at TEXT,
        last_outbox_id INTEGER NOT NULL DEFAULT 0,
        error_message TEXT NOT NULL DEFAULT ''
    );

    CREATE INDEX IF NOT EXISTS idx_raw_document_imported_at ON raw_document(imported_at);
    CREATE INDEX IF NOT EXISTS idx_event_time_type ON event(event_time, event_type);
    CREATE INDEX IF NOT EXISTS idx_event_manual_status ON event(manual_status, archived_at);
    CREATE INDEX IF NOT EXISTS idx_evidence_raw_document ON evidence(raw_document_id);
    CREATE INDEX IF NOT EXISTS idx_topic_event_event ON topic_event(event_id);
    CREATE INDEX IF NOT EXISTS idx_event_relation_source ON event_relation(source_event_id);
    CREATE INDEX IF NOT EXISTS idx_event_relation_target ON event_relation(target_event_id);
    CREATE INDEX IF NOT EXISTS idx_processing_job_status_next_run ON processing_job(status, next_run_at);
    CREATE INDEX IF NOT EXISTS idx_graph_sync_outbox_status ON graph_sync_outbox(status, id);
    """
