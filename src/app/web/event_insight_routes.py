"""FastAPI routes for Event Insight."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

from ...services.event_insight_import_service import EventInsightImportService, EventInsightImportValidationError
from ...services.event_insight_job_service import EventInsightJobNotFoundError, EventInsightJobService


logger = logging.getLogger(__name__)


def register_event_insight_routes(
    app: FastAPI,
    *,
    import_service: EventInsightImportService,
    job_service: EventInsightJobService,
) -> None:
    """注册 Event Insight 前端 API。

    Args:
        app: FastAPI 应用。
        import_service: 材料导入服务。
        job_service: 任务状态服务。

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
