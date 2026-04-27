"""SQLite-backed storage for Macro 数据因子和数据源矩阵。"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Iterator, Sequence

from ..domain.macro_data_factors import MacroFactorDefinition, MacroSourceMatrixRow


def _utc_now() -> str:
    """返回统一的 UTC ISO 时间字符串。"""

    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class MacroDataFactorStore:
    """持久化 Macro 数据因子定义和来源可用性矩阵。"""

    def __init__(self, db_path: str | Path = ".data/macro_data_factors.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self.seed_defaults()

    @property
    def db_path(self) -> Path:
        """返回当前 SQLite 数据库路径。"""

        return self._db_path

    def list_factor_definitions(self) -> list[MacroFactorDefinition]:
        """按展示顺序读取数据因子定义。"""

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT
                    factor_code,
                    factor_label,
                    category,
                    description,
                    default_unit,
                    frequency,
                    source_key,
                    storage_table,
                    calculation_method,
                    display_order,
                    status
                FROM macro_factor_definitions
                ORDER BY display_order ASC, factor_code ASC
                """
            ).fetchall()
        return [
            MacroFactorDefinition(
                factor_code=str(row["factor_code"]),
                factor_label=str(row["factor_label"]),
                category=str(row["category"]),
                description=str(row["description"]),
                default_unit=str(row["default_unit"]),
                frequency=str(row["frequency"]),
                source_key=str(row["source_key"]),
                storage_table=str(row["storage_table"]),
                calculation_method=str(row["calculation_method"]),
                display_order=int(row["display_order"]),
                status=str(row["status"]),
            )
            for row in rows
        ]

    def list_source_matrix_rows(self) -> list[MacroSourceMatrixRow]:
        """按指标和优先级读取数据源可用性矩阵。"""

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT
                    matrix_id,
                    factor_code,
                    factor_label,
                    source_key,
                    source_label,
                    source_role,
                    source_type,
                    availability_status,
                    reliability_level,
                    coverage_scope,
                    coverage_start,
                    coverage_end,
                    frequency,
                    access_method,
                    field_mapping_status,
                    parser_status,
                    license_note,
                    priority_order,
                    warning_message,
                    last_verified_at
                FROM macro_source_availability_matrix
                ORDER BY factor_code ASC, priority_order ASC, source_key ASC
                """
            ).fetchall()
        return [
            MacroSourceMatrixRow(
                matrix_id=str(row["matrix_id"]),
                factor_code=str(row["factor_code"]),
                factor_label=str(row["factor_label"]),
                source_key=str(row["source_key"]),
                source_label=str(row["source_label"]),
                source_role=str(row["source_role"]),
                source_type=str(row["source_type"]),
                availability_status=str(row["availability_status"]),
                reliability_level=str(row["reliability_level"]),
                coverage_scope=str(row["coverage_scope"]),
                coverage_start=str(row["coverage_start"]),
                coverage_end=str(row["coverage_end"]),
                frequency=str(row["frequency"]),
                access_method=str(row["access_method"]),
                field_mapping_status=str(row["field_mapping_status"]),
                parser_status=str(row["parser_status"]),
                license_note=str(row["license_note"]),
                priority_order=int(row["priority_order"]),
                warning_message=str(row["warning_message"]),
                last_verified_at=str(row["last_verified_at"]),
            )
            for row in rows
        ]

    def get_table_field_comments(self, table_name: str) -> dict[str, str]:
        """读取指定表的字段中文注释。

        Args:
            table_name: 需要查询字段注释的 SQLite 表名。

        Returns:
            以字段名为 key、中文注释为 value 的字典。
        """

        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT field_name, comment
                FROM macro_table_field_comments
                WHERE table_name = ?
                ORDER BY display_order ASC, field_name ASC
                """,
                (table_name,),
            ).fetchall()
        return {str(row["field_name"]): str(row["comment"]) for row in rows}

    def seed_defaults(self) -> None:
        """幂等写入第一阶段默认因子和来源矩阵。"""

        timestamp = _utc_now()
        with self._session() as connection:
            connection.executemany(
                """
                INSERT INTO macro_factor_definitions (
                    factor_code,
                    factor_label,
                    category,
                    description,
                    default_unit,
                    frequency,
                    source_key,
                    storage_table,
                    calculation_method,
                    display_order,
                    status,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(factor_code) DO UPDATE SET
                    factor_label=excluded.factor_label,
                    category=excluded.category,
                    description=excluded.description,
                    default_unit=excluded.default_unit,
                    frequency=excluded.frequency,
                    source_key=excluded.source_key,
                    storage_table=excluded.storage_table,
                    calculation_method=excluded.calculation_method,
                    display_order=excluded.display_order,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                [(*row, timestamp, timestamp) for row in _DEFAULT_FACTOR_ROWS],
            )
            connection.executemany(
                """
                INSERT INTO macro_source_availability_matrix (
                    matrix_id,
                    factor_code,
                    factor_label,
                    source_key,
                    source_label,
                    source_role,
                    source_type,
                    availability_status,
                    reliability_level,
                    coverage_scope,
                    coverage_start,
                    coverage_end,
                    frequency,
                    access_method,
                    field_mapping_status,
                    parser_status,
                    license_note,
                    priority_order,
                    warning_message,
                    last_verified_at,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(matrix_id) DO UPDATE SET
                    factor_label=excluded.factor_label,
                    source_label=excluded.source_label,
                    source_role=excluded.source_role,
                    source_type=excluded.source_type,
                    availability_status=excluded.availability_status,
                    reliability_level=excluded.reliability_level,
                    coverage_scope=excluded.coverage_scope,
                    coverage_start=excluded.coverage_start,
                    coverage_end=excluded.coverage_end,
                    frequency=excluded.frequency,
                    access_method=excluded.access_method,
                    field_mapping_status=excluded.field_mapping_status,
                    parser_status=excluded.parser_status,
                    license_note=excluded.license_note,
                    priority_order=excluded.priority_order,
                    warning_message=excluded.warning_message,
                    last_verified_at=excluded.last_verified_at,
                    updated_at=excluded.updated_at
                """,
                [(*row, timestamp, timestamp) for row in _DEFAULT_SOURCE_MATRIX_ROWS],
            )
            connection.executemany(
                """
                INSERT INTO macro_table_field_comments (
                    table_name,
                    field_name,
                    comment,
                    display_order,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(table_name, field_name) DO UPDATE SET
                    comment=excluded.comment,
                    display_order=excluded.display_order,
                    updated_at=excluded.updated_at
                """,
                [(*row, timestamp) for row in _build_field_comment_rows()],
            )

    def _initialize(self) -> None:
        """创建数据因子第一阶段需要的 SQLite 表。"""

        with self._session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS macro_factor_definitions (
                    factor_code TEXT PRIMARY KEY,
                    factor_label TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    default_unit TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    storage_table TEXT NOT NULL,
                    calculation_method TEXT NOT NULL,
                    display_order INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS macro_source_availability_matrix (
                    matrix_id TEXT PRIMARY KEY,
                    factor_code TEXT NOT NULL,
                    factor_label TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    source_label TEXT NOT NULL,
                    source_role TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    availability_status TEXT NOT NULL,
                    reliability_level TEXT NOT NULL,
                    coverage_scope TEXT NOT NULL,
                    coverage_start TEXT NOT NULL,
                    coverage_end TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    access_method TEXT NOT NULL,
                    field_mapping_status TEXT NOT NULL,
                    parser_status TEXT NOT NULL,
                    license_note TEXT NOT NULL,
                    priority_order INTEGER NOT NULL,
                    warning_message TEXT NOT NULL,
                    last_verified_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(factor_code, source_key, source_role)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_macro_factor_definitions_category
                ON macro_factor_definitions(category, display_order)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_macro_source_matrix_factor
                ON macro_source_availability_matrix(factor_code, priority_order)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_macro_source_matrix_status
                ON macro_source_availability_matrix(availability_status, reliability_level)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS macro_table_field_comments (
                    table_name TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    comment TEXT NOT NULL,
                    display_order INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (table_name, field_name)
                )
                """
            )
            for table_name in _history_table_names():
                connection.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        observation_id TEXT PRIMARY KEY,
                        factor_code TEXT NOT NULL,
                        region_code TEXT NOT NULL,
                        region_label TEXT NOT NULL,
                        period_end TEXT NOT NULL,
                        period_label TEXT NOT NULL,
                        frequency TEXT NOT NULL,
                        value REAL,
                        unit TEXT NOT NULL,
                        source_key TEXT NOT NULL,
                        source_url TEXT NOT NULL,
                        status TEXT NOT NULL,
                        warning_message TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(factor_code, region_code, period_end, source_key)
                    )
                    """
                )
                connection.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_factor_period
                    ON {table_name}(factor_code, period_end)
                    """
                )

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        """打开一次 SQLite 会话并在成功后提交事务。"""

        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


_DEFAULT_FACTOR_ROWS: Sequence[tuple[str, str, str, str, str, str, str, str, str, int, str]] = (
    (
        "housing_price",
        "房价数据",
        "housing",
        "全国、一线城市、新一线样本城市的新房和二手房价格变化。",
        "%",
        "monthly",
        "nbs_70_city_price",
        "macro_housing_price_history",
        "official_raw",
        10,
        "candidate",
    ),
    (
        "gdp_nominal",
        "名义 GDP",
        "growth",
        "名义 GDP 或名义 GDP 增速。",
        "%",
        "quarterly",
        "nbs_gdp",
        "macro_gdp_nominal_history",
        "official_raw",
        20,
        "candidate",
    ),
    (
        "gdp_real",
        "实际 GDP",
        "growth",
        "实际 GDP 增速。",
        "%",
        "quarterly",
        "nbs_gdp",
        "macro_gdp_real_history",
        "official_raw",
        30,
        "candidate",
    ),
    (
        "gdp_gap",
        "GDP 差值",
        "growth",
        "名义 GDP 增速减实际 GDP 增速。",
        "%",
        "quarterly",
        "derived_gdp_gap",
        "macro_gdp_gap_history",
        "derived_calculation",
        40,
        "candidate",
    ),
    (
        "ppi",
        "企业 PPI",
        "price",
        "工业生产者出厂价格指数或同比。",
        "%",
        "monthly",
        "nbs_ppi",
        "macro_ppi_history",
        "official_raw",
        50,
        "candidate",
    ),
    (
        "household_new_loans",
        "居民新增贷款",
        "credit",
        "人民银行月度金融统计数据报告中的住户部门新增贷款。",
        "亿元",
        "monthly",
        "pbc_financial_statistics",
        "macro_household_new_loans_history",
        "official_raw",
        60,
        "candidate",
    ),
    (
        "household_loan_growth",
        "居民贷款增速",
        "credit",
        "住户贷款余额同比增速。",
        "%",
        "quarterly",
        "pbc_loan_report",
        "macro_household_loan_growth_history",
        "official_raw",
        70,
        "candidate",
    ),
    (
        "household_demand_deposit_growth",
        "居民活期存款增速",
        "deposit",
        "居民活期存款同比增速；公开连续序列需验证。",
        "%",
        "mixed",
        "pbc_deposit_statistics_pending",
        "macro_household_demand_deposit_growth_history",
        "official_raw",
        80,
        "degraded",
    ),
)


def _history_table_names() -> list[str]:
    """根据默认因子配置返回需要初始化的独立历史数据表名。"""

    return sorted({row[7] for row in _DEFAULT_FACTOR_ROWS})


def _build_field_comment_rows() -> list[tuple[str, str, str, int]]:
    """生成 SQLite 字段中文注释元数据。"""

    rows: list[tuple[str, str, str, int]] = [
        ("macro_factor_definitions", "factor_code", "数据因子唯一编码", 10),
        ("macro_factor_definitions", "factor_label", "数据因子中文名称", 20),
        ("macro_factor_definitions", "category", "因子所属分类", 30),
        ("macro_factor_definitions", "description", "因子口径说明", 40),
        ("macro_factor_definitions", "default_unit", "默认展示单位", 50),
        ("macro_factor_definitions", "frequency", "数据更新频率", 60),
        ("macro_factor_definitions", "source_key", "首选数据源编码", 70),
        ("macro_factor_definitions", "storage_table", "该因子对应的本地历史数据表", 80),
        ("macro_factor_definitions", "calculation_method", "原始读取或派生计算方式", 90),
        ("macro_factor_definitions", "display_order", "前端展示排序", 100),
        ("macro_factor_definitions", "status", "因子当前可用状态", 110),
        ("macro_factor_definitions", "created_at", "记录创建时间", 120),
        ("macro_factor_definitions", "updated_at", "记录更新时间", 130),
        ("macro_source_availability_matrix", "matrix_id", "来源矩阵唯一编码", 10),
        ("macro_source_availability_matrix", "factor_code", "数据因子唯一编码", 20),
        ("macro_source_availability_matrix", "factor_label", "数据因子中文名称", 30),
        ("macro_source_availability_matrix", "source_key", "数据源唯一编码", 40),
        ("macro_source_availability_matrix", "source_label", "数据源中文名称", 50),
        ("macro_source_availability_matrix", "source_role", "来源角色：主源或备选源", 60),
        ("macro_source_availability_matrix", "source_type", "来源类型：官方、开源或派生", 70),
        ("macro_source_availability_matrix", "availability_status", "来源可用性状态", 80),
        ("macro_source_availability_matrix", "reliability_level", "来源可靠性等级", 90),
        ("macro_source_availability_matrix", "coverage_scope", "来源覆盖范围说明", 100),
        ("macro_source_availability_matrix", "coverage_start", "来源覆盖起始周期", 110),
        ("macro_source_availability_matrix", "coverage_end", "来源覆盖结束周期，空值表示仍在更新", 120),
        ("macro_source_availability_matrix", "frequency", "来源更新频率", 130),
        ("macro_source_availability_matrix", "access_method", "计划接入方式", 140),
        ("macro_source_availability_matrix", "field_mapping_status", "字段映射确认状态", 150),
        ("macro_source_availability_matrix", "parser_status", "解析器实现状态", 160),
        ("macro_source_availability_matrix", "license_note", "授权和引用说明", 170),
        ("macro_source_availability_matrix", "priority_order", "同一因子下的来源优先级", 180),
        ("macro_source_availability_matrix", "warning_message", "来源限制或风险提示", 190),
        ("macro_source_availability_matrix", "last_verified_at", "来源最近核验时间", 200),
        ("macro_source_availability_matrix", "created_at", "记录创建时间", 210),
        ("macro_source_availability_matrix", "updated_at", "记录更新时间", 220),
    ]
    history_comments = [
        ("observation_id", "历史观测值唯一编码"),
        ("factor_code", "数据因子唯一编码"),
        ("region_code", "地区或城市编码，全国口径使用 CN"),
        ("region_label", "地区或城市中文名称"),
        ("period_end", "观测周期结束日期"),
        ("period_label", "前端展示周期标签"),
        ("frequency", "数据频率"),
        ("value", "观测值，无法确认时保持空值"),
        ("unit", "观测值单位"),
        ("source_key", "数据来源编码"),
        ("source_url", "来源链接或发布页地址"),
        ("status", "该观测值质量状态"),
        ("warning_message", "该观测值的口径或质量提示"),
        ("created_at", "记录创建时间"),
        ("updated_at", "记录更新时间"),
    ]
    for table_name in _history_table_names():
        rows.extend(
            (table_name, field_name, comment, index * 10)
            for index, (field_name, comment) in enumerate(history_comments, start=1)
        )
    return rows

_DEFAULT_SOURCE_MATRIX_ROWS: Sequence[tuple[str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, int, str, str]] = (
    (
        "housing_price:nbs_70_city_price:primary",
        "housing_price",
        "房价数据",
        "nbs_70_city_price",
        "国家统计局 70 城商品住宅销售价格指数",
        "primary",
        "official",
        "candidate",
        "official",
        "70 城新房、二手房环比、同比和定基指数。",
        "2011-01",
        "",
        "monthly",
        "official_page_parse",
        "partial",
        "pending",
        "官方公开发布页面，需按页面口径引用。",
        1,
        "官方源最可信，但需要稳定解析月度发布页面。",
        "2026-04-26T00:00:00Z",
    ),
    (
        "housing_price:akshare_new_house_price:fallback",
        "housing_price",
        "房价数据",
        "akshare_new_house_price",
        "AKShare 新房价指数接口",
        "fallback",
        "open_source",
        "candidate",
        "community",
        "可作为字段对齐和样例数据来源。",
        "2011-01",
        "",
        "monthly",
        "akshare_api",
        "partial",
        "pending",
        "需核对上游真实来源和接口覆盖范围。",
        2,
        "不能直接等同于完整 70 城官方口径。",
        "2026-04-26T00:00:00Z",
    ),
    (
        "gdp_nominal:nbs_gdp:primary",
        "gdp_nominal",
        "名义 GDP",
        "nbs_gdp",
        "国家统计局 GDP 数据",
        "primary",
        "official",
        "candidate",
        "official",
        "全国季度 GDP。",
        "",
        "",
        "quarterly",
        "official_page_parse",
        "pending",
        "pending",
        "官方公开数据，需确认字段口径。",
        1,
        "",
        "2026-04-26T00:00:00Z",
    ),
    (
        "gdp_real:nbs_gdp:primary",
        "gdp_real",
        "实际 GDP",
        "nbs_gdp",
        "国家统计局 GDP 数据",
        "primary",
        "official",
        "candidate",
        "official",
        "全国季度 GDP 实际增速。",
        "",
        "",
        "quarterly",
        "official_page_parse",
        "pending",
        "pending",
        "官方公开数据，需明确使用实际增速还是不变价金额。",
        1,
        "",
        "2026-04-26T00:00:00Z",
    ),
    (
        "gdp_gap:derived_gdp_gap:primary",
        "gdp_gap",
        "GDP 差值",
        "derived_gdp_gap",
        "本地派生计算",
        "primary",
        "derived",
        "candidate",
        "derived",
        "由名义 GDP 增速减实际 GDP 增速得到。",
        "",
        "",
        "quarterly",
        "derived_calculation",
        "ready",
        "not_needed",
        "依赖上游名义 GDP 和实际 GDP 数据质量。",
        1,
        "上游两个指标缺失时不可计算。",
        "2026-04-26T00:00:00Z",
    ),
    (
        "ppi:nbs_ppi:primary",
        "ppi",
        "企业 PPI",
        "nbs_ppi",
        "国家统计局 PPI 数据",
        "primary",
        "official",
        "candidate",
        "official",
        "工业生产者出厂价格指数。",
        "",
        "",
        "monthly",
        "official_page_parse",
        "pending",
        "pending",
        "官方公开数据。",
        1,
        "",
        "2026-04-26T00:00:00Z",
    ),
    (
        "household_new_loans:pbc_financial_statistics:primary",
        "household_new_loans",
        "居民新增贷款",
        "pbc_financial_statistics",
        "人民银行金融统计数据报告",
        "primary",
        "official",
        "candidate",
        "official",
        "住户部门新增贷款。",
        "",
        "",
        "monthly",
        "official_page_parse",
        "pending",
        "pending",
        "需解析月度报告中的住户部门贷款新增额。",
        1,
        "",
        "2026-04-26T00:00:00Z",
    ),
    (
        "household_loan_growth:pbc_loan_report:primary",
        "household_loan_growth",
        "居民贷款增速",
        "pbc_loan_report",
        "人民银行金融机构贷款投向统计报告",
        "primary",
        "official",
        "candidate",
        "official",
        "住户贷款余额同比增速。",
        "",
        "",
        "quarterly",
        "official_page_parse",
        "pending",
        "pending",
        "若只有季度口径，前端必须标注频率。",
        1,
        "",
        "2026-04-26T00:00:00Z",
    ),
    (
        "household_demand_deposit_growth:pbc_deposit_statistics_pending:primary",
        "household_demand_deposit_growth",
        "居民活期存款增速",
        "pbc_deposit_statistics_pending",
        "人民银行居民活期存款口径待确认",
        "primary",
        "official",
        "degraded",
        "official",
        "住户或个人活期存款同比增速。",
        "",
        "",
        "mixed",
        "official_page_parse",
        "blocked",
        "pending",
        "公开连续序列不稳定，需进一步确认。",
        1,
        "暂不硬造数据，只保留矩阵项和后续接入位置。",
        "2026-04-26T00:00:00Z",
    ),
)
