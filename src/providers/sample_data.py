"""Sample providers used for local dashboard and integration tests."""
from datetime import date

from ..domain.external_data import (
    ConfidenceLevel,
    EventHorizon,
    MacroIndicatorReading,
    MarketIndexSnapshot,
    NewsCategory,
    NewsItem,
    ResearchFinding,
    SearchResultItem,
    SourceReference,
)
from .contracts import ProviderAvailability, ProviderStatus


class SampleNewsProvider:
    provider_key = "sample-news"

    def __init__(self) -> None:
        today = date.today().isoformat()
        self._items = {
            NewsCategory.TECHNOLOGY: (
                NewsItem(self.provider_key, "OpenAI Blog", NewsCategory.TECHNOLOGY, "Workflow agents move into production rollouts", "https://openai.example/agents", f"{today}T08:00:00Z", "Official note on production agents."),
                NewsItem(self.provider_key, "TechCrunch AI", NewsCategory.TECHNOLOGY, "Chip vendors expand AI inference capacity plans", "https://tech.example/chips", f"{today}T09:15:00Z", "Capacity and inference capex remain elevated."),
            ),
            NewsCategory.FINANCE: (
                NewsItem(self.provider_key, "Reuters Finance", NewsCategory.FINANCE, "Liquidity conditions remain the macro market pivot", "https://finance.example/liquidity", f"{today}T07:40:00Z", "Markets still anchor on liquidity and growth mix."),
                NewsItem(self.provider_key, "Bloomberg Markets", NewsCategory.FINANCE, "Positioning turns selective ahead of data-heavy weeks", "https://finance.example/positioning", f"{today}T10:00:00Z", "Cross-asset positioning remains selective."),
            ),
            NewsCategory.POLICY: (
                NewsItem(self.provider_key, "State Council", NewsCategory.POLICY, "Policy work plan highlights industrial and credit coordination", "https://policy.example/workplan", f"{today}T08:20:00Z", "Official work plan and coordination themes."),
                NewsItem(self.provider_key, "Xinhua", NewsCategory.POLICY, "Officials signal stable macro policy execution window", "https://policy.example/execution", f"{today}T11:00:00Z", "Policy execution remains the core watchpoint."),
            ),
        }

    def fetch_latest(self, *, category, published_on, limit):
        return list(self._items.get(category, ()))[:limit]

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "sample data", "2026-03-15T00:00:00Z")


class SampleSearchProvider:
    provider_key = "sample-search"

    def __init__(self) -> None:
        today = date.today().isoformat()
        self._items = {
            "AI platform release today": (
                SearchResultItem(self.provider_key, "AI platform release today", "Workflow agents move into production rollouts", "Search corroboration", "https://theverge.example/agents", None),
            ),
            "macro market liquidity today": (
                SearchResultItem(self.provider_key, "macro market liquidity today", "Liquidity conditions remain the macro market pivot", "Search corroboration", "https://markets.example/liquidity", f"{today}T10:30:00Z"),
            ),
            "policy briefing today": (
                SearchResultItem(self.provider_key, "policy briefing today", "Policy work plan highlights industrial and credit coordination", "Search corroboration", "https://xinhua.example/workplan", None),
            ),
        }

    def search(self, *, query, published_on, limit):
        return list(self._items.get(query, ()))[:limit]

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "sample data", "2026-03-15T00:00:00Z")


class SampleMacroProvider:
    provider_key = "sample-macro"

    def fetch_latest_readings(self, *, indicator_codes):
        sample_map = {
            "cpi": MacroIndicatorReading(self.provider_key, "cpi", "CPI", 0.3, "%", "2026-02", "2026-03-09", "https://www.stats.gov.cn/", previous_value=0.1, change_value=0.2, change_kind="MoM", trend_summary="Inflation pressure edged up slightly."),
            "ppi": MacroIndicatorReading(self.provider_key, "ppi", "PPI", -1.2, "%", "2026-02", "2026-03-09", "https://www.stats.gov.cn/", previous_value=-1.5, change_value=0.3, change_kind="MoM", trend_summary="Industrial price contraction is easing."),
            "gdp_nominal": MacroIndicatorReading(self.provider_key, "gdp_nominal", "Nominal GDP", 33.4, "tn yuan", "2026-Q1", "2026-04-18", "https://www.stats.gov.cn/", previous_value=31.8, change_value=1.6, change_kind="vs prior quarter", trend_summary="Nominal output remains on a moderate uptrend."),
            "gdp_real": MacroIndicatorReading(self.provider_key, "gdp_real", "Real GDP", 4.9, "%", "2026-Q1", "2026-04-18", "https://www.stats.gov.cn/", previous_value=4.8, change_value=0.1, change_kind="YoY", trend_summary="Real growth is broadly stable."),
            "social_financing": MacroIndicatorReading(self.provider_key, "social_financing", "Social Financing", 9.4, "tn yuan", "2026-02", "2026-03-14", "https://www.pbc.gov.cn/", previous_value=8.9, change_value=0.5, change_kind="vs prior month", trend_summary="Credit impulse is improving modestly."),
            "household_leverage": MacroIndicatorReading(self.provider_key, "household_leverage", "Household Leverage", 62.1, "%", "2025-Q4", "2026-02-20", "https://www.stats.gov.cn/", previous_value=61.7, change_value=0.4, change_kind="vs prior quarter", trend_summary="Leverage pressure is still drifting higher."),
        }
        return [sample_map[code] for code in indicator_codes if code in sample_map]

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "sample data", "2026-03-15T00:00:00Z")


class SampleMarketDataProvider:
    provider_key = "sample-market"

    def fetch_index_snapshots(self, *, symbols, trade_date: date):
        history = {
            "CSI300": (3590.0, 3588.0, 3592.0, 3595.0, 3597.0, 3600.0, 3602.0, 3605.0, 3604.0, 3606.0, 3608.0, 3610.0, 3611.0, 3613.0, 3615.0, 3616.0, 3618.0, 3620.0, 3621.0),
            "CSI500": (5470.0, 5472.0, 5475.0, 5478.0, 5480.0, 5482.0, 5485.0, 5484.0, 5486.0, 5488.0, 5490.0, 5492.0, 5494.0, 5495.0, 5498.0, 5500.0, 5502.0, 5505.0, 5507.0),
            "CSI1000": (6070.0, 6073.0, 6075.0, 6078.0, 6080.0, 6082.0, 6084.0, 6086.0, 6088.0, 6090.0, 6093.0, 6095.0, 6096.0, 6098.0, 6100.0, 6103.0, 6105.0, 6107.0, 6109.0),
            "SSE": (3050.0, 3052.0, 3051.0, 3053.0, 3054.0, 3056.0, 3058.0, 3057.0, 3059.0, 3060.0, 3062.0, 3064.0, 3065.0, 3067.0, 3068.0, 3070.0, 3072.0, 3073.0, 3075.0),
            "CHINEXT": (1880.0, 1882.0, 1884.0, 1886.0, 1888.0, 1889.0, 1891.0, 1893.0, 1892.0, 1894.0, 1896.0, 1898.0, 1899.0, 1901.0, 1902.0, 1904.0, 1906.0, 1907.0, 1909.0),
            "HSTECH": (3810.0, 3814.0, 3818.0, 3822.0, 3825.0, 3829.0, 3833.0, 3838.0, 3840.0, 3844.0, 3849.0, 3852.0, 3855.0, 3858.0, 3862.0, 3865.0, 3868.0, 3871.0, 3874.0),
        }
        current = {
            "CSI300": 3632.0,
            "CSI500": 5528.0,
            "CSI1000": 6124.0,
            "SSE": 3084.0,
            "CHINEXT": 1918.0,
        }
        snapshots = []
        for symbol in symbols:
            if symbol not in current:
                continue
            snapshots.append(
                MarketIndexSnapshot(
                    provider=self.provider_key,
                    symbol=symbol,
                    display_name=symbol,
                    trade_date=trade_date,
                    close_price=current[symbol],
                    currency="CNY",
                    source_url="https://akshare.akfamily.xyz/",
                    lookback_closes=history[symbol],
                )
            )
        return snapshots

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "sample data", "2026-03-15T00:00:00Z")


class SampleResearchProvider:
    provider_key = "sample-research"

    def collect_outlook(self, *, horizon, topics, as_of):
        data = {
            EventHorizon.NEXT_7_DAYS: (
                ResearchFinding(self.provider_key, horizon, "Central-bank communication window", "CN", "2026-03-20", "A policy communication window may reset liquidity expectations.", ConfidenceLevel.MEDIUM, (SourceReference("Official calendar", "https://calendar.example/cb"),)),
                ResearchFinding(self.provider_key, horizon, "Unattributed rumor event", "CN", "2026-03-18", "This item should be filtered.", ConfidenceLevel.LOW, (SourceReference("Weak source", "https://rumor.example"),)),
            ),
            EventHorizon.NEXT_30_DAYS: (
                ResearchFinding(self.provider_key, horizon, "Quarter-end macro release cluster", "CN", "2026-04-15", "Inflation, credit, and growth releases arrive in a concentrated window.", ConfidenceLevel.HIGH, (SourceReference("NBS calendar", "https://calendar.example/nbs"),)),
            ),
            EventHorizon.NEXT_90_DAYS: (
                ResearchFinding(self.provider_key, horizon, "Policy implementation checkpoint", "CN", "2026-05-30", "Implementation deadlines may drive sector-level policy follow-through.", ConfidenceLevel.MEDIUM, (SourceReference("Official agenda", "https://calendar.example/policy"),)),
            ),
            EventHorizon.NEXT_180_DAYS: (
                ResearchFinding(self.provider_key, horizon, "Mid-year policy review", "CN", "2026-08-30", "Mid-year policy review could recalibrate fiscal and credit priorities.", ConfidenceLevel.HIGH, (SourceReference("Official schedule", "https://calendar.example/review"),)),
            ),
        }
        return list(data.get(horizon, ()))

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "sample data", "2026-03-15T00:00:00Z")
