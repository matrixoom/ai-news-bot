"""Domain models for macro-indicator monitoring."""
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
    updated_at: str
    frequency: MacroFrequency
    context: str
    status: str


@dataclass(frozen=True)
class MacroMonitoringSnapshot:
    """Top-level macro-monitoring snapshot."""

    generated_at: str
    indicators: List[MacroIndicatorView] = field(default_factory=list)


def build_default_macro_registry() -> Dict[str, MacroIndicatorDefinition]:
    """Return the default macro registry for Task 05."""
    definitions = (
        MacroIndicatorDefinition(
            indicator_code="cpi",
            display_name="CPI",
            frequency=MacroFrequency.MONTHLY,
            unit="%",
            source_label="国家统计局",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按月发布，通常在月中前后更新。",
            display_hint="用于观察居民消费价格的总体变化。",
        ),
        MacroIndicatorDefinition(
            indicator_code="ppi",
            display_name="PPI",
            frequency=MacroFrequency.MONTHLY,
            unit="%",
            source_label="国家统计局",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按月发布，通常与 CPI 同期更新。",
            display_hint="用于跟踪上游价格压力和工业利润趋势。",
        ),
        MacroIndicatorDefinition(
            indicator_code="gdp_nominal",
            display_name="名义 GDP 增速",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="国家统计局",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按季度发布，通常随季度 GDP 数据一并更新。",
            display_hint="与实际 GDP 一致，使用增速口径展示名义增长变化。",
        ),
        MacroIndicatorDefinition(
            indicator_code="gdp_real",
            display_name="实际 GDP",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="国家统计局",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按季度发布，重点观察实际增速变化。",
            display_hint="优先展示增速与方向，而不是绝对产出规模。",
        ),
        MacroIndicatorDefinition(
            indicator_code="social_financing",
            display_name="社会融资规模",
            frequency=MacroFrequency.MONTHLY,
            unit="tn yuan",
            source_label="中国人民银行",
            source_url="https://www.pbc.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按月发布，通常在融资数据汇总后更新。",
            display_hint="可作为广义信用脉冲和流动性环境的代理指标。",
        ),
        MacroIndicatorDefinition(
            indicator_code="household_leverage",
            display_name="居民杠杆率",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="机构研究",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_akshare_fallback",
            update_rule="按季度或阶段性更新，取决于数据源可用性。",
            display_hint="展示杠杆率水平及其压力是上升还是缓和。",
        ),
        MacroIndicatorDefinition(
            indicator_code="government_leverage",
            display_name="政府杠杆率",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="机构研究",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_akshare_fallback",
            update_rule="按季度或阶段性更新，取决于数据源可用性。",
            display_hint="用于跟踪财政平衡压力与政策空间。",
        ),
    )

    return {definition.indicator_code: definition for definition in definitions}
