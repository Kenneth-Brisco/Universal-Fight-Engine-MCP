"""Exercise the real stdio MCP protocol with original, synthetic docs only.

Child servers either run offline or use a synthetic replacement source. A
child-only socket guard detects network access even if the server catches it.
"""

from __future__ import annotations

import asyncio
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
REFRESHED_MOVE_BODY = """# Sparrow uppercut

This updated original fixture uses the aurora lantern cue.

## Raw revision
The fictional move begins at frame eleven after an imaginary whistle.
"""
TOOLS = {
    "ufe_search_docs",
    "ufe_get_doc",
    "ufe_list_topics",
    "ufe_docs_status",
    "ufe_refresh_docs",
}

_OFFLINE_GUARD = """\
import os
import socket

_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex

def _record_and_deny(address):
    with open(os.environ['UFE_TEST_NETWORK_SENTINEL'], 'a') as marker:
        marker.write(repr(address) + '\\n')
    raise RuntimeError('Network access is forbidden in MCP protocol tests')

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

_SYNTHETIC_SOURCE = r"""
import json
from pathlib import Path
from ufe_docs_mcp.index import Document
import ufe_docs_mcp.runtime as _runtime

_fixture = json.loads(Path(os.environ['UFE_TEST_SOURCE_FIXTURE']).read_text(encoding='utf-8'))

def _synthetic_fetch(**kwargs):
    raw_pages = kwargs.get('refresh_pages', False)
    with open(os.environ['UFE_TEST_SOURCE_CALLS'], 'a', encoding='utf-8') as calls:
        calls.write(json.dumps({'refresh_pages': raw_pages}) + '\n')
    documents = [Document(**document) for document in _fixture['documents']]
    metadata = dict(_fixture['metadata'])
    metadata['content_mode'] = 'raw_pages' if raw_pages else 'published_catalog'
    return documents, metadata

_runtime.fetch_official_documents = _synthetic_fetch
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
        metadata={
            "fixture": True,
            "source": "Original synthetic documentation",
            "fetched_at": "2000-01-01T00:00:00+00:00",
            "content_mode": "published_catalog",
            "catalog_generated_at": "2000-01-01T00:00:00+00:00",
        },
    )


class MCPProtocolTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def _server(
        self, cache_dir: Path, *, offline: bool = True,
        source_fixture: Path | None = None, source_calls: Path | None = None,
    ):
        if not offline and (source_fixture is None or source_calls is None):
            raise ValueError("Online protocol tests must supply a synthetic source")
        with tempfile.TemporaryDirectory(prefix="ufe-mcp-network-guard-") as guard_dir:
            guard = Path(guard_dir)
            guard_code = _OFFLINE_GUARD + (_SYNTHETIC_SOURCE if source_fixture else "")
            (guard / "sitecustomize.py").write_text(guard_code, encoding="utf-8")
            marker = guard / "network-attempts.txt"
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join((str(guard), str(ROOT / "src")))
            env["UFE_TEST_NETWORK_SENTINEL"] = str(marker)
            env["PYTHONUNBUFFERED"] = "1"
            env["UFE_DOCS_OFFLINE"] = "1" if offline else "0"
            if source_fixture is not None:
                env["UFE_TEST_SOURCE_FIXTURE"] = str(source_fixture)
                env["UFE_TEST_SOURCE_CALLS"] = str(source_calls)
            parameters = StdioServerParameters(
                command=sys.executable,
                args=[
                    "-m",
                    "ufe_docs_mcp",
                    "--cache-dir",
                    str(cache_dir),
                    "serve",
                    "--offline" if offline else "--no-auto-refresh",
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
                        "The MCP test server attempted a network connection.",
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
                        self.assertTrue(tool.title)
                        self.assertEqual(tool.annotations.title, tool.title)
                        if tool.output_schema is not None:
                            Draft202012Validator.check_schema(tool.output_schema)
                self.assertIn("query", tools["ufe_search_docs"].input_schema["properties"])
                self.assertIn("doc_id", tools["ufe_get_doc"].input_schema["properties"])
                self.assertIn("refresh_pages", tools["ufe_refresh_docs"].input_schema["properties"])
                self.assertIsNotNone(tools["ufe_refresh_docs"].annotations)
                self.assertFalse(tools["ufe_refresh_docs"].annotations.read_only_hint)
                for name in TOOLS - {"ufe_refresh_docs"}:
                    self.assertTrue(tools[name].annotations.read_only_hint)

                status = self._payload(await session.call_tool("ufe_docs_status", {}))
                self.assertTrue(status["available"])
                self.assertEqual(status["document_count"], 2)
                self.assertTrue(status["offline"])
                self.assertIsInstance(status["freshness"], dict)
                self.assertEqual(status["freshness"]["state"], "offline")
                self.assertTrue(status["freshness"]["check_overdue"])

                search = self._payload(
                    await session.call_tool("ufe_search_docs", {"query": "sparrow uppercut"})
                )
                self.assertTrue(search["results"])
                found = next(item for item in search["results"] if item["doc_id"] == MOVE_ID)
                self.assertEqual(found["url"], MOVE_URL)
                self.assertIsInstance(search["freshness"], dict)
                self.assertEqual(search["freshness"]["state"], "offline")
                self.assertTrue(search["freshness"]["check_overdue"])
                self.assertEqual(search["snapshot"]["content_hash"], status["content_hash"])
                self.assertEqual(search["snapshot"]["fetched_at"], "2000-01-01T00:00:00+00:00")

                document = self._payload(
                    await session.call_tool("ufe_get_doc", {"doc_id": found["doc_id"]})
                )
                self.assertEqual(document["url"], MOVE_URL)
                self.assertEqual(document["doc_id"], MOVE_ID)
                self.assertIn("face the paper moon", document["content"])
                self.assertTrue(document["warnings"])
                self.assertIsNone(document["next_start_line"])
                self.assertEqual(document["snapshot"], search["snapshot"])
                self.assertIsInstance(document["freshness"], dict)

                topics = self._payload(await session.call_tool("ufe_list_topics", {}))
                self.assertEqual(topics["total"], 2)
                self.assertEqual(
                    {topic["doc_id"] for topic in topics["topics"]},
                    {MOVE_ID, "synthetic.character.cloud"},
                )
                self.assertEqual(topics["snapshot"], search["snapshot"])
                self.assertIsInstance(topics["freshness"], dict)

                before_refresh = (cache / "docs.sqlite3").read_bytes()
                for refresh_pages in (False, True):
                    rejected = await session.call_tool(
                        "ufe_refresh_docs", {"refresh_pages": refresh_pages}
                    )
                    self.assertTrue(rejected.is_error)
                    self.assertIn("offline", self._text(rejected).lower())
                    self.assertRegex(
                        self._text(rejected).lower(), r"(restart|reconnect|sync|without|network)"
                    )
                self.assertEqual((cache / "docs.sqlite3").read_bytes(), before_refresh)

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
                self.assertIsInstance(status["freshness"], dict)
                self.assertRegex(str(status.get("guidance", "")).lower(), r"(sync|index|cache)")

                result = await session.call_tool("ufe_search_docs", {"query": "sparrow"})
                self.assertTrue(result.is_error)
                self.assertRegex(self._text(result).lower(), r"(sync|index|cache)")
                refresh = await session.call_tool("ufe_refresh_docs", {})
                self.assertTrue(refresh.is_error)
                self.assertIn("offline", self._text(refresh).lower())
                self.assertFalse((cache / "docs.sqlite3").exists())

    async def test_explicit_raw_refresh_updates_docs_through_real_stdio(self):
        with tempfile.TemporaryDirectory(prefix="ufe-mcp-explicit-refresh-") as temp_dir:
            cache = Path(temp_dir)
            _seed_index(cache)
            fixture = cache / "synthetic-source.json"
            calls = cache / "synthetic-source-calls.jsonl"
            fixture.write_text(json.dumps({
                "documents": [{
                    "doc_id": MOVE_ID,
                    "title": "Sparrow uppercut",
                    "url": MOVE_URL,
                    "content": REFRESHED_MOVE_BODY,
                    "category": "Synthetic moves",
                    "source_version": "synthetic-fixture-v2",
                    "warnings": ["Original updated test fixture; not UFE documentation."],
                }],
                "metadata": {
                    "fixture": True,
                    "source": "Original synthetic raw-page fixture",
                    "catalog_generated_at": "2000-01-01T00:00:00+00:00",
                },
            }), encoding="utf-8")
            async with self._server(
                cache, offline=False, source_fixture=fixture, source_calls=calls,
            ) as session:
                before = self._payload(await session.call_tool("ufe_docs_status", {}))
                self.assertFalse(before["offline"])
                self.assertFalse(before["freshness"]["automatic_refresh"])
                self.assertTrue(before["freshness"]["check_overdue"])
                self.assertEqual(before["snapshot"]["content_mode"], "published_catalog")
                self.assertFalse(calls.exists(), "A source fetch happened before the explicit request")

                requested = self._payload(await session.call_tool(
                    "ufe_refresh_docs", {"refresh_pages": True},
                ))
                self.assertTrue(requested["accepted"])
                self.assertEqual(requested["reason"], "started")

                async def wait_for_updated_snapshot():
                    for _ in range(100):
                        current = self._payload(await session.call_tool("ufe_docs_status", {}))
                        if current["freshness"]["state"] == "current_to_raw_pages":
                            return current
                        self.assertNotEqual(current["sync_state"], "error", current)
                        await asyncio.sleep(0.02)
                    self.fail("Synthetic raw refresh did not publish within bounded polling")

                after = await asyncio.wait_for(wait_for_updated_snapshot(), timeout=5.0)
                self.assertEqual(after["snapshot"]["content_mode"], "raw_pages")
                self.assertNotEqual(after["snapshot"]["id"], before["snapshot"]["id"])
                self.assertFalse(after["freshness"]["check_overdue"])
                self.assertFalse(after["freshness"]["automatic_refresh"])
                self.assertEqual(after["document_count"], 1)
                self.assertEqual(
                    [json.loads(line) for line in calls.read_text().splitlines()],
                    [{"refresh_pages": True}],
                )

                search = self._payload(await session.call_tool(
                    "ufe_search_docs", {"query": "aurora lantern"},
                ))
                self.assertTrue(search["results"])
                found = search["results"][0]
                self.assertEqual(found["doc_id"], MOVE_ID)
                self.assertEqual(found["url"], MOVE_URL)
                self.assertIn("aurora lantern", found["content"])
                self.assertEqual(search["snapshot"], after["snapshot"])
                self.assertEqual(search["freshness"]["state"], "current_to_raw_pages")

                document = self._payload(await session.call_tool(
                    "ufe_get_doc", {"doc_id": MOVE_ID},
                ))
                self.assertEqual(document["content"], REFRESHED_MOVE_BODY.rstrip("\n"))
                self.assertEqual(document["source_version"], "synthetic-fixture-v2")
                self.assertEqual(document["url"], MOVE_URL)
                self.assertEqual(document["snapshot"], after["snapshot"])
                self.assertEqual(document["freshness"]["state"], "current_to_raw_pages")
                self.assertFalse(document["freshness"]["check_overdue"])


if __name__ == "__main__":
    unittest.main()
