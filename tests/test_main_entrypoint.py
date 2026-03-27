import unittest
from unittest.mock import patch

import main


class MainEntrypointTests(unittest.TestCase):
    @patch("main.run_dev_server")
    @patch("main.run_push_job")
    def test_main_defaults_to_web_mode(self, run_push_job, run_dev_server):
        result = main.main([])

        self.assertEqual(result, 0)
        run_dev_server.assert_called_once_with(host="127.0.0.1", port=8000, reload=True)
        run_push_job.assert_not_called()

    @patch("main.run_dev_server")
    @patch("main.run_push_job")
    def test_main_supports_explicit_web_host_and_port(self, run_push_job, run_dev_server):
        result = main.main(["web", "--host", "0.0.0.0", "--port", "9000"])

        self.assertEqual(result, 0)
        run_dev_server.assert_called_once_with(host="0.0.0.0", port=9000, reload=True)
        run_push_job.assert_not_called()

    @patch("main.run_dev_server")
    @patch("main.run_push_job")
    def test_main_supports_disabling_reload(self, run_push_job, run_dev_server):
        result = main.main(["web", "--no-reload"])

        self.assertEqual(result, 0)
        run_dev_server.assert_called_once_with(host="127.0.0.1", port=8000, reload=False)
        run_push_job.assert_not_called()

    @patch("main.run_dev_server")
    @patch("main.run_push_job", return_value=7)
    def test_main_routes_push_mode_to_push_job(self, run_push_job, run_dev_server):
        result = main.main(["push"])

        self.assertEqual(result, 7)
        run_push_job.assert_called_once_with()
        run_dev_server.assert_not_called()


if __name__ == "__main__":
    unittest.main()
