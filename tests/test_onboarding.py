"""Check renamed identity and direct, skill-optional onboarding.

No client settings are written. The real stdio check uses synthetic documents
and a child-only network guard, not a model session or the publisher's site.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from ufe_docs_mcp.cli import CLIENT_FORMATS, SERVER_KEY, client_config
from ufe_docs_mcp.packaging import PLUGIN_NAME, export_plugin
from ufe_docs_mcp.server import SERVER_NAME
from test_mcp_protocol import MOVE_ID, MOVE_URL, TOOLS, _OFFLINE_GUARD, _seed_index

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SERVER = "UFE3D-MCP"
EXPECTED_PLUGIN = "ufe3d-mcp"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class OnboardingTests(unittest.TestCase):
    def test_public_identifiers_are_fixed_and_manifests_match(self):
        self.assertEqual(SERVER_KEY, EXPECTED_SERVER)
        self.assertEqual(SERVER_NAME, EXPECTED_SERVER)
        self.assertEqual(PLUGIN_NAME, EXPECTED_PLUGIN)
        agent = read_json(ROOT / "plugin.json")
        claude = read_json(ROOT / ".claude-plugin" / "plugin.json")
        market = read_json(ROOT / ".claude-plugin" / "marketplace.json")
        self.assertEqual(agent["name"], EXPECTED_PLUGIN)
        self.assertEqual(claude["name"], EXPECTED_PLUGIN)
        self.assertEqual(market["name"], EXPECTED_PLUGIN)
        self.assertEqual([p["name"] for p in market["plugins"]], [EXPECTED_PLUGIN])
        self.assertEqual(claude["displayName"], EXPECTED_SERVER)
        self.assertEqual(agent["extensions"]["com.openai"]["interface"]["displayName"], EXPECTED_SERVER)
        for manifest in (claude, read_json(ROOT / "mcp.json"), read_json(ROOT / "examples" / "client-config.json")):
            self.assertEqual(set(manifest["mcpServers"]), {EXPECTED_SERVER})

    def test_generated_local_and_remote_json_use_one_renamed_entry(self):
        with tempfile.TemporaryDirectory(prefix="ufe-config-fixture-") as directory:
            cache = Path(directory) / "cache"
            for fmt in ("json", "cursor", "antigravity"):
                for url in (None, "https://example.invalid/mcp"):
                    with self.subTest(format=fmt, remote=bool(url)):
                        result = json.loads(client_config(fmt, cache, url=url))
                        self.assertEqual(set(result["mcpServers"]), {EXPECTED_SERVER})
                        entry = result["mcpServers"][EXPECTED_SERVER]
                        if url:
                            self.assertEqual(entry.get("url", entry.get("serverUrl")), url)
                        else:
                            self.assertTrue(Path(entry["command"]).is_absolute())
                            self.assertEqual(entry["args"], ["-m", "ufe_docs_mcp", "--cache-dir", str(cache), "serve"])
            self.assertFalse(cache.exists(), "Printing configuration must not create a cache")

    def test_shell_registration_uses_new_identity_and_unchanged_executable(self):
        cache = Path("/example/cache with spaces")
        for url in (None, "https://example.invalid/mcp"):
            command = shlex.split(client_config("claude-code", cache, url=url))
            self.assertEqual(command[:6], ["claude", "mcp", "add-json", "--scope", "user", EXPECTED_SERVER])
            entry = json.loads(command[6])
            if url:
                self.assertEqual(entry["url"], url)
            else:
                self.assertIn("ufe_docs_mcp", entry["args"])
            grok = shlex.split(client_config("grok", cache, url=url))
            self.assertEqual(grok[:4], ["grok", "mcp", "add", EXPECTED_SERVER])
        self.assertEqual(set(CLIENT_FORMATS), {"json", "claude-code", "codex", "cursor", "antigravity", "grok"})

    @unittest.skipIf(sys.version_info < (3, 11), "tomllib requires Python 3.11")
    def test_hyphenated_codex_table_parses_as_one_server(self):
        import tomllib
        for url in (None, "https://example.invalid/mcp"):
            result = tomllib.loads(client_config("codex", Path("/example/cache"), url=url))
            self.assertEqual(set(result["mcp_servers"]), {EXPECTED_SERVER})

    def test_exported_plugins_carry_new_names_and_optional_development_skill(self):
        with tempfile.TemporaryDirectory(prefix="ufe-export-fixture-") as directory:
            root = Path(directory)
            for client in ("cursor", "antigravity"):
                for remote in (False, True):
                    with self.subTest(client=client, remote=remote):
                        out = root / f"{client}-{remote}"
                        export_plugin(client, out, root / "cache", url="https://example.invalid/mcp" if remote else None)
                        manifest_path = out / (".cursor-plugin/plugin.json" if client == "cursor" else "plugin.json")
                        self.assertEqual(read_json(manifest_path)["name"], EXPECTED_PLUGIN)
                        config_path = out / ("mcp.json" if client == "cursor" else "mcp_config.json")
                        self.assertEqual(set(read_json(config_path)["mcpServers"]), {EXPECTED_SERVER})
                        skill = (out / "skills" / "ufe-docs" / "SKILL.md").read_text(encoding="utf-8")
                        self.assertIn(EXPECTED_SERVER, skill)
                        self.assertIn("planning-only", skill)
                        self.assertIn("not an installer", skill)

    def test_setup_changelog_and_agent_guidance_are_discoverable(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("# UFE3D-MCP", readme)
        self.assertIn("docs/SETUP.md", readme)
        self.assertIn("No skill installation is required", readme)
        self.assertIn("CHANGELOG.md", readme)
        self.assertNotIn("Use UFE3D to", readme)
        self.assertNotIn("add the `UFE3D` server", readme)
        setup = (ROOT / "docs" / "SETUP.md").read_text(encoding="utf-8")
        for tool in ("ufe_docs_status", "ufe_search_docs", "ufe_get_doc"):
            self.assertIn(tool, setup)
        self.assertIn("PENDING/BLOCKED", setup)
        self.assertIn("Preserve", setup)
        for name in ("AGENTS.md", "CONTRIBUTING.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("CHANGELOG.md", text)
            self.assertIn("Unreleased", text)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## Unreleased", changelog)
        self.assertIn("### Migration", changelog)
        for old in ("`UFE3D`", "`ufe_docs`", "`ufe-docs`", "`ufe3d`"):
            self.assertIn(old, changelog)

    def test_relative_links_in_onboarding_documents_exist(self):
        paths = ("README.md", "docs/SETUP.md", "docs/ONBOARDING-VERIFICATION.md",
                 "docs/SPECIFICATION.md", "CONTRIBUTING.md", "AGENTS.md", "CHANGELOG.md")
        for name in paths:
            source = ROOT / name
            text = source.read_text(encoding="utf-8")
            for raw in re.findall(r"\]\(([^\s)]+)\)", text):
                parsed = urlsplit(raw)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                with self.subTest(document=name, link=raw):
                    self.assertTrue((source.parent / unquote(parsed.path)).exists(), raw)


class GeneratedRegistrationProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_generated_stdio_registration_works_without_plugin_or_skill(self):
        with tempfile.TemporaryDirectory(prefix="ufe-onboarding-fixture-") as directory:
            root = Path(directory)
            cache = root / "cache"
            _seed_index(cache)
            guard = root / "guard"
            guard.mkdir()
            (guard / "sitecustomize.py").write_text(_OFFLINE_GUARD, encoding="utf-8")
            marker = root / "network-attempts.txt"
            entry = json.loads(client_config("json", cache))["mcpServers"][EXPECTED_SERVER]
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join((str(guard), str(ROOT / "src")))
            env["UFE_TEST_NETWORK_SENTINEL"] = str(marker)
            env["UFE_DOCS_OFFLINE"] = "1"
            parameters = StdioServerParameters(
                command=entry["command"], args=[*entry["args"], "--offline"],
                cwd=str(root), env=env,
            )
            with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errlog:
                try:
                    async with stdio_client(parameters, errlog=errlog) as (read, write):
                        async with ClientSession(read, write, read_timeout_seconds=15.0) as session:
                            initialized = await session.initialize()
                            self.assertEqual(initialized.server_info.name, EXPECTED_SERVER)
                            self.assertEqual({tool.name for tool in (await session.list_tools()).tools}, TOOLS)
                            status_result = await session.call_tool("ufe_docs_status", {})
                            self.assertFalse(status_result.is_error)
                            status = status_result.structured_content
                            self.assertTrue(status["available"])
                            self.assertNotIn("path", status)
                            search_result = await session.call_tool("ufe_search_docs", {"query": "sparrow uppercut", "limit": 3})
                            self.assertFalse(search_result.is_error)
                            found = search_result.structured_content["results"][0]
                            self.assertEqual(found["doc_id"], MOVE_ID)
                            document_result = await session.call_tool("ufe_get_doc", {"doc_id": found["doc_id"]})
                            self.assertFalse(document_result.is_error)
                            document = document_result.structured_content
                            self.assertEqual(document["url"], MOVE_URL)
                            self.assertIn("face the paper moon", document["content"])
                            self.assertEqual(document["freshness"]["state"], "offline")
                finally:
                    self.assertFalse(marker.exists(), "The synthetic onboarding server attempted network access")


if __name__ == "__main__":
    unittest.main()
