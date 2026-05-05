"""SQLite repository for the Market Data module."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Mapping, Sequence


MARKET_DATA_TABLES: dict[str, str] = {
    "wti_crude_oil": "market_wti_crude_oil",
    "brent_crude_oil": "market_brent_crude_oil",
    "gold_spot": "market_gold_spot",
    "silver_spot": "market_silver_spot",
    "copper": "market_copper",
    "second_hand_housing": "market_second_hand_housing",
}

HOUSING_TABLES: set[str] = {"market_second_hand_housing"}


class MarketDataValidationError(ValueError):
    """市场数据参数校验失败。"""


@dataclass(frozen=True)
class MarketIndicatorDefinition:
    indicator_id: str
    table_name: str
    category: str
    title: str
    unit: str
    frequency: str
    display_order: int
    status: str


@dataclass(frozen=True)
class MarketDataPoint:
    period_end: str
    period_label: str
    value: float
    unit: str
    frequency: str
    released_at: str


@dataclass(frozen=True)
class MarketSyncState:
    indicator_id: str
    provider_key: str
    latest_period_end: str | None
    earliest_period_end: str | None
    point_count: int
    status: str
    warning_message: str
    synced_at: str


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class MarketDataRepository:
    """管理 Market Data 本地 SQLite 持久化。"""

    def __init__(self, db_path: str | Path = ".data/market_data.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self._seed_defaults()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def list_table_names(self) -> set[str]:
        with self._session() as connection:
            rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        return {str(row["name"]) for row in rows}

    def list_indicators(self, category: str) -> list[MarketIndicatorDefinition]:
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT indicator_id, table_name, category, title, unit, frequency, display_order, status
                FROM market_data_indicator_registry
                WHERE category = ?
                ORDER BY display_order ASC
                """,
                (category,),
            ).fetchall()
        return [self._build_definition(row) for row in rows]

    def get_indicator(self, indicator_id: str) -> MarketIndicatorDefinition | None:
        with self._session() as connection:
            row = connection.execute(
                """
                SELECT indicator_id, table_name, category, title, unit, frequency, display_order, status
                FROM market_data_indicator_registry
                WHERE indicator_id = ?
                """,
                (indicator_id,),
            ).fetchone()
        return self._build_definition(row) if row else None

    def upsert_points(
        self,
        indicator_id: str,
        points: Sequence[Mapping[str, Any]],
        *,
        status: str,
        warning_message: str,
    ) -> None:
        definition = self.get_indicator(indicator_id)
        if definition is None:
            raise ValueError(f"unknown market indicator: {indicator_id}")
        table_name = self._safe_table_name(definition.table_name)
        timestamp = _utc_now()
        rows = [
            (
                str(point["period_end"]),
                str(point["period_label"]),
                float(point["value"]),
                str(point["unit"]),
                str(point["frequency"]),
                str(point["provider_key"]),
                str(point["source_url"]),
                str(point["released_at"]),
                timestamp,
            )
            for point in points
        ]
        with self._session() as connection:
            if rows:
                connection.executemany(
                    f"""
                    INSERT INTO {table_name} (
                        period_end, period_label, value, unit, frequency, provider_key, source_url, released_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(period_end, frequency) DO UPDATE SET
                        period_label=excluded.period_label,
                        value=excluded.value,
                        unit=excluded.unit,
                        frequency=excluded.frequency,
                        provider_key=excluded.provider_key,
                        source_url=excluded.source_url,
                        released_at=excluded.released_at,
                        last_seen_at=excluded.last_seen_at
                    """,
                    rows,
                )
            aggregate = connection.execute(
                f"""
                SELECT MIN(period_end) AS earliest_period_end, MAX(period_end) AS latest_period_end, COUNT(*) AS point_count
                FROM {table_name}
                """
            ).fetchone()
            connection.execute(
                """
                INSERT INTO market_data_sync_state (
                    indicator_id, provider_key, latest_period_end, earliest_period_end,
                    point_count, status, warning_message, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(indicator_id) DO UPDATE SET
                    provider_key=excluded.provider_key,
                    latest_period_end=excluded.latest_period_end,
                    earliest_period_end=excluded.earliest_period_end,
                    point_count=excluded.point_count,
                    status=excluded.status,
                    warning_message=excluded.warning_message,
                    synced_at=excluded.synced_at
                """,
                (
                    indicator_id,
                    rows[-1][5] if rows else "manual_seed",
                    aggregate["latest_period_end"] if aggregate else None,
                    aggregate["earliest_period_end"] if aggregate else None,
                    int(aggregate["point_count"]) if aggregate else 0,
                    status,
                    warning_message,
                    timestamp,
                ),
            )

    def replace_points(
        self,
        indicator_id: str,
        points: Sequence[Mapping[str, Any]],
        *,
        status: str,
        warning_message: str,
    ) -> None:
        definition = self.get_indicator(indicator_id)
        if definition is None:
            raise ValueError(f"unknown market indicator: {indicator_id}")
        table_name = self._safe_table_name(definition.table_name)
        with self._session() as connection:
            connection.execute(f"DELETE FROM {table_name}")
            connection.execute("DELETE FROM market_data_sync_state WHERE indicator_id = ?", (indicator_id,))
        self.upsert_points(indicator_id, points, status=status, warning_message=warning_message)

    def load_points(
        self,
        *,
        indicator_id: str,
        start_date: str,
        end_date: str,
        frequency: str | None = None,
    ) -> list[MarketDataPoint]:
        definition = self.get_indicator(indicator_id)
        if definition is None:
            raise ValueError(f"unknown market indicator: {indicator_id}")
        table_name = self._safe_table_name(definition.table_name)
        with self._session() as connection:
            if frequency:
                rows = connection.execute(
                    f"""
                    SELECT period_end, period_label, value, unit, frequency, released_at
                    FROM {table_name}
                    WHERE period_end >= ? AND period_end <= ? AND frequency = ?
                    ORDER BY period_end ASC
                    """,
                    (start_date, end_date, frequency),
                ).fetchall()
            else:
                rows = connection.execute(
                    f"""
                    SELECT period_end, period_label, value, unit, frequency, released_at
                    FROM {table_name}
                    WHERE period_end >= ? AND period_end <= ?
                    ORDER BY period_end ASC, frequency ASC
                    """,
                    (start_date, end_date),
                ).fetchall()
        return [
            MarketDataPoint(
                period_end=str(row["period_end"]),
                period_label=str(row["period_label"]),
                value=float(row["value"]),
                unit=str(row["unit"]),
                frequency=str(row["frequency"]),
                released_at=str(row["released_at"]),
            )
            for row in rows
        ]

    def list_housing_cities(self, indicator_id: str) -> list[str]:
        definition = self.get_indicator(indicator_id)
        if definition is None:
            raise ValueError(f"unknown market indicator: {indicator_id}")
        table_name = self._safe_table_name(definition.table_name)
        with self._session() as connection:
            rows = connection.execute(
                f"SELECT DISTINCT city FROM {table_name} ORDER BY city ASC"
            ).fetchall()
        return [str(row["city"]) for row in rows]

    def load_housing_points(
        self,
        *,
        indicator_id: str,
        cities: list[str],
        start_date: str,
        end_date: str,
    ) -> dict[str, list[MarketDataPoint]]:
        definition = self.get_indicator(indicator_id)
        if definition is None:
            raise ValueError(f"unknown market indicator: {indicator_id}")
        table_name = self._safe_table_name(definition.table_name)
        result: dict[str, list[MarketDataPoint]] = {}
        with self._session() as connection:
            for city in cities:
                rows = connection.execute(
                    f"""
                    SELECT period_end, period_label, value, unit, frequency, released_at
                    FROM {table_name}
                    WHERE city = ? AND period_end >= ? AND period_end <= ?
                    ORDER BY period_end ASC
                    """,
                    (city, start_date, end_date),
                ).fetchall()
                result[city] = [
                    MarketDataPoint(
                        period_end=str(row["period_end"]),
                        period_label=str(row["period_label"]),
                        value=float(row["value"]),
                        unit=str(row["unit"]),
                        frequency=str(row["frequency"]),
                        released_at=str(row["released_at"]),
                    )
                    for row in rows
                ]
        return result

    def upsert_housing_points(
        self,
        indicator_id: str,
        points: Sequence[Mapping[str, Any]],
        *,
        status: str,
        warning_message: str,
    ) -> None:
        definition = self.get_indicator(indicator_id)
        if definition is None:
            raise ValueError(f"unknown market indicator: {indicator_id}")
        table_name = self._safe_table_name(definition.table_name)
        timestamp = _utc_now()
        rows = [
            (
                str(point["period_end"]),
                str(point["period_label"]),
                str(point["city"]),
                float(point["value"]),
                str(point["unit"]),
                str(point["frequency"]),
                str(point["provider_key"]),
                str(point["source_url"]),
                str(point["released_at"]),
                timestamp,
            )
            for point in points
        ]
        with self._session() as connection:
            if rows:
                connection.executemany(
                    f"""
                    INSERT INTO {table_name} (
                        period_end, period_label, city, value, unit, frequency, provider_key, source_url, released_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(period_end, frequency, city) DO UPDATE SET
                        period_label=excluded.period_label,
                        value=excluded.value,
                        unit=excluded.unit,
                        frequency=excluded.frequency,
                        provider_key=excluded.provider_key,
                        source_url=excluded.source_url,
                        released_at=excluded.released_at,
                        last_seen_at=excluded.last_seen_at
                    """,
                    rows,
                )
            aggregate = connection.execute(
                f"""
                SELECT MIN(period_end) AS earliest_period_end, MAX(period_end) AS latest_period_end, COUNT(*) AS point_count
                FROM {table_name}
                """
            ).fetchone()
            connection.execute(
                """
                INSERT INTO market_data_sync_state (
                    indicator_id, provider_key, latest_period_end, earliest_period_end,
                    point_count, status, warning_message, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(indicator_id) DO UPDATE SET
                    provider_key=excluded.provider_key,
                    latest_period_end=excluded.latest_period_end,
                    earliest_period_end=excluded.earliest_period_end,
                    point_count=excluded.point_count,
                    status=excluded.status,
                    warning_message=excluded.warning_message,
                    synced_at=excluded.synced_at
                """,
                (
                    indicator_id,
                    rows[-1][6] if rows else "manual_seed",
                    aggregate["latest_period_end"] if aggregate else None,
                    aggregate["earliest_period_end"] if aggregate else None,
                    int(aggregate["point_count"]) if aggregate else 0,
                    status,
                    warning_message,
                    timestamp,
                ),
            )

    def replace_housing_points(
        self,
        indicator_id: str,
        points: Sequence[Mapping[str, Any]],
        *,
        status: str,
        warning_message: str,
    ) -> None:
        definition = self.get_indicator(indicator_id)
        if definition is None:
            raise ValueError(f"unknown market indicator: {indicator_id}")
        table_name = self._safe_table_name(definition.table_name)
        with self._session() as connection:
            connection.execute(f"DELETE FROM {table_name}")
            connection.execute("DELETE FROM market_data_sync_state WHERE indicator_id = ?", (indicator_id,))
        self.upsert_housing_points(indicator_id, points, status=status, warning_message=warning_message)

    def get_sync_state(self, indicator_id: str) -> MarketSyncState | None:
        with self._session() as connection:
            row = connection.execute(
                """
                SELECT indicator_id, provider_key, latest_period_end, earliest_period_end,
                       point_count, status, warning_message, synced_at
                FROM market_data_sync_state
                WHERE indicator_id = ?
                """,
                (indicator_id,),
            ).fetchone()
        if row is None:
            return None
        return MarketSyncState(
            indicator_id=str(row["indicator_id"]),
            provider_key=str(row["provider_key"]),
            latest_period_end=str(row["latest_period_end"]) if row["latest_period_end"] else None,
            earliest_period_end=str(row["earliest_period_end"]) if row["earliest_period_end"] else None,
            point_count=int(row["point_count"]),
            status=str(row["status"]),
            warning_message=str(row["warning_message"]),
            synced_at=str(row["synced_at"]),
        )

    def _initialize(self) -> None:
        with self._session() as connection:
            for table_name in MARKET_DATA_TABLES.values():
                if table_name in HOUSING_TABLES:
                    connection.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            period_end TEXT NOT NULL,
                            period_label TEXT NOT NULL,
                            city TEXT NOT NULL,
                            value REAL NOT NULL,
                            unit TEXT NOT NULL,
                            frequency TEXT NOT NULL,
                            provider_key TEXT NOT NULL,
                            source_url TEXT NOT NULL,
                            released_at TEXT NOT NULL,
                            last_seen_at TEXT NOT NULL,
                            PRIMARY KEY (period_end, frequency, city)
                        )
                        """
                    )
                else:
                    connection.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            period_end TEXT NOT NULL,
                            period_label TEXT NOT NULL,
                            value REAL NOT NULL,
                            unit TEXT NOT NULL,
                            frequency TEXT NOT NULL,
                            provider_key TEXT NOT NULL,
                            source_url TEXT NOT NULL,
                            released_at TEXT NOT NULL,
                            last_seen_at TEXT NOT NULL,
                            PRIMARY KEY (period_end, frequency)
                        )
                        """
                    )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_data_indicator_registry (
                    indicator_id TEXT PRIMARY KEY,
                    table_name TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    display_order INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_market_data_registry_category_order
                ON market_data_indicator_registry(category, display_order)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_market_data_registry_status_order
                ON market_data_indicator_registry(status, display_order)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_data_sync_state (
                    indicator_id TEXT PRIMARY KEY,
                    provider_key TEXT NOT NULL,
                    latest_period_end TEXT,
                    earliest_period_end TEXT,
                    point_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    warning_message TEXT NOT NULL DEFAULT '',
                    synced_at TEXT NOT NULL
                )
                """
            )

    def _seed_defaults(self) -> None:
        timestamp = _utc_now()
        definitions = _default_indicator_rows(timestamp)
        with self._session() as connection:
            connection.executemany(
                """
                INSERT INTO market_data_indicator_registry (
                    indicator_id, table_name, category, title, unit, frequency,
                    display_order, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(indicator_id) DO UPDATE SET
                    table_name=excluded.table_name,
                    category=excluded.category,
                    title=excluded.title,
                    unit=excluded.unit,
                    frequency=excluded.frequency,
                    display_order=excluded.display_order,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                definitions,
            )
        for indicator_id, points in _default_sample_points().items():
            definition = self.get_indicator(indicator_id)
            if definition is None:
                continue
            if definition.table_name in HOUSING_TABLES:
                if not self.list_housing_cities(indicator_id):
                    self.upsert_housing_points(indicator_id, points, status="sample", warning_message="sample data")
            else:
                if not self.load_points(indicator_id=indicator_id, start_date="1900-01-01", end_date="2999-12-31"):
                    self.upsert_points(indicator_id, points, status="sample", warning_message="sample data")

    def _safe_table_name(self, table_name: str) -> str:
        if table_name not in MARKET_DATA_TABLES.values():
            raise ValueError(f"unsafe market data table: {table_name}")
        return table_name

    def _build_definition(self, row: sqlite3.Row) -> MarketIndicatorDefinition:
        return MarketIndicatorDefinition(
            indicator_id=str(row["indicator_id"]),
            table_name=str(row["table_name"]),
            category=str(row["category"]),
            title=str(row["title"]),
            unit=str(row["unit"]),
            frequency=str(row["frequency"]),
            display_order=int(row["display_order"]),
            status=str(row["status"]),
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


def _default_indicator_rows(timestamp: str) -> list[tuple[str, str, str, str, str, str, int, str, str, str]]:
    return [
        (
            "wti_crude_oil",
            "market_wti_crude_oil",
            "commodities",
            "WTI原油",
            "美元/桶",
            "daily",
            1,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "brent_crude_oil",
            "market_brent_crude_oil",
            "commodities",
            "布伦特原油",
            "美元/桶",
            "daily",
            2,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "gold_spot",
            "market_gold_spot",
            "precious_metals",
            "黄金现货",
            "美元/盎司",
            "daily",
            1,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "silver_spot",
            "market_silver_spot",
            "precious_metals",
            "白银现货",
            "美元/盎司",
            "daily",
            2,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "copper",
            "market_copper",
            "precious_metals",
            "铜",
            "美元/磅",
            "daily",
            3,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "second_hand_housing",
            "market_second_hand_housing",
            "real_estate",
            "全国70城二手房价格指数",
            "%",
            "monthly",
            1,
            "sample",
            timestamp,
            timestamp,
        ),
    ]


def _default_sample_points() -> dict[str, list[dict[str, object]]]:
    daily_periods = ["2026-04-27", "2026-04-28", "2026-04-29", "2026-04-30", "2026-05-01"]
    daily_labels = ["04-27", "04-28", "04-29", "04-30", "05-01"]

    def daily(values: list[float], unit: str) -> list[dict[str, object]]:
        return [
            _point(period, label, value, unit, "daily")
            for period, label, value in zip(daily_periods, daily_labels, values)
        ]

    housing_periods = ["2025-11-01", "2025-12-01", "2026-01-01", "2026-02-01", "2026-03-01"]
    housing_labels = ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03"]

    def housing_point(period: str, label: str, city: str, value: float) -> dict[str, object]:
        return {
            "period_end": period,
            "period_label": label,
            "city": city,
            "value": value,
            "unit": "%",
            "frequency": "monthly",
            "provider_key": "manual_seed",
            "source_url": "",
            "released_at": "",
        }

    return {
        "wti_crude_oil": daily([62.3, 63.1, 61.8, 64.2, 62.5], "美元/桶"),
        "brent_crude_oil": daily([66.1, 67.3, 65.8, 68.0, 66.4], "美元/桶"),
        "gold_spot": daily([2350, 2372, 2345, 2385, 2368], "美元/盎司"),
        "silver_spot": daily([28.5, 29.1, 28.3, 29.6, 28.9], "美元/盎司"),
        "copper": daily([4.22, 4.35, 4.18, 4.42, 4.28], "美元/磅"),
        "second_hand_housing": [
            housing_point(p, l, c, v)
            for p, l in zip(housing_periods, housing_labels)
            for c, v in [
                ("北京", 91.6), ("上海", 93.8), ("广州", 91.2), ("深圳", 93.5),
                ("杭州", 95.1), ("成都", 94.3),
            ]
        ],
    }


def _point(period_end: str, period_label: str, value: float, unit: str, frequency: str) -> dict[str, object]:
    return {
        "period_end": period_end,
        "period_label": period_label,
        "value": value,
        "unit": unit,
        "frequency": frequency,
        "provider_key": "manual_seed",
        "source_url": "",
        "released_at": "",
    }
