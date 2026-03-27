"""Sample providers used for local dashboard and integration tests."""

from __future__ import annotations

from datetime import date, timedelta

from ..domain.external_data import (
    MacroHistoryPoint,
    MacroIndicatorReading,
    MacroIndicatorSeries,
    MarketIndexHistoryPoint,
    MarketIndexSnapshot,
    NewsCategory,
    NewsItem,
    SearchResultItem,
)
from .contracts import ProviderAvailability, ProviderStatus


class SampleNewsProvider:
    provider_key = "sample-news"

    def __init__(self) -> None:
        today = date.today().isoformat()
        self._items = {
            NewsCategory.TECHNOLOGY: (
                NewsItem(
                    self.provider_key,
                    "OpenAI Blog",
                    NewsCategory.TECHNOLOGY,
                    "Workflow agents are moving into production environments",
                    "https://openai.example/agents",
                    f"{today}T08:00:00Z",
                    "Official notes suggest agentic production patterns are accelerating.",
                ),
                NewsItem(
                    self.provider_key,
                    "TechCrunch AI",
                    NewsCategory.TECHNOLOGY,
                    "Chip vendors continue expanding AI inference capacity",
                    "https://tech.example/chips",
                    f"{today}T09:15:00Z",
                    "Inference capacity and related capex remain elevated.",
                ),
            ),
            NewsCategory.FINANCE: (
                NewsItem(
                    self.provider_key,
                    "Reuters Finance",
                    NewsCategory.FINANCE,
                    "Liquidity conditions remain central to macro pricing",
                    "https://finance.example/liquidity",
                    f"{today}T07:40:00Z",
                    "Markets continue to price around liquidity and growth mix.",
                ),
                NewsItem(
                    self.provider_key,
                    "Bloomberg Markets",
                    NewsCategory.FINANCE,
                    "Positioning turns more cautious before a dense data week",
                    "https://finance.example/positioning",
                    f"{today}T10:00:00Z",
                    "Cross-asset positioning remains selective.",
                ),
            ),
            NewsCategory.POLICY: (
                NewsItem(
                    self.provider_key,
                    "State Council",
                    NewsCategory.POLICY,
                    "Policy plan emphasizes industrial and credit coordination",
                    "https://policy.example/workplan",
                    f"{today}T08:20:00Z",
                    "The official work plan continues to stress coordinated support.",
                ),
                NewsItem(
                    self.provider_key,
                    "Xinhua",
                    NewsCategory.POLICY,
                    "Official communication reinforces steady macro execution",
                    "https://policy.example/execution",
                    f"{today}T11:00:00Z",
                    "Execution rhythm remains a core policy watchpoint.",
                ),
            ),
        }

    def fetch_latest(self, *, category, published_on, limit):
        _ = published_on
        return list(self._items.get(category, ()))[:limit]

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "sample data", "2026-03-15T00:00:00Z")


class SampleSearchProvider:
    provider_key = "sample-search"

    def __init__(self) -> None:
        today = date.today().isoformat()
        self._items = {
            "AI platform release today": (
                SearchResultItem(
                    self.provider_key,
                    "AI platform release today",
                    "Workflow agents are moving into production environments",
                    "Search-side low-latency backfill",
                    "https://theverge.example/agents",
                    None,
                ),
            ),
            "macro market liquidity today": (
                SearchResultItem(
                    self.provider_key,
                    "macro market liquidity today",
                    "Liquidity conditions remain central to macro pricing",
                    "Search-side low-latency backfill",
                    "https://markets.example/liquidity",
                    f"{today}T10:30:00Z",
                ),
            ),
            "policy briefing today": (
                SearchResultItem(
                    self.provider_key,
                    "policy briefing today",
                    "Policy plan emphasizes industrial and credit coordination",
                    "Search-side low-latency backfill",
                    "https://xinhua.example/workplan",
                    None,
                ),
            ),
        }

    def search(self, *, query, published_on, limit):
        _ = published_on
        return list(self._items.get(query, ()))[:limit]

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "sample data", "2026-03-15T00:00:00Z")


class SampleMacroProvider:
    provider_key = "sample-macro"

    def fetch_history_series(self, *, indicator_codes, start_date):
        _ = start_date
        monthly_periods = [
            ("2025-03", date(2025, 3, 31)),
            ("2025-04", date(2025, 4, 30)),
            ("2025-05", date(2025, 5, 31)),
            ("2025-06", date(2025, 6, 30)),
            ("2025-07", date(2025, 7, 31)),
            ("2025-08", date(2025, 8, 31)),
            ("2025-09", date(2025, 9, 30)),
            ("2025-10", date(2025, 10, 31)),
            ("2025-11", date(2025, 11, 30)),
            ("2025-12", date(2025, 12, 31)),
            ("2026-01", date(2026, 1, 31)),
            ("2026-02", date(2026, 2, 28)),
        ]
        quarterly_periods = [
            ("2024-Q4", date(2024, 12, 31)),
            ("2025-Q1", date(2025, 3, 31)),
            ("2025-Q2", date(2025, 6, 30)),
            ("2025-Q3", date(2025, 9, 30)),
            ("2025-Q4", date(2025, 12, 31)),
        ]
        daily_periods = [
            ("2026-03-11", date(2026, 3, 11)),
            ("2026-03-12", date(2026, 3, 12)),
            ("2026-03-13", date(2026, 3, 13)),
            ("2026-03-16", date(2026, 3, 16)),
            ("2026-03-17", date(2026, 3, 17)),
            ("2026-03-18", date(2026, 3, 18)),
            ("2026-03-19", date(2026, 3, 19)),
            ("2026-03-20", date(2026, 3, 20)),
            ("2026-03-23", date(2026, 3, 23)),
            ("2026-03-24", date(2026, 3, 24)),
            ("2026-03-25", date(2026, 3, 25)),
        ]
        series_specs = {
            "cpi": {
                "periods": monthly_periods,
                "values": [-0.4, -0.1, 0.2, 0.1, 0.3, 0.4, 0.6, 0.5, 0.4, 0.3, 0.1, 0.3],
                "display_name": "CPI",
                "unit": "%",
                "source_url": "https://www.stats.gov.cn/",
                "released_at": "2026-03-09",
            },
            "ppi": {
                "periods": monthly_periods,
                "values": [-2.7, -2.5, -2.2, -1.9, -1.7, -1.6, -1.5, -1.4, -1.4, -1.3, -1.5, -1.2],
                "display_name": "PPI",
                "unit": "%",
                "source_url": "https://www.stats.gov.cn/",
                "released_at": "2026-03-09",
            },
            "household_new_loans": {
                "periods": monthly_periods,
                "values": [-0.18, 0.21, 0.42, 0.37, 0.44, 0.31, 0.29, 0.35, 0.41, 0.22, -0.08, -0.19],
                "display_name": "Household New Loans",
                "unit": "tn yuan",
                "source_url": "https://www.pbc.gov.cn/",
                "released_at": "2026-03-14",
            },
            "enterprise_new_loans": {
                "periods": monthly_periods,
                "values": [3.10, 1.82, 1.54, 1.38, 1.61, 1.45, 1.58, 1.63, 1.49, 1.82, 2.31, 2.97],
                "display_name": "Enterprise New Loans",
                "unit": "tn yuan",
                "source_url": "https://www.pbc.gov.cn/",
                "released_at": "2026-03-14",
            },
            "gdp_nominal": {
                "periods": quarterly_periods,
                "values": [4.6, 4.9, 5.0, 5.2, 5.5],
                "display_name": "Nominal GDP Growth",
                "unit": "%",
                "source_url": "https://www.stats.gov.cn/",
                "released_at": "2026-01-17",
            },
            "gdp_real": {
                "periods": quarterly_periods,
                "values": [4.8, 5.0, 5.1, 5.0, 4.9],
                "display_name": "Real GDP Growth",
                "unit": "%",
                "source_url": "https://www.stats.gov.cn/",
                "released_at": "2026-01-17",
            },
            "household_leverage": {
                "periods": quarterly_periods,
                "values": [58.7, 59.4, 60.2, 61.0, 61.8],
                "display_name": "Household Leverage",
                "unit": "%",
                "source_url": "https://www.pbc.gov.cn/",
                "released_at": "2026-01-17",
            },
            "enterprise_leverage": {
                "periods": quarterly_periods,
                "values": [131.5, 132.0, 132.6, 133.1, 133.8],
                "display_name": "Enterprise Leverage",
                "unit": "%",
                "source_url": "https://www.pbc.gov.cn/",
                "released_at": "2026-01-17",
            },
            "usd_cny": {
                "periods": daily_periods,
                "values": [7.2441, 7.2387, 7.2308, 7.2261, 7.2142, 7.2054, 7.2120, 7.1988, 7.1876, 7.1819, 7.1764],
                "display_name": "USD/CNY",
                "unit": "CNY/USD",
                "source_url": "https://www.federalreserve.gov/RELEASES/H10/hist/dat00_ch.htm",
                "released_at": "2026-03-25",
            },
            "gold_price": {
                "periods": monthly_periods,
                "values": [2325.4, 2358.9, 2411.6, 2442.8, 2488.2, 2551.3, 2664.5, 2738.9, 2792.4, 2864.7, 3011.8, 3128.6],
                "display_name": "Gold",
                "unit": "USD/troy oz",
                "source_url": "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
                "released_at": "2026-03-03",
            },
            "oil_price": {
                "periods": monthly_periods,
                "values": [81.2, 79.4, 78.1, 76.8, 75.9, 74.3, 71.5, 69.8, 67.4, 63.9, 61.7, 64.6],
                "display_name": "WTI Crude",
                "unit": "USD/bbl",
                "source_url": "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
                "released_at": "2026-03-03",
            },
            "us_10y_yield": {
                "periods": daily_periods,
                "values": [4.28, 4.24, 4.21, 4.18, 4.16, 4.14, 4.20, 4.27, 4.31, 4.39, 4.33],
                "display_name": "US 10Y Treasury",
                "unit": "pct",
                "source_url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve",
                "released_at": "2026-03-25",
            },
            "us_credit_spread": {
                "periods": monthly_periods,
                "values": [0.92, 0.95, 0.98, 1.01, 0.97, 0.93, 0.90, 0.88, 0.91, 0.94, 0.99, 1.04],
                "display_name": "US Credit Spread",
                "unit": "pct",
                "source_url": "https://home.treasury.gov/data/treasury-coupon-issues-and-corporate-bond-yield-curve/corporate-bond-yield-curve",
                "released_at": "2026-03-03",
            },
            "copper_gold_ratio": {
                "periods": monthly_periods,
                "values": [0.00171, 0.00168, 0.00166, 0.00165, 0.00161, 0.00158, 0.00154, 0.00149, 0.00146, 0.00141, 0.00137, 0.00133],
                "display_name": "Copper/Gold Ratio",
                "unit": "ratio",
                "source_url": "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
                "released_at": "2026-03-03",
            },
            "nvidia_stock_price": {
                "periods": daily_periods,
                "values": [154.9, 156.8, 158.6, 160.4, 164.2, 167.7, 171.3, 172.7, 175.6, 175.2, 176.4],
                "display_name": "NVIDIA",
                "unit": "USD",
                "source_url": "https://api.nasdaq.com/api/quote/NVDA/historical?assetclass=stocks",
                "released_at": "2026-03-25",
            },
        }
        series_map = {}
        for code, spec in series_specs.items():
            points = tuple(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=period_label,
                    value=value,
                    unit=spec["unit"],
                    source_url=spec["source_url"],
                    released_at=spec["released_at"],
                )
                for (period_label, period_end), value in zip(spec["periods"], spec["values"], strict=True)
            )
            series_map[code] = MacroIndicatorSeries(
                provider=self.provider_key,
                indicator_code=code,
                display_name=spec["display_name"],
                unit=spec["unit"],
                source_url=spec["source_url"],
                points=points,
            )
        return [series_map[code] for code in indicator_codes if code in series_map]

    def fetch_latest_readings(self, *, indicator_codes):
        series_map = {
            item.indicator_code: item
            for item in self.fetch_history_series(indicator_codes=indicator_codes, start_date=date(2025, 1, 1))
        }
        readings = []
        for code in indicator_codes:
            series = series_map.get(code)
            if not series or not series.points:
                continue
            latest = series.points[-1]
            previous = series.points[-2] if len(series.points) > 1 else None
            readings.append(
                MacroIndicatorReading(
                    self.provider_key,
                    code,
                    series.display_name,
                    latest.value,
                    latest.unit,
                    latest.period_label,
                    latest.released_at,
                    latest.source_url,
                    previous_value=previous.value if previous else None,
                    change_value=(latest.value - previous.value) if previous else None,
                    change_kind="vs prior release" if previous else None,
                    trend_summary=None,
                )
            )
        return readings

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "sample data", "2026-03-15T00:00:00Z")


class SampleMarketDataProvider:
    provider_key = "sample-market"

    def _build_history_points(self, *, trade_date: date, start_value: float, drift: float) -> tuple[MarketIndexHistoryPoint, ...]:
        points: list[MarketIndexHistoryPoint] = []
        cursor = trade_date - timedelta(days=210)
        value = start_value
        step = 0
        while cursor < trade_date:
            if cursor.weekday() < 5:
                wave = ((step % 6) - 2.5) * drift * 0.2
                points.append(
                    MarketIndexHistoryPoint(
                        trade_date=cursor,
                        close_price=round(value + wave, 2),
                    )
                )
                value += drift
                step += 1
            cursor += timedelta(days=1)
        return tuple(points)

    def fetch_index_snapshots(self, *, symbols, trade_date: date):
        history = {
            "CSI300": self._build_history_points(trade_date=trade_date, start_value=3520.0, drift=1.7),
            "CSI500": self._build_history_points(trade_date=trade_date, start_value=5400.0, drift=2.0),
            "CSI1000": self._build_history_points(trade_date=trade_date, start_value=5980.0, drift=2.4),
            "SSE": self._build_history_points(trade_date=trade_date, start_value=3010.0, drift=1.0),
            "CHINEXT": self._build_history_points(trade_date=trade_date, start_value=1830.0, drift=1.2),
            "HSTECH": self._build_history_points(trade_date=trade_date, start_value=3720.0, drift=2.6),
        }
        current = {
            "CSI300": 3632.0,
            "CSI500": 5528.0,
            "CSI1000": 6124.0,
            "SSE": 3084.0,
            "CHINEXT": 1918.0,
            "HSTECH": 3926.0,
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
                    currency="HKD" if symbol == "HSTECH" else "CNY",
                    source_url="https://akshare.akfamily.xyz/",
                    lookback_closes=tuple(point.close_price for point in history[symbol][-19:]),
                    history_points=history[symbol],
                )
            )
        return snapshots

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "sample data", "2026-03-15T00:00:00Z")
