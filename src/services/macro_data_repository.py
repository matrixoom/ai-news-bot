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
    "nominal_gdp_growth": "macro_nominal_gdp_growth",
    "real_gdp_growth": "macro_real_gdp_growth",
    "manufacturing_pmi": "macro_manufacturing_pmi",
    "non_manufacturing_pmi": "macro_non_manufacturing_pmi",
    "comprehensive_pmi": "macro_comprehensive_pmi",
    "exports": "macro_exports",
    "imports": "macro_imports",
    "social_financing_rmb_loans": "macro_social_financing_rmb_loans",
    "social_financing_foreign_loans": "macro_social_financing_foreign_loans",
    "social_financing_entrusted_loans": "macro_social_financing_entrusted_loans",
    "social_financing_trust_loans": "macro_social_financing_trust_loans",
    "social_financing_bankers_acceptance": "macro_social_financing_bankers_acceptance",
    "social_financing_corporate_bonds": "macro_social_financing_corporate_bonds",
    "social_financing_government_bonds": "macro_social_financing_government_bonds",
    "social_financing_equity": "macro_social_financing_equity",
    "m0": "macro_m0",
    "m1": "macro_m1",
    "m2": "macro_m2",
    "new_rmb_loans": "macro_new_rmb_loans",
    "social_financing": "macro_social_financing",
    "household_short_term_loans": "macro_household_short_term_loans",
    "household_long_term_loans": "macro_household_long_term_loans",
    "corporate_short_term_loans": "macro_corporate_short_term_loans",
    "corporate_long_term_loans": "macro_corporate_long_term_loans",
    "household_deposits": "macro_household_deposits",
    "household_demand_deposits": "macro_household_demand_deposits",
    "household_time_deposits": "macro_household_time_deposits",
    "china_10y_bond_yield": "macro_china_10y_bond_yield",
    "us_10y_bond_yield": "macro_us_10y_bond_yield",
    "usd_cny": "macro_usd_cny",
    "us_credit_spread": "macro_us_credit_spread",
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
            connection.execute(
                """
                UPDATE macro_data_indicator_registry
                SET status = ?, updated_at = ?
                WHERE indicator_id = ?
                """,
                (status, timestamp, indicator_id),
            )

    def replace_points(
        self,
        indicator_id: str,
        points: Sequence[Mapping[str, Any]],
        *,
        status: str,
        warning_message: str,
    ) -> None:
        """替换单个指标事实表内的全部历史点。

        Args:
            indicator_id: 指标稳定 ID。
            points: 新的完整历史点集合。
            status: 本次同步状态。
            warning_message: 降级或失败原因。

        Returns:
            无返回值；替换完成后同步状态会反映新历史集合。
        """

        definition = self.get_indicator(indicator_id)
        if definition is None:
            raise ValueError(f"unknown macro indicator: {indicator_id}")
        table_name = self._safe_table_name(definition.table_name)
        with self._session() as connection:
            connection.execute(f"DELETE FROM {table_name}")
            connection.execute("DELETE FROM macro_data_sync_state WHERE indicator_id = ?", (indicator_id,))
        self.upsert_points(indicator_id, points, status=status, warning_message=warning_message)

    def load_points(
        self,
        *,
        indicator_id: str,
        start_date: str,
        end_date: str,
        frequency: str | None = None,
    ) -> list[MacroDataPoint]:
        """按时间范围读取单个指标事实表。

        Args:
            indicator_id: 指标稳定 ID。
            start_date: 起始日期，格式 `YYYY-MM-DD`。
            end_date: 结束日期，格式 `YYYY-MM-DD`。
            frequency: 可选频率过滤，例如 `yearly` 或 `quarterly`。

        Returns:
            按周期升序排列的点位列表。
        """

        definition = self.get_indicator(indicator_id)
        if definition is None:
            raise ValueError(f"unknown macro indicator: {indicator_id}")
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
                self._migrate_fact_table_primary_key(connection, table_name)
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

    def _migrate_fact_table_primary_key(self, connection: sqlite3.Connection, table_name: str) -> None:
        """将旧版单日期主键事实表迁移为日期和频率联合主键。

        Args:
            connection: 当前 SQLite 连接。
            table_name: 事实表名。

        Returns:
            无返回值；已是新结构时保持不变。
        """

        index_rows = connection.execute(f"PRAGMA index_list({table_name})").fetchall()
        for index_row in index_rows:
            if str(index_row["origin"]) != "pk":
                continue
            index_columns = connection.execute(f"PRAGMA index_info({index_row['name']})").fetchall()
            column_names = [str(column["name"]) for column in index_columns]
            if column_names == ["period_end", "frequency"]:
                return
        temporary_table_name = f"{table_name}_v2"
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {temporary_table_name} (
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
            f"""
            INSERT OR REPLACE INTO {temporary_table_name} (
                period_end, period_label, value, unit, frequency, provider_key, source_url, released_at, last_seen_at
            )
            SELECT period_end, period_label, value, unit, frequency, provider_key, source_url, released_at, last_seen_at
            FROM {table_name}
            """
        )
        connection.execute(f"DROP TABLE {table_name}")
        connection.execute(f"ALTER TABLE {temporary_table_name} RENAME TO {table_name}")

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
                    status=CASE
                        WHEN macro_data_indicator_registry.status = 'sample' THEN excluded.status
                        ELSE macro_data_indicator_registry.status
                    END,
                    updated_at=CASE
                        WHEN macro_data_indicator_registry.status = 'sample' THEN excluded.updated_at
                        ELSE macro_data_indicator_registry.updated_at
                    END
                """,
                definitions,
            )
            # 真实同步状态是运行时事实，初始化默认注册表时不能把它回写成 sample。
            connection.execute(
                """
                UPDATE macro_data_indicator_registry
                SET status = (
                        SELECT macro_data_sync_state.status
                        FROM macro_data_sync_state
                        WHERE macro_data_sync_state.indicator_id = macro_data_indicator_registry.indicator_id
                    ),
                    updated_at = (
                        SELECT macro_data_sync_state.synced_at
                        FROM macro_data_sync_state
                        WHERE macro_data_sync_state.indicator_id = macro_data_indicator_registry.indicator_id
                    )
                WHERE EXISTS (
                    SELECT 1
                    FROM macro_data_sync_state
                    WHERE macro_data_sync_state.indicator_id = macro_data_indicator_registry.indicator_id
                )
                """
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
            "nominal_gdp_growth",
            "macro_nominal_gdp_growth",
            "derived",
            "名义GDP增速",
            "%",
            "quarterly",
            1,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "real_gdp_growth",
            "macro_real_gdp_growth",
            "derived",
            "实际GDP增速",
            "%",
            "quarterly",
            2,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "household_new_loans",
            "macro_household_new_loans",
            "credit_component",
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
            "credit_component",
            "企业新增贷款",
            "亿元",
            "monthly",
            2,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "new_rmb_loans",
            "macro_new_rmb_loans",
            "credit",
            "新增人民币贷款",
            "亿元",
            "monthly",
            1,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "social_financing",
            "macro_social_financing",
            "credit",
            "社会融资规模",
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
            "credit",
            "居民杠杆率",
            "%",
            "quarterly",
            3,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "corporate_leverage_ratio",
            "macro_corporate_leverage_ratio",
            "credit",
            "企业杠杆率",
            "%",
            "quarterly",
            5,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "household_short_term_loans",
            "macro_household_short_term_loans",
            "credit_component",
            "居民新增短期贷款",
            "亿元",
            "monthly",
            3,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "household_long_term_loans",
            "macro_household_long_term_loans",
            "credit_component",
            "居民新增长期贷款",
            "亿元",
            "monthly",
            4,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "corporate_short_term_loans",
            "macro_corporate_short_term_loans",
            "credit_component",
            "企业新增短期贷款",
            "亿元",
            "monthly",
            5,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "corporate_long_term_loans",
            "macro_corporate_long_term_loans",
            "credit_component",
            "企业新增长期贷款",
            "亿元",
            "monthly",
            6,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "household_deposits",
            "macro_household_deposits",
            "credit_component",
            "居民存款总计",
            "亿元",
            "monthly",
            7,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "household_demand_deposits",
            "macro_household_demand_deposits",
            "credit",
            "居民活期存款",
            "亿元",
            "monthly",
            2,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "household_time_deposits",
            "macro_household_time_deposits",
            "credit_component",
            "居民定期及其他存款",
            "亿元",
            "monthly",
            8,
            "sample",
            timestamp,
            timestamp,
        ),
        ("ppi", "macro_ppi", "prices", "PPI", "%", "monthly", 1, "sample", timestamp, timestamp),
        ("cpi", "macro_cpi", "prices", "CPI", "%", "monthly", 2, "sample", timestamp, timestamp),
        (
            "manufacturing_pmi",
            "macro_manufacturing_pmi",
            "climate",
            "制造业PMI",
            "%",
            "monthly",
            1,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "non_manufacturing_pmi",
            "macro_non_manufacturing_pmi",
            "climate",
            "非制造业PMI",
            "%",
            "monthly",
            2,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "comprehensive_pmi",
            "macro_comprehensive_pmi",
            "climate",
            "综合PMI",
            "%",
            "monthly",
            3,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "exports",
            "macro_exports",
            "trade",
            "出口",
            "亿元",
            "monthly",
            1,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "imports",
            "macro_imports",
            "trade",
            "进口",
            "亿元",
            "monthly",
            2,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "social_financing_rmb_loans",
            "macro_social_financing_rmb_loans",
            "credit_component",
            "人民币贷款",
            "亿元",
            "monthly",
            5,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "social_financing_foreign_loans",
            "macro_social_financing_foreign_loans",
            "credit_component",
            "外币贷款",
            "亿元",
            "monthly",
            6,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "social_financing_entrusted_loans",
            "macro_social_financing_entrusted_loans",
            "credit_component",
            "委托贷款",
            "亿元",
            "monthly",
            7,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "social_financing_trust_loans",
            "macro_social_financing_trust_loans",
            "credit_component",
            "信托贷款",
            "亿元",
            "monthly",
            8,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "social_financing_bankers_acceptance",
            "macro_social_financing_bankers_acceptance",
            "credit_component",
            "未贴现银行承兑汇票",
            "亿元",
            "monthly",
            9,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "social_financing_corporate_bonds",
            "macro_social_financing_corporate_bonds",
            "credit_component",
            "企业债券融资",
            "亿元",
            "monthly",
            10,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "social_financing_government_bonds",
            "macro_social_financing_government_bonds",
            "credit_component",
            "政府债券融资",
            "亿元",
            "monthly",
            11,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "social_financing_equity",
            "macro_social_financing_equity",
            "credit_component",
            "股票融资",
            "亿元",
            "monthly",
            12,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "m0",
            "macro_m0",
            "currency",
            "M0",
            "亿元",
            "monthly",
            1,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "m1",
            "macro_m1",
            "currency",
            "M1",
            "亿元",
            "monthly",
            2,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "m2",
            "macro_m2",
            "currency",
            "M2",
            "亿元",
            "monthly",
            3,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "china_10y_bond_yield",
            "macro_china_10y_bond_yield",
            "expectations",
            "中国10年期国债收益率",
            "%",
            "monthly",
            1,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "us_10y_bond_yield",
            "macro_us_10y_bond_yield",
            "expectations",
            "美国10年期国债收益率",
            "%",
            "monthly",
            2,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "usd_cny",
            "macro_usd_cny",
            "expectations",
            "人民币汇率（兑美元）",
            "元",
            "monthly",
            3,
            "sample",
            timestamp,
            timestamp,
        ),
        (
            "us_credit_spread",
            "macro_us_credit_spread",
            "expectations",
            "美国信用利差",
            "%",
            "monthly",
            4,
            "sample",
            timestamp,
            timestamp,
        ),
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
        "manufacturing_pmi": monthly([50.1, 50.2, 49.8, 50.3, 50.5], "%"),
        "non_manufacturing_pmi": monthly([52.3, 52.7, 51.9, 53.1, 53.4], "%"),
        "comprehensive_pmi": monthly([51.4, 51.7, 50.8, 52.1, 52.4], "%"),
        "exports": monthly([16200, 16800, 17100, 15500, 17400], "亿元"),
        "imports": monthly([11800, 12300, 13200, 12100, 14600], "亿元"),
        "social_financing_rmb_loans": monthly([32000, 28000, 41000, 36000, 45000], "亿元"),
        "social_financing_foreign_loans": monthly([300, -200, 500, 200, 400], "亿元"),
        "social_financing_entrusted_loans": monthly([200, -100, 300, 150, 250], "亿元"),
        "social_financing_trust_loans": monthly([-500, -300, 100, -200, 50], "亿元"),
        "social_financing_bankers_acceptance": monthly([-100, 200, 0, -300, 150], "亿元"),
        "social_financing_corporate_bonds": monthly([4000, 3500, 5000, 4200, 4800], "亿元"),
        "social_financing_government_bonds": monthly([5000, 4500, 6000, 5200, 5800], "亿元"),
        "social_financing_equity": monthly([800, 600, 1000, 700, 900], "亿元"),
        "m0": monthly([121000, 124000, 128000, 125000, 130000], "亿元"),
        "m1": monthly([735000, 742000, 751000, 738000, 756000], "亿元"),
        "m2": monthly([3110000, 3140000, 3180000, 3130000, 3220000], "亿元"),
        "new_rmb_loans": monthly([32000, 28000, 49000, 9000, 29900], "亿元"),
        "social_financing": monthly([45000, 28000, 61000, 12000, 45000], "亿元"),
        "household_short_term_loans": monthly([3200, 4100, 6200, 2800, 5100], "亿元"),
        "household_long_term_loans": monthly([9800, 8500, 14300, 9100, 11800], "亿元"),
        "corporate_short_term_loans": monthly([7600, 8500, 14300, 9100, 11800], "亿元"),
        "corporate_long_term_loans": monthly([14200, 12800, 19500, 11500, 18600], "亿元"),
        "household_deposits": monthly([1510000, 1530000, 1580000, 1600000, 1620000], "亿元"),
        "household_demand_deposits": monthly([395000, 402000, 408000, 412000, 420000], "亿元"),
        "household_time_deposits": monthly([1115000, 1128000, 1172000, 1188000, 1200000], "亿元"),
        "china_10y_bond_yield": monthly([1.72, 1.68, 1.75, 1.80, 1.78], "%"),
        "us_10y_bond_yield": monthly([4.25, 4.32, 4.28, 4.41, 4.38], "%"),
        "usd_cny": monthly([7.28, 7.25, 7.31, 7.27, 7.24], "元"),
        "us_credit_spread": monthly([1.05, 1.12, 1.08, 1.15, 1.10], "%"),
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
