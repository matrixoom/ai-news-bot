"""Domain models for macro monitoring and grouped chart rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Dict, List


class MacroFrequency(StrEnum):
    """Supported release cadences for macro indicators."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class TrendDirection(StrEnum):
    """Simple trend directions for macro cards."""

    UP = "up"
    DOWN = "down"
    FLAT = "flat"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class MacroIndicatorDefinition:
    """Registry definition for one macro indicator."""

    indicator_code: str
    display_name: str
    frequency: MacroFrequency
    unit: str
    source_label: str
    source_url: str
    provider_key: str
    update_rule: str
    display_hint: str
    pair_key: str


@dataclass(frozen=True)
class MacroPairDefinition:
    """Grouped comparison panel definition for the frontend."""

    key: str
    title: str
    description: str
    primary_code: str
    secondary_code: str
    delta_label: str


@dataclass(frozen=True)
class MacroSeriesPointView:
    """Frontend-facing normalized point for one macro series."""

    period_end: str
    period_label: str
    value: float


@dataclass(frozen=True)
class MacroIndicatorView:
    """Dashboard-facing normalized macro indicator card."""

    key: str
    label: str
    value: str
    previous_value: str
    change_label: str
    trend: TrendDirection
    source_label: str
    source_url: str
    updated_at: str
    period_label: str
    frequency: MacroFrequency
    context: str
    unit: str
    pair_key: str
    status: str
    numeric_value: float | None = None
    history_points: List[MacroSeriesPointView] = field(default_factory=list)


@dataclass(frozen=True)
class MacroMonitoringSnapshot:
    """Top-level macro-monitoring snapshot."""

    generated_at: str
    indicators: List[MacroIndicatorView] = field(default_factory=list)


def build_default_macro_registry() -> Dict[str, MacroIndicatorDefinition]:
    """Return the default macro registry for the macro dashboard."""
    definitions = (
        MacroIndicatorDefinition(
            indicator_code="cpi",
            display_name="CPI",
            frequency=MacroFrequency.MONTHLY,
            unit="%",
            source_label="国家统计局",
            source_url="https://data.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按月更新，展示全国居民消费价格同比。",
            display_hint="用于观察居民消费价格压力。",
            pair_key="inflation",
        ),
        MacroIndicatorDefinition(
            indicator_code="ppi",
            display_name="PPI",
            frequency=MacroFrequency.MONTHLY,
            unit="%",
            source_label="国家统计局",
            source_url="https://data.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按月更新，展示工业生产者出厂价格同比。",
            display_hint="用于观察上游价格与工业利润压力。",
            pair_key="inflation",
        ),
        MacroIndicatorDefinition(
            indicator_code="gdp_nominal",
            display_name="名义 GDP 增速",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="国家统计局",
            source_url="https://data.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按季度更新，按现价季度 GDP 同比推导。",
            display_hint="和实际 GDP 增速的差值可视作价格因子。",
            pair_key="gdp",
        ),
        MacroIndicatorDefinition(
            indicator_code="gdp_real",
            display_name="实际 GDP 增速",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="国家统计局",
            source_url="https://data.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按季度更新，使用国家统计局 GDP 不变价指数。",
            display_hint="用于观察真实增长韧性。",
            pair_key="gdp",
        ),
        MacroIndicatorDefinition(
            indicator_code="household_new_loans",
            display_name="居民新增贷款",
            frequency=MacroFrequency.MONTHLY,
            unit="tn yuan",
            source_label="中国人民银行",
            source_url="https://www.pbc.gov.cn/diaochatongjisi/116219/116225/index.html",
            provider_key="macro_official_primary",
            update_rule="按月更新，由金融统计数据报告中的分部门累计增量拆分为单月值。",
            display_hint="观察居民端信用扩张与消费修复力度。",
            pair_key="credit",
        ),
        MacroIndicatorDefinition(
            indicator_code="enterprise_new_loans",
            display_name="企业新增贷款",
            frequency=MacroFrequency.MONTHLY,
            unit="tn yuan",
            source_label="中国人民银行",
            source_url="https://www.pbc.gov.cn/diaochatongjisi/116219/116225/index.html",
            provider_key="macro_official_primary",
            update_rule="按月更新，由金融统计数据报告中的分部门累计增量拆分为单月值。",
            display_hint="观察企业端融资需求和信用投放结构。",
            pair_key="credit",
        ),
        MacroIndicatorDefinition(
            indicator_code="household_leverage",
            display_name="居民杠杆率",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="中国人民银行 + 国家统计局",
            source_url="https://www.pbc.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按季度更新，使用住户贷款余额 / 滚动四季度名义 GDP 推导。",
            display_hint="口径为官方数据推导的贷款杠杆率代理。",
            pair_key="leverage",
        ),
        MacroIndicatorDefinition(
            indicator_code="enterprise_leverage",
            display_name="企业杠杆率",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="中国人民银行 + 国家统计局",
            source_url="https://www.pbc.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按季度更新，使用企事业单位贷款余额 / 滚动四季度名义 GDP 推导。",
            display_hint="口径为官方数据推导的贷款杠杆率代理。",
            pair_key="leverage",
        ),
    )
    return {definition.indicator_code: definition for definition in definitions}


def build_default_macro_pair_registry() -> Dict[str, MacroPairDefinition]:
    """Return the grouped macro comparison panels."""
    definitions = (
        MacroPairDefinition(
            key="inflation",
            title="CPI vs PPI",
            description="居民端与工业端通胀对比，差值反映上下游价格剪刀差。",
            primary_code="cpi",
            secondary_code="ppi",
            delta_label="CPI - PPI",
        ),
        MacroPairDefinition(
            key="gdp",
            title="名义 GDP vs 实际 GDP",
            description="名义与实际增速对比，差值可近似反映 GDP 平减指数方向。",
            primary_code="gdp_nominal",
            secondary_code="gdp_real",
            delta_label="名义 - 实际",
        ),
        MacroPairDefinition(
            key="credit",
            title="居民新增贷款 vs 企业新增贷款",
            description="居民和企业部门月度信用扩张对比，差值反映信用分布偏向。",
            primary_code="household_new_loans",
            secondary_code="enterprise_new_loans",
            delta_label="居民 - 企业",
        ),
        MacroPairDefinition(
            key="leverage",
            title="居民杠杆率 vs 企业杠杆率",
            description="官方贷款余额与滚动四季度名义 GDP 推导的季度杠杆率对比。",
            primary_code="household_leverage",
            secondary_code="enterprise_leverage",
            delta_label="居民 - 企业",
        ),
    )
    return {definition.key: definition for definition in definitions}
