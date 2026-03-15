"""FastAPI entrypoint for the dashboard shell."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from ...services.dashboard_service import DashboardService
from .app import build_dashboard_payload, render_dashboard_html, render_error_html


def create_fastapi_app(dashboard_service: DashboardService | None = None) -> FastAPI:
    """Create the FastAPI app used by the development web server."""
    service = dashboard_service or DashboardService()
    app = FastAPI(
        title="Finance And Policy Intelligence Dashboard",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

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

    @app.get("/", response_class=HTMLResponse)
    def homepage() -> HTMLResponse:
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
