"""Dashboard service that provides shared view models for web and push layers."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import List

from ..domain.external_data import NewsCategory
from ..providers import (
    AkshareMacroDataProvider,
    AkshareMarketDataProvider,
    ArkResearchProvider,
    FallbackMacroProvider,
    FallbackMarketDataProvider,
    FallbackNewsProvider,
    FallbackResearchProvider,
    FallbackSearchProvider,
    GoogleNewsSearchProvider,
    ProviderAvailability,
    PublicRssNewsProvider,
    SampleMacroProvider,
    SampleMarketDataProvider,
    SampleNewsProvider,
    SampleResearchProvider,
    SampleSearchProvider,
)
from .events_outlook_service import EventsOutlookService
from .macro_monitoring_service import MacroMonitoringService
from .market_monitoring_service import MarketMonitoringService
from .news_pipeline_service import NewsPipelineService


@dataclass(frozen=True)
class DashboardSection:
    """Legacy-compatible summary section retained for early migration tests."""

    key: str
    title: str
    status: str
    description: str


@dataclass(frozen=True)
class SummaryBlock:
    """Top summary content for the homepage."""

    title: str
    subtitle: str
    as_of_label: str
    coverage_note: str
    highlights: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class NewsItemView:
    """Headline item rendered in a news column."""

    title: str
    source: str
    published_at: str
    tag: str


@dataclass(frozen=True)
class NewsSectionView:
    """A category-specific news section for the homepage."""

    key: str
    title: str
    status: str
    description: str
    items: List[NewsItemView] = field(default_factory=list)


@dataclass(frozen=True)
class MetricCard:
    """Macro indicator card rendered in the dashboard shell."""

    key: str
    label: str
    value: str
    context: str
    status: str
    previous_value: str = "暂无数据"
    change_label: str = "暂无变化信息"
    trend: str = "unavailable"
    source_label: str = "暂无数据"
    updated_at: str = "暂无数据"
    frequency: str = "unavailable"


@dataclass(frozen=True)
class MarketCard:
    """Market model card rendered in the dashboard shell."""

    key: str
    label: str
    close_value: str
    ma20_value: str
    signal: str
    status: str
    trade_date: str = "暂无数据"
    deviation_pct: str = "暂无数据"
    source_label: str = "暂无数据"
    explanation: str = "暂无数据"


@dataclass(frozen=True)
class EventItemView:
    """Single upcoming event row."""

    title: str
    time_window: str
    confidence: str
    source: str


@dataclass(frozen=True)
class EventSectionView:
    """Grouped future events for one horizon bucket."""

    key: str
    title: str
    status: str
    items: List[EventItemView] = field(default_factory=list)


@dataclass(frozen=True)
class DataStatusItem:
    """Operational status for one data domain."""

    key: str
    label: str
    status: str
    detail: str


@dataclass(frozen=True)
class DashboardSnapshot:
    """Structured dashboard data shared across the web and push entrypoints."""

    generated_at: str
    title: str
    summary: str
    sections: List[DashboardSection]
    dashboard_summary: SummaryBlock
    news_sections: List[NewsSectionView]
    macro_sections: List[MetricCard]
    market_sections: List[MarketCard]
    event_sections: List[EventSectionView]
    data_status: List[DataStatusItem]


class DashboardService:
    """Compose the dashboard from news, macro, market, and events services."""

    def __init__(
        self,
        news_service: NewsPipelineService | None = None,
        macro_service: MacroMonitoringService | None = None,
        market_service: MarketMonitoringService | None = None,
        events_service: EventsOutlookService | None = None,
        *,
        prefer_live_data: bool = False,
    ) -> None:
        self._prefer_live_data = prefer_live_data
        self._news_provider = None
        self._search_provider = None
        self._macro_provider = None
        self._market_provider = None
        self._research_provider = None

        if news_service is None:
            news_provider, search_provider = self._build_news_providers(prefer_live_data=prefer_live_data)
            self._news_provider = news_provider
            self._search_provider = search_provider
            self._news_service = NewsPipelineService(
                news_provider=news_provider,
                search_provider=search_provider,
            )
        else:
            self._news_service = news_service

        if macro_service is None:
            macro_provider = self._build_macro_provider(prefer_live_data=prefer_live_data)
            self._macro_provider = macro_provider
            self._macro_service = MacroMonitoringService(macro_provider=macro_provider)
        else:
            self._macro_service = macro_service

        if market_service is None:
            market_provider = self._build_market_provider(prefer_live_data=prefer_live_data)
            self._market_provider = market_provider
            self._market_service = MarketMonitoringService(market_provider=market_provider)
        else:
            self._market_service = market_service

        if events_service is None:
            research_provider = self._build_research_provider(prefer_live_data=prefer_live_data)
            self._research_provider = research_provider
            self._events_service = EventsOutlookService(research_provider=research_provider)
        else:
            self._events_service = events_service

    def build_snapshot(self) -> DashboardSnapshot:
        """Return a structured dashboard snapshot composed from service outputs."""
        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        news_snapshot = self._news_service.build_snapshot()
        macro_snapshot = self._macro_service.build_snapshot()
        market_snapshot = self._market_service.build_snapshot()
        events_snapshot = self._events_service.build_snapshot()
        data_status = self._build_data_status()

        summary = SummaryBlock(
            title="财经与政策情报仪表盘",
            subtitle="聚合财经、政策、宏观与市场监控的首页概览。",
            as_of_label=generated_at,
            coverage_note=self._coverage_note(data_status),
            highlights=self._summary_highlights(data_status),
        )

        title_by_category = {
            NewsCategory.TECHNOLOGY: "科技新闻",
            NewsCategory.FINANCE: "财经新闻",
            NewsCategory.POLICY: "政策新闻",
        }
        news_sections = [
            NewsSectionView(
                key=digest.category.value,
                title=title_by_category[digest.category],
                status="live" if digest.items else "degraded",
                description=(
                    f"候选 {digest.candidate_count} 条，"
                    f"合并重复 {digest.merged_duplicate_count} 条，"
                    f"剔除过期 {digest.dropped_outdated_count} 条。"
                ),
                items=[
                    NewsItemView(
                        title=item.title,
                        source=item.source_name,
                        published_at=item.published_at or "暂无数据",
                        tag=item.source_type.value,
                    )
                    for item in digest.items[:10]
                ],
            )
            for digest in news_snapshot.domains
        ]

        macro_sections = [
            MetricCard(
                key=item.key,
                label=item.label,
                value=item.value,
                context=item.context,
                status=item.status,
                previous_value=item.previous_value,
                change_label=item.change_label,
                trend=item.trend.value,
                source_label=item.source_label,
                updated_at=item.updated_at,
                frequency=item.frequency.value,
            )
            for item in macro_snapshot.indicators
        ]

        market_sections = [
            MarketCard(
                key=item.key,
                label=item.label,
                close_value=item.close_value,
                ma20_value=item.ma20_value,
                signal=item.fishbowl_state.value,
                status=item.status,
                trade_date=item.trade_date,
                deviation_pct=item.deviation_pct,
                source_label=item.source_label,
                explanation=item.explanation,
            )
            for item in market_snapshot.items
        ]

        event_sections = [
            EventSectionView(
                key=window.key,
                title=window.title,
                status=window.status,
                items=[
                    EventItemView(
                        title=item.title,
                        time_window=item.time_window,
                        confidence=item.confidence.value,
                        source=item.source,
                    )
                    for item in window.items
                ],
            )
            for window in events_snapshot.windows
        ]

        sections = [
            DashboardSection("news", "新闻情报", data_status[0].status, "三类新闻管道已接入服务化视图模型。"),
            DashboardSection("macro", "宏观指标", data_status[1].status, "宏观卡片基于指标注册表生成，包含来源和新鲜度信息。"),
            DashboardSection("market", "市场模型", data_status[2].status, "Fishbowl 与 MA20 输出可复现，并按指数独立计算。"),
            DashboardSection("events", "事件与政策展望", data_status[3].status, "展望窗口会过滤低置信度和弱来源条目。"),
            DashboardSection("push", "推送自动化", "compatible", "推送报告已复用共享的仪表盘快照。"),
        ]

        return DashboardSnapshot(
            generated_at=generated_at,
            title=summary.title,
            summary=summary.subtitle,
            sections=sections,
            dashboard_summary=summary,
            news_sections=news_sections,
            macro_sections=macro_sections,
            market_sections=market_sections,
            event_sections=event_sections,
            data_status=data_status,
        )

    def _build_news_providers(self, *, prefer_live_data: bool):
        if not prefer_live_data:
            return SampleNewsProvider(), SampleSearchProvider()
        return (
            FallbackNewsProvider(PublicRssNewsProvider(), SampleNewsProvider()),
            FallbackSearchProvider(GoogleNewsSearchProvider(), SampleSearchProvider()),
        )

    def _build_macro_provider(self, *, prefer_live_data: bool):
        if not prefer_live_data:
            return SampleMacroProvider()
        return FallbackMacroProvider(AkshareMacroDataProvider(), SampleMacroProvider())

    def _build_market_provider(self, *, prefer_live_data: bool):
        if not prefer_live_data:
            return SampleMarketDataProvider()
        return FallbackMarketDataProvider(AkshareMarketDataProvider(), SampleMarketDataProvider())

    def _build_research_provider(self, *, prefer_live_data: bool):
        if not prefer_live_data:
            return SampleResearchProvider()
        return FallbackResearchProvider(ArkResearchProvider, SampleResearchProvider())

    def _build_data_status(self) -> List[DataStatusItem]:
        if not self._prefer_live_data:
            return [
                DataStatusItem("news", "新闻管道", "sample", "当前展示样例 RSS 与搜索数据，便于本地开发。"),
                DataStatusItem("macro", "宏观监控", "sample", "当前为样例宏观卡片，因为实时模式未开启。"),
                DataStatusItem("market", "市场模型", "sample", "当前为样例市场快照，因为实时模式未开启。"),
                DataStatusItem("events", "事件展望", "sample", "当前为样例事件展望，因为实时模式未开启。"),
            ]

        news_status = self._combine_statuses(
            key="news",
            label="新闻管道",
            statuses=[
                self._news_provider.healthcheck() if self._news_provider else None,
                self._search_provider.healthcheck() if self._search_provider else None,
            ],
        )
        macro_status = self._single_status("macro", "宏观监控", self._macro_provider)
        market_status = self._single_status("market", "市场模型", self._market_provider)
        events_status = self._single_status("events", "事件展望", self._research_provider)
        return [news_status, macro_status, market_status, events_status]

    def _single_status(self, key: str, label: str, provider) -> DataStatusItem:
        if provider is None:
            return DataStatusItem(key, label, "unknown", "暂无可用的数据源状态。")
        status = provider.healthcheck()
        return DataStatusItem(key, label, status.availability.value, status.detail)

    def _combine_statuses(self, *, key: str, label: str, statuses) -> DataStatusItem:
        available = [status for status in statuses if status is not None]
        if not available:
            return DataStatusItem(key, label, "unknown", "暂无可用的数据源状态。")

        if any(status.availability == ProviderAvailability.DEGRADED for status in available):
            final_status = ProviderAvailability.DEGRADED.value
        elif all(status.availability == ProviderAvailability.LIVE for status in available):
            final_status = ProviderAvailability.LIVE.value
        else:
            final_status = available[0].availability.value

        detail = " | ".join(dict.fromkeys(status.detail for status in available))
        return DataStatusItem(key, label, final_status, detail)

    def _coverage_note(self, data_status: List[DataStatusItem]) -> str:
        if not self._prefer_live_data:
            return "当前仪表盘运行在样例数据模式，便于稳定的本地开发与测试。"
        if any(item.status == ProviderAvailability.DEGRADED.value for item in data_status):
            return "当前仪表盘运行在实时优先模式，对缺少密钥、依赖或不可达数据源自动回退到样例数据。"
        return "当前仪表盘运行在实时优先模式，最近一次抓取中所有已配置数据源都返回正常状态。"

    def _summary_highlights(self, data_status: List[DataStatusItem]) -> List[str]:
        base = [
            "新闻、宏观、市场和事件模块都由独立服务聚合，而不是硬编码区块。",
            "首页与推送报告共用同一份仪表盘快照。",
        ]
        if not self._prefer_live_data:
            base.append("运行入口可切换到实时优先数据源，测试仍使用确定性的样例数据。")
            return base

        degraded = [item.label for item in data_status if item.status == ProviderAvailability.DEGRADED.value]
        if degraded:
            base.append("以下模块已启用自动样例回退：" + "、".join(degraded) + "。")
        else:
            base.append("最近一次刷新中，所有数据源分组均返回正常状态。")
        return base
