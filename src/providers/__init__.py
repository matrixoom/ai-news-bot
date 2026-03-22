"""External data and API providers."""

from importlib import import_module

from .contracts import (
    MacroDataProvider,
    MarketDataProvider,
    NewsProvider,
    ProviderAvailability,
    ProviderStatus,
    ResearchProvider,
    SearchProvider,
)

__all__ = [
    "AkshareMacroDataProvider",
    "AkshareMarketDataProvider",
    "ArkResearchProvider",
    "CategoryStrategy",
    "CompositeNewsProvider",
    "FeasibilityLevel",
    "FallbackMacroProvider",
    "FallbackMarketDataProvider",
    "FallbackNewsProvider",
    "FallbackResearchProvider",
    "FallbackSearchProvider",
    "GoogleNewsSearchProvider",
    "MacroDataProvider",
    "MarketDataProvider",
    "NewsProvider",
    "NewsNowAggregatedNewsProvider",
    "NewsNowModeProvider",
    "NewsNowSourceMode",
    "ProviderAvailability",
    "ProviderConfigurationError",
    "ProviderStatus",
    "PublicRssNewsProvider",
    "ResearchProvider",
    "UnavailableResearchProvider",
    "SampleMacroProvider",
    "SampleMarketDataProvider",
    "SampleNewsProvider",
    "SampleSearchProvider",
    "SearchProvider",
    "SourcePlan",
    "StrategyCategory",
    "build_provider_strategy",
]

_MODULE_BY_EXPORT = {
    "AkshareMacroDataProvider": ".live_data",
    "AkshareMarketDataProvider": ".live_data",
    "ArkResearchProvider": ".live_data",
    "FallbackMacroProvider": ".live_data",
    "FallbackMarketDataProvider": ".live_data",
    "FallbackNewsProvider": ".live_data",
    "FallbackResearchProvider": ".live_data",
    "FallbackSearchProvider": ".live_data",
    "GoogleNewsSearchProvider": ".live_data",
    "ProviderConfigurationError": ".live_data",
    "PublicRssNewsProvider": ".live_data",
    "UnavailableResearchProvider": ".live_data",
    "CompositeNewsProvider": ".newsnow_provider",
    "NewsNowAggregatedNewsProvider": ".newsnow_provider",
    "NewsNowModeProvider": ".newsnow_provider",
    "NewsNowSourceMode": ".newsnow_provider",
    "SampleMacroProvider": ".sample_data",
    "SampleMarketDataProvider": ".sample_data",
    "SampleNewsProvider": ".sample_data",
    "SampleSearchProvider": ".sample_data",
    "CategoryStrategy": ".strategy",
    "FeasibilityLevel": ".strategy",
    "SourcePlan": ".strategy",
    "StrategyCategory": ".strategy",
    "build_provider_strategy": ".strategy",
}


def __getattr__(name: str):
    module_name = _MODULE_BY_EXPORT.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
