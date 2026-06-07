"""LLM provider 包导入行为测试。"""

from __future__ import annotations

import subprocess
import sys
import unittest


class LlmProviderImportTests(unittest.TestCase):
    """校验 Web 启动不会提前加载未使用的重型模型 SDK。"""

    def test_package_import_does_not_load_gemini_provider(self) -> None:
        """仅导入 provider 包时不应加载 Gemini 实现或输出弃用警告。"""

        script = (
            "import sys\n"
            "import src.llm_providers\n"
            "print('src.llm_providers.gemini_provider' in sys.modules)\n"
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "False")
        self.assertNotIn("google.generativeai", result.stderr)


if __name__ == "__main__":
    unittest.main()
