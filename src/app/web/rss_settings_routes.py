"""FastAPI routes for RSS settings."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ...services.rss_config_service import (
    RssConfigNotFoundError,
    RssConfigService,
    RssConfigValidationError,
)


logger = logging.getLogger(__name__)


def register_rss_settings_routes(app: FastAPI, *, rss_config_service: RssConfigService) -> None:
    """注册系统 RSS 源设置 API。"""

    @app.get("/api/system/rss/sources")
    def list_rss_sources() -> JSONResponse:
        """返回 RSS 源列表与全局调度配置。"""

        try:
            return JSONResponse(rss_config_service.list_sources())
        except Exception:
            logger.exception("rss source list failed")
            return JSONResponse({"error": "rss_source_list_failed"}, status_code=503)

    @app.post("/api/system/rss/sources")
    def create_rss_source(payload: dict | None = None) -> JSONResponse:
        """创建 RSS 源配置。"""

        try:
            return JSONResponse(rss_config_service.create_source(payload), status_code=201)
        except RssConfigValidationError:
            return JSONResponse({"error": "invalid_rss_source_payload"}, status_code=400)
        except Exception:
            logger.exception("rss source create failed")
            return JSONResponse({"error": "rss_source_create_failed"}, status_code=503)

    @app.put("/api/system/rss/sources/{source_id}")
    def update_rss_source(source_id: int, payload: dict | None = None) -> JSONResponse:
        """更新 RSS 源配置。"""

        try:
            return JSONResponse(rss_config_service.update_source(source_id, payload))
        except RssConfigNotFoundError:
            return JSONResponse({"error": "rss_source_not_found"}, status_code=404)
        except RssConfigValidationError:
            return JSONResponse({"error": "invalid_rss_source_payload"}, status_code=400)
        except Exception:
            logger.exception("rss source update failed", extra={"source_id": source_id})
            return JSONResponse({"error": "rss_source_update_failed"}, status_code=503)

    @app.post("/api/system/rss/sources/{source_id}/disable")
    def disable_rss_source(source_id: int) -> JSONResponse:
        """禁用 RSS 源配置。"""

        try:
            return JSONResponse(rss_config_service.disable_source(source_id))
        except RssConfigNotFoundError:
            return JSONResponse({"error": "rss_source_not_found"}, status_code=404)
        except Exception:
            logger.exception("rss source disable failed", extra={"source_id": source_id})
            return JSONResponse({"error": "rss_source_disable_failed"}, status_code=503)

    @app.post("/api/system/rss/sources/{source_id}/fetch")
    def fetch_rss_source(source_id: int) -> JSONResponse:
        """手动抓取 RSS 源并接入 Event Insight 事件列表。"""

        try:
            return JSONResponse(rss_config_service.fetch_source(source_id))
        except RssConfigNotFoundError:
            return JSONResponse({"error": "rss_source_not_found"}, status_code=404)
        except Exception:
            logger.exception("rss source fetch failed", extra={"source_id": source_id})
            return JSONResponse({"error": "rss_source_fetch_failed"}, status_code=503)

    @app.put("/api/system/rss/scheduler")
    def update_rss_scheduler(payload: dict | None = None) -> JSONResponse:
        """保存 RSS 每日抓取调度配置。"""

        try:
            return JSONResponse(rss_config_service.update_scheduler(payload))
        except RssConfigValidationError:
            return JSONResponse({"error": "invalid_rss_scheduler_payload"}, status_code=400)
        except Exception:
            logger.exception("rss scheduler update failed")
            return JSONResponse({"error": "rss_scheduler_update_failed"}, status_code=503)
