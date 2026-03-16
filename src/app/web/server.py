"""Development web server for the dashboard shell."""
import uvicorn

from ...services.dashboard_service import DashboardService
from .fastapi_app import create_fastapi_app


def run_dev_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the FastAPI dashboard shell locally."""
    app = create_fastapi_app(DashboardService(prefer_live_data=True))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_dev_server()
