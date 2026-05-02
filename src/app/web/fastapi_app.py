"""FastAPI entrypoint for the separated frontend and backend dashboard."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from ...services.dashboard_service import DashboardService
from ...services.macro_data_service import MacroDataService, MacroDataValidationError
from ...services.push_center_service import PushCenterService
from .spa_assets import WORKBENCH_ROUTES, build_spa_unavailable_response, load_spa_assets

logger = logging.getLogger(__name__)


def render_error_html(title: str, message: str) -> bytes:
    """渲染通用错误页。

    Args:
        title: 错误标题。
        message: 面向用户展示的错误说明。

    Returns:
        可直接写入 HTMLResponse 的 UTF-8 HTML 字节串。
    """
    return (
        "<!doctype html>"
        "<html lang='en'>"
        "<head><meta charset='utf-8'><title>{title}</title></head>"
        "<body><main><h1>{title}</h1><p>{message}</p></main></body>"
        "</html>"
    ).format(title=title, message=message).encode("utf-8")


def create_fastapi_app(
    dashboard_service: DashboardService | None = None,
    push_center_service: PushCenterService | None = None,
    macro_data_service: MacroDataService | None = None,
) -> FastAPI:
    """创建开发 Web 服务使用的 FastAPI 应用。

    Args:
        dashboard_service: Dashboard 聚合服务。
        push_center_service: 推送中心服务。
        macro_data_service: Macro Data 模块服务。

    Returns:
        已注册前端工作台接口和 SPA 路由的 FastAPI 应用。
    """
    service = dashboard_service or DashboardService()
    push_service = push_center_service or PushCenterService(
        dashboard_service=service,
        enable_scheduler=True,
    )
    macro_service = macro_data_service or MacroDataService()
    app = FastAPI(
        title="Finance And Policy Intelligence Dashboard",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    spa_assets = load_spa_assets()
    spa_assets_dir = spa_assets.dist_dir / "assets"
    if spa_assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=spa_assets_dir), name="spa-assets")

    def _loading_response(payload: dict[str, object], detail: str) -> JSONResponse:
        module = payload.get("module")
        if isinstance(module, dict):
            module["loading"] = True
            module["note"] = detail
        payload["refresh_after_ms"] = 2000
        return JSONResponse(payload, status_code=202)

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.on_event("shutdown")
    def shutdown_background_refresh() -> None:
        service.stop_background_refresh()
        push_service.stop_scheduler()

    @app.get("/api/frontend/modules/push")
    def frontend_push_module(refresh: bool = False, include_preview: bool = True) -> JSONResponse:
        try:
            if not refresh:
                loading, detail = push_service.should_serve_loading_module()
                if loading:
                    return _loading_response(
                        push_service.build_module_payload(include_preview=include_preview),
                        detail,
                    )
            payload = push_service.build_module_payload(
                force_refresh_preview=refresh,
                include_preview=include_preview,
            )
            payload["refresh_after_ms"] = push_service.frontend_auto_refresh_ms
            return JSONResponse(payload)
        except Exception:
            return JSONResponse(
                {"error": "frontend_push_module_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/modules/macro-data")
    def frontend_macro_data_module(tab: str = "gdp") -> JSONResponse:
        """返回 Macro Data 模块元数据。

        Args:
            tab: 当前分类子标签。

        Returns:
            前端可渲染的模块元数据 JSON。
        """
        try:
            return JSONResponse(macro_service.build_module_payload(tab=tab))
        except MacroDataValidationError:
            return JSONResponse({"error": "invalid_macro_data_tab"}, status_code=400)
        except Exception:
            logger.exception("frontend macro data module failed")
            return JSONResponse({"error": "frontend_macro_data_module_unavailable"}, status_code=503)

    @app.get("/api/frontend/modules/macro-data/charts/{chart_id}")
    def frontend_macro_data_chart(
        chart_id: str,
        range: str = "1y",
        start_date: str | None = None,
        end_date: str | None = None,
        frequency: str | None = None,
    ) -> JSONResponse:
        """返回 Macro Data 单张图表序列。

        Args:
            chart_id: 图表指标 ID。
            range: 时间范围类型。
            start_date: 自定义起始日期。
            end_date: 自定义结束日期。
            frequency: 数据频率。

        Returns:
            前端可渲染的图表数据 JSON。
        """
        try:
            return JSONResponse(
                macro_service.build_chart_payload(
                    chart_id,
                    range_type=range,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                )
            )
        except MacroDataValidationError:
            return JSONResponse({"error": "invalid_macro_data_range"}, status_code=400)
        except Exception:
            logger.exception("frontend macro data chart failed", extra={"chart_id": chart_id})
            return JSONResponse({"error": "frontend_macro_data_chart_unavailable"}, status_code=503)

    @app.put("/api/push/config")
    def update_push_config(payload: dict | None = None) -> JSONResponse:
        try:
            return JSONResponse(push_service.update_config(payload))
        except Exception:
            logger.exception("push config update failed")
            return JSONResponse(
                {"error": "push_config_update_failed"},
                status_code=400,
            )

    @app.post("/api/push/preview")
    def preview_push(payload: dict | None = None) -> JSONResponse:
        try:
            return JSONResponse(push_service.build_preview_response(payload))
        except Exception:
            logger.exception("push preview failed")
            return JSONResponse(
                {"error": "push_preview_failed"},
                status_code=400,
            )

    @app.post("/api/push/trigger")
    def trigger_push(payload: dict | None = None) -> JSONResponse:
        try:
            response = push_service.trigger_push(payload)
            return JSONResponse(response, status_code=200 if response.get("ok") else 502)
        except Exception:
            logger.exception("push trigger failed")
            return JSONResponse(
                {"error": "push_trigger_failed"},
                status_code=400,
            )

    @app.get("/")
    def homepage() -> Response:
        if spa_assets.is_available:
            return RedirectResponse(url="/push")
        return build_spa_unavailable_response(spa_assets)

    def workbench_spa_entry() -> Response:
        if spa_assets.is_available:
            return FileResponse(spa_assets.index_path)
        return build_spa_unavailable_response(spa_assets)

    for route_path in WORKBENCH_ROUTES:
        app.add_api_route(route_path, workbench_spa_entry, methods=["GET"], response_class=HTMLResponse)

    @app.get("/{_:path}", response_class=HTMLResponse)
    def not_found(_: str) -> HTMLResponse:
        return HTMLResponse(
            render_error_html("Page not found", "The requested dashboard route does not exist."),
            status_code=404,
        )

    return app
