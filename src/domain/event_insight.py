"""Event Insight 领域模型。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RawDocumentSourceType(StrEnum):
    """原始材料来源类型。"""

    NEWS = "news"
    ANNOUNCEMENT = "announcement"
    EARNINGS_REPORT = "earnings_report"
    MEETING_MINUTES = "meeting_minutes"
    RESEARCH_REPORT = "research_report"
    POLICY = "policy"
    INDUSTRY_REPORT = "industry_report"
    MACRO_DATA = "macro_data"
    MARKET_MOVE = "market_move"
    OTHER = "other"


class EventInsightEventType(StrEnum):
    """事件洞察支持的结构化事件类型。"""

    POLICY = "policy"
    PRICE_CHANGE = "price_change"
    SUPPLY_DEMAND = "supply_demand"
    ORDER_CONTRACT = "order_contract"
    CAPACITY = "capacity"
    EARNINGS = "earnings"
    TECHNOLOGY = "technology"
    CAPITAL_MARKET = "capital_market"
    INSTITUTION_VIEW = "institution_view"
    MACRO = "macro"
    RISK = "risk"
    OTHER = "other"


class ProcessingStatus(StrEnum):
    """本地异步任务状态。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class ManualStatus(StrEnum):
    """人工处置状态。"""

    ACTIVE = "active"
    IGNORED = "ignored"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class EventInsightEventRecord:
    """事件洞察事实事件。

    Args:
        id: SQLite 自增主键。
        title: 事件标题。
        summary: 事件摘要。
        event_time: 事件发生时间，使用 ISO 字符串。
        event_type: 结构化事件类型。
        confidence_score: 模型或人工确认置信度，范围为 0 到 1。

    Returns:
        不返回值；该数据类用于在 Repository 与 Service 之间传递事件事实。
    """

    id: int
    title: str
    summary: str
    event_time: str
    event_type: str
    confidence_score: float


@dataclass(frozen=True)
class RawDocumentRecord:
    """原始研究材料记录。

    Args:
        id: SQLite 自增主键。
        source_type: 材料来源类型。
        title: 材料标题。
        content_hash: 正文或文件内容哈希。

    Returns:
        不返回值；该数据类用于描述已入库材料。
    """

    id: int
    source_type: str
    title: str
    content_hash: str


__all__ = [
    "EventInsightEventRecord",
    "EventInsightEventType",
    "ManualStatus",
    "ProcessingStatus",
    "RawDocumentRecord",
    "RawDocumentSourceType",
]
