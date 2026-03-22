"""Sample providers used for local dashboard and integration tests."""

from __future__ import annotations

from datetime import date, timedelta

from ..domain.external_data import (
    MacroIndicatorReading,
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
                    "工作流智能体开始进入生产环境落地",
                    "https://openai.example/agents",
                    f"{today}T08:00:00Z",
                    "官方说明生产级智能体方案正在推进。",
                ),
                NewsItem(
                    self.provider_key,
                    "TechCrunch AI",
                    NewsCategory.TECHNOLOGY,
                    "芯片厂商继续扩张 AI 推理算力计划",
                    "https://tech.example/chips",
                    f"{today}T09:15:00Z",
                    "推理产能与相关资本开支仍处于高位。",
                ),
            ),
            NewsCategory.FINANCE: (
                NewsItem(
                    self.provider_key,
                    "Reuters Finance",
                    NewsCategory.FINANCE,
                    "流动性环境仍是宏观市场的核心锚点",
                    "https://finance.example/liquidity",
                    f"{today}T07:40:00Z",
                    "市场仍围绕流动性与增长组合进行定价。",
                ),
                NewsItem(
                    self.provider_key,
                    "Bloomberg Markets",
                    NewsCategory.FINANCE,
                    "数据密集周前资金配置转向谨慎筛选",
                    "https://finance.example/positioning",
                    f"{today}T10:00:00Z",
                    "跨资产仓位仍呈现选择性配置。",
                ),
            ),
            NewsCategory.POLICY: (
                NewsItem(
                    self.provider_key,
                    "State Council",
                    NewsCategory.POLICY,
                    "政策工作方案强调产业与信用协同",
                    "https://policy.example/workplan",
                    f"{today}T08:20:00Z",
                    "官方工作方案继续突出协同发力方向。",
                ),
                NewsItem(
                    self.provider_key,
                    "Xinhua",
                    NewsCategory.POLICY,
                    "官方释放宏观政策稳步执行信号",
                    "https://policy.example/execution",
                    f"{today}T11:00:00Z",
                    "政策执行节奏仍是当前主要观察点。",
                ),
            ),
        }

    def fetch_latest(self, *, category, published_on, limit):
        _ = published_on
        return list(self._items.get(category, ()))[:limit]

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "样例数据", "2026-03-15T00:00:00Z")


class SampleSearchProvider:
    provider_key = "sample-search"

    def __init__(self) -> None:
        today = date.today().isoformat()
        self._items = {
            "AI platform release today": (
                SearchResultItem(
                    self.provider_key,
                    "AI platform release today",
                    "工作流智能体开始进入生产环境落地",
                    "搜索侧低位补充",
                    "https://theverge.example/agents",
                    None,
                ),
            ),
            "macro market liquidity today": (
                SearchResultItem(
                    self.provider_key,
                    "macro market liquidity today",
                    "流动性环境仍是宏观市场的核心锚点",
                    "搜索侧低位补充",
                    "https://markets.example/liquidity",
                    f"{today}T10:30:00Z",
                ),
            ),
            "policy briefing today": (
                SearchResultItem(
                    self.provider_key,
                    "policy briefing today",
                    "政策工作方案强调产业与信用协同",
                    "搜索侧低位补充",
                    "https://xinhua.example/workplan",
                    None,
                ),
            ),
        }

    def search(self, *, query, published_on, limit):
        _ = published_on
        return list(self._items.get(query, ()))[:limit]

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "样例数据", "2026-03-15T00:00:00Z")


class SampleMacroProvider:
    provider_key = "sample-macro"

    def fetch_latest_readings(self, *, indicator_codes):
        sample_map = {
            "cpi": MacroIndicatorReading(
                self.provider_key,
                "cpi",
                "CPI",
                0.3,
                "%",
                "2026-02",
                "2026-03-09",
                "https://www.stats.gov.cn/",
                previous_value=0.1,
                change_value=0.2,
                change_kind="MoM",
                trend_summary="通胀压力小幅抬升。",
            ),
            "ppi": MacroIndicatorReading(
                self.provider_key,
                "ppi",
                "PPI",
                -1.2,
                "%",
                "2026-02",
                "2026-03-09",
                "https://www.stats.gov.cn/",
                previous_value=-1.5,
                change_value=0.3,
                change_kind="MoM",
                trend_summary="工业品价格收缩正在缓和。",
            ),
            "gdp_nominal": MacroIndicatorReading(
                self.provider_key,
                "gdp_nominal",
                "Nominal GDP Growth",
                5.1,
                "%",
                "2026-Q1",
                "2026-04-18",
                "https://www.stats.gov.cn/",
                previous_value=4.8,
                change_value=0.3,
                change_kind="YoY",
                trend_summary="名义 GDP 增速小幅回升。",
            ),
            "gdp_real": MacroIndicatorReading(
                self.provider_key,
                "gdp_real",
                "Real GDP",
                4.9,
                "%",
                "2026-Q1",
                "2026-04-18",
                "https://www.stats.gov.cn/",
                previous_value=4.8,
                change_value=0.1,
                change_kind="YoY",
                trend_summary="实际增长整体保持稳定。",
            ),
            "social_financing": MacroIndicatorReading(
                self.provider_key,
                "social_financing",
                "Social Financing",
                9.4,
                "tn yuan",
                "2026-02",
                "2026-03-14",
                "https://www.pbc.gov.cn/",
                previous_value=8.9,
                change_value=0.5,
                change_kind="vs prior month",
                trend_summary="信用脉冲温和改善。",
            ),
            "household_leverage": MacroIndicatorReading(
                self.provider_key,
                "household_leverage",
                "Household Leverage",
                62.1,
                "%",
                "2025-Q4",
                "2026-02-20",
                "https://www.stats.gov.cn/",
                previous_value=61.7,
                change_value=0.4,
                change_kind="vs prior quarter",
                trend_summary="杠杆压力仍在缓慢上行。",
            ),
        }
        return [sample_map[code] for code in indicator_codes if code in sample_map]

    def healthcheck(self):
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "样例数据", "2026-03-15T00:00:00Z")


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
        return ProviderStatus(self.provider_key, ProviderAvailability.DEGRADED, "样例数据", "2026-03-15T00:00:00Z")
