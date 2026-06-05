"""Events and policy outlook service."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import os
from pathlib import Path
from typing import Callable, Sequence

from ..domain.events_outlook import (
    EventsOutlookSnapshot,
    OutlookEventView,
    OutlookWindowView,
    build_default_outlook_horizons,
    build_default_outlook_official_links,
)
from ..domain.external_data import ConfidenceLevel, EventHorizon
from ..providers.contracts import ProviderAvailability
from ..providers import ResearchProvider
from .events_outlook_store import EventsOutlookStore


TIMELINE_EVENT_CATEGORIES = {"technology", "politics", "finance"}


class EventOutlookValidationError(ValueError):
    """Outlook 参数校验错误。"""


class EventsOutlookService:
    """Collect and filter source-backed events for dashboard display."""

    def __init__(
        self,
        *,
        research_provider: ResearchProvider,
        store: EventsOutlookStore | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._research_provider = research_provider
        default_db_path = Path(os.getenv("EVENTS_OUTLOOK_DB_PATH", ".data/events_outlook.db"))
        self._store = store or EventsOutlookStore(default_db_path)
        self._now_factory = now_factory or (lambda: datetime.now(UTC))

    def build_timeline_payload(
        self,
        *,
        region: str = "domestic",
        start_date: str | None = None,
        end_date: str | None = None,
        refresh: bool = False,
    ) -> dict[str, object]:
        """构建 Outlook 时间轴模块数据。

        Args:
            region: 子标签区域，domestic 或 international。
            start_date: 自定义起始日期。
            end_date: 自定义结束日期。
            refresh: 是否刷新默认日程种子。

        Returns:
            前端时间轴页面可直接渲染的 JSON 字典。
        """
        effective_region = self._validate_region(region)
        now = self._now_factory()
        today = now.date()
        effective_start = self._parse_date(start_date, fallback=today)
        effective_end = self._parse_date(end_date, fallback=today + timedelta(days=365))
        if effective_end < effective_start:
            raise EventOutlookValidationError("end date must be after start date")

        if refresh or not self._store.list_timeline_events(
            region=effective_region,
            start_date=effective_start.isoformat(),
            end_date=effective_end.isoformat(),
        ):
            self.refresh_timeline_events()

        events = self._store.list_timeline_events(
            region=effective_region,
            start_date=effective_start.isoformat(),
            end_date=effective_end.isoformat(),
        )

        return {
            "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "module": {
                "id": "event-outlook",
                "title": "Outlook",
                "description": "Forward calendar for technology, policy, and finance events.",
            },
            "region": effective_region,
            "tabs": [
                {"value": "domestic", "label": "国内"},
                {"value": "international", "label": "国际"},
            ],
            "range": {
                "start_date": effective_start.isoformat(),
                "end_date": effective_end.isoformat(),
            },
            "resolution_options": [
                {"value": "day", "label": "天"},
                {"value": "week", "label": "周"},
                {"value": "month", "label": "月"},
            ],
            "events": [self._timeline_event_payload(event) for event in events],
        }

    def refresh_timeline_events(self) -> dict[str, int]:
        """刷新内置的未来一年科技、时政与财经日程种子。

        Returns:
            按区域统计的写入数量。
        """
        timestamp = self._now_factory().isoformat(timespec="seconds").replace("+00:00", "Z")
        events = self._default_timeline_events()
        written = self._store.upsert_timeline_events(events, now=timestamp)
        return {"written": written}

    def create_timeline_event(self, payload: dict | None) -> dict[str, object]:
        """手工新增一条时间轴事件。

        Args:
            payload: 前端提交的事件字段。

        Returns:
            包含新增事件的响应字典。
        """
        event = self._validate_event_payload(payload)
        timestamp = self._now_factory().isoformat(timespec="seconds").replace("+00:00", "Z")
        created = self._store.create_timeline_event(**event, now=timestamp)
        return {"event": self._timeline_event_payload(created)}

    def update_timeline_event(self, event_id: int, payload: dict | None) -> dict[str, object]:
        """更新一条时间轴事件的标题和摘要。

        Args:
            event_id: 事件主键。
            payload: 前端提交的标题和摘要。

        Returns:
            包含更新后事件的响应字典。
        """
        if not isinstance(payload, dict):
            raise EventOutlookValidationError("payload must be object")
        title = self._non_empty_text(payload.get("title"), field_name="title")
        summary = self._non_empty_text(payload.get("summary"), field_name="summary")
        timestamp = self._now_factory().isoformat(timespec="seconds").replace("+00:00", "Z")
        updated = self._store.update_timeline_event(
            event_id=event_id,
            title=title,
            summary=summary,
            now=timestamp,
        )
        if updated is None:
            raise EventOutlookValidationError("timeline event not found")
        return {"event": self._timeline_event_payload(updated)}

    def build_snapshot(
        self,
        *,
        as_of: date | None = None,
        topics: Sequence[str] | None = None,
        refresh_store: bool = False,
    ) -> EventsOutlookSnapshot:
        """Build one outlook snapshot across all configured time windows."""
        current_time = self._now_factory()
        effective_as_of = as_of or current_time.date()
        effective_topics = tuple(topics or ("policy", "macro", "meeting"))
        provider_not_live = self._provider_is_not_live()
        if refresh_store:
            refreshed = self.refresh_store(as_of=effective_as_of, topics=effective_topics)
            has_stored_records = self._store.has_records()
            if refreshed == 0 and not has_stored_records and provider_not_live:
                return self._empty_snapshot(current_time=current_time)
        elif not self._store.has_records():
            return self._empty_snapshot(current_time=current_time)

        max_expected_date = effective_as_of + timedelta(days=self._days_for_horizon(EventHorizon.NEXT_180_DAYS))
        stored_findings = self._store.load_future_findings(
            as_of=effective_as_of,
            max_expected_date=max_expected_date,
        )
        grouped_findings = {horizon: [] for horizon in build_default_outlook_horizons()}
        for finding in stored_findings:
            horizon = self._horizon_for_expected_date(finding.expected_date, as_of=effective_as_of)
            if horizon is None:
                continue
            if finding.confidence not in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}:
                continue
            grouped_findings[horizon].append(finding)

        official_links = list(build_default_outlook_official_links())
        windows = []
        for horizon in build_default_outlook_horizons():
            filtered = sorted(
                grouped_findings[horizon],
                key=lambda finding: self._sort_key_for_date(finding.expected_date),
            )
            windows.append(
                OutlookWindowView(
                    key=horizon.value,
                    title=self._title_for_horizon(horizon),
                    status="degraded" if provider_not_live else ("live" if filtered else "degraded"),
                    items=[
                        OutlookEventView(
                            title=finding.title,
                            category="policy_outlook",
                            region=finding.region,
                            expected_date=finding.expected_date,
                            time_window=self._title_for_horizon(horizon),
                            confidence=finding.confidence,
                            impact_summary=finding.summary,
                            source=finding.source_title or finding.provider,
                        )
                        for finding in filtered
                    ],
                    official_links=list(official_links),
                )
            )

        return EventsOutlookSnapshot(
            generated_at=current_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            windows=windows,
            official_links=official_links,
        )

    def refresh_store(self, *, as_of: date | None = None, topics: Sequence[str] | None = None) -> int:
        current_time = self._now_factory()
        effective_as_of = as_of or current_time.date()
        effective_topics = tuple(topics or ("policy", "macro", "meeting"))
        collected_at = current_time.isoformat(timespec="seconds").replace("+00:00", "Z")
        findings = []
        for horizon in build_default_outlook_horizons():
            findings.extend(
                self._research_provider.collect_outlook(
                    horizon=horizon,
                    topics=effective_topics,
                    as_of=effective_as_of,
                )
            )
        return self._store.upsert_findings(findings, collected_at=collected_at)

    def _validate_region(self, value: str) -> str:
        """校验并规范化区域参数。"""
        normalized = (value or "").strip()
        if normalized not in {"domestic", "international"}:
            raise EventOutlookValidationError("invalid region")
        return normalized

    def _validate_event_payload(self, payload: dict | None) -> dict[str, str]:
        """校验手工事件录入参数。"""
        if not isinstance(payload, dict):
            raise EventOutlookValidationError("payload must be object")
        region = self._validate_region(str(payload.get("region", "")))
        event_date = self._non_empty_text(payload.get("event_date"), field_name="event_date")
        self._parse_date(event_date, fallback=None)
        category = self._non_empty_text(payload.get("category", "technology"), field_name="category")
        if category not in TIMELINE_EVENT_CATEGORIES:
            raise EventOutlookValidationError("invalid category")
        return {
            "region": region,
            "event_date": event_date,
            "title": self._non_empty_text(payload.get("title"), field_name="title"),
            "summary": self._non_empty_text(payload.get("summary"), field_name="summary"),
            "category": category,
            "source_url": str(payload.get("source_url") or ""),
            "source_name": str(payload.get("source_name") or "manual"),
        }

    def _non_empty_text(self, value: object, *, field_name: str) -> str:
        """读取非空字符串字段。"""
        if not isinstance(value, str) or not value.strip():
            raise EventOutlookValidationError(f"{field_name} is required")
        return value.strip()

    def _parse_date(self, value: str | None, *, fallback: date | None) -> date:
        """解析 ISO 日期，必要时使用兜底日期。"""
        if value is None or value == "":
            if fallback is None:
                raise EventOutlookValidationError("date is required")
            return fallback
        try:
            return date.fromisoformat(value.strip())
        except ValueError as exc:
            raise EventOutlookValidationError("invalid date") from exc

    def _timeline_event_payload(self, event) -> dict[str, object]:
        """转换持久化事件为前端响应字段。"""
        return {
            "id": event.id,
            "region": event.region,
            "event_date": event.event_date,
            "title": event.title,
            "summary": event.summary,
            "category": event.category,
            "source_url": event.source_url,
            "source_name": event.source_name,
            "updated_at": event.updated_at,
        }

    def _default_timeline_events(self) -> list[dict[str, str]]:
        """返回内置的未来一年科技、时政与财经日程种子。"""
        return [
            {
                "event_key": "domestic|2026-06-02|computex-2026",
                "region": "domestic",
                "event_date": "2026-06-02",
                "title": "COMPUTEX 2026",
                "summary": "台北国际电脑展将于 2026 年 6 月 2 日至 5 日举行，重点覆盖 AI、机器人、半导体与下一代计算。",
                "category": "technology",
                "source_name": "COMPUTEX",
                "source_url": "https://www.computextaipei.com.tw/en/news/8F914C77B6AF77A5/info.html?cid=news&cr=5&lt=data",
            },
            {
                "event_key": "domestic|2026-06-23|wef-amnc-dalian-2026",
                "region": "domestic",
                "event_date": "2026-06-23",
                "title": "夏季达沃斯 2026",
                "summary": "世界经济论坛新领军者年会将于 2026 年 6 月 23 日至 25 日在大连举行，议题覆盖新增长模式、全球经济、供应链和中国经济前景。",
                "category": "finance",
                "source_name": "World Economic Forum",
                "source_url": "https://www.weforum.org/meetings/annual-meeting-of-the-new-champions-2026/about/",
            },
            {
                "event_key": "domestic|2026-07-01|waic-2026",
                "region": "domestic",
                "event_date": "2026-07-01",
                "title": "2026 世界人工智能大会",
                "summary": "第九届世界人工智能大会预计 2026 年 7 月在上海举行，聚焦 AI 前沿研究、产业应用和治理议题；具体开幕日以官方更新为准。",
                "category": "technology",
                "source_name": "世界人工智能大会",
                "source_url": "https://waica2026.worldaic.com.cn/",
            },
            {
                "event_key": "domestic|2026-08-21|wrc-sara-2026",
                "region": "domestic",
                "event_date": "2026-08-21",
                "title": "世界机器人大会 WRC SARA",
                "summary": "WRC 高级机器人与自动化研讨会将在北京举行，是 2026 世界机器人大会期间的学术交流节点。",
                "category": "technology",
                "source_name": "World Robot Conference",
                "source_url": "https://www.worldrobotconference.com/en/sara/",
            },
            {
                "event_key": "domestic|2026-09-09|ciftis-2026",
                "region": "domestic",
                "event_date": "2026-09-09",
                "title": "2026 中国国际服务贸易交易会",
                "summary": "服贸会将于 2026 年 9 月 9 日至 13 日在北京首钢园举行，含全球服务贸易峰会及投资、服务贸易、金融服务相关论坛。",
                "category": "finance",
                "source_name": "北京市人民政府",
                "source_url": "https://english.beijing.gov.cn/investinginbeijing/Investmentnews/202601/t20260116_4437219.html",
            },
            {
                "event_key": "domestic|2026-10-12|ciif-2026",
                "region": "domestic",
                "event_date": "2026-10-12",
                "title": "中国国际工业博览会",
                "summary": "第 26 届中国工博会将在上海举行，信息通信、工业自动化、智能制造等展区关注工业 AI 与数字化转型。",
                "category": "technology",
                "source_name": "中国工博会",
                "source_url": "https://ias.pwee.cn/",
            },
            {
                "event_key": "domestic|2026-11-18|apec-leaders-shenzhen",
                "region": "domestic",
                "event_date": "2026-11-18",
                "title": "APEC 领导人非正式会议",
                "summary": "第三十三次 APEC 领导人非正式会议将于 2026 年 11 月 18 日至 19 日在深圳举行，主题围绕亚太共同体、开放、创新与合作。",
                "category": "politics",
                "source_name": "中国政府网",
                "source_url": "https://english.www.gov.cn/news/202512/12/content_WS693c1432c6d00ca5f9a080e6.html",
            },
            {
                "event_key": "international|2026-05-19|google-io-2026",
                "region": "international",
                "event_date": "2026-05-19",
                "title": "Google I/O 2026",
                "summary": "Google 年度开发者大会预计发布 Gemini、Android、Chrome 与云端 AI 能力相关更新。",
                "category": "technology",
                "source_name": "Google I/O",
                "source_url": "https://io.google/2026/",
            },
            {
                "event_key": "international|2026-06-02|microsoft-build-2026",
                "region": "international",
                "event_date": "2026-06-02",
                "title": "Microsoft Build 2026",
                "summary": "Microsoft Build 将于 2026 年 6 月 2 日至 3 日在旧金山举行，重点关注 Azure、GitHub、智能体 AI 和开发者工具。",
                "category": "technology",
                "source_name": "Microsoft",
                "source_url": "https://www.microsoft.com/en-us/startups/blog/microsoft-build-2026-sessions-every-startup-should-attend/",
            },
            {
                "event_key": "international|2026-06-08|wwdc26",
                "region": "international",
                "event_date": "2026-06-08",
                "title": "Apple WWDC26",
                "summary": "Apple WWDC26 将于 2026 年 6 月 8 日至 12 日在线举行，并在 Apple Park 举办特别活动，预计展示平台软件、AI 与开发者工具更新。",
                "category": "technology",
                "source_name": "Apple Developer",
                "source_url": "https://developer.apple.com/news/?id=yi8qj25k",
            },
            {
                "event_key": "international|2026-06-16|fomc-june-2026",
                "region": "international",
                "event_date": "2026-06-16",
                "title": "FOMC 利率会议",
                "summary": "美联储 FOMC 将于 2026 年 6 月 16 日至 17 日召开议息会议，并发布经济预测摘要，市场将关注政策路径和通胀判断。",
                "category": "finance",
                "source_name": "Federal Reserve",
                "source_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
            },
            {
                "event_key": "international|2026-06-15|g7-evian-2026",
                "region": "international",
                "event_date": "2026-06-15",
                "title": "G7 Summit 2026",
                "summary": "第 52 届 G7 峰会预计于 2026 年 6 月 15 日至 17 日在法国 Évian-les-Bains 举行，关注安全、经济韧性与全球治理。",
                "category": "politics",
                "source_name": "G7 Research Group",
                "source_url": "https://www.g7.utoronto.ca/evaluations/2026evian/kirton-G7-prospects-260331.pdf",
            },
            {
                "event_key": "international|2026-07-07|nato-ankara-2026",
                "region": "international",
                "event_date": "2026-07-07",
                "title": "NATO Summit 2026",
                "summary": "北约峰会将于 2026 年 7 月 7 日至 8 日在土耳其安卡拉举行，预计讨论防务投入、联盟能力与地区安全。",
                "category": "politics",
                "source_name": "NATO",
                "source_url": "https://www.nato.int/en/news-and-events/articles/news/2025/08/20/turkiye-to-host-2026-nato-summit-in-ankara",
            },
            {
                "event_key": "international|2026-09-22|unga81-general-debate",
                "region": "international",
                "event_date": "2026-09-22",
                "title": "UNGA 81 General Debate",
                "summary": "联合国大会第 81 届会议一般性辩论将于 2026 年 9 月 22 日开幕，是年度多边外交核心窗口。",
                "category": "politics",
                "source_name": "United Nations",
                "source_url": "https://research.un.org/en/docs/ga/generaldebate",
            },
            {
                "event_key": "international|2026-10-12|imf-world-bank-annual-meetings-2026",
                "region": "international",
                "event_date": "2026-10-12",
                "title": "IMF/World Bank Annual Meetings",
                "summary": "2026 年 IMF 与世界银行年会将于 10 月 12 日至 18 日在泰国曼谷举行，核心议程包括全球经济、金融市场、发展融资和多边政策协调。",
                "category": "finance",
                "source_name": "World Bank Group",
                "source_url": "https://www.worldbank.org/en/meetings/splash/annual",
            },
            {
                "event_key": "international|2026-12-14|g20-miami-2026",
                "region": "international",
                "event_date": "2026-12-14",
                "title": "G20 Leaders' Summit 2026",
                "summary": "G20 领导人峰会将于 2026 年 12 月 14 日至 15 日在美国迈阿密举行。",
                "category": "politics",
                "source_name": "U.S. Department of State",
                "source_url": "https://www.state.gov/releases/office-of-the-spokesperson/2025/12/united-states-hosts-first-g20-sherpa-meeting/",
            },
        ]

    def _title_for_horizon(self, horizon: EventHorizon) -> str:
        titles = {
            EventHorizon.NEXT_7_DAYS: "\u672a\u6765 7 \u5929",
            EventHorizon.NEXT_30_DAYS: "\u672a\u6765 30 \u5929",
            EventHorizon.NEXT_90_DAYS: "\u672a\u6765 90 \u5929",
            EventHorizon.NEXT_180_DAYS: "\u672a\u6765 180 \u5929",
        }
        return titles[horizon]

    def _horizon_for_expected_date(self, expected_date: str, *, as_of: date) -> EventHorizon | None:
        parsed = self._parse_expected_date(expected_date)
        if parsed is None:
            return None
        delta_days = (parsed - as_of).days
        if delta_days < 0:
            return None
        if delta_days <= self._days_for_horizon(EventHorizon.NEXT_7_DAYS):
            return EventHorizon.NEXT_7_DAYS
        if delta_days <= self._days_for_horizon(EventHorizon.NEXT_30_DAYS):
            return EventHorizon.NEXT_30_DAYS
        if delta_days <= self._days_for_horizon(EventHorizon.NEXT_90_DAYS):
            return EventHorizon.NEXT_90_DAYS
        if delta_days <= self._days_for_horizon(EventHorizon.NEXT_180_DAYS):
            return EventHorizon.NEXT_180_DAYS
        return None

    def _sort_key_for_date(self, expected_date: str) -> tuple[int, str]:
        parsed = self._parse_expected_date(expected_date)
        if parsed is None:
            return (1, expected_date or "")
        return (0, parsed.isoformat())

    def _parse_expected_date(self, value: str) -> date | None:
        try:
            return date.fromisoformat((value or "").strip())
        except ValueError:
            return None

    def _days_for_horizon(self, horizon: EventHorizon) -> int:
        days = {
            EventHorizon.NEXT_7_DAYS: 7,
            EventHorizon.NEXT_30_DAYS: 30,
            EventHorizon.NEXT_90_DAYS: 90,
            EventHorizon.NEXT_180_DAYS: 180,
        }
        return days[horizon]

    def _provider_is_not_live(self) -> bool:
        try:
            status = self._research_provider.healthcheck()
        except Exception:
            return False
        availability = getattr(status, "availability", None)
        return availability != ProviderAvailability.LIVE and str(availability) != ProviderAvailability.LIVE.value

    def _empty_snapshot(self, *, current_time: datetime) -> EventsOutlookSnapshot:
        official_links = list(build_default_outlook_official_links())
        windows = [
            OutlookWindowView(
                key=horizon.value,
                title=self._title_for_horizon(horizon),
                status="degraded",
                items=[],
                official_links=list(official_links),
            )
            for horizon in build_default_outlook_horizons()
        ]
        return EventsOutlookSnapshot(
            generated_at=current_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
            windows=windows,
            official_links=official_links,
        )
