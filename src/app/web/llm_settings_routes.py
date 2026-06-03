"""FastAPI routes for LLM settings."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ...services.llm_config_service import (
    LlmConfigService,
    LlmConfigValidationError,
    LlmProviderInUseError,
    LlmProviderNotFoundError,
)


logger = logging.getLogger(__name__)


def register_llm_settings_routes(app: FastAPI, *, llm_config_service: LlmConfigService) -> None:
    """注册系统 LLM 设置 API。"""

    @app.get("/api/system/llm/providers")
    def list_llm_providers() -> JSONResponse:
        """返回脱敏 provider 列表。"""

        try:
            return JSONResponse(llm_config_service.list_providers())
        except Exception:
            logger.exception("llm provider list failed")
            return JSONResponse({"error": "llm_provider_list_failed"}, status_code=503)

    @app.post("/api/system/llm/providers")
    def create_llm_provider(payload: dict | None = None) -> JSONResponse:
        """创建 provider 配置。"""

        try:
            return JSONResponse(llm_config_service.create_provider(payload), status_code=201)
        except LlmConfigValidationError:
            return JSONResponse({"error": "invalid_llm_provider_payload"}, status_code=400)
        except Exception:
            logger.exception("llm provider create failed")
            return JSONResponse({"error": "llm_provider_create_failed"}, status_code=503)

    @app.put("/api/system/llm/providers/{provider_id}")
    def update_llm_provider(provider_id: int, payload: dict | None = None) -> JSONResponse:
        """更新 provider 配置。"""

        try:
            return JSONResponse(llm_config_service.update_provider(provider_id, payload))
        except LlmProviderNotFoundError:
            return JSONResponse({"error": "llm_provider_not_found"}, status_code=404)
        except LlmConfigValidationError:
            return JSONResponse({"error": "invalid_llm_provider_payload"}, status_code=400)
        except Exception:
            logger.exception("llm provider update failed", extra={"provider_id": provider_id})
            return JSONResponse({"error": "llm_provider_update_failed"}, status_code=503)

    @app.post("/api/system/llm/providers/{provider_id}/disable")
    def disable_llm_provider(provider_id: int) -> JSONResponse:
        """禁用 provider。"""

        try:
            return JSONResponse(llm_config_service.disable_provider(provider_id))
        except LlmProviderInUseError:
            return JSONResponse({"error": "provider_in_use"}, status_code=409)
        except LlmProviderNotFoundError:
            return JSONResponse({"error": "llm_provider_not_found"}, status_code=404)
        except Exception:
            logger.exception("llm provider disable failed", extra={"provider_id": provider_id})
            return JSONResponse({"error": "llm_provider_disable_failed"}, status_code=503)

    @app.post("/api/system/llm/providers/{provider_id}/test")
    def test_llm_provider(provider_id: int) -> JSONResponse:
        """测试 provider 连接。"""

        try:
            return JSONResponse(llm_config_service.test_provider(provider_id))
        except LlmProviderNotFoundError:
            return JSONResponse({"error": "llm_provider_not_found"}, status_code=404)
        except Exception:
            logger.exception("llm provider test failed", extra={"provider_id": provider_id})
            return JSONResponse({"error": "llm_provider_test_failed"}, status_code=503)

    @app.get("/api/system/llm/task-configs")
    def list_llm_task_configs() -> JSONResponse:
        """返回任务模型映射。"""

        try:
            return JSONResponse(llm_config_service.list_task_configs())
        except Exception:
            logger.exception("llm task config list failed")
            return JSONResponse({"error": "llm_task_config_list_failed"}, status_code=503)

    @app.get("/api/system/llm/call-logs")
    def list_llm_call_logs(taskType: str = "", limit: int = 20) -> JSONResponse:
        """返回 LLM 调用日志，用于核验连接测试是否真实发生。"""

        try:
            return JSONResponse(llm_config_service.list_call_logs(task_type=taskType, limit=limit))
        except Exception:
            logger.exception("llm call log list failed", extra={"task_type": taskType})
            return JSONResponse({"error": "llm_call_log_list_failed"}, status_code=503)

    @app.put("/api/system/llm/task-configs/{task_type}")
    def update_llm_task_config(task_type: str, payload: dict | None = None) -> JSONResponse:
        """保存任务模型映射。"""

        try:
            return JSONResponse(llm_config_service.upsert_task_config(task_type, payload))
        except LlmProviderNotFoundError:
            return JSONResponse({"error": "llm_provider_not_found"}, status_code=404)
        except LlmConfigValidationError:
            return JSONResponse({"error": "invalid_llm_task_config_payload"}, status_code=400)
        except Exception:
            logger.exception("llm task config update failed", extra={"task_type": task_type})
            return JSONResponse({"error": "llm_task_config_update_failed"}, status_code=503)
