"""Frontend payload builder for the separated web dashboard."""
from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

from ...providers.newsnow_provider import get_upstream_service_status
from ...services.dashboard_service import (
    DashboardSnapshot,
    DataStatusItem,
    EventSectionView,
    MarketCard,
    MetricCard,
    NewsSectionView,
)

MACRO_TREND_MONTHS = 12


def build_frontend_payload(snapshot: DashboardSnapshot) -> dict[str, Any]:
    """Build one frontend-focused payload from the shared dashboard snapshot."""
    generated_at = snapshot.generated_at
    return {
        "generated_at": generated_at,
        "news_mode": snapshot.news_mode,
        "news_mode_options": [
            {"value": "hybrid", "label": "Hybrid"},
            {"value": "api", "label": "API"},
            {"value": "upstream", "label": "Upstream"},
        ],
        "upstream_service_status": get_upstream_service_status(),
        "title": snapshot.dashboard_summary.title,
        "subtitle": snapshot.dashboard_summary.subtitle,
        "coverage_note": snapshot.dashboard_summary.coverage_note,
        "highlights": list(snapshot.dashboard_summary.highlights),
        "news_sections": _build_news_sections(snapshot),
        "macro_sections": _build_macro_sections(snapshot, generated_at),
        "market_sections": _build_market_sections_from_views(snapshot.market_sections),
        "event_sections": _build_event_sections_from_views(snapshot.event_sections),
        "data_status": [
            {
                "key": item.key,
                "label": item.label,
                "status": item.status,
                "detail": item.detail,
            }
            for item in snapshot.data_status
        ],
    }


def build_frontend_news_module_payload(
    *,
    generated_at: str,
    news_mode: str,
    news_sections: list[NewsSectionView],
    news_status: DataStatusItem,
    module_loading: bool = False,
    loading_note: str | None = None,
) -> dict[str, Any]:
    sections = _build_news_sections_from_views(news_sections)
    return {
        "generated_at": generated_at,
        "news_mode": news_mode,
        "news_mode_options": [
            {"value": "hybrid", "label": "Hybrid"},
            {"value": "api", "label": "API"},
            {"value": "upstream", "label": "Upstream"},
        ],
        "upstream_service_status": get_upstream_service_status(),
        "module": {
            "id": "news",
            "label": "新闻情报",
            "note": f"{len(sections)} 个频道",
            "description": "科技、财经、政策新闻",
            "status": "loading" if module_loading else _group_status(sections, fallback=news_status.status),
            "loading": module_loading,
            "details": [
                {
                    "id": section["key"],
                    "label": section["title"],
                    "kind": "news",
                    "note": f"{section['item_count']} 条",
                    "section": section,
                }
                for section in sections
            ],
        },
    }


def build_frontend_macro_module_payload(
    *,
    generated_at: str,
    macro_sections: list[MetricCard],
    module_loading: bool = False,
    loading_note: str | None = None,
) -> dict[str, Any]:
    sections = _build_macro_sections_from_views(macro_sections, generated_at)
    return {
        "generated_at": generated_at,
        "module": {
            "id": "macro",
            "label": "宏观指标",
            "note": f"{len(sections)} 个指标",
            "description": "宏观数据",
            "status": "loading" if module_loading else _group_status(sections),
            "loading": module_loading,
            "details": [
                {
                    "id": section["key"],
                    "label": section["label"],
                    "kind": "macro",
                    "note": section["latest_value"],
                    "section": section,
                }
                for section in sections
            ],
        },
    }


def build_frontend_market_module_payload(
    *,
    generated_at: str,
    market_sections: list[MarketCard],
    module_loading: bool = False,
    loading_note: str | None = None,
) -> dict[str, Any]:
    sections = _build_market_sections_from_views(market_sections)
    return {
        "generated_at": generated_at,
        "module": {
            "id": "market",
            "label": "市场模型",
            "note": f"{len(sections)} 个模型",
            "description": "技术指标",
            "status": "loading" if module_loading else _group_status(sections),
            "loading": module_loading,
            "details": [
                {
                    "id": section["key"],
                    "label": section["label"],
                    "kind": "market",
                    "note": section["signal"],
                    "section": section,
                }
                for section in sections
            ],
        },
    }


def build_frontend_events_module_payload(
    *,
    generated_at: str,
    event_sections: list[EventSectionView],
    module_loading: bool = False,
    loading_note: str | None = None,
) -> dict[str, Any]:
    sections = _build_event_sections_from_views(event_sections)
    return {
        "generated_at": generated_at,
        "module": {
            "id": "events",
            "label": "事件展望",
            "note": f"{len(sections)} 个窗口",
            "description": "未来展望",
            "status": "loading" if module_loading else _group_status(sections),
            "loading": module_loading,
            "details": [
                {
                    "id": section["key"],
                    "label": section["title"],
                    "kind": "events",
                    "note": f"{len(section['items'])} 条",
                    "section": section,
                }
                for section in sections
            ],
        },
    }


def build_frontend_status_module_payload(
    *,
    generated_at: str,
    data_status: list[DataStatusItem],
    coverage_note: str,
    module_loading: bool = False,
    loading_note: str | None = None,
) -> dict[str, Any]:
    sections = [
        {
            "key": item.key,
            "label": item.label,
            "status": item.status,
            "detail": item.detail,
        }
        for item in data_status
    ]
    return {
        "generated_at": generated_at,
        "coverage_note": coverage_note,
        "module": {
            "id": "status",
            "label": "数据状态",
            "note": f"{len(sections)} 个模块",
            "description": "状态监控",
            "status": "loading" if module_loading else _group_status(sections),
            "loading": module_loading,
            "details": [
                {
                    "id": section["key"],
                    "label": section["label"],
                    "kind": "status",
                    "note": section["status"],
                    "section": section,
                }
                for section in sections
            ],
        },
    }


def _build_news_sections(snapshot: DashboardSnapshot) -> list[dict[str, Any]]:
    return _build_news_sections_from_views(snapshot.news_sections)


def _build_news_sections_from_views(news_sections: list[NewsSectionView]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section in news_sections:
        ranked_items = [
            {
                "rank": index + 1,
                "title": item.title,
                "source": item.source,
                "url": item.url,
                "published_at": item.published_at,
                "tag": item.tag,
                "summary": item.summary,
                "is_placeholder": False,
            }
            for index, item in enumerate(section.items)
        ]
        sections.append(
            {
                "key": section.key,
                "title": section.title,
                "status": section.status,
                "description": section.description,
                "item_count": len(ranked_items),
                "items": ranked_items,
            }
        )
    return sections


def _build_macro_sections(snapshot: DashboardSnapshot, generated_at: str) -> list[dict[str, Any]]:
    return _build_macro_sections_from_views(snapshot.macro_sections, generated_at)


def _build_macro_sections_from_views(macro_sections: list[MetricCard], generated_at: str) -> list[dict[str, Any]]:
    month_labels = _last_month_labels(generated_at, MACRO_TREND_MONTHS)
    sections: list[dict[str, Any]] = []
    for card in macro_sections:
        latest = _extract_float(card.value)
        unit = _extract_unit(card.value)
        points = _build_trend_points(
            key=card.key,
            latest_value=latest,
            trend=card.trend,
            labels=month_labels,
        )
        sections.append(
            {
                "key": card.key,
                "label": card.label,
                "status": card.status,
                "latest_value": card.value,
                "previous_value": card.previous_value,
                "change_label": card.change_label,
                "trend": card.trend,
                "frequency": card.frequency,
                "source_label": card.source_label,
                "updated_at": card.updated_at,
                "context": card.context,
                "unit": unit,
                "points": points,
            }
        )
    return sections


def _build_market_sections_from_views(market_sections: list[MarketCard]) -> list[dict[str, Any]]:
    return [
        {
            "key": section.key,
            "label": section.label,
            "status": section.status,
            "close_value": section.close_value,
            "ma20_value": section.ma20_value,
            "signal": section.signal,
            "deviation_pct": section.deviation_pct,
            "trade_date": section.trade_date,
            "source_label": section.source_label,
            "explanation": section.explanation,
            "data_window_label": section.data_window_label,
            "history_warning": section.history_warning,
            "chart_points": list(section.chart_points),
        }
        for section in market_sections
    ]


def _build_event_sections_from_views(event_sections: list[EventSectionView]) -> list[dict[str, Any]]:
    return [
        {
            "key": section.key,
            "title": section.title,
            "status": section.status,
            "items": [
                {
                    "title": item.title,
                    "region": item.region,
                    "expected_date": item.expected_date,
                    "time_window": item.time_window,
                    "confidence": item.confidence,
                    "impact_summary": item.impact_summary,
                    "source": item.source,
                }
                for item in section.items
            ],
            "official_links": [
                {
                    "region": link.region,
                    "label": link.label,
                    "url": link.url,
                }
                for link in section.official_links
            ],
        }
        for section in event_sections
    ]


def _group_status(items: list[dict[str, Any]], *, fallback: str = "compatible") -> str:
    if not items:
        return fallback
    statuses = [item.get("status") for item in items if item.get("status")]
    if "degraded" in statuses:
        return "degraded"
    if "live" in statuses:
        return "live"
    if "sample" in statuses:
        return "sample"
    return statuses[0] if statuses else fallback


def _build_trend_points(
    *,
    key: str,
    latest_value: float | None,
    trend: str,
    labels: list[str],
) -> list[dict[str, Any]]:
    if latest_value is None:
        return [{"period": label, "value": None} for label in labels]

    slope_sign = {"up": 1.0, "down": -1.0, "flat": 0.0}.get(trend, 0.0)
    span = max(abs(latest_value) * 0.12, 0.2)
    start = latest_value - (slope_sign * span)
    wobble = max(abs(latest_value) * 0.015, 0.03)
    wobble_seed = (sum(ord(char) for char in key) % 7) + 1
    points: list[dict[str, Any]] = []
    divisor = max(len(labels) - 1, 1)
    for index, label in enumerate(labels):
        progress = index / divisor
        trend_value = start + ((latest_value - start) * progress)
        wobble_value = ((index % wobble_seed) - (wobble_seed / 2)) * (wobble / wobble_seed)
        points.append({"period": label, "value": round(trend_value + wobble_value, 3)})
    points[-1]["value"] = round(latest_value, 3)
    return points


def _last_month_labels(generated_at: str, count: int) -> list[str]:
    try:
        anchor = datetime.fromisoformat(generated_at.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        anchor = datetime.now(UTC)

    year = anchor.year
    month = anchor.month
    labels: list[str] = []
    for offset in reversed(range(count)):
        y = year
        m = month - offset
        while m <= 0:
            m += 12
            y -= 1
        labels.append(f"{y:04d}-{m:02d}")
    return labels


def _extract_float(text: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text or "")
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _extract_unit(text: str) -> str:
    if not text:
        return ""
    unit = re.sub(r"[-+]?\d+(?:\.\d+)?", "", text)
    unit = unit.replace("+", "").replace("-", "").strip()
    return unit
