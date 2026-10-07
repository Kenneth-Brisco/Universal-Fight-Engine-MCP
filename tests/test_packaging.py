"""Check the plugin manifests and generated client configurations."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator

from ufe_docs_mcp import __version__
from ufe_docs_mcp.cli import CLIENT_FORMATS, SERVER_KEY, client_config
from ufe_docs_mcp.packaging import PLUGIN_NAME, export_plugin

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = Path(__file__).resolve().parent / "schemas"
CACHE = Path("/tmp/ufe-docs-cache")
URL = "https://ufe-docs.example.invalid/mcp"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ManifestTests(unittest.TestCase):
    def test_agent_plugins_manifests_match_published_schemas(self):
        for name, schema in (("plugin.json", "plugin"), ("mcp.json", "mcp")):
            with self.subTest(manifest=name):
                Draft202012Validator(_json(SCHEMAS / f"agent-plugins-1.0.0-{schema}.schema.json")).validate(_json(ROOT / name))

    def test_names_versions_and_server_keys_agree(self):
        agent = _json(ROOT / "plugin.json")
        claude = _json(ROOT / ".claude-plugin" / "plugin.json")
        market = _json(ROOT / ".claude-plugin" / "marketplace.json")
        self.assertEqual(agent["name"], PLUGIN_NAME)
        self.assertEqual(claude["name"], PLUGIN_NAME)
        self.assertEqual([p["name"] for p in market["plugins"]], [PLUGIN_NAME])
        self.assertEqual(agent["version"], __version__)
        self.assertEqual(claude["version"], __version__)
        self.assertEqual(list(_json(ROOT / "mcp.json")["mcpServers"]), [SERVER_KEY])
        self.assertEqual(list(claude["mcpServers"]), [SERVER_KEY])
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", claude["mcpServers"][SERVER_KEY]["args"])

    def test_repository_has_no_project_mcp_file(self):
        # A root .mcp.json would also load as project config in Claude Code and Grok.
        self.assertFalse((ROOT / ".mcp.json").exists())

    def test_skill_frontmatter(self):
        text = (ROOT / "skills" / "ufe-docs" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: ufe-docs\ndescription: "))
        self.assertIn("ufe_search_docs", text)


class ClientConfigTests(unittest.TestCase):
    def test_every_format_renders_local_and_remote(self):
        for fmt in CLIENT_FORMATS:
            for url in (None, URL):
                with self.subTest(format=fmt, url=url):
                    text = client_config(fmt, CACHE, url=url, token_env="UFE_DOCS_TOKEN" if url else None)
                    self.assertIn(SERVER_KEY, text)
                    self.assertIn(URL if url else str(CACHE), text)

    def test_json_formats_parse(self):
        for fmt in ("json", "cursor", "antigravity"):
            with self.subTest(format=fmt):
                local = json.loads(client_config(fmt, CACHE))["mcpServers"][SERVER_KEY]
                self.assertTrue(Path(local["command"]).is_absolute())
                self.assertEqual(local["args"][-1], "serve")
                remote = json.loads(client_config(fmt, CACHE, url=URL))["mcpServers"][SERVER_KEY]
                self.assertEqual(remote.get("url", remote.get("serverUrl")), URL)

    @unittest.skipIf(sys.version_info < (3, 11), "tomllib requires Python 3.11")
    def test_codex_toml_parses(self):
        import tomllib

        local = tomllib.loads(client_config("codex", CACHE))["mcp_servers"][SERVER_KEY]
        self.assertTrue(Path(local["command"]).is_absolute())
        remote = tomllib.loads(client_config("codex", CACHE, url=URL, token_env="UFE_DOCS_TOKEN"))["mcp_servers"][SERVER_KEY]
        self.assertEqual(remote, {"url": URL, "bearer_token_env_var": "UFE_DOCS_TOKEN"})


class ExportPluginTests(unittest.TestCase):
    def test_antigravity_package_uses_only_allowed_manifest_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "pkg"
            files = export_plugin("antigravity", out, CACHE)
            self.assertEqual(set(_json(out / "plugin.json")), {"name", "description"})
            server = _json(out / "mcp_config.json")["mcpServers"][SERVER_KEY]
            self.assertTrue(Path(server["command"]).is_absolute())
            self.assertIn("skills/ufe-docs/SKILL.md", files)
            with self.assertRaises(FileExistsError):
                export_plugin("antigravity", out, CACHE)

    def test_cursor_package_and_remote_variant(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "cursor"
            export_plugin("cursor", out, CACHE, url=URL)
            self.assertEqual(_json(out / ".cursor-plugin" / "plugin.json")["name"], PLUGIN_NAME)
            self.assertEqual(_json(out / "mcp.json")["mcpServers"][SERVER_KEY], {"url": URL})
            self.assertTrue((out / "skills" / "ufe-docs" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
