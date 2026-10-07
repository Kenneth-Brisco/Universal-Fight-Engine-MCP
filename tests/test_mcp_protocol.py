"""Exercise the real stdio MCP protocol with original, synthetic docs only.

The child server runs offline, and a child-only socket guard makes any attempted
network access fail the test even if the server catches the resulting exception.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from ufe_docs_mcp.index import Document, build_index


ROOT = Path(__file__).resolve().parents[1]
MOVE_ID = "synthetic.move.sparrow"
MOVE_URL = "https://example.invalid/ufe-docs/#/synthetic:move:sparrow"
MOVE_BODY = """# Sparrow uppercut

This original synthetic move fixture describes a sparrow uppercut.
Its imaginary practice cue is to face the paper moon before pressing jump.

## Timing
The synthetic move starts on frame seven and ends on frame twenty.
"""
TOOLS = {
    "ufe_search_docs",
    "ufe_get_doc",
    "ufe_list_topics",
    "ufe_docs_status",
}

_OFFLINE_GUARD = """\
import os
import socket

_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex

def _record_and_deny(address):
    with open(os.environ['UFE_TEST_NETWORK_SENTINEL'], 'a') as marker:
        marker.write(repr(address) + '\\n')
    raise RuntimeError('Network access is forbidden in offline MCP tests')

def _connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        _record_and_deny(address)
    return _original_connect(self, address)

def _connect_ex(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        _record_and_deny(address)
    return _original_connect_ex(self, address)

def _getaddrinfo(host, port, *args, **kwargs):
    _record_and_deny((host, port))

socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex
socket.getaddrinfo = _getaddrinfo
"""


def _seed_index(cache_dir: Path) -> None:
    build_index(
        [
            Document(
                doc_id=MOVE_ID,
                title="Sparrow uppercut",
                url=MOVE_URL,
                content=MOVE_BODY,
                category="Synthetic moves",
                source_version="synthetic-fixture-v1",
                warnings=("Original test fixture; not UFE documentation.",),
            ),
            Document(
                doc_id="synthetic.character.cloud",
                title="Cloud character",
                url="https://example.invalid/ufe-docs/#/synthetic:character:cloud",
                content="# Cloud character\n\nA wholly invented training character.\n",
                category="Synthetic characters",
                source_version="synthetic-fixture-v1",
            ),
        ],
        cache_dir / "docs.sqlite3",
        metadata={"fixture": True, "source": "Original synthetic documentation"},
    )


class MCPProtocolTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def _server(self, cache_dir: Path):
        with tempfile.TemporaryDirectory(prefix="ufe-mcp-offline-guard-") as guard_dir:
            guard = Path(guard_dir)
            (guard / "sitecustomize.py").write_text(_OFFLINE_GUARD, encoding="utf-8")
            marker = guard / "network-attempts.txt"
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join((str(guard), str(ROOT / "src")))
            env["UFE_TEST_NETWORK_SENTINEL"] = str(marker)
            env["PYTHONUNBUFFERED"] = "1"
            parameters = StdioServerParameters(
                command=sys.executable,
                args=[
                    "-m",
                    "ufe_docs_mcp",
                    "--cache-dir",
                    str(cache_dir),
                    "serve",
                    "--offline",
                ],
                cwd=str(ROOT),
                env=env,
            )
            with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errlog:
                try:
                    async with stdio_client(parameters, errlog=errlog) as (read, write):
                        async with ClientSession(
                            read, write, read_timeout_seconds=15.0
                        ) as session:
                            initialized = await session.initialize()
                            self.assertTrue(initialized.protocol_version)
                            self.assertIsNotNone(initialized.capabilities.tools)
                            yield session
                finally:
                    self.assertFalse(
                        marker.exists(),
                        "The offline MCP server attempted a network connection.",
                    )

    def _payload(self, result) -> dict:
        self.assertFalse(result.is_error, self._text(result))
        if result.structured_content is not None:
            payload = result.structured_content
        else:
            payload = json.loads(self._text(result))
        self.assertIsInstance(payload, dict)
        return payload

    @staticmethod
    def _text(result) -> str:
        return "\n".join(
            block.text for block in result.content if getattr(block, "type", None) == "text"
        )

    async def test_stdio_discovery_search_read_and_validation(self):
        with tempfile.TemporaryDirectory(prefix="ufe-mcp-protocol-") as temp_dir:
            cache = Path(temp_dir)
            _seed_index(cache)
            async with self._server(cache) as session:
                discovery = await session.list_tools()
                tools = {tool.name: tool for tool in discovery.tools}
                self.assertEqual(set(tools), TOOLS)
                for name, tool in tools.items():
                    with self.subTest(tool=name):
                        Draft202012Validator.check_schema(tool.input_schema)
                        self.assertEqual(tool.input_schema.get("type"), "object")
                        self.assertTrue(tool.description)
                        if tool.output_schema is not None:
                            Draft202012Validator.check_schema(tool.output_schema)
                self.assertIn("query", tools["ufe_search_docs"].input_schema["properties"])
                self.assertIn("doc_id", tools["ufe_get_doc"].input_schema["properties"])

                status = self._payload(await session.call_tool("ufe_docs_status", {}))
                self.assertTrue(status["available"])
                self.assertEqual(status["document_count"], 2)
                self.assertTrue(status["offline"])

                search = self._payload(
                    await session.call_tool("ufe_search_docs", {"query": "sparrow uppercut"})
                )
                self.assertTrue(search["results"])
                found = next(item for item in search["results"] if item["doc_id"] == MOVE_ID)
                self.assertEqual(found["url"], MOVE_URL)

                document = self._payload(
                    await session.call_tool("ufe_get_doc", {"doc_id": found["doc_id"]})
                )
                self.assertEqual(document["url"], MOVE_URL)
                self.assertEqual(document["doc_id"], MOVE_ID)
                self.assertIn("face the paper moon", document["content"])
                self.assertTrue(document["warnings"])
                self.assertIsNone(document["next_start_line"])

                topics = self._payload(await session.call_tool("ufe_list_topics", {}))
                self.assertEqual(topics["total"], 2)
                self.assertEqual(
                    {topic["doc_id"] for topic in topics["topics"]},
                    {MOVE_ID, "synthetic.character.cloud"},
                )

                unknown = await session.call_tool("ufe_get_doc", {"doc_id": "does.not.exist"})
                self.assertTrue(unknown.is_error)
                self.assertRegex(self._text(unknown).lower(), r"(unknown|not found|not indexed)")

                invalid_calls = [
                    ("ufe_search_docs", {"query": "sparrow", "limit": 0}),
                    ("ufe_search_docs", {"query": "sparrow", "max_chars": 0}),
                    ("ufe_get_doc", {"doc_id": MOVE_ID, "start_line": 0}),
                    ("ufe_get_doc", {"doc_id": MOVE_ID, "max_lines": 0}),
                    ("ufe_list_topics", {"offset": -1}),
                    ("ufe_list_topics", {"limit": 0}),
                ]
                for name, arguments in invalid_calls:
                    with self.subTest(tool=name, arguments=arguments):
                        result = await session.call_tool(name, arguments)
                        self.assertTrue(result.is_error)
                        self.assertTrue(self._text(result).strip())

    async def test_offline_empty_cache_has_status_and_actionable_guidance(self):
        with tempfile.TemporaryDirectory(prefix="ufe-mcp-empty-") as temp_dir:
            cache = Path(temp_dir)
            async with self._server(cache) as session:
                discovery = await session.list_tools()
                self.assertEqual({tool.name for tool in discovery.tools}, TOOLS)
                status = self._payload(await session.call_tool("ufe_docs_status", {}))
                self.assertFalse(status["available"])
                self.assertTrue(status["offline"])
                self.assertRegex(str(status.get("guidance", "")).lower(), r"(sync|index|cache)")

                result = await session.call_tool("ufe_search_docs", {"query": "sparrow"})
                self.assertTrue(result.is_error)
                self.assertRegex(self._text(result).lower(), r"(sync|index|cache)")
                self.assertFalse((cache / "docs.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
