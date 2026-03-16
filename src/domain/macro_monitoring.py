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
            source_label="National Bureau of Statistics",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="Monthly release, typically around the middle of the month.",
            display_hint="Use headline inflation as the first consumer-price proxy.",
        ),
        MacroIndicatorDefinition(
            indicator_code="ppi",
            display_name="PPI",
            frequency=MacroFrequency.MONTHLY,
            unit="%",
            source_label="National Bureau of Statistics",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="Monthly release aligned with CPI updates.",
            display_hint="Track upstream price pressure and industrial margin trend.",
        ),
        MacroIndicatorDefinition(
            indicator_code="gdp_nominal",
            display_name="Nominal GDP",
            frequency=MacroFrequency.QUARTERLY,
            unit="tn yuan",
            source_label="National Bureau of Statistics",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="Quarterly release after quarter close.",
            display_hint="Prefer direct value plus growth context for dashboard cards.",
        ),
        MacroIndicatorDefinition(
            indicator_code="gdp_real",
            display_name="Real GDP",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="National Bureau of Statistics",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="Quarterly release with real-growth interpretation.",
            display_hint="Use growth figure and trend direction, not absolute output.",
        ),
        MacroIndicatorDefinition(
            indicator_code="social_financing",
            display_name="Social Financing",
            frequency=MacroFrequency.MONTHLY,
            unit="tn yuan",
            source_label="People's Bank of China",
            source_url="https://www.pbc.gov.cn/",
            provider_key="macro_official_primary",
            update_rule="Monthly release after financing data consolidation.",
            display_hint="Proxy for broad credit impulse and liquidity conditions.",
        ),
        MacroIndicatorDefinition(
            indicator_code="household_leverage",
            display_name="Household Leverage",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="National Institution Research",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_akshare_fallback",
            update_rule="Quarterly or periodic update depending on source availability.",
            display_hint="Show ratio and whether leverage pressure is rising or easing.",
        ),
        MacroIndicatorDefinition(
            indicator_code="government_leverage",
            display_name="Government Leverage",
            frequency=MacroFrequency.QUARTERLY,
            unit="%",
            source_label="National Institution Research",
            source_url="https://www.stats.gov.cn/",
            provider_key="macro_akshare_fallback",
            update_rule="Quarterly or periodic update depending on source availability.",
            display_hint="Track fiscal-balance pressure and policy space.",
        ),
    )

    return {definition.indicator_code: definition for definition in definitions}
