"""SQLite-backed storage for market index history."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
import sqlite3
from typing import Iterator, Sequence

from ..domain.external_data import MarketIndexHistoryPoint


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class StoredMarketPoint:
    """本地持久化的单日市场指数数据。"""

    trade_date: date
    close_price: float
    volume: float | None = None


@dataclass(frozen=True)
class MarketSyncState:
    """Persisted per-symbol sync summary."""

    symbol: str
    display_name: str
    currency: str
    provider_key: str
    source_url: str
    latest_trade_date: date | None
    earliest_trade_date: date | None
    point_count: int
    coverage_days: int
    window_label: str
    status: str
    warning_message: str
    synced_at: str


class MarketHistoryStore:
    """Store historical market closes and sync metadata."""

    def __init__(self, db_path: str | Path = ".data/market_history.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def upsert_symbol_history(
        self,
        *,
        symbol: str,
        display_name: str,
        currency: str,
        provider_key: str,
        source_url: str,
        points: Sequence[MarketIndexHistoryPoint],
        status: str,
        window_label: str,
        warning_message: str,
        synced_at: str | None = None,
        replace_from: date | None = None,
    ) -> None:
        """写入单个指数历史，并可在同一事务内替换指定日期后的窗口。

        Args:
            symbol: 指数标识。
            display_name: 展示名称。
            currency: 计价币种。
            provider_key: 数据源标识。
            source_url: 数据源地址。
            points: 待写入的日线点位。
            status: 同步状态。
            window_label: 历史覆盖窗口标签。
            warning_message: 同步告警。
            synced_at: 可选同步时间。
            replace_from: 可选窗口起点；传入时先删除该日期及之后的旧行。

        Returns:
            无返回值。
        """
        timestamp = synced_at or _utc_now()
        ordered_points = sorted(points, key=lambda item: item.trade_date)
        point_rows = [
            (
                symbol,
                point.trade_date.isoformat(),
                display_name,
                float(point.close_price),
                float(getattr(point, "volume")) if isinstance(getattr(point, "volume", None), (int, float)) else None,
                currency,
                provider_key,
                source_url,
                timestamp,
            )
            for point in ordered_points
        ]
        with self._session() as connection:
            if replace_from is not None:
                connection.execute(
                    """
                    DELETE FROM market_index_daily
                    WHERE symbol = ?
                      AND trade_date >= ?
                    """,
                    (symbol, replace_from.isoformat()),
                )
            if point_rows:
                connection.executemany(
                    """
                    INSERT INTO market_index_daily (
                        symbol,
                        trade_date,
                        display_name,
                        close_price,
                        volume,
                        currency,
                        provider_key,
                        source_url,
                        last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, trade_date) DO UPDATE SET
                        display_name=excluded.display_name,
                        close_price=excluded.close_price,
                        volume=excluded.volume,
                        currency=excluded.currency,
                        provider_key=excluded.provider_key,
                        source_url=excluded.source_url,
                        last_seen_at=excluded.last_seen_at
                    """,
                    point_rows,
                )
            aggregate_row = connection.execute(
                """
                SELECT
                    MIN(trade_date) AS earliest_trade_date,
                    MAX(trade_date) AS latest_trade_date,
                    COUNT(*) AS point_count
                FROM market_index_daily
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()
            earliest_trade_date = (
                date.fromisoformat(aggregate_row["earliest_trade_date"])
                if aggregate_row and aggregate_row["earliest_trade_date"]
                else None
            )
            latest_trade_date = (
                date.fromisoformat(aggregate_row["latest_trade_date"])
                if aggregate_row and aggregate_row["latest_trade_date"]
                else None
            )
            point_count = int(aggregate_row["point_count"]) if aggregate_row and aggregate_row["point_count"] else 0
            coverage_days = (latest_trade_date - earliest_trade_date).days if earliest_trade_date and latest_trade_date else 0
            connection.execute(
                """
                INSERT INTO market_index_sync_state (
                    symbol,
                    display_name,
                    currency,
                    provider_key,
                    source_url,
                    latest_trade_date,
                    earliest_trade_date,
                    point_count,
                    coverage_days,
                    window_label,
                    status,
                    warning_message,
                    synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    display_name=excluded.display_name,
                    currency=excluded.currency,
                    provider_key=excluded.provider_key,
                    source_url=excluded.source_url,
                    latest_trade_date=excluded.latest_trade_date,
                    earliest_trade_date=excluded.earliest_trade_date,
                    point_count=excluded.point_count,
                    coverage_days=excluded.coverage_days,
                    window_label=excluded.window_label,
                    status=excluded.status,
                    warning_message=excluded.warning_message,
                    synced_at=excluded.synced_at
                """,
                (
                    symbol,
                    display_name,
                    currency,
                    provider_key,
                    source_url,
                    latest_trade_date.isoformat() if latest_trade_date else None,
                    earliest_trade_date.isoformat() if earliest_trade_date else None,
                    point_count,
                    coverage_days,
                    window_label,
                    status,
                    warning_message,
                    timestamp,
                ),
            )

    def upsert_symbol_status(
        self,
        *,
        symbol: str,
        display_name: str,
        currency: str,
        provider_key: str,
        source_url: str,
        status: str,
        warning_message: str,
        synced_at: str | None = None,
    ) -> None:
        timestamp = synced_at or _utc_now()
        existing = self.get_sync_state(symbol)
        latest_trade_date = existing.latest_trade_date.isoformat() if existing and existing.latest_trade_date else None
        earliest_trade_date = existing.earliest_trade_date.isoformat() if existing and existing.earliest_trade_date else None
        point_count = existing.point_count if existing else 0
        coverage_days = existing.coverage_days if existing else 0
        window_label = existing.window_label if existing else ""
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO market_index_sync_state (
                    symbol,
                    display_name,
                    currency,
                    provider_key,
                    source_url,
                    latest_trade_date,
                    earliest_trade_date,
                    point_count,
                    coverage_days,
                    window_label,
                    status,
                    warning_message,
                    synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    display_name=excluded.display_name,
                    currency=excluded.currency,
                    provider_key=excluded.provider_key,
                    source_url=excluded.source_url,
                    status=excluded.status,
                    warning_message=excluded.warning_message,
                    synced_at=excluded.synced_at
                """,
                (
                    symbol,
                    display_name,
                    currency,
                    provider_key,
                    source_url,
                    latest_trade_date,
                    earliest_trade_date,
                    point_count,
                    coverage_days,
                    window_label,
                    status,
                    warning_message,
                    timestamp,
                ),
            )

    def get_sync_state(self, symbol: str) -> MarketSyncState | None:
        with self._session() as connection:
            row = connection.execute(
                """
                SELECT
                    symbol,
                    display_name,
                    currency,
                    provider_key,
                    source_url,
                    latest_trade_date,
                    earliest_trade_date,
                    point_count,
                    coverage_days,
                    window_label,
                    status,
                    warning_message,
                    synced_at
                FROM market_index_sync_state
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()
        return self._build_sync_state(row)

    def load_points(
        self,
        *,
        symbol: str,
        end_date: date,
        window_days: int,
    ) -> list[StoredMarketPoint]:
        start_date = end_date - timedelta(days=max(window_days, 1))
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT trade_date, close_price, volume
                FROM market_index_daily
                WHERE symbol = ?
                  AND trade_date >= ?
                  AND trade_date <= ?
                ORDER BY trade_date ASC
                """,
                (symbol, start_date.isoformat(), end_date.isoformat()),
            ).fetchall()
        return [
            StoredMarketPoint(
                trade_date=date.fromisoformat(row["trade_date"]),
                close_price=float(row["close_price"]),
                volume=float(row["volume"]) if row["volume"] is not None else None,
            )
            for row in rows
        ]

    def load_latest_points(self, *, symbol: str, limit: int) -> list[StoredMarketPoint]:
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT trade_date, close_price, volume
                FROM market_index_daily
                WHERE symbol = ?
                ORDER BY trade_date DESC
                LIMIT ?
                """,
                (symbol, max(limit, 1)),
            ).fetchall()
        return [
            StoredMarketPoint(
                trade_date=date.fromisoformat(row["trade_date"]),
                close_price=float(row["close_price"]),
                volume=float(row["volume"]) if row["volume"] is not None else None,
            )
            for row in reversed(rows)
        ]

    def has_non_sample_history(self, symbol: str) -> bool:
        with self._session() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM market_index_daily
                WHERE symbol = ?
                  AND provider_key NOT LIKE 'sample-%'
                LIMIT 1
                """,
                (symbol,),
            ).fetchone()
        return row is not None

    def purge_sample_rows_if_mixed(self, *, symbol: str, warning_message: str = "", synced_at: str | None = None) -> bool:
        timestamp = synced_at or _utc_now()
        with self._session() as connection:
            provider_rows = connection.execute(
                """
                SELECT DISTINCT provider_key
                FROM market_index_daily
                WHERE symbol = ?
                """,
                (symbol,),
            ).fetchall()
            provider_keys = [str(row["provider_key"]) for row in provider_rows]
            has_sample = any(key.startswith("sample-") for key in provider_keys)
            has_non_sample = any(not key.startswith("sample-") for key in provider_keys)
            if not (has_sample and has_non_sample):
                return False

            connection.execute(
                """
                DELETE FROM market_index_daily
                WHERE symbol = ?
                  AND provider_key LIKE 'sample-%'
                """,
                (symbol,),
            )
            self._rewrite_sync_state_from_daily_rows(
                connection=connection,
                symbol=symbol,
                status="degraded",
                warning_message=warning_message or "已移除混入的样例数据，当前仅保留实盘历史。",
                synced_at=timestamp,
            )
        return True

    def clear_all(self) -> None:
        with self._session() as connection:
            connection.execute("DELETE FROM market_index_daily")
            connection.execute("DELETE FROM market_index_sync_state")

    def _initialize(self) -> None:
        with self._session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_index_daily (
                    symbol TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    close_price REAL NOT NULL,
                    volume REAL,
                    currency TEXT NOT NULL,
                    provider_key TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, trade_date)
                )
                """
            )
            self._ensure_market_index_daily_columns(connection)
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_index_sync_state (
                    symbol TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    provider_key TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    latest_trade_date TEXT,
                    earliest_trade_date TEXT,
                    point_count INTEGER NOT NULL DEFAULT 0,
                    coverage_days INTEGER NOT NULL DEFAULT 0,
                    window_label TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    warning_message TEXT NOT NULL DEFAULT '',
                    synced_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_market_index_daily_symbol_date ON market_index_daily(symbol, trade_date)"
            )

    def _ensure_market_index_daily_columns(self, connection: sqlite3.Connection) -> None:
        """为旧版 SQLite 库补齐新增列，避免本地历史数据需要手工重建。"""
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(market_index_daily)").fetchall()
        }
        if "volume" not in columns:
            connection.execute("ALTER TABLE market_index_daily ADD COLUMN volume REAL")

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _build_sync_state(self, row: sqlite3.Row | None) -> MarketSyncState | None:
        if row is None:
            return None
        latest_trade_date = date.fromisoformat(row["latest_trade_date"]) if row["latest_trade_date"] else None
        earliest_trade_date = date.fromisoformat(row["earliest_trade_date"]) if row["earliest_trade_date"] else None
        return MarketSyncState(
            symbol=str(row["symbol"]),
            display_name=str(row["display_name"]),
            currency=str(row["currency"]),
            provider_key=str(row["provider_key"]),
            source_url=str(row["source_url"]),
            latest_trade_date=latest_trade_date,
            earliest_trade_date=earliest_trade_date,
            point_count=int(row["point_count"]),
            coverage_days=int(row["coverage_days"]),
            window_label=str(row["window_label"]),
            status=str(row["status"]),
            warning_message=str(row["warning_message"]),
            synced_at=str(row["synced_at"]),
        )

    def _rewrite_sync_state_from_daily_rows(
        self,
        *,
        connection: sqlite3.Connection,
        symbol: str,
        status: str,
        warning_message: str,
        synced_at: str,
    ) -> None:
        latest_row = connection.execute(
            """
            SELECT display_name, currency, provider_key, source_url, trade_date
            FROM market_index_daily
            WHERE symbol = ?
            ORDER BY trade_date DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()
        aggregate_row = connection.execute(
            """
            SELECT
                MIN(trade_date) AS earliest_trade_date,
                MAX(trade_date) AS latest_trade_date,
                COUNT(*) AS point_count
            FROM market_index_daily
            WHERE symbol = ?
            """,
            (symbol,),
        ).fetchone()
        if latest_row is None or aggregate_row is None or int(aggregate_row["point_count"] or 0) <= 0:
            connection.execute("DELETE FROM market_index_sync_state WHERE symbol = ?", (symbol,))
            return

        earliest_trade_date = aggregate_row["earliest_trade_date"]
        latest_trade_date = aggregate_row["latest_trade_date"]
        coverage_days = (
            date.fromisoformat(latest_trade_date) - date.fromisoformat(earliest_trade_date)
        ).days if earliest_trade_date and latest_trade_date else 0
        if coverage_days >= 150:
            window_label = "近6个月"
        elif coverage_days >= 75:
            window_label = "近3个月"
        elif coverage_days >= 20:
            window_label = "近1个月"
        else:
            window_label = f"近{coverage_days + 1}天"
        connection.execute(
            """
            INSERT INTO market_index_sync_state (
                symbol,
                display_name,
                currency,
                provider_key,
                source_url,
                latest_trade_date,
                earliest_trade_date,
                point_count,
                coverage_days,
                window_label,
                status,
                warning_message,
                synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                display_name=excluded.display_name,
                currency=excluded.currency,
                provider_key=excluded.provider_key,
                source_url=excluded.source_url,
                latest_trade_date=excluded.latest_trade_date,
                earliest_trade_date=excluded.earliest_trade_date,
                point_count=excluded.point_count,
                coverage_days=excluded.coverage_days,
                window_label=excluded.window_label,
                status=excluded.status,
                warning_message=excluded.warning_message,
                synced_at=excluded.synced_at
            """,
            (
                symbol,
                str(latest_row["display_name"]),
                str(latest_row["currency"]),
                str(latest_row["provider_key"]),
                str(latest_row["source_url"]),
                str(latest_trade_date),
                str(earliest_trade_date),
                int(aggregate_row["point_count"]),
                coverage_days,
                window_label,
                status,
                warning_message,
                synced_at,
            ),
        )
