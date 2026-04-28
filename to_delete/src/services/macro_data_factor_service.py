"""Macro 数据因子和数据源矩阵的业务服务。"""

from __future__ import annotations

from datetime import UTC, datetime

from ..domain.macro_data_factors import (
    MacroDataFactorSnapshot,
    MacroFactorDefinition,
    MacroFactorSeries,
    MacroFactorTableRow,
    MacroSourceMatrixSummary,
)
from .macro_data_factor_store import MacroDataFactorStore


class MacroDataFactorService:
    """组装 Macro 数据因子模块的前端快照。"""

    def __init__(self, store: MacroDataFactorStore | None = None) -> None:
        self._store = store or MacroDataFactorStore()

    def build_snapshot(self, *, generated_at: str | None = None) -> MacroDataFactorSnapshot:
        """构建包含数据因子、来源矩阵和真实空观测状态的快照。"""

        timestamp = generated_at or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        factors = self._store.list_factor_definitions()
        source_rows = self._store.list_source_matrix_rows()
        return MacroDataFactorSnapshot(
            generated_at=timestamp,
            factors=factors,
            series=self._build_empty_series(factors),
            table_rows=self._build_empty_table_rows(factors),
            source_matrix_rows=source_rows,
            source_matrix_summary=MacroSourceMatrixSummary(
                factor_count=len({row.factor_code for row in source_rows}),
                source_count=len({row.source_key for row in source_rows}),
                official_primary_count=sum(
                    1
                    for row in source_rows
                    if row.source_role == "primary" and row.source_type == "official"
                ),
                degraded_count=sum(1 for row in source_rows if row.availability_status == "degraded"),
                unavailable_count=sum(1 for row in source_rows if row.availability_status == "unavailable"),
                last_verified_at=max((row.last_verified_at for row in source_rows), default=""),
            ),
        )

    def _build_empty_series(self, factors: list[MacroFactorDefinition]) -> list[MacroFactorSeries]:
        """在真实采集器接入前返回无观测点的因子序列。"""

        return [
            MacroFactorSeries(
                factor_code=factor.factor_code,
                label=factor.factor_label,
                unit=factor.default_unit,
                frequency=factor.frequency,
                status=factor.status,
                source_label=self._source_label_for_factor(factor),
                points=[],
            )
            for factor in factors
        ]

    def _build_empty_table_rows(self, factors: list[MacroFactorDefinition]) -> list[MacroFactorTableRow]:
        """在真实采集器接入前返回明确标记暂无数据的表格行。"""

        rows: list[MacroFactorTableRow] = []
        for factor in factors:
            rows.append(
                MacroFactorTableRow(
                    factor_code=factor.factor_code,
                    factor_label=factor.factor_label,
                    period_label="暂无数据",
                    dimension="全国" if factor.category != "housing" else "全国 / 新房同比",
                    value="暂无数据",
                    unit=factor.default_unit,
                    source_label=self._source_label_for_factor(factor),
                    status=factor.status,
                    updated_at="2026-04-26T00:00:00Z",
                )
            )
        return rows

    def _source_label_for_factor(self, factor: MacroFactorDefinition) -> str:
        """根据因子编码返回第一阶段展示用来源名称。"""

        labels = {
            "housing_price": "国家统计局 70 城商品住宅销售价格指数",
            "gdp_nominal": "国家统计局 GDP 数据",
            "gdp_real": "国家统计局 GDP 数据",
            "gdp_gap": "本地派生计算",
            "ppi": "国家统计局 PPI 数据",
            "household_new_loans": "人民银行金融统计数据报告",
            "household_loan_growth": "人民银行金融机构贷款投向统计报告",
            "household_demand_deposit_growth": "人民银行居民活期存款口径待确认",
        }
        return labels.get(factor.factor_code, factor.source_key)
