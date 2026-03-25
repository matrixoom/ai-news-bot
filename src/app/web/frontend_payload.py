"""Frontend payload builder for the separated web dashboard."""

from __future__ import annotations

import re
from typing import Any

from ...domain import build_default_macro_pair_registry
from ...providers.newsnow_provider import get_upstream_service_status
from ...services.dashboard_service import (
    DashboardSnapshot,
    DataStatusItem,
    EventSectionView,
    MarketCard,
    MetricCard,
    NewsSectionView,
)


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
            "note": f"{len(sections)} 组对比图",
            "description": "官方宏观历史序列与差值比较",
            "status": "loading" if module_loading else _group_status(sections),
            "loading": module_loading,
            "details": [
                {
                    "id": section["key"],
                    "label": section["title"],
                    "kind": "macro",
                    "note": section["summary"],
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
    _ = generated_at
    cards_by_code = {card.key: card for card in macro_sections}
    pair_registry = build_default_macro_pair_registry()
    sections: list[dict[str, Any]] = []
    for pair in pair_registry.values():
        primary = cards_by_code.get(pair.primary_code)
        secondary = cards_by_code.get(pair.secondary_code)
        if primary is None or secondary is None:
            continue
        primary_points = _normalize_macro_points(primary)
        secondary_points = _normalize_macro_points(secondary)
        merged_points = _merge_macro_pair_points(primary_points, secondary_points)
        delta_points = [
            {
                "period_end": item["period_end"],
                "period_label": item["period_label"],
                "value": round(item["primary_value"] - item["secondary_value"], 4),
            }
            for item in merged_points
            if item["primary_value"] is not None and item["secondary_value"] is not None
        ]
        sections.append(
            {
                "key": pair.key,
                "title": pair.title,
                "status": _group_status(
                    [{"status": primary.status}, {"status": secondary.status}],
                    fallback="compatible",
                ),
                "description": pair.description,
                "summary": f"{primary.label}: {primary.value} | {secondary.label}: {secondary.value}",
                "primary": _build_macro_indicator_payload(primary, primary_points),
                "secondary": _build_macro_indicator_payload(secondary, secondary_points),
                "delta_label": pair.delta_label,
                "delta_points": delta_points,
                "sources": _dedupe_macro_sources(primary, secondary),
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


def _normalize_macro_points(card: MetricCard) -> list[dict[str, Any]]:
    points = []
    for point in list(getattr(card, "history_points", []) or []):
        value = point.get("value")
        if not isinstance(value, (int, float)):
            continue
        points.append(
            {
                "period_end": str(point.get("period_end") or ""),
                "period_label": str(point.get("period_label") or ""),
                "value": float(value),
            }
        )
    points.sort(key=lambda item: item["period_end"])
    return points


def _build_macro_indicator_payload(card: MetricCard, points: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "key": card.key,
        "label": card.label,
        "status": card.status,
        "latest_value": card.value,
        "previous_value": card.previous_value,
        "change_label": card.change_label,
        "trend": card.trend,
        "frequency": card.frequency,
        "source_label": card.source_label,
        "source_url": getattr(card, "source_url", ""),
        "updated_at": card.updated_at,
        "period_label": getattr(card, "period_label", ""),
        "context": card.context,
        "unit": getattr(card, "unit", "") or _extract_unit(card.value),
        "points": points,
    }


def _merge_macro_pair_points(
    primary_points: list[dict[str, Any]],
    secondary_points: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_period: dict[str, dict[str, Any]] = {}
    for point in primary_points:
        entry = by_period.setdefault(
            point["period_end"],
            {
                "period_end": point["period_end"],
                "period_label": point["period_label"],
                "primary_value": None,
                "secondary_value": None,
            },
        )
        entry["primary_value"] = point["value"]
    for point in secondary_points:
        entry = by_period.setdefault(
            point["period_end"],
            {
                "period_end": point["period_end"],
                "period_label": point["period_label"],
                "primary_value": None,
                "secondary_value": None,
            },
        )
        entry["secondary_value"] = point["value"]
        if not entry["period_label"]:
            entry["period_label"] = point["period_label"]
    return [by_period[key] for key in sorted(by_period)]


def _dedupe_macro_sources(primary: MetricCard, secondary: MetricCard) -> list[dict[str, str]]:
    sources = []
    seen = set()
    for card in (primary, secondary):
        source_label = card.source_label
        source_url = getattr(card, "source_url", "")
        key = (source_label, source_url)
        if key in seen:
            continue
        seen.add(key)
        sources.append({"label": source_label, "url": source_url})
    return sources


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
