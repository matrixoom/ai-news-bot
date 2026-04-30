import unittest
from unittest.mock import patch

from pathlib import Path

from src.app.web.server import create_dev_app, run_dev_server


class DevServerTests(unittest.TestCase):
    @patch("src.app.web.server.create_fastapi_app", return_value="app-object")
    @patch("src.app.web.server.DashboardService", return_value="dashboard-service")
    def test_create_dev_app_builds_fastapi_app_from_dashboard_service(self, mock_dashboard_service, mock_create_fastapi_app):
        app = create_dev_app()

        self.assertEqual(app, "app-object")
        mock_dashboard_service.assert_called_once_with(prefer_live_data=True)
        mock_create_fastapi_app.assert_called_once_with("dashboard-service")

    @patch("src.app.web.server.uvicorn.run")
    def test_run_dev_server_enables_reload_by_default(self, mock_run):
        run_dev_server()

        expected_src_dir = Path(__file__).resolve().parents[1] / "src"
        mock_run.assert_called_once_with(
            "src.app.web.server:create_dev_app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            factory=True,
            reload_dirs=[str(expected_src_dir)],
        )

    @patch("src.app.web.server.uvicorn.run")
    def test_run_dev_server_can_disable_reload(self, mock_run):
        run_dev_server(host="0.0.0.0", port=9000, reload=False)

        expected_src_dir = Path(__file__).resolve().parents[1] / "src"
        mock_run.assert_called_once_with(
            "src.app.web.server:create_dev_app",
            host="0.0.0.0",
            port=9000,
            reload=False,
            factory=True,
            reload_dirs=[str(expected_src_dir)],
        )


if __name__ == "__main__":
    unittest.main()
