"""SQLite-backed storage for macro indicator history."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3
from typing import Iterator, Sequence

from ..domain.external_data import MacroHistoryPoint


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class StoredMacroPoint:
    """One persisted macro observation."""

    period_end: date
    period_label: str
    value: float
    unit: str
    released_at: str


@dataclass(frozen=True)
class MacroSyncState:
    """Persisted per-indicator sync summary."""

    indicator_code: str
    provider_key: str
    source_url: str
    latest_period_end: date | None
    earliest_period_end: date | None
    point_count: int
    status: str
    warning_message: str
    synced_at: str


class MacroHistoryStore:
    """Store macro indicator history and sync metadata."""

    def __init__(self, db_path: str | Path = ".data/macro_history.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def upsert_indicator_history(
        self,
        *,
        indicator_code: str,
        provider_key: str,
        source_url: str,
        points: Sequence[MacroHistoryPoint],
        status: str,
        warning_message: str,
        synced_at: str | None = None,
    ) -> None:
        timestamp = synced_at or _utc_now()
        ordered = sorted(points, key=lambda item: item.period_end)
        rows = [
            (
                indicator_code,
                point.period_end.isoformat(),
                point.period_label,
                float(point.value),
                point.unit,
                provider_key,
                point.source_url or source_url,
                point.released_at,
                timestamp,
            )
            for point in ordered
        ]
        with self._session() as connection:
            if rows:
                connection.executemany(
                    """
                    INSERT INTO macro_indicator_history (
                        indicator_code,
                        period_end,
                        period_label,
                        value,
                        unit,
                        provider_key,
                        source_url,
                        released_at,
                        last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(indicator_code, period_end) DO UPDATE SET
                        period_label=excluded.period_label,
                        value=excluded.value,
                        unit=excluded.unit,
                        provider_key=excluded.provider_key,
                        source_url=excluded.source_url,
                        released_at=excluded.released_at,
                        last_seen_at=excluded.last_seen_at
                    """,
                    rows,
                )
            aggregate = connection.execute(
                """
                SELECT
                    MIN(period_end) AS earliest_period_end,
                    MAX(period_end) AS latest_period_end,
                    COUNT(*) AS point_count
                FROM macro_indicator_history
                WHERE indicator_code = ?
                """,
                (indicator_code,),
            ).fetchone()
            earliest_period_end = (
                date.fromisoformat(aggregate["earliest_period_end"])
                if aggregate and aggregate["earliest_period_end"]
                else None
            )
            latest_period_end = (
                date.fromisoformat(aggregate["latest_period_end"])
                if aggregate and aggregate["latest_period_end"]
                else None
            )
            point_count = int(aggregate["point_count"]) if aggregate and aggregate["point_count"] else 0
            connection.execute(
                """
                INSERT INTO macro_indicator_sync_state (
                    indicator_code,
                    provider_key,
                    source_url,
                    latest_period_end,
                    earliest_period_end,
                    point_count,
                    status,
                    warning_message,
                    synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(indicator_code) DO UPDATE SET
                    provider_key=excluded.provider_key,
                    source_url=excluded.source_url,
                    latest_period_end=excluded.latest_period_end,
                    earliest_period_end=excluded.earliest_period_end,
                    point_count=excluded.point_count,
                    status=excluded.status,
                    warning_message=excluded.warning_message,
                    synced_at=excluded.synced_at
                """,
                (
                    indicator_code,
                    provider_key,
                    source_url,
                    latest_period_end.isoformat() if latest_period_end else None,
                    earliest_period_end.isoformat() if earliest_period_end else None,
                    point_count,
                    status,
                    warning_message,
                    timestamp,
                ),
            )

    def upsert_indicator_status(
        self,
        *,
        indicator_code: str,
        provider_key: str,
        source_url: str,
        status: str,
        warning_message: str,
        synced_at: str | None = None,
    ) -> None:
        timestamp = synced_at or _utc_now()
        existing = self.get_sync_state(indicator_code)
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO macro_indicator_sync_state (
                    indicator_code,
                    provider_key,
                    source_url,
                    latest_period_end,
                    earliest_period_end,
                    point_count,
                    status,
                    warning_message,
                    synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(indicator_code) DO UPDATE SET
                    provider_key=excluded.provider_key,
                    source_url=excluded.source_url,
                    status=excluded.status,
                    warning_message=excluded.warning_message,
                    synced_at=excluded.synced_at
                """,
                (
                    indicator_code,
                    provider_key,
                    source_url,
                    existing.latest_period_end.isoformat() if existing and existing.latest_period_end else None,
                    existing.earliest_period_end.isoformat() if existing and existing.earliest_period_end else None,
                    existing.point_count if existing else 0,
                    status,
                    warning_message,
                    timestamp,
                ),
            )

    def get_sync_state(self, indicator_code: str) -> MacroSyncState | None:
        with self._session() as connection:
            row = connection.execute(
                """
                SELECT
                    indicator_code,
                    provider_key,
                    source_url,
                    latest_period_end,
                    earliest_period_end,
                    point_count,
                    status,
                    warning_message,
                    synced_at
                FROM macro_indicator_sync_state
                WHERE indicator_code = ?
                """,
                (indicator_code,),
            ).fetchone()
        if row is None:
            return None
        return MacroSyncState(
            indicator_code=str(row["indicator_code"]),
            provider_key=str(row["provider_key"]),
            source_url=str(row["source_url"]),
            latest_period_end=date.fromisoformat(row["latest_period_end"]) if row["latest_period_end"] else None,
            earliest_period_end=date.fromisoformat(row["earliest_period_end"]) if row["earliest_period_end"] else None,
            point_count=int(row["point_count"]),
            status=str(row["status"]),
            warning_message=str(row["warning_message"]),
            synced_at=str(row["synced_at"]),
        )

    def load_points(self, *, indicator_code: str, start_date: date) -> list[StoredMacroPoint]:
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT period_end, period_label, value, unit, released_at
                FROM macro_indicator_history
                WHERE indicator_code = ?
                  AND period_end >= ?
                ORDER BY period_end ASC
                """,
                (indicator_code, start_date.isoformat()),
            ).fetchall()
        return [
            StoredMacroPoint(
                period_end=date.fromisoformat(row["period_end"]),
                period_label=str(row["period_label"]),
                value=float(row["value"]),
                unit=str(row["unit"]),
                released_at=str(row["released_at"]),
            )
            for row in rows
        ]

    def load_latest_points(self, *, indicator_code: str, limit: int) -> list[StoredMacroPoint]:
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT period_end, period_label, value, unit, released_at
                FROM macro_indicator_history
                WHERE indicator_code = ?
                ORDER BY period_end DESC
                LIMIT ?
                """,
                (indicator_code, max(limit, 1)),
            ).fetchall()
        return [
            StoredMacroPoint(
                period_end=date.fromisoformat(row["period_end"]),
                period_label=str(row["period_label"]),
                value=float(row["value"]),
                unit=str(row["unit"]),
                released_at=str(row["released_at"]),
            )
            for row in reversed(rows)
        ]

    def clear_all(self) -> None:
        with self._session() as connection:
            connection.execute("DELETE FROM macro_indicator_history")
            connection.execute("DELETE FROM macro_indicator_sync_state")

    def _initialize(self) -> None:
        with self._session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS macro_indicator_history (
                    indicator_code TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    period_label TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    provider_key TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    released_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY (indicator_code, period_end)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS macro_indicator_sync_state (
                    indicator_code TEXT PRIMARY KEY,
                    provider_key TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    latest_period_end TEXT,
                    earliest_period_end TEXT,
                    point_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    warning_message TEXT NOT NULL DEFAULT '',
                    synced_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_macro_indicator_history_code_date
                ON macro_indicator_history(indicator_code, period_end)
                """
            )

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()
