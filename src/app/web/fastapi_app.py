"""FastAPI entrypoint for the separated frontend and backend dashboard."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ...services.dashboard_service import DashboardService
from .app import build_dashboard_payload, render_dashboard_html, render_error_html
from .frontend_payload import build_frontend_payload


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
    def dashboard_payload() -> JSONResponse:
        try:
            snapshot = service.build_snapshot()
            return JSONResponse(build_dashboard_payload(snapshot))
        except Exception:
            return JSONResponse(
                {"error": "dashboard_unavailable"},
                status_code=503,
            )

    @app.get("/api/frontend/dashboard")
    def frontend_dashboard_payload() -> JSONResponse:
        try:
            snapshot = service.build_snapshot()
            return JSONResponse(build_frontend_payload(snapshot))
        except Exception:
            return JSONResponse(
                {"error": "frontend_dashboard_unavailable"},
                status_code=503,
            )

    @app.get("/", response_class=FileResponse)
    def homepage() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/legacy", response_class=HTMLResponse)
    def legacy_homepage() -> HTMLResponse:
        try:
            snapshot = service.build_snapshot()
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
