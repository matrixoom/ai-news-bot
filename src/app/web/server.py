"""Development web server for the dashboard shell."""
from pathlib import Path

import uvicorn

from ...services.dashboard_service import DashboardService
from .fastapi_app import create_fastapi_app


def create_dev_app():
    """Create the FastAPI app used by the local development server."""
    return create_fastapi_app(DashboardService(prefer_live_data=True))


def run_dev_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = True) -> None:
    """Run the FastAPI dashboard shell locally, with hot reload enabled by default."""
    src_dir = Path(__file__).resolve().parents[2]
    uvicorn.run(
        "src.app.web.server:create_dev_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
        reload_dirs=[str(src_dir)],
    )


if __name__ == "__main__":
    run_dev_server()
