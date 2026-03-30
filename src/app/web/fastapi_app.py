"""FastAPI entrypoint for the separated frontend and backend dashboard."""
from __future__ import annotations

from datetime import UTC, datetime
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from ...services.dashboard_service import DashboardService, DataStatusItem
from ...services.push_center_service import PushCenterService
from .app import build_dashboard_payload, render_dashboard_html, render_error_html
from .frontend_payload import (
    build_frontend_events_module_payload,
    build_frontend_macro_module_payload,
    build_frontend_market_module_payload,
    build_frontend_news_module_payload,
    build_frontend_payload,
    build_frontend_status_module_payload,
)
from .spa_assets import WORKBENCH_ROUTES, build_spa_unavailable_response, load_spa_assets

logger = logging.getLogger(__name__)


def create_fastapi_app(
    dashboard_service: DashboardService | None = None,
    push_center_service: PushCenterService | None = None,
) -> FastAPI:
    """Create the FastAPI app used by the development web server."""
    service = dashboard_service or DashboardService()
    push_service = push_center_service or PushCenterService(
        dashboard_service=service,
        enable_scheduler=True,
    )
    app = FastAPI(
        title="Finance And Policy Intelligence Dashboard",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    static_dir = Path(__file__).resolve().parent / "static"
    spa_assets = load_spa_assets()
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    def _generated_at_now() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

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

    @app.get("/api/dashboard")
    def dashboard_payload(news_mode: str | None = None, refresh: bool = False) -> JSONResponse:
        try:
            snapshot = service.build_snapshot(news_mode=news_mode, force_refresh=refresh)
            return JSONResponse(build_dashboard_payload(snapshot))
        except Exception:
            return JSONResponse(
                {"error": "dashboard_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/dashboard")
    def frontend_dashboard_payload(news_mode: str | None = None, refresh: bool = False) -> JSONResponse:
        try:
            snapshot = service.build_snapshot(news_mode=news_mode, force_refresh=refresh)
            return JSONResponse(build_frontend_payload(snapshot))
        except Exception:
            return JSONResponse(
                {"error": "frontend_dashboard_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/modules/news")
    def frontend_news_module(news_mode: str | None = None, refresh: bool = False) -> JSONResponse:
        try:
            if not refresh and service.should_serve_loading_module("news", news_mode=news_mode):
                _, detail = service.get_module_bootstrap_state("news", news_mode=news_mode)
                return _loading_response(
                    build_frontend_news_module_payload(
                        generated_at=_generated_at_now(),
                        news_mode=news_mode or "hybrid",
                        news_sections=[],
                        news_status=DataStatusItem("news", "新闻情报", "loading", detail),
                        module_loading=True,
                    ),
                    detail,
                )
            generated_at, effective_news_mode, news_sections, news_status = service.build_news_module(
                news_mode=news_mode,
                force_refresh=refresh,
            )
            return JSONResponse(
                build_frontend_news_module_payload(
                    generated_at=generated_at,
                    news_mode=effective_news_mode,
                    news_sections=news_sections,
                    news_status=news_status,
                )
            )
        except Exception:
            return JSONResponse(
                {"error": "frontend_news_module_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/modules/macro")
    def frontend_macro_module(refresh: bool = False) -> JSONResponse:
        try:
            if not refresh and service.should_serve_loading_module("macro"):
                _, detail = service.get_module_bootstrap_state("macro")
                return _loading_response(
                    build_frontend_macro_module_payload(
                        generated_at=_generated_at_now(),
                        macro_sections=[],
                        module_loading=True,
                    ),
                    detail,
                )
            generated_at, macro_sections = service.build_macro_module(force_refresh=refresh)
            return JSONResponse(
                build_frontend_macro_module_payload(
                    generated_at=generated_at,
                    macro_sections=macro_sections,
                )
            )
        except Exception:
            return JSONResponse(
                {"error": "frontend_macro_module_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/modules/market")
    def frontend_market_module(refresh: bool = False) -> JSONResponse:
        try:
            if not refresh and service.should_serve_loading_module("market"):
                _, detail = service.get_module_bootstrap_state("market")
                return _loading_response(
                    build_frontend_market_module_payload(
                        generated_at=_generated_at_now(),
                        market_sections=[],
                        module_loading=True,
                    ),
                    detail,
                )
            generated_at, market_sections = service.build_market_module(force_refresh=refresh)
            return JSONResponse(
                build_frontend_market_module_payload(
                    generated_at=generated_at,
                    market_sections=market_sections,
                )
            )
        except Exception:
            return JSONResponse(
                {"error": "frontend_market_module_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/modules/events")
    def frontend_events_module(refresh: bool = False) -> JSONResponse:
        try:
            if not refresh and service.should_serve_loading_module("events"):
                _, detail = service.get_module_bootstrap_state("events")
                return _loading_response(
                    build_frontend_events_module_payload(
                        generated_at=_generated_at_now(),
                        event_sections=[],
                        module_loading=True,
                    ),
                    detail,
                )
            generated_at, event_sections = service.build_events_module(force_refresh=refresh)
            return JSONResponse(
                build_frontend_events_module_payload(
                    generated_at=generated_at,
                    event_sections=event_sections,
                )
            )
        except Exception:
            return JSONResponse(
                {"error": "frontend_events_module_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/modules/status")
    def frontend_status_module(news_mode: str | None = None, refresh: bool = False) -> JSONResponse:
        try:
            if not refresh and service.should_serve_loading_module("status", news_mode=news_mode):
                _, detail = service.get_module_bootstrap_state("status", news_mode=news_mode)
                return _loading_response(
                    build_frontend_status_module_payload(
                        generated_at=_generated_at_now(),
                        data_status=[],
                        coverage_note="",
                        module_loading=True,
                    ),
                    detail,
                )
            generated_at, data_status, coverage_note = service.build_status_module(
                news_mode=news_mode,
                force_refresh=refresh,
            )
            return JSONResponse(
                build_frontend_status_module_payload(
                    generated_at=generated_at,
                    data_status=data_status,
                    coverage_note=coverage_note,
                )
            )
        except Exception:
            return JSONResponse(
                {"error": "frontend_status_module_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/modules/push")
    def frontend_push_module(refresh: bool = False) -> JSONResponse:
        try:
            if not refresh:
                loading, detail = push_service.should_serve_loading_module()
                if loading:
                    return _loading_response(push_service.build_module_payload(), detail)
            payload = push_service.build_module_payload(force_refresh_preview=refresh)
            payload["refresh_after_ms"] = push_service.frontend_auto_refresh_ms
            return JSONResponse(payload)
        except Exception:
            return JSONResponse(
                {"error": "frontend_push_module_unavailable"},
                status_code=503,
            )

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
            return RedirectResponse(url="/dashboard")
        return FileResponse(static_dir / "index.html")

    @app.get("/legacy", response_class=HTMLResponse)
    def legacy_homepage(news_mode: str | None = None) -> HTMLResponse:
        try:
            snapshot = service.build_snapshot(news_mode=news_mode)
            return HTMLResponse(render_dashboard_html(snapshot))
        except Exception:
            return HTMLResponse(
                render_error_html("Dashboard unavailable", "The dashboard view model could not be built."),
                status_code=503,
            )

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
