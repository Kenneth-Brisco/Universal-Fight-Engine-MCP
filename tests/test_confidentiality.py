"""Guard the public repository against personal and project information.

See AGENTS.md, "Users' games and projects are confidential". Automated checks
can only catch machine-shaped leaks such as home paths; names from a user's
game must be caught by the contributor's own pre-push search, which this test
cannot know about and must never list.
"""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOME_PATH = re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\Users\\)([A-Za-z0-9._-]+)")
# Generic or synthetic owners used deliberately by the Dockerfile and privacy tests.
ALLOWED_OWNERS = {"user", "private-fixture"}


def _tracked_text_files():
    try:
        names = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True,
        ).stdout.decode("utf-8").split("\0")
    except (OSError, subprocess.CalledProcessError):
        return None
    files = []
    for name in filter(None, names):
        path = ROOT / name
        if path.suffix in {".png", ".jpg", ".ico", ".lock"} or not path.is_file():
            continue
        try:
            files.append((name, path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    return files


class ConfidentialityTests(unittest.TestCase):
    def test_tracked_files_contain_no_personal_home_paths(self):
        files = _tracked_text_files()
        if files is None:
            self.skipTest("not a Git checkout")
        for name, text in files:
            for match in HOME_PATH.finditer(text):
                with self.subTest(file=name, path=match.group(0)):
                    self.assertIn(match.group(1), ALLOWED_OWNERS)

    def test_agent_guidance_covers_project_confidentiality(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("## Users' games and projects are confidential", agents)
        self.assertIn("never line numbers", agents)
        self.assertIn("@AGENTS.md", (ROOT / "CLAUDE.md").read_text(encoding="utf-8"))
        skill = (ROOT / "skills" / "ufe-docs" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Keep the user's game confidential", skill)


if __name__ == "__main__":
    unittest.main()
