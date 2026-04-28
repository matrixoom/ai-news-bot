"""Macro 数据因子模块的领域模型。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MacroFactorDefinition:
    """描述一个 Macro 数据因子的展示、存储和来源配置。"""

    factor_code: str
    factor_label: str
    category: str
    description: str
    default_unit: str
    frequency: str
    source_key: str
    storage_table: str
    calculation_method: str
    display_order: int
    status: str


@dataclass(frozen=True)
class MacroSourceMatrixRow:
    """描述一个指标与一个数据来源之间的可用性关系。"""

    matrix_id: str
    factor_code: str
    factor_label: str
    source_key: str
    source_label: str
    source_role: str
    source_type: str
    availability_status: str
    reliability_level: str
    coverage_scope: str
    coverage_start: str
    coverage_end: str
    frequency: str
    access_method: str
    field_mapping_status: str
    parser_status: str
    license_note: str
    priority_order: int
    warning_message: str
    last_verified_at: str


@dataclass(frozen=True)
class MacroFactorSeriesPoint:
    """前端趋势图使用的单个时间序列点。"""

    period_end: str
    period_label: str
    value: float


@dataclass(frozen=True)
class MacroFactorSeries:
    """前端趋势图使用的一条数据因子序列。"""

    factor_code: str
    label: str
    unit: str
    frequency: str
    status: str
    source_label: str
    points: list[MacroFactorSeriesPoint] = field(default_factory=list)


@dataclass(frozen=True)
class MacroFactorTableRow:
    """前端数据表使用的单行历史数据。"""

    factor_code: str
    factor_label: str
    period_label: str
    dimension: str
    value: str
    unit: str
    source_label: str
    status: str
    updated_at: str


@dataclass(frozen=True)
class MacroSourceMatrixSummary:
    """数据源矩阵顶部汇总信息。"""

    factor_count: int
    source_count: int
    official_primary_count: int
    degraded_count: int
    unavailable_count: int
    last_verified_at: str


@dataclass(frozen=True)
class MacroDataFactorSnapshot:
    """Macro 数据因子模块供前端接口消费的完整快照。"""

    generated_at: str
    factors: list[MacroFactorDefinition]
    series: list[MacroFactorSeries]
    table_rows: list[MacroFactorTableRow]
    source_matrix_rows: list[MacroSourceMatrixRow]
    source_matrix_summary: MacroSourceMatrixSummary

