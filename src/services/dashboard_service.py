"""Dashboard service that provides shared view models for web and push layers."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
import os
import threading
import time
from typing import List

from ..domain.external_data import NewsCategory
from ..providers import (
    AkshareMacroDataProvider,
    AkshareMarketDataProvider,
    ArkResearchProvider,
    CompositeNewsProvider,
    FallbackMacroProvider,
    FallbackMarketDataProvider,
    FallbackNewsProvider,
    FallbackResearchProvider,
    FallbackSearchProvider,
    GoogleNewsSearchProvider,
    NewsNowModeProvider,
    NewsNowSourceMode,
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


logger = logging.getLogger(__name__)


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
    url: str
    published_at: str
    tag: str
    summary: str = ""


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
    news_mode: str
    title: str
    summary: str
    sections: List[DashboardSection]
    dashboard_summary: SummaryBlock
    news_sections: List[NewsSectionView]
    macro_sections: List[MetricCard]
    market_sections: List[MarketCard]
    event_sections: List[EventSectionView]
    data_status: List[DataStatusItem]


@dataclass
class _CachedValue:
    payload: object
    refreshed_at: float


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
        news_mode: str = NewsNowSourceMode.HYBRID.value,
        enable_background_refresh: bool = True,
    ) -> None:
        self._prefer_live_data = prefer_live_data
        self._news_mode = self._resolve_news_mode(news_mode)
        self._snapshot_cache: dict[str, _CachedValue] = {}
        self._snapshot_lock = threading.Lock()
        self._module_cache: dict[str, _CachedValue] = {}
        self._module_lock = threading.Lock()
        self._module_refresh_state: dict[str, str] = {}
        self._module_refresh_detail: dict[str, str] = {}
        self._module_refresh_state_lock = threading.Lock()
        self._enable_background_refresh = enable_background_refresh
        self._refresh_intervals_seconds = {
            "news": float(os.getenv("DASHBOARD_NEWS_REFRESH_SECONDS", "3600")),
            "macro": float(os.getenv("DASHBOARD_MACRO_REFRESH_SECONDS", "86400")),
            "market": float(os.getenv("DASHBOARD_MARKET_REFRESH_SECONDS", "900")),
            "events": float(os.getenv("DASHBOARD_EVENTS_REFRESH_SECONDS", "86400")),
            "status": float(os.getenv("DASHBOARD_STATUS_REFRESH_SECONDS", "900")),
            "snapshot": float(os.getenv("DASHBOARD_SNAPSHOT_REFRESH_SECONDS", "900")),
        }
        self._refresh_check_interval_seconds = max(
            5.0,
            float(os.getenv("DASHBOARD_BACKGROUND_REFRESH_CHECK_SECONDS", "60")),
        )
        self._refresh_stop_event = threading.Event()
        self._refresh_thread: threading.Thread | None = None
        self._news_provider = None
        self._search_provider = None
        self._macro_provider = None
        self._market_provider = None
        self._research_provider = None
        self._prime_live_caches_on_startup = (
            self._prefer_live_data
            and self._enable_background_refresh
            and news_service is None
            and macro_service is None
            and market_service is None
            and events_service is None
        )
        self._background_managed_module_keys = self._build_background_managed_module_keys()
        if self._prime_live_caches_on_startup:
            for cache_key in self._background_managed_module_keys:
                self._module_refresh_state[cache_key] = "pending"
                self._module_refresh_detail[cache_key] = "后台已启动，正在异步拉取最新数据。"

        if news_service is None:
            news_provider, search_provider = self._build_news_providers(
                prefer_live_data=prefer_live_data,
                news_mode=self._news_mode,
            )
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

        if self._prefer_live_data and self._enable_background_refresh:
            self._start_background_refresh()

    def _build_background_managed_module_keys(self) -> set[str]:
        return {
            "module:macro",
            "module:market",
            "module:events",
            f"module:news:{NewsNowSourceMode.HYBRID.value}",
            f"module:news:{NewsNowSourceMode.API.value}",
            f"module:news:{NewsNowSourceMode.UPSTREAM.value}",
            f"module:status:{NewsNowSourceMode.HYBRID.value}",
            f"module:status:{NewsNowSourceMode.API.value}",
            f"module:status:{NewsNowSourceMode.UPSTREAM.value}",
        }

    def _module_cache_key(self, module_id: str, *, news_mode: str | None = None) -> str:
        if module_id in {"news", "status"}:
            effective_news_mode = self._resolve_news_mode(news_mode or self._news_mode)
            return f"module:{module_id}:{effective_news_mode}"
        return f"module:{module_id}"

    def get_module_bootstrap_state(self, module_id: str, *, news_mode: str | None = None) -> tuple[str, str]:
        cache_key = self._module_cache_key(module_id, news_mode=news_mode)
        if self._get_cached_module(cache_key) is not None:
            return "ready", ""
        with self._module_refresh_state_lock:
            state = self._module_refresh_state.get(cache_key, "idle")
            detail = self._module_refresh_detail.get(cache_key, "")
        return state, detail

    def should_serve_loading_module(self, module_id: str, *, news_mode: str | None = None) -> bool:
        state, _ = self.get_module_bootstrap_state(module_id, news_mode=news_mode)
        return state in {"pending", "refreshing", "error"}

    def build_snapshot(self, *, news_mode: str | None = None, force_refresh: bool = False) -> DashboardSnapshot:
        """Return a structured dashboard snapshot composed from service outputs."""
        effective_news_mode = self._resolve_news_mode(news_mode or self._news_mode)
        return self._get_or_build_snapshot(
            effective_news_mode,
            lambda: self._build_snapshot_uncached(effective_news_mode=effective_news_mode),
            force_refresh=force_refresh,
        )

    def build_news_module(
        self,
        *,
        news_mode: str | None = None,
        force_refresh: bool = False,
    ) -> tuple[str, str, List[NewsSectionView], DataStatusItem]:
        """Build one frontend-ready news module without waiting on unrelated modules."""
        effective_news_mode = self._resolve_news_mode(news_mode or self._news_mode)
        cache_key = f"module:news:{effective_news_mode}"
        return self._get_or_build_module(
            cache_key,
            lambda: self._build_news_module_uncached(effective_news_mode=effective_news_mode),
            force_refresh=force_refresh,
        )

    def build_macro_module(self, *, force_refresh: bool = False) -> tuple[str, List[MetricCard]]:
        """Build one frontend-ready macro module."""
        return self._get_or_build_module("module:macro", self._build_macro_module_uncached, force_refresh=force_refresh)

    def build_market_module(self, *, force_refresh: bool = False) -> tuple[str, List[MarketCard]]:
        """Build one frontend-ready market module."""
        return self._get_or_build_module("module:market", self._build_market_module_uncached, force_refresh=force_refresh)

    def build_events_module(self, *, force_refresh: bool = False) -> tuple[str, List[EventSectionView]]:
        """Build one frontend-ready events module."""
        return self._get_or_build_module("module:events", self._build_events_module_uncached, force_refresh=force_refresh)

    def build_status_module(
        self,
        *,
        news_mode: str | None = None,
        force_refresh: bool = False,
    ) -> tuple[str, List[DataStatusItem], str]:
        """Build the lightweight status module used by the shell chrome."""
        effective_news_mode = self._resolve_news_mode(news_mode or self._news_mode)
        cache_key = f"module:status:{effective_news_mode}"
        return self._get_or_build_module(
            cache_key,
            lambda: self._build_status_module_uncached(effective_news_mode=effective_news_mode),
            force_refresh=force_refresh,
        )

    def _build_snapshot_uncached(self, *, effective_news_mode: str) -> DashboardSnapshot:
        """Build one dashboard snapshot without consulting the short-lived cache."""
        news_service, news_provider, search_provider = self._resolve_news_runtime(effective_news_mode)

        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        with ThreadPoolExecutor(max_workers=4) as executor:
            news_future = executor.submit(news_service.build_snapshot)
            macro_future = executor.submit(self._macro_service.build_snapshot)
            market_future = executor.submit(self._market_service.build_snapshot)
            events_future = executor.submit(self._events_service.build_snapshot)
            news_snapshot = news_future.result()
            macro_snapshot = macro_future.result()
            market_snapshot = market_future.result()
            events_snapshot = events_future.result()
        data_status = self._build_data_status(news_provider=news_provider, search_provider=search_provider)

        summary = SummaryBlock(
            title="财经与政策情报仪表盘",
            subtitle="聚合财经、政策、宏观与市场监控的首页概览。",
            as_of_label=generated_at,
            coverage_note=self._coverage_note(data_status),
            highlights=self._summary_highlights(data_status),
        )

        news_sections = self._build_news_sections_from_snapshot(news_snapshot)
        macro_sections = self._build_macro_sections_from_snapshot(macro_snapshot)
        market_sections = self._build_market_sections_from_snapshot(market_snapshot)
        event_sections = self._build_event_sections_from_snapshot(events_snapshot)

        sections = [
            DashboardSection("news", "新闻情报", data_status[0].status, "三类新闻管道已接入服务化视图模型。"),
            DashboardSection("macro", "宏观指标", data_status[1].status, "宏观卡片基于指标注册表生成，包含来源和新鲜度信息。"),
            DashboardSection("market", "市场模型", data_status[2].status, "Fishbowl 与 MA20 输出可复现，并按指数独立计算。"),
            DashboardSection("events", "事件与政策展望", data_status[3].status, "展望窗口会过滤低置信度和弱来源条目。"),
            DashboardSection("push", "推送自动化", "compatible", "推送报告已复用共享的仪表盘快照。"),
        ]

        return DashboardSnapshot(
            generated_at=generated_at,
            news_mode=effective_news_mode,
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

    def _build_news_module_uncached(self, *, effective_news_mode: str) -> tuple[str, str, List[NewsSectionView], DataStatusItem]:
        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        news_service, news_provider, search_provider = self._resolve_news_runtime(effective_news_mode)
        news_snapshot = news_service.build_snapshot()
        news_sections = self._build_news_sections_from_snapshot(news_snapshot)
        news_status = self._build_data_status(news_provider=news_provider, search_provider=search_provider)[0]
        return generated_at, effective_news_mode, news_sections, news_status

    def _build_macro_module_uncached(self) -> tuple[str, List[MetricCard]]:
        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        macro_snapshot = self._macro_service.build_snapshot()
        return generated_at, self._build_macro_sections_from_snapshot(macro_snapshot)

    def _build_market_module_uncached(self) -> tuple[str, List[MarketCard]]:
        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        market_snapshot = self._market_service.build_snapshot()
        return generated_at, self._build_market_sections_from_snapshot(market_snapshot)

    def _build_events_module_uncached(self) -> tuple[str, List[EventSectionView]]:
        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        events_snapshot = self._events_service.build_snapshot()
        return generated_at, self._build_event_sections_from_snapshot(events_snapshot)

    def _build_status_module_uncached(self, *, effective_news_mode: str) -> tuple[str, List[DataStatusItem], str]:
        generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        _, news_provider, search_provider = self._resolve_news_runtime(effective_news_mode)
        data_status = self._build_data_status(news_provider=news_provider, search_provider=search_provider)
        return generated_at, data_status, self._coverage_note(data_status)

    def _get_or_build_snapshot(self, cache_key: str, builder, *, force_refresh: bool = False):
        if not force_refresh:
            cached = self._get_cached_snapshot(cache_key)
            if cached is not None:
                return cached

        with self._snapshot_lock:
            if not force_refresh:
                cached = self._get_cached_snapshot(cache_key)
                if cached is not None:
                    return cached
            payload = builder()
            self._set_cached_snapshot(cache_key, payload)
            return payload

    def _get_or_build_module(self, cache_key: str, builder, *, force_refresh: bool = False):
        if not force_refresh:
            cached = self._get_cached_module(cache_key)
            if cached is not None:
                return cached

        with self._module_lock:
            if not force_refresh:
                cached = self._get_cached_module(cache_key)
                if cached is not None:
                    return cached
            payload = builder()
            self._set_cached_module(cache_key, payload)
            return payload

    def prime_caches(self, *, force_refresh: bool = False) -> None:
        """Warm module caches so the frontend can switch views without live refetches."""
        tasks = [
            (
                f"module:news:{NewsNowSourceMode.HYBRID.value}",
                lambda: self.build_news_module(
                    news_mode=NewsNowSourceMode.HYBRID.value,
                    force_refresh=force_refresh,
                ),
            ),
            (
                f"module:news:{NewsNowSourceMode.API.value}",
                lambda: self.build_news_module(
                    news_mode=NewsNowSourceMode.API.value,
                    force_refresh=force_refresh,
                ),
            ),
            (
                f"module:news:{NewsNowSourceMode.UPSTREAM.value}",
                lambda: self.build_news_module(
                    news_mode=NewsNowSourceMode.UPSTREAM.value,
                    force_refresh=force_refresh,
                ),
            ),
            (
                f"module:status:{NewsNowSourceMode.HYBRID.value}",
                lambda: self.build_status_module(
                    news_mode=NewsNowSourceMode.HYBRID.value,
                    force_refresh=force_refresh,
                ),
            ),
            (
                f"module:status:{NewsNowSourceMode.API.value}",
                lambda: self.build_status_module(
                    news_mode=NewsNowSourceMode.API.value,
                    force_refresh=force_refresh,
                ),
            ),
            (
                f"module:status:{NewsNowSourceMode.UPSTREAM.value}",
                lambda: self.build_status_module(
                    news_mode=NewsNowSourceMode.UPSTREAM.value,
                    force_refresh=force_refresh,
                ),
            ),
            ("module:macro", lambda: self.build_macro_module(force_refresh=force_refresh)),
            ("module:market", lambda: self.build_market_module(force_refresh=force_refresh)),
            ("module:events", lambda: self.build_events_module(force_refresh=force_refresh)),
        ]

        with ThreadPoolExecutor(max_workers=min(4, len(tasks))) as executor:
            futures = [
                (cache_key, executor.submit(self._run_module_refresh_task, cache_key=cache_key, refresher=task))
                for cache_key, task in tasks
            ]
            for cache_key, future in futures:
                try:
                    future.result()
                except Exception as error:
                    logger.warning("startup cache warm failed for %s: %s", cache_key, error)

    def _start_background_refresh(self) -> None:
        if self._refresh_thread is not None:
            return
        self._refresh_thread = threading.Thread(
            target=self._background_refresh_loop,
            name="dashboard-cache-refresh",
            daemon=True,
        )
        self._refresh_thread.start()

    def stop_background_refresh(self) -> None:
        self._refresh_stop_event.set()
        if self._refresh_thread is not None:
            self._refresh_thread.join(timeout=2)
            self._refresh_thread = None

    def _background_refresh_loop(self) -> None:
        if self._prime_live_caches_on_startup:
            self.prime_caches(force_refresh=True)
        while not self._refresh_stop_event.is_set():
            if self._refresh_stop_event.wait(self._refresh_check_interval_seconds):
                break
            self._refresh_due_caches()

    def _refresh_due_caches(self) -> None:
        news_modes = (
            NewsNowSourceMode.HYBRID.value,
            NewsNowSourceMode.API.value,
            NewsNowSourceMode.UPSTREAM.value,
        )
        for mode in news_modes:
            self._refresh_module_if_due(
                cache_key=f"module:news:{mode}",
                interval_key="news",
                refresher=lambda mode=mode: self.build_news_module(news_mode=mode, force_refresh=True),
            )
            self._refresh_module_if_due(
                cache_key=f"module:status:{mode}",
                interval_key="status",
                refresher=lambda mode=mode: self.build_status_module(news_mode=mode, force_refresh=True),
            )

        self._refresh_module_if_due(
            cache_key="module:macro",
            interval_key="macro",
            refresher=lambda: self.build_macro_module(force_refresh=True),
        )
        self._refresh_module_if_due(
            cache_key="module:market",
            interval_key="market",
            refresher=lambda: self.build_market_module(force_refresh=True),
        )
        self._refresh_module_if_due(
            cache_key="module:events",
            interval_key="events",
            refresher=lambda: self.build_events_module(force_refresh=True),
        )

    def _refresh_module_if_due(self, *, cache_key: str, interval_key: str, refresher) -> None:
        if not self._is_cache_due(self._module_cache.get(cache_key), interval_key):
            return
        try:
            self._run_module_refresh_task(cache_key=cache_key, refresher=refresher)
        except Exception as error:
            logger.warning("background refresh failed for %s: %s", cache_key, error)

    def _is_cache_due(self, cached: _CachedValue | None, interval_key: str) -> bool:
        if cached is None:
            return True
        interval_seconds = max(0.0, self._refresh_intervals_seconds.get(interval_key, 0.0))
        if interval_seconds <= 0:
            return False
        return (time.monotonic() - cached.refreshed_at) >= interval_seconds

    def _run_module_refresh_task(self, *, cache_key: str, refresher) -> None:
        self._set_module_refresh_state(cache_key, "refreshing", "后台正在拉取最新数据。")
        try:
            refresher()
        except Exception as error:
            if self._get_cached_module(cache_key) is None:
                self._set_module_refresh_state(
                    cache_key,
                    "error",
                    f"后台拉取失败，稍后自动重试。{error}",
                )
            raise
        else:
            self._set_module_refresh_state(cache_key, "ready", "")

    def _set_module_refresh_state(self, cache_key: str, state: str, detail: str) -> None:
        with self._module_refresh_state_lock:
            self._module_refresh_state[cache_key] = state
            self._module_refresh_detail[cache_key] = detail

    def _get_cached_snapshot(self, news_mode: str) -> DashboardSnapshot | None:
        cached = self._snapshot_cache.get(news_mode)
        return cached.payload if cached is not None else None

    def _set_cached_snapshot(self, news_mode: str, snapshot: DashboardSnapshot) -> None:
        self._snapshot_cache[news_mode] = _CachedValue(
            payload=snapshot,
            refreshed_at=time.monotonic(),
        )

    def _get_cached_module(self, key: str):
        cached = self._module_cache.get(key)
        return cached.payload if cached is not None else None

    def _set_cached_module(self, key: str, payload: object) -> None:
        self._module_cache[key] = _CachedValue(
            payload=payload,
            refreshed_at=time.monotonic(),
        )

    def _resolve_news_runtime(self, effective_news_mode: str):
        news_service = self._news_service
        news_provider = self._news_provider
        search_provider = self._search_provider
        if self._prefer_live_data and effective_news_mode != self._news_mode:
            news_provider, search_provider = self._build_news_providers(
                prefer_live_data=True,
                news_mode=effective_news_mode,
            )
            news_service = NewsPipelineService(
                news_provider=news_provider,
                search_provider=search_provider,
            )
        return news_service, news_provider, search_provider

    def _build_news_sections_from_snapshot(self, news_snapshot) -> List[NewsSectionView]:
        title_by_category = {
            NewsCategory.TECHNOLOGY: "科技新闻",
            NewsCategory.FINANCE: "财经新闻",
            NewsCategory.POLICY: "政策新闻",
        }
        return [
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
                        url=item.url,
                        published_at=item.published_at or "暂无数据",
                        tag=self._news_tag_label(item.source_tag or item.source_type.value),
                        summary=(getattr(item, "summary", None) or getattr(item, "raw_summary", "") or "").strip(),
                    )
                    for item in digest.items
                ],
            )
            for digest in news_snapshot.domains
        ]

    def _news_tag_label(self, value: str) -> str:
        tag_map = {
            "rss": "rss",
            "search": "search",
            "realtime": "live",
            "hottest": "hot",
            "none": "feed",
        }
        normalized = str(value or "").strip().lower()
        return tag_map.get(normalized, normalized or "feed")

    def _build_macro_sections_from_snapshot(self, macro_snapshot) -> List[MetricCard]:
        return [
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

    def _build_market_sections_from_snapshot(self, market_snapshot) -> List[MarketCard]:
        return [
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

    def _build_event_sections_from_snapshot(self, events_snapshot) -> List[EventSectionView]:
        return [
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

    def _build_news_providers(self, *, prefer_live_data: bool, news_mode: str):
        if not prefer_live_data:
            return SampleNewsProvider(), SampleSearchProvider()
        selected_news_provider = NewsNowModeProvider(mode=news_mode)
        return (
            FallbackNewsProvider(
                CompositeNewsProvider(
                    (
                        selected_news_provider,
                        PublicRssNewsProvider(),
                    )
                ),
                SampleNewsProvider(),
            ),
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

    def _build_data_status(self, *, news_provider=None, search_provider=None) -> List[DataStatusItem]:
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
                news_provider.healthcheck() if news_provider else (self._news_provider.healthcheck() if self._news_provider else None),
                search_provider.healthcheck() if search_provider else (self._search_provider.healthcheck() if self._search_provider else None),
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
        _ = data_status
        return ""

    def _summary_highlights(self, data_status: List[DataStatusItem]) -> List[str]:
        base = [
            "新闻、宏观、市场和事件模块都由独立服务聚合，而不是硬编码区块。",
            "首页与推送报告共用同一份仪表盘快照。",
        ]
        _ = data_status
        return base

    def _resolve_news_mode(self, value: str | NewsNowSourceMode) -> str:
        try:
            return NewsNowSourceMode(str(value)).value
        except ValueError:
            return NewsNowSourceMode.HYBRID.value

