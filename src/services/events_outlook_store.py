"""SQLite-backed persistence for events outlook findings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
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
