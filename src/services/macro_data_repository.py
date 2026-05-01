"""SQLite repository for the Macro Data module."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Mapping, Sequence


MACRO_DATA_TABLES: dict[str, str] = {
    "nominal_gdp": "macro_nominal_gdp",
    "real_gdp": "macro_real_gdp",
    "household_new_loans": "macro_household_new_loans",
    "corporate_new_loans": "macro_corporate_new_loans",
    "household_leverage_ratio": "macro_household_leverage_ratio",
    "corporate_leverage_ratio": "macro_corporate_leverage_ratio",
    "ppi": "macro_ppi",
    "cpi": "macro_cpi",
}


@dataclass(frozen=True)
class MacroIndicatorDefinition:
    """宏观指标注册信息。

    Args:
        indicator_id: 指标稳定 ID。
        table_name: SQLite 独立事实表名。
        category: 页面分类标签。
        title: 用户可见中文标题。
        unit: 默认展示单位。
        frequency: 默认发布频率。
        display_order: 分类内排序。
        status: 数据质量状态。

    Returns:
        不返回值；该数据类用于在 Repository 与 Service 之间传递指标元数据。
    """

    indicator_id: str
    table_name: str
    category: str
    title: str
    unit: str
    frequency: str
    display_order: int
    status: str


@dataclass(frozen=True)
class MacroDataPoint:
    """宏观指标单个历史点。

    Args:
        period_end: 周期结束日期。
        period_label: 展示用周期标签。
        value: 指标数值。
        unit: 单位。
        frequency: 数据频率。
        released_at: 发布时间。

    Returns:
        不返回值；该数据类用于传递可绘图点位。
    """

    period_end: str
    period_label: str
    value: float
    unit: str
    frequency: str
    released_at: str


@dataclass(frozen=True)
class MacroSyncState:
    """宏观指标同步状态。

    Args:
        indicator_id: 指标稳定 ID。
        provider_key: 最近使用的数据来源。
        latest_period_end: 最新周期。
        earliest_period_end: 最早周期。
        point_count: 当前记录数。
        status: 同步状态。
        warning_message: 降级或失败原因。
        synced_at: 同步时间。

    Returns:
        不返回值；该数据类用于页面展示数据状态。
    """

    indicator_id: str
    provider_key: str
    latest_period_end: str | None
    earliest_period_end: str | None
    point_count: int
    status: str
    warning_message: str
    synced_at: str


def _utc_now() -> str:
    """返回 UTC ISO 时间字符串。

    Returns:
        形如 `2026-05-01T00:00:00Z` 的时间字符串。
    """

    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class MacroDataRepository:
    """管理 Macro Data 本地 SQLite 持久化。

    Args:
        db_path: SQLite 数据库路径，默认写入 `.data/macro_data.db`。

    Returns:
        初始化后的仓储实例；构造时会创建表并写入默认注册与样例数据。
    """

    def __init__(self, db_path: str | Path = ".data/macro_data.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self._seed_defaults()

    @property
    def db_path(self) -> Path:
        """返回 SQLite 数据库路径。

        Returns:
            当前仓储使用的数据库路径。
        """

        return self._db_path

    def list_table_names(self) -> set[str]:
        """列出当前数据库内所有表名。

        Returns:
            SQLite schema 中的表名集合。
        """

        with self._session() as connection:
            rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        return {str(row["name"]) for row in rows}

    def list_indicators(self, category: str) -> list[MacroIndicatorDefinition]:
        """按分类读取指标定义。

        Args:
            category: 页面分类标签，例如 `gdp`。

        Returns:
            指标定义列表，按展示顺序排序。
        """

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT indicator_id, table_name, category, title, unit, frequency, display_order, status
                FROM macro_data_indicator_registry
                WHERE category = ?
                ORDER BY display_order ASC
                """,
                (category,),
            ).fetchall()
        return [self._build_definition(row) for row in rows]

    def get_indicator(self, indicator_id: str) -> MacroIndicatorDefinition | None:
        """读取单个指标定义。

        Args:
            indicator_id: 指标稳定 ID。

        Returns:
            找到时返回指标定义，否则返回 `None`。
        """

        with self._session() as connection:
            row = connection.execute(
                """
                SELECT indicator_id, table_name, category, title, unit, frequency, display_order, status
                FROM macro_data_indicator_registry
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
        """幂等写入单个指标事实表并更新同步状态。

        Args:
            indicator_id: 指标稳定 ID。
            points: 待写入的历史点。
            status: 本次同步状态。
            warning_message: 降级或失败原因。

        Returns:
            无返回值；写入失败时抛出 SQLite 异常。
        """

        definition = self.get_indicator(indicator_id)
        if definition is None:
            raise ValueError(f"unknown macro indicator: {indicator_id}")
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
                    ON CONFLICT(period_end) DO UPDATE SET
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
                INSERT INTO macro_data_sync_state (
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

    def load_points(self, *, indicator_id: str, start_date: str, end_date: str) -> list[MacroDataPoint]:
        """按时间范围读取单个指标事实表。

        Args:
            indicator_id: 指标稳定 ID。
            start_date: 起始日期，格式 `YYYY-MM-DD`。
            end_date: 结束日期，格式 `YYYY-MM-DD`。

        Returns:
            按周期升序排列的点位列表。
        """

        definition = self.get_indicator(indicator_id)
        if definition is None:
            raise ValueError(f"unknown macro indicator: {indicator_id}")
        table_name = self._safe_table_name(definition.table_name)
        with self._session() as connection:
            rows = connection.execute(
                f"""
                SELECT period_end, period_label, value, unit, frequency, released_at
                FROM {table_name}
                WHERE period_end >= ? AND period_end <= ?
                ORDER BY period_end ASC
                """,
                (start_date, end_date),
            ).fetchall()
        return [
            MacroDataPoint(
                period_end=str(row["period_end"]),
                period_label=str(row["period_label"]),
                value=float(row["value"]),
                unit=str(row["unit"]),
                frequency=str(row["frequency"]),
                released_at=str(row["released_at"]),
            )
            for row in rows
        ]

    def get_sync_state(self, indicator_id: str) -> MacroSyncState | None:
        """读取指标同步状态。

        Args:
            indicator_id: 指标稳定 ID。

        Returns:
            找到时返回同步状态，否则返回 `None`。
        """

        with self._session() as connection:
            row = connection.execute(
                """
                SELECT indicator_id, provider_key, latest_period_end, earliest_period_end,
                       point_count, status, warning_message, synced_at
                FROM macro_data_sync_state
                WHERE indicator_id = ?
                """,
                (indicator_id,),
            ).fetchone()
        if row is None:
            return None
        return MacroSyncState(
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
        """创建 Macro Data 所需表结构。

        Returns:
            无返回值；表已存在时保持幂等。
        """

        with self._session() as connection:
            for table_name in MACRO_DATA_TABLES.values():
                connection.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        period_end TEXT PRIMARY KEY,
                        period_label TEXT NOT NULL,
                        value REAL NOT NULL,
                        unit TEXT NOT NULL,
                        frequency TEXT NOT NULL,
                        provider_key TEXT NOT NULL,
                        source_url TEXT NOT NULL,
                        released_at TEXT NOT NULL,
                        last_seen_at TEXT NOT NULL
                    )
                    """
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS macro_data_indicator_registry (
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
                CREATE INDEX IF NOT EXISTS idx_macro_data_registry_category_order
                ON macro_data_indicator_registry(category, display_order)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_macro_data_registry_status_order
                ON macro_data_indicator_registry(status, display_order)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS macro_data_sync_state (
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
        """写入默认指标注册信息和确定性样例数据。

        Returns:
            无返回值；重复执行保持幂等。
        """

        timestamp = _utc_now()
        definitions = _default_indicator_rows(timestamp)
        with self._session() as connection:
            connection.executemany(
                """
                INSERT INTO macro_data_indicator_registry (
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
            if not self.load_points(indicator_id=indicator_id, start_date="1900-01-01", end_date="2999-12-31"):
                self.upsert_points(indicator_id, points, status="sample", warning_message="sample data")

    def _safe_table_name(self, table_name: str) -> str:
        """校验表名来自受控注册表。

        Args:
            table_name: 候选事实表名。

        Returns:
            通过校验的表名。
        """

        if table_name not in MACRO_DATA_TABLES.values():
            raise ValueError(f"unsafe macro data table: {table_name}")
        return table_name

    def _build_definition(self, row: sqlite3.Row) -> MacroIndicatorDefinition:
        """从 SQLite 行构造指标定义。

        Args:
            row: SQLite 查询行。

        Returns:
            指标定义对象。
        """

        return MacroIndicatorDefinition(
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
        """打开 SQLite 会话并在退出时提交。

        Returns:
            可执行 SQL 的连接对象。
        """

        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


def _default_indicator_rows(timestamp: str) -> list[tuple[str, str, str, str, str, str, int, str, str, str]]:
    """构造默认指标注册记录。

    Args:
        timestamp: 创建和更新时间。

    Returns:
        可直接 executemany 写入注册表的记录列表。
    """

    return [
        ("nominal_gdp", "macro_nominal_gdp", "gdp", "名义GDP", "亿元", "quarterly", 1, "sample", timestamp, timestamp),
        ("real_gdp", "macro_real_gdp", "gdp", "实际GDP", "亿元", "quarterly", 2, "sample", timestamp, timestamp),
        (
            "household_new_loans",
            "macro_household_new_loans",
            "credit",
            "居民新增贷款",
            "亿元",
            "monthly",
            1,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "corporate_new_loans",
            "macro_corporate_new_loans",
            "credit",
            "企业新增贷款",
            "亿元",
            "monthly",
            2,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "household_leverage_ratio",
            "macro_household_leverage_ratio",
            "leverage",
            "居民杠杆率",
            "%",
            "quarterly",
            1,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "corporate_leverage_ratio",
            "macro_corporate_leverage_ratio",
            "leverage",
            "企业杠杆率",
            "%",
            "quarterly",
            2,
            "sample",
            timestamp,
            timestamp,
        ),
        ("ppi", "macro_ppi", "prices", "PPI", "%", "monthly", 1, "sample", timestamp, timestamp),
        ("cpi", "macro_cpi", "prices", "CPI", "%", "monthly", 2, "sample", timestamp, timestamp),
    ]


def _default_sample_points() -> dict[str, list[dict[str, object]]]:
    """构造每个指标的确定性样例序列。

    Returns:
        以指标 ID 为键的样例点位字典。
    """

    periods = ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31"]
    labels = ["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1"]
    monthly_periods = ["2025-11-30", "2025-12-31", "2026-01-31", "2026-02-28", "2026-03-31"]
    monthly_labels = ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03"]

    def quarterly(values: list[float], unit: str) -> list[dict[str, object]]:
        return [_point(period, label, value, unit, "quarterly") for period, label, value in zip(periods, labels, values)]

    def monthly(values: list[float], unit: str) -> list[dict[str, object]]:
        return [
            _point(period, label, value, unit, "monthly")
            for period, label, value in zip(monthly_periods, monthly_labels, values)
        ]

    return {
        "nominal_gdp": quarterly([310000, 625000, 940000, 1260000, 322000], "亿元"),
        "real_gdp": quarterly([295000, 598000, 902000, 1210000, 309000], "亿元"),
        "household_new_loans": monthly([3200, 4100, 6200, 2800, 5100], "亿元"),
        "corporate_new_loans": monthly([7600, 8500, 14300, 9100, 11800], "亿元"),
        "household_leverage_ratio": quarterly([63.1, 63.4, 63.6, 63.9, 64.1], "%"),
        "corporate_leverage_ratio": quarterly([162.2, 162.8, 163.5, 164.1, 164.6], "%"),
        "ppi": monthly([-2.5, -2.3, -2.1, -1.8, -1.6], "%"),
        "cpi": monthly([0.2, 0.1, 0.5, 0.7, 0.8], "%"),
    }


def _point(period_end: str, period_label: str, value: float, unit: str, frequency: str) -> dict[str, object]:
    """构造样例点位。

    Args:
        period_end: 周期结束日期。
        period_label: 展示周期标签。
        value: 指标数值。
        unit: 单位。
        frequency: 频率。

    Returns:
        可写入 Repository 的点位字典。
    """

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
