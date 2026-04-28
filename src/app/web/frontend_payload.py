"""Frontend payload builders for remaining web modules."""

from __future__ import annotations

from typing import Any

from ...services.dashboard_service import DataStatusItem


def build_frontend_status_module_payload(
    *,
    generated_at: str,
    data_status: list[DataStatusItem],
    coverage_note: str,
    module_loading: bool = False,
    loading_note: str | None = None,
) -> dict[str, Any]:
    """构建 Status 模块前端 payload。

    Args:
        generated_at: payload 生成时间。
        data_status: 各数据源状态项。
        coverage_note: 状态覆盖说明。
        module_loading: 是否处于加载中状态。
        loading_note: 加载中的补充说明，当前保留兼容入口。

    Returns:
        Status 页面可直接消费的模块结构。
    """
    _ = loading_note
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


def _group_status(items: list[dict[str, Any]], *, fallback: str = "compatible") -> str:
    """归并多个状态项为单个模块状态。

    Args:
        items: 包含 `status` 字段的状态字典列表。
        fallback: 无状态项时使用的默认状态。

    Returns:
        优先级归并后的状态字符串。
    """
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
