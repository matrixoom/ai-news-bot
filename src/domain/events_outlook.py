"""Domain models for events and policy outlook."""
from dataclasses import dataclass, field
from typing import List

from .external_data import ConfidenceLevel, EventHorizon


@dataclass(frozen=True)
class OutlookEventView:
    """Dashboard-facing outlook event row."""

    title: str
    category: str
    region: str
    expected_date: str
    time_window: str
    confidence: ConfidenceLevel
    impact_summary: str
    source: str


@dataclass(frozen=True)
class OutlookOfficialLink:
    """Official external source link for one covered economy."""

    region: str
    label: str
    url: str


@dataclass(frozen=True)
class OutlookWindowView:
    """Windowed collection of upcoming events."""

    key: str
    title: str
    status: str
    items: List[OutlookEventView] = field(default_factory=list)
    official_links: List[OutlookOfficialLink] = field(default_factory=list)


@dataclass(frozen=True)
class EventsOutlookSnapshot:
    """Top-level outlook snapshot."""

    generated_at: str
    windows: List[OutlookWindowView] = field(default_factory=list)
    official_links: List[OutlookOfficialLink] = field(default_factory=list)


def build_default_outlook_horizons() -> tuple[EventHorizon, ...]:
    """Return the fixed outlook windows for Task 07."""
    return (
        EventHorizon.NEXT_7_DAYS,
        EventHorizon.NEXT_30_DAYS,
        EventHorizon.NEXT_90_DAYS,
        EventHorizon.NEXT_180_DAYS,
    )


def build_default_outlook_official_links() -> tuple[OutlookOfficialLink, ...]:
    """Return official source links for the major-economy events outlook."""
    return (
        OutlookOfficialLink("中国", "国家统计局发布日程", "https://www.stats.gov.cn/xxgk/sjfb/fbrcb/202512/t20251224_1962137.html"),
        OutlookOfficialLink("中国", "国务院政策吹风会", "https://www.gov.cn/zccfh/index.htm"),
        OutlookOfficialLink("美国", "Federal Reserve Calendar", "https://www.federalreserve.gov/newsevents/calendar.htm"),
        OutlookOfficialLink("美国", "BLS Release Calendar", "https://www.bls.gov/schedule/news_release/"),
        OutlookOfficialLink("欧元区", "ECB Meeting Calendar", "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html"),
        OutlookOfficialLink("欧元区", "ECOFIN / Eurogroup", "https://www.consilium.europa.eu/en/council-eu/council-meetings-explained/ecofin/"),
        OutlookOfficialLink("日本", "BOJ Release Schedule", "https://www.boj.or.jp/en/announcements/calendar/"),
        OutlookOfficialLink("日本", "Japan CPI Schedule", "https://www.stat.go.jp/english/data/cpi/1582.htm"),
    )
