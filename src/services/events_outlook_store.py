"""SQLite-backed persistence for events outlook findings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from contextlib import contextmanager
import re
import sqlite3
from typing import Iterable

from ..domain.external_data import ConfidenceLevel, ResearchFinding


@dataclass(frozen=True)
class StoredOutlookFinding:
    """Persisted event finding used to build the outlook windows."""

    title: str
    region: str
    expected_date: str
    summary: str
    confidence: ConfidenceLevel
    source_title: str
    source_url: str
    provider: str


@dataclass(frozen=True)
class TimelineEventRecord:
    """时间轴事件记录。

    Args:
        id: SQLite 自增主键。
        region: 事件区域，取值为 domestic 或 international。
        event_date: 事件日期，使用 YYYY-MM-DD。
        title: 事件标题。
        summary: 事件摘要。
        category: 事件分类，当前为 technology、politics 或 finance。
        source_url: 来源链接。
        source_name: 来源名称。
        created_at: 首次创建时间。
        updated_at: 最近更新时间。

    Returns:
        不可变的本地持久化事件视图。
    """

    id: int
    region: str
    event_date: str
    title: str
    summary: str
    category: str
    source_url: str
    source_name: str
    created_at: str
    updated_at: str


class EventsOutlookStore:
    """Persist and load future-event findings in a local SQLite database."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def has_records(self) -> bool:
        with self._session() as connection:
            row = connection.execute("SELECT 1 FROM outlook_findings LIMIT 1").fetchone()
        return row is not None

    def upsert_findings(self, findings: Iterable[ResearchFinding], *, collected_at: str) -> int:
        written = 0
        with self._session() as connection:
            for finding in findings:
                source_title = finding.sources[0].title if finding.sources else ""
                source_url = finding.sources[0].url if finding.sources else ""
                connection.execute(
                    """
                    INSERT INTO outlook_findings (
                        dedupe_key,
                        title,
                        region,
                        expected_date,
                        summary,
                        confidence,
                        source_title,
                        source_url,
                        provider,
                        first_seen_at,
                        last_seen_at,
                        seen_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT(dedupe_key) DO UPDATE SET
                        summary = excluded.summary,
                        confidence = excluded.confidence,
                        source_title = CASE
                            WHEN outlook_findings.source_title = '' THEN excluded.source_title
                            ELSE outlook_findings.source_title
                        END,
                        source_url = CASE
                            WHEN outlook_findings.source_url = '' THEN excluded.source_url
                            ELSE outlook_findings.source_url
                        END,
                        provider = excluded.provider,
                        last_seen_at = excluded.last_seen_at,
                        seen_count = outlook_findings.seen_count + 1
                    """,
                    (
                        self._dedupe_key(finding.title, finding.region, finding.expected_date),
                        finding.title.strip(),
                        finding.region.strip(),
                        finding.expected_date.strip(),
                        finding.summary.strip(),
                        finding.confidence.value,
                        source_title.strip(),
                        source_url.strip(),
                        finding.provider,
                        collected_at,
                        collected_at,
                    ),
                )
                written += 1
        return written

    def load_future_findings(self, *, as_of: date, max_expected_date: date) -> list[StoredOutlookFinding]:
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT
                    title,
                    region,
                    expected_date,
                    summary,
                    confidence,
                    source_title,
                    source_url,
                    provider
                FROM outlook_findings
                WHERE expected_date >= ? AND expected_date <= ?
                ORDER BY expected_date ASC, region ASC, title ASC
                """,
                (as_of.isoformat(), max_expected_date.isoformat()),
            ).fetchall()

        return [
            StoredOutlookFinding(
                title=row[0],
                region=row[1],
                expected_date=row[2],
                summary=row[3],
                confidence=ConfidenceLevel(row[4]),
                source_title=row[5],
                source_url=row[6],
                provider=row[7],
            )
            for row in rows
        ]

    def create_timeline_event(
        self,
        *,
        region: str,
        event_date: str,
        title: str,
        summary: str,
        category: str,
        source_url: str = "",
        source_name: str = "",
        event_key: str | None = None,
        now: str | None = None,
    ) -> TimelineEventRecord:
        """新增一条时间轴事件。

        Args:
            region: 事件区域。
            event_date: 事件日期。
            title: 事件标题。
            summary: 事件摘要。
            category: 事件分类。
            source_url: 来源链接。
            source_name: 来源名称。
            event_key: 可选去重键；手工事件为空。
            now: 当前写入时间，便于测试固定。

        Returns:
            新增后的事件记录。
        """
        timestamp = now or self._utc_timestamp()
        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO timeline_events (
                    event_key,
                    region,
                    event_date,
                    title,
                    summary,
                    category,
                    source_url,
                    source_name,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_key,
                    region.strip(),
                    event_date.strip(),
                    title.strip(),
                    summary.strip(),
                    category.strip(),
                    source_url.strip(),
                    source_name.strip(),
                    timestamp,
                    timestamp,
                ),
            )
            event_id = int(cursor.lastrowid)

        event = self.get_timeline_event(event_id)
        if event is None:
            raise RuntimeError("timeline event insert failed")
        return event

    def upsert_timeline_events(self, events: Iterable[dict[str, str]], *, now: str) -> int:
        """按去重键写入默认时间轴事件。

        Args:
            events: 事件字典列表，必须包含 event_key。
            now: 当前写入时间。

        Returns:
            写入或更新的记录数量。
        """
        written = 0
        with self._session() as connection:
            for event in events:
                connection.execute(
                    """
                    INSERT INTO timeline_events (
                        event_key,
                        region,
                        event_date,
                        title,
                        summary,
                        category,
                        source_url,
                        source_name,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(event_key) DO UPDATE SET
                        event_date = excluded.event_date,
                        title = excluded.title,
                        summary = excluded.summary,
                        category = excluded.category,
                        source_url = excluded.source_url,
                        source_name = excluded.source_name,
                        updated_at = excluded.updated_at
                    """,
                    (
                        event["event_key"],
                        event["region"],
                        event["event_date"],
                        event["title"],
                        event["summary"],
                        event["category"],
                        event.get("source_url", ""),
                        event.get("source_name", ""),
                        now,
                        now,
                    ),
                )
                written += 1
        return written

    def list_timeline_events(self, *, region: str, start_date: str, end_date: str) -> list[TimelineEventRecord]:
        """按区域和日期范围读取时间轴事件。

        Args:
            region: 事件区域。
            start_date: 起始日期。
            end_date: 结束日期。

        Returns:
            按日期、标题排序的事件列表。
        """
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    region,
                    event_date,
                    title,
                    summary,
                    category,
                    source_url,
                    source_name,
                    created_at,
                    updated_at
                FROM timeline_events
                WHERE region = ? AND event_date >= ? AND event_date <= ?
                ORDER BY event_date ASC, title ASC, id ASC
                """,
                (region, start_date, end_date),
            ).fetchall()

        return [self._timeline_event_from_row(row) for row in rows]

    def get_timeline_event(self, event_id: int) -> TimelineEventRecord | None:
        """按主键读取一条时间轴事件。

        Args:
            event_id: 事件主键。

        Returns:
            存在时返回事件记录，否则返回 None。
        """
        with self._session() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    region,
                    event_date,
                    title,
                    summary,
                    category,
                    source_url,
                    source_name,
                    created_at,
                    updated_at
                FROM timeline_events
                WHERE id = ?
                """,
                (event_id,),
            ).fetchone()

        if row is None:
            return None
        return self._timeline_event_from_row(row)

    def update_timeline_event(self, *, event_id: int, title: str, summary: str, now: str | None = None) -> TimelineEventRecord | None:
        """更新时间轴事件标题和摘要。

        Args:
            event_id: 事件主键。
            title: 新标题。
            summary: 新摘要。
            now: 当前写入时间，便于测试固定。

        Returns:
            更新后的事件记录；事件不存在时返回 None。
        """
        timestamp = now or self._utc_timestamp()
        with self._session() as connection:
            cursor = connection.execute(
                """
                UPDATE timeline_events
                SET title = ?, summary = ?, updated_at = ?
                WHERE id = ?
                """,
                (title.strip(), summary.strip(), timestamp, event_id),
            )
            if cursor.rowcount == 0:
                return None

        return self.get_timeline_event(event_id)

    def _ensure_schema(self) -> None:
        with self._session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS outlook_findings (
                    dedupe_key TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    region TEXT NOT NULL,
                    expected_date TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    source_title TEXT NOT NULL DEFAULT '',
                    source_url TEXT NOT NULL DEFAULT '',
                    provider TEXT NOT NULL DEFAULT '',
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    seen_count INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outlook_findings_expected_date
                ON outlook_findings(expected_date)
                """
            )
            self._ensure_timeline_events_schema(connection)
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timeline_events_region_date
                ON timeline_events(region, event_date)
                """
            )

    def _ensure_timeline_events_schema(self, connection: sqlite3.Connection) -> None:
        """确保时间轴事件表支持当前分类约束。

        Args:
            connection: 当前 SQLite 连接。

        Returns:
            无返回值；必要时会把旧的两分类 CHECK 表迁移为三分类表。
        """
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'timeline_events'"
        ).fetchone()
        if row is None:
            connection.execute(self._timeline_events_table_sql("timeline_events", include_if_not_exists=True))
            return
        table_sql = str(row[0] or "")
        if "'finance'" in table_sql:
            return

        connection.execute(self._timeline_events_table_sql("timeline_events_next", include_if_not_exists=False))
        connection.execute(
            """
            INSERT INTO timeline_events_next (
                id,
                event_key,
                region,
                event_date,
                title,
                summary,
                category,
                source_url,
                source_name,
                created_at,
                updated_at
            )
            SELECT
                id,
                event_key,
                region,
                event_date,
                title,
                summary,
                category,
                source_url,
                source_name,
                created_at,
                updated_at
            FROM timeline_events
            """
        )
        connection.execute("DROP TABLE timeline_events")
        connection.execute("ALTER TABLE timeline_events_next RENAME TO timeline_events")

    def _timeline_events_table_sql(self, table_name: str, *, include_if_not_exists: bool) -> str:
        """生成时间轴事件表建表 SQL。

        Args:
            table_name: 要创建的表名。
            include_if_not_exists: 是否带 IF NOT EXISTS。

        Returns:
            可直接执行的建表 SQL。
        """
        if_not_exists = "IF NOT EXISTS " if include_if_not_exists else ""
        return f"""
                CREATE TABLE {if_not_exists}{table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_key TEXT UNIQUE,
                    region TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source_url TEXT NOT NULL DEFAULT '',
                    source_name TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    CHECK (region IN ('domestic', 'international')),
                    CHECK (category IN ('technology', 'politics', 'finance'))
                )
                """

    def _utc_timestamp(self) -> str:
        """返回用于 SQLite 审计字段的 UTC 时间戳。"""
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def _session(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _dedupe_key(self, title: str, region: str, expected_date: str) -> str:
        normalized_title = re.sub(r"\s+", " ", title.strip().lower())
        normalized_region = region.strip().lower()
        normalized_date = expected_date.strip()
        return f"{normalized_region}|{normalized_date}|{normalized_title}"

    def _timeline_event_from_row(self, row) -> TimelineEventRecord:
        """把 SQLite 行转换为时间轴事件记录。"""
        return TimelineEventRecord(
            id=int(row[0]),
            region=row[1],
            event_date=row[2],
            title=row[3],
            summary=row[4],
            category=row[5],
            source_url=row[6],
            source_name=row[7],
            created_at=row[8],
            updated_at=row[9],
        )
