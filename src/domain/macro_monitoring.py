"""Domain models for macro monitoring and grouped chart rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Dict, List


class MacroFrequency(StrEnum):
    """Supported release cadences for macro indicators."""

    DAILY = "daily"
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
    secondary_code: str | None = None
    delta_label: str = ""


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
            display_name="居民消费价格指数（CPI）",
            frequency=MacroFrequency.MONTHLY,
            unit="%",
            source_label="国家统计局",
            source_url="https://data.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按国家统计局月度同比口径更新。",
            display_hint="用于观察居民端通胀压力变化。",
            pair_key="inflation",
        ),
        MacroIndicatorDefinition(
            indicator_code="ppi",
            display_name="工业生产者出厂价格指数（PPI）",
            frequency=MacroFrequency.MONTHLY,
            unit="%",
            source_label="国家统计局",
            source_url="https://data.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按国家统计局月度同比口径更新。",
            display_hint="用于观察上游工业价格压力。",
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
            update_rule="基于国家统计局季度 GDP 名义值推导同比增速。",
            display_hint="与实际 GDP 对比后，可近似观察 GDP 平减指数变化。",
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
            update_rule="按国家统计局季度 GDP 同比口径更新。",
            display_hint="用于观察经济实际增长周期。",
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
            update_rule="基于人民银行金融统计数据报告推导月度增量。",
            display_hint="用于观察居民信用扩张与消费修复节奏。",
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
            update_rule="基于人民银行金融统计数据报告推导月度增量。",
            display_hint="用于观察企业融资需求与信用投放方向。",
            pair_key="credit",
        ),
        MacroIndicatorDefinition(
            indicator_code="household_leverage",
            display_name="居民杠杆率",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="人民银行 + 国家统计局",
            source_url="https://www.pbc.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按居民贷款余额 / 滚动四季度名义 GDP 计算。",
            display_hint="基于官方贷款余额和 GDP 构造的居民杠杆率代理指标。",
            pair_key="leverage",
        ),
        MacroIndicatorDefinition(
            indicator_code="enterprise_leverage",
            display_name="企业杠杆率",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="人民银行 + 国家统计局",
            source_url="https://www.pbc.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="按企业贷款余额 / 滚动四季度名义 GDP 计算。",
            display_hint="基于官方贷款余额和 GDP 构造的企业杠杆率代理指标。",
            pair_key="leverage",
        ),
        MacroIndicatorDefinition(
            indicator_code="usd_cny",
            display_name="人民币兑美元中间价",
            frequency=MacroFrequency.DAILY,
            unit="CNY/USD",
            source_label="国家外汇管理局",
            source_url="https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do",
            provider_key="macro_official_primary",
            update_rule="按国家外汇管理局人民币汇率中间价中“美元”栏更新，并换算为每 1 美元对应人民币价格。",
            display_hint="使用官方中间价口径，不再混用其他站点页面抓取值。",
            pair_key="fx",
        ),
        MacroIndicatorDefinition(
            indicator_code="gold_price",
            display_name="黄金价格",
            frequency=MacroFrequency.MONTHLY,
            unit="USD/troy oz",
            source_label="世界银行 Pink Sheet",
            source_url="https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
            provider_key="macro_official_primary",
            update_rule="按世界银行 Pink Sheet 月度商品价格表更新。",
            display_hint="采用世界银行月度黄金美元价格序列。",
            pair_key="gold_oil",
        ),
        MacroIndicatorDefinition(
            indicator_code="oil_price",
            display_name="WTI 原油价格",
            frequency=MacroFrequency.MONTHLY,
            unit="USD/bbl",
            source_label="世界银行 Pink Sheet",
            source_url="https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
            provider_key="macro_official_primary",
            update_rule="按世界银行 Pink Sheet 月度商品价格表更新。",
            display_hint="采用世界银行月度 WTI 原油价格序列。",
            pair_key="gold_oil",
        ),
        MacroIndicatorDefinition(
            indicator_code="us_10y_yield",
            display_name="美国 10 年期国债收益率",
            frequency=MacroFrequency.DAILY,
            unit="pct",
            source_label="美国财政部",
            source_url="https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve",
            provider_key="macro_official_primary",
            update_rule="按美国财政部日度国债收益率曲线数据更新。",
            display_hint="跟踪美国 10 年期常数期限国债收益率。",
            pair_key="us_10y_yield",
        ),
        MacroIndicatorDefinition(
            indicator_code="us_credit_spread",
            display_name="美国信用利差",
            frequency=MacroFrequency.MONTHLY,
            unit="pct",
            source_label="美国财政部 HQM",
            source_url="https://home.treasury.gov/data/treasury-coupon-issues-and-corporate-bond-yield-curve/corporate-bond-yield-curve",
            provider_key="macro_official_primary",
            update_rule="按美国财政部 HQM 10 年期企业债收益率减去美国国债 10 年期月均收益率计算。",
            display_hint="使用财政部 HQM 企业债曲线构造高等级信用利差代理指标。",
            pair_key="us_credit_spread",
        ),
        MacroIndicatorDefinition(
            indicator_code="copper_gold_ratio",
            display_name="铜金比",
            frequency=MacroFrequency.MONTHLY,
            unit="ratio",
            source_label="世界银行 Pink Sheet",
            source_url="https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
            provider_key="macro_official_primary",
            update_rule="按月度铜价换算为磅后除以月度金价计算。",
            display_hint="铜价先从吨价换算为磅价，再与金价计算比值。",
            pair_key="copper_gold_ratio",
        ),
        MacroIndicatorDefinition(
            indicator_code="nvidia_stock_price",
            display_name="英伟达股价",
            frequency=MacroFrequency.DAILY,
            unit="USD",
            source_label="Nasdaq",
            source_url="https://www.nasdaq.com/market-activity/stocks/nvda/historical",
            provider_key="macro_official_primary",
            update_rule="按 Nasdaq 官方历史行情接口收盘价更新。",
            display_hint="用于跟踪 NVDA 日度收盘价。",
            pair_key="nvidia_stock_price",
        ),
    )
    return {definition.indicator_code: definition for definition in definitions}


def build_default_macro_pair_registry() -> Dict[str, MacroPairDefinition]:
    """Return the grouped macro comparison panels."""
    definitions = (
        MacroPairDefinition(
            key="inflation",
            title="CPI 与 PPI",
            description="观察居民端通胀与工业品价格的分化方向。",
            primary_code="cpi",
            secondary_code="ppi",
            delta_label="CPI - PPI",
        ),
        MacroPairDefinition(
            key="gdp",
            title="名义 GDP 与实际 GDP",
            description="观察名义增长与实际增长的剪刀差。",
            primary_code="gdp_nominal",
            secondary_code="gdp_real",
            delta_label="名义 - 实际",
        ),
        MacroPairDefinition(
            key="credit",
            title="居民新增贷款与企业新增贷款",
            description="对比居民与企业信贷投放节奏。",
            primary_code="household_new_loans",
            secondary_code="enterprise_new_loans",
            delta_label="居民 - 企业",
        ),
        MacroPairDefinition(
            key="leverage",
            title="居民杠杆率与企业杠杆率",
            description="对比居民与企业部门杠杆变化。",
            primary_code="household_leverage",
            secondary_code="enterprise_leverage",
            delta_label="居民 - 企业",
        ),
        MacroPairDefinition(
            key="gold_oil",
            title="黄金与原油",
            description="在同一张图中比较黄金与 WTI 原油月度走势。",
            primary_code="gold_price",
            secondary_code="oil_price",
            delta_label="黄金 - 原油",
        ),
        MacroPairDefinition(
            key="fx",
            title="人民币兑美元",
            description="跟踪官方人民币兑美元中间价走势。",
            primary_code="usd_cny",
        ),
        MacroPairDefinition(
            key="us_10y_yield",
            title="美国 10 年期国债收益率",
            description="跟踪美国长端无风险利率变化。",
            primary_code="us_10y_yield",
        ),
        MacroPairDefinition(
            key="us_credit_spread",
            title="美国信用利差",
            description="观察高等级企业债相对国债的利差变化。",
            primary_code="us_credit_spread",
        ),
        MacroPairDefinition(
            key="copper_gold_ratio",
            title="铜金比",
            description="用铜金比刻画增长预期与避险偏好的相对强弱。",
            primary_code="copper_gold_ratio",
        ),
        MacroPairDefinition(
            key="nvidia_stock_price",
            title="英伟达股价",
            description="跟踪 NVDA 日度收盘价走势。",
            primary_code="nvidia_stock_price",
        ),
    )
    return {definition.key: definition for definition in definitions}
