"""Keep future evaluation observers aligned without rewriting old run evidence."""
from pathlib import Path
import json
import unittest

from ufe_docs_mcp.cli import SERVER_KEY
from ufe_docs_mcp.packaging import PLUGIN_NAME

ROOT = Path(__file__).resolve().parents[1]


class EvaluationNamingTests(unittest.TestCase):
    def test_all_nine_tool_observers_match_current_plugin_namespace(self):
        files = sorted((ROOT / "evals").glob("*/graders/used-docs-tool.md"))
        self.assertEqual(len(files), 9)
        expected = f"mcp__plugin_{PLUGIN_NAME}_{SERVER_KEY}__ufe_search_docs"
        for path in files:
            with self.subTest(case=path.parent.parent.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn(f"tool: {expected}\n", text)
                self.assertIn("arm: with-only", text)
        guide = (ROOT / "evals/README.md").read_text(encoding="utf-8")
        self.assertIn(expected, guide)
        self.assertNotIn("mcp__plugin_ufe3d_UFE3D__", guide)

    def test_skill_observers_accept_hyphenated_namespace(self):
        files = sorted((ROOT / "evals").glob("*/graders/skill-fired.md"))
        self.assertEqual(len(files), 9)
        payload = json.dumps({"skill": f"{PLUGIN_NAME}:ufe-docs"})
        for path in files:
            with self.subTest(case=path.parent.parent.name):
                line = next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("input_match: "))
                pattern = line.split(": ", 1)[1].strip("'")
                self.assertRegex(payload, pattern)


if __name__ == "__main__":
    unittest.main()
