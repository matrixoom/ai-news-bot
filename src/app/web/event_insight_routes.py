"""FastAPI routes for Event Insight."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

from ...services.event_insight_import_service import EventInsightImportService, EventInsightImportValidationError
from ...services.event_insight_job_service import EventInsightJobNotFoundError, EventInsightJobService
from ...services.event_insight_service import (
    EventInsightNotFoundError,
    EventInsightService,
    EventInsightValidationError,
)


logger = logging.getLogger(__name__)


def register_event_insight_routes(
    app: FastAPI,
    *,
    import_service: EventInsightImportService,
    job_service: EventInsightJobService,
    event_service: EventInsightService,
) -> None:
    """注册 Event Insight 前端 API。

    Args:
        app: FastAPI 应用。
        import_service: 材料导入服务。
        job_service: 任务状态服务。
        event_service: 事件工作台业务服务。

    Returns:
        无返回值；路由直接挂载到 app。
    """

    @app.post("/api/frontend/modules/event-insight/documents/import")
    def import_event_insight_document(
        payload: dict | None = None,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> JSONResponse:
        """导入 Event Insight 原始材料。"""

        try:
            return JSONResponse(
                import_service.import_document(payload, idempotency_key=idempotency_key),
                status_code=202,
            )
        except EventInsightImportValidationError:
            return JSONResponse({"error": "invalid_event_insight_import_payload"}, status_code=400)
        except Exception:
            logger.exception("event insight import failed")
            return JSONResponse({"error": "event_insight_import_failed"}, status_code=503)

    @app.get("/api/frontend/modules/event-insight/jobs/{job_id}")
    def get_event_insight_job(job_id: int) -> JSONResponse:
        """返回 Event Insight 本地任务状态。"""

        try:
            return JSONResponse(job_service.get_job(job_id))
        except EventInsightJobNotFoundError:
            return JSONResponse({"error": "event_insight_job_not_found"}, status_code=404)
        except Exception:
            logger.exception("event insight job status failed", extra={"job_id": job_id})
            return JSONResponse({"error": "event_insight_job_status_failed"}, status_code=503)

    @app.get("/api/frontend/modules/event-insight/events")
    def list_event_insight_events(
        keyword: str = "",
        status: str = "active",
        topicId: int | None = None,
        page: int = 1,
        pageSize: int = 20,
        sortBy: str = "event_time",
        sortOrder: str = "desc",
    ) -> JSONResponse:
        """返回 Event Insight 事件工作台分页列表。"""

        try:
            return JSONResponse(
                event_service.list_events(
                    keyword=keyword,
                    status=status,
                    topic_id=topicId,
                    page=page,
                    page_size=pageSize,
                    sort_by=sortBy,
                    sort_order=sortOrder,
                )
            )
        except EventInsightValidationError:
            return JSONResponse({"error": "invalid_event_insight_events_query"}, status_code=400)
        except Exception:
            logger.exception("event insight events list failed", extra={"keyword": keyword, "status": status})
            return JSONResponse({"error": "event_insight_events_unavailable"}, status_code=503)

    @app.get("/api/frontend/modules/event-insight/graph")
    def get_event_insight_graph(topicId: int | None = None) -> JSONResponse:
        """返回 Event Insight 事件关系图投影。"""

        try:
            return JSONResponse(event_service.get_event_graph(topic_id=topicId))
        except EventInsightNotFoundError:
            return JSONResponse({"error": "event_insight_topic_not_found"}, status_code=404)
        except Exception:
            logger.exception("event insight graph failed", extra={"topic_id": topicId})
            return JSONResponse({"error": "event_insight_graph_failed"}, status_code=503)

    @app.post("/api/frontend/modules/event-insight/events/batch-action")
    def run_event_insight_batch_action(payload: dict | None = None) -> JSONResponse:
        """执行 Event Insight 事件批量操作。"""

        try:
            return JSONResponse(event_service.run_batch_action(payload))
        except EventInsightValidationError:
            return JSONResponse({"error": "invalid_event_insight_batch_action"}, status_code=400)
        except Exception:
            logger.exception("event insight batch action failed")
            return JSONResponse({"error": "event_insight_batch_action_failed"}, status_code=503)

    @app.get("/api/frontend/modules/event-insight/events/{event_id}")
    def get_event_insight_event(event_id: int) -> JSONResponse:
        """返回 Event Insight 单个事件详情。"""

        try:
            return JSONResponse(event_service.get_event_detail(event_id))
        except EventInsightNotFoundError:
            return JSONResponse({"error": "event_insight_event_not_found"}, status_code=404)
        except Exception:
            logger.exception("event insight event detail failed", extra={"event_id": event_id})
            return JSONResponse({"error": "event_insight_event_detail_failed"}, status_code=503)

    @app.put("/api/frontend/modules/event-insight/events/{event_id}")
    def update_event_insight_event(event_id: int, payload: dict | None = None) -> JSONResponse:
        """写入 Event Insight 事件人工字段覆盖。"""

        try:
            return JSONResponse(event_service.update_event(event_id, payload))
        except EventInsightNotFoundError:
            return JSONResponse({"error": "event_insight_event_not_found"}, status_code=404)
        except EventInsightValidationError:
            return JSONResponse({"error": "invalid_event_insight_event_payload"}, status_code=400)
        except Exception:
            logger.exception("event insight event update failed", extra={"event_id": event_id})
            return JSONResponse({"error": "event_insight_event_update_failed"}, status_code=503)

    @app.post("/api/frontend/modules/event-insight/events/{event_id}/ignore")
    def ignore_event_insight_event(event_id: int, payload: dict | None = None) -> JSONResponse:
        """将 Event Insight 事件标记为忽略。"""

        try:
            return JSONResponse(event_service.ignore_event(event_id, payload))
        except EventInsightNotFoundError:
            return JSONResponse({"error": "event_insight_event_not_found"}, status_code=404)
        except Exception:
            logger.exception("event insight event ignore failed", extra={"event_id": event_id})
            return JSONResponse({"error": "event_insight_event_ignore_failed"}, status_code=503)

    @app.post("/api/frontend/modules/event-insight/topics")
    def create_event_insight_topic(payload: dict | None = None) -> JSONResponse:
        """创建 Event Insight 主题。"""

        try:
            return JSONResponse(event_service.create_topic(payload), status_code=201)
        except EventInsightValidationError:
            return JSONResponse({"error": "invalid_event_insight_topic_payload"}, status_code=400)
        except Exception:
            logger.exception("event insight topic create failed")
            return JSONResponse({"error": "event_insight_topic_create_failed"}, status_code=503)

    @app.get("/api/frontend/modules/event-insight/topics")
    def list_event_insight_topics() -> JSONResponse:
        """返回 Event Insight 主题列表。"""

        try:
            return JSONResponse(event_service.list_topics())
        except Exception:
            logger.exception("event insight topics list failed")
            return JSONResponse({"error": "event_insight_topics_unavailable"}, status_code=503)

    @app.get("/api/frontend/modules/event-insight/topics/{topic_id}/trace")
    def get_event_insight_topic_trace(topic_id: int) -> JSONResponse:
        """返回 Event Insight 主题溯源。"""

        try:
            return JSONResponse(event_service.get_topic_trace(topic_id))
        except EventInsightNotFoundError:
            return JSONResponse({"error": "event_insight_topic_not_found"}, status_code=404)
        except Exception:
            logger.exception("event insight topic trace failed", extra={"topic_id": topic_id})
            return JSONResponse({"error": "event_insight_topic_trace_failed"}, status_code=503)

    @app.post("/api/frontend/modules/event-insight/events/{event_id}/link-topic")
    def link_event_insight_topic(event_id: int, payload: dict | None = None) -> JSONResponse:
        """将 Event Insight 事件关联到主题。"""

        try:
            return JSONResponse(event_service.link_event_topic(event_id, payload))
        except EventInsightNotFoundError:
            return JSONResponse({"error": "event_insight_event_or_topic_not_found"}, status_code=404)
        except EventInsightValidationError:
            return JSONResponse({"error": "invalid_event_insight_topic_link_payload"}, status_code=400)
        except Exception:
            logger.exception("event insight topic link failed", extra={"event_id": event_id})
            return JSONResponse({"error": "event_insight_topic_link_failed"}, status_code=503)
