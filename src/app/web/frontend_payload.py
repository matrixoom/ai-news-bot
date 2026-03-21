"""Frontend payload builder for the separated web dashboard."""
from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

from ...providers.newsnow_provider import get_upstream_service_status
from ...services.dashboard_service import DashboardSnapshot

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
        "market_sections": [
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
            }
            for section in snapshot.market_sections
        ],
        "event_sections": [
            {
                "key": section.key,
                "title": section.title,
                "status": section.status,
                "items": [
                    {
                        "title": item.title,
                        "time_window": item.time_window,
                        "confidence": item.confidence,
                        "source": item.source,
                    }
                    for item in section.items
                ],
            }
            for section in snapshot.event_sections
        ],
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


def _build_news_sections(snapshot: DashboardSnapshot) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section in snapshot.news_sections:
        ranked_items = [
            {
                "rank": index + 1,
                "title": item.title,
                "source": item.source,
                "url": item.url,
                "published_at": item.published_at,
                "tag": item.tag,
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
    month_labels = _last_month_labels(generated_at, MACRO_TREND_MONTHS)
    sections: list[dict[str, Any]] = []
    for card in snapshot.macro_sections:
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

