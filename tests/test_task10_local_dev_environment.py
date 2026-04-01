import json
import unittest
from pathlib import Path


class Task10LocalDevEnvironmentTests(unittest.TestCase):
    def test_task10_doc_exists_at_correct_path(self):
        self.assertTrue(Path("tasks/10-local-dev-environment-and-debug.md").exists())
        self.assertFalse(Path("tasks/0-local-dev-environment-and-debug.md").exists())

    def test_python_version_is_pinned_to_312(self):
        self.assertEqual(Path(".python-version").read_text(encoding="utf-8").strip(), "3.12")

    def test_launch_json_contains_full_regression_target(self):
        payload = json.loads(Path(".vscode/launch.json").read_text(encoding="utf-8"))
        names = {item["name"] for item in payload["configurations"]}

        self.assertIn("Python: Web Shell (uv .venv)", names)
        self.assertIn("Python: Project Main Entrypoint (uv .venv)", names)
        self.assertIn("Python: Push Job Via Main (uv .venv)", names)
        self.assertIn("Python: Full Regression Suite (uv .venv)", names)


if __name__ == "__main__":
    unittest.main()
