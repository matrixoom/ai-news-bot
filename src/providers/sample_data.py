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
        sample_points = {
            "cpi": [-0.4, -0.1, 0.2, 0.1, 0.3, 0.4, 0.6, 0.5, 0.4, 0.3, 0.1, 0.3],
            "ppi": [-2.7, -2.5, -2.2, -1.9, -1.7, -1.6, -1.5, -1.4, -1.4, -1.3, -1.5, -1.2],
            "household_new_loans": [-0.18, 0.21, 0.42, 0.37, 0.44, 0.31, 0.29, 0.35, 0.41, 0.22, -0.08, -0.19],
            "enterprise_new_loans": [3.10, 1.82, 1.54, 1.38, 1.61, 1.45, 1.58, 1.63, 1.49, 1.82, 2.31, 2.97],
            "gdp_nominal": [4.6, 4.9, 5.0, 5.2, 5.5],
            "gdp_real": [4.8, 5.0, 5.1, 5.0, 4.9],
            "household_leverage": [58.7, 59.4, 60.2, 61.0, 61.8],
            "enterprise_leverage": [131.5, 132.0, 132.6, 133.1, 133.8],
        }
        display_names = {
            "cpi": "CPI",
            "ppi": "PPI",
            "gdp_nominal": "Nominal GDP Growth",
            "gdp_real": "Real GDP Growth",
            "household_new_loans": "Household New Loans",
            "enterprise_new_loans": "Enterprise New Loans",
            "household_leverage": "Household Leverage",
            "enterprise_leverage": "Enterprise Leverage",
        }
        source_urls = {
            "cpi": "https://www.stats.gov.cn/",
            "ppi": "https://www.stats.gov.cn/",
            "gdp_nominal": "https://www.stats.gov.cn/",
            "gdp_real": "https://www.stats.gov.cn/",
            "household_new_loans": "https://www.pbc.gov.cn/",
            "enterprise_new_loans": "https://www.pbc.gov.cn/",
            "household_leverage": "https://www.pbc.gov.cn/",
            "enterprise_leverage": "https://www.pbc.gov.cn/",
        }
        series_map = {}
        for code, values in sample_points.items():
            periods = monthly_periods if len(values) == len(monthly_periods) else quarterly_periods
            unit = "tn yuan" if "new_loans" in code else "%"
            released_at = "2026-03-14" if "new_loans" in code else "2026-03-09"
            points = tuple(
                MacroHistoryPoint(
                    period_end=period_end,
                    period_label=period_label,
                    value=value,
                    unit=unit,
                    source_url=source_urls[code],
                    released_at=released_at,
                )
                for (period_label, period_end), value in zip(periods, values, strict=True)
            )
            series_map[code] = MacroIndicatorSeries(
                provider=self.provider_key,
                indicator_code=code,
                display_name=display_names[code],
                unit=unit,
                source_url=source_urls[code],
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
