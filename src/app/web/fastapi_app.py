"""FastAPI entrypoint for the separated frontend and backend dashboard."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ...services.dashboard_service import DashboardService
from .app import build_dashboard_payload, render_dashboard_html, render_error_html
from .frontend_payload import (
    build_frontend_events_module_payload,
    build_frontend_macro_module_payload,
    build_frontend_market_module_payload,
    build_frontend_news_module_payload,
    build_frontend_payload,
    build_frontend_status_module_payload,
)


def create_fastapi_app(dashboard_service: DashboardService | None = None) -> FastAPI:
    """Create the FastAPI app used by the development web server."""
    service = dashboard_service or DashboardService()
    app = FastAPI(
        title="Finance And Policy Intelligence Dashboard",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/dashboard")
    def dashboard_payload(news_mode: str | None = None) -> JSONResponse:
        try:
            snapshot = service.build_snapshot(news_mode=news_mode)
            return JSONResponse(build_dashboard_payload(snapshot))
        except Exception:
            return JSONResponse(
                {"error": "dashboard_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/dashboard")
    def frontend_dashboard_payload(news_mode: str | None = None) -> JSONResponse:
        try:
            snapshot = service.build_snapshot(news_mode=news_mode)
            return JSONResponse(build_frontend_payload(snapshot))
        except Exception:
            return JSONResponse(
                {"error": "frontend_dashboard_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/modules/news")
    def frontend_news_module(news_mode: str | None = None) -> JSONResponse:
        try:
            generated_at, effective_news_mode, news_sections, news_status = service.build_news_module(news_mode=news_mode)
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
    def frontend_macro_module() -> JSONResponse:
        try:
            generated_at, macro_sections = service.build_macro_module()
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
    def frontend_market_module() -> JSONResponse:
        try:
            generated_at, market_sections = service.build_market_module()
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
    def frontend_events_module() -> JSONResponse:
        try:
            generated_at, event_sections = service.build_events_module()
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
    def frontend_status_module(news_mode: str | None = None) -> JSONResponse:
        try:
            generated_at, data_status, coverage_note = service.build_status_module(news_mode=news_mode)
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

    @app.get("/", response_class=FileResponse)
    def homepage() -> FileResponse:
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

    @app.get("/{_:path}", response_class=HTMLResponse)
    def not_found(_: str) -> HTMLResponse:
        return HTMLResponse(
            render_error_html("Page not found", "The requested dashboard route does not exist."),
            status_code=404,
        )

    return app
