"""Keep host diagnostics out of real MCP responses without editing source text.

Fixtures are synthetic. Child servers use a failing synthetic source and never
contact the documentation publisher. HTTP tests use a real loopback socket.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from ufe_docs_mcp.index import (
    Document, build_index, get_doc, index_status, list_topics, search_docs, snapshot_from_status,
)
from ufe_docs_mcp.runtime import DocumentationRuntime
import test_mcp_protocol as protocol
from test_mcp_protocol import MOVE_BODY, MOVE_ID, MOVE_URL, _seed_index
from test_remote import _free_port


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "synthetic-private-operator-marker"
PRIVATE_DETAILS = (
    "synthetic-private-operator-marker /Users/private-fixture/cache "
    r"C:\Users\private-fixture\cache private-fixture@example.invalid"
)


def _seed_legacy_failure(cache: Path) -> None:
    _seed_index(cache)
    (cache / "refresh-state.json").write_text(json.dumps({
        "schema_version": 1,
        "snapshot_id": snapshot_from_status(index_status(cache / "docs.sqlite3"))["id"],
        "last_outcome": "failed",
        "last_error": PRIVATE_DETAILS,
    }), encoding="utf-8")


class RuntimePrivacyTests(unittest.TestCase):
    def test_existing_failure_history_is_private_but_remains_diagnostic_locally(self):
        with tempfile.TemporaryDirectory(prefix=PRIVATE_MARKER) as directory:
            cache = Path(directory)
            _seed_legacy_failure(cache)
            runtime = DocumentationRuntime(cache, auto_refresh=False)
            status = runtime.status()
            self.assertNotIn("path", status)
            self.assertEqual(status["freshness"]["state"], "check_failed")
            self.assertIn("local logs", status["freshness"]["last_error"])
            for result in (
                status,
                runtime.decorate(search_docs(runtime.path, "sparrow")),
                runtime.decorate(get_doc(runtime.path, MOVE_ID)),
                runtime.decorate(list_topics(runtime.path)),
            ):
                serialized = json.dumps(result)
                self.assertNotIn(PRIVATE_MARKER, serialized)
                self.assertNotIn("private-fixture", serialized)
                self.assertNotIn(str(cache), serialized)
            self.assertEqual(index_status(runtime.path)["path"], str(runtime.path))
            self.assertIn(PRIVATE_MARKER, (cache / "refresh-state.json").read_text())
            runtime.close()

    def test_cache_read_failures_and_history_write_warnings_use_safe_guidance(self):
        with tempfile.TemporaryDirectory(prefix=PRIVATE_MARKER) as directory:
            cache = Path(directory)
            _seed_index(cache)
            runtime = DocumentationRuntime(cache, auto_refresh=False)
            runtime._state_warning = PRIVATE_DETAILS
            warning = runtime.status()
            self.assertIn("saving update history failed", json.dumps(warning))
            self.assertNotIn(PRIVATE_MARKER, json.dumps(warning))
            with mock.patch("ufe_docs_mcp.runtime.index_status", side_effect=PermissionError(PRIVATE_DETAILS)):
                status = runtime.status()
            self.assertFalse(status["available"])
            self.assertNotIn("path", status)
            self.assertIn("sync", status["reason"])
            self.assertNotIn(PRIVATE_MARKER, json.dumps(status))
            runtime.close()

    def test_document_paths_and_publisher_metadata_are_not_redacted(self):
        with tempfile.TemporaryDirectory(prefix=PRIVATE_MARKER) as directory:
            cache = Path(directory)
            body = "# Synthetic example\n\nThe documented example is /examples/Assets/move.asset.\n"
            build_index([Document(MOVE_ID, "Synthetic example", MOVE_URL, body,
                                  warnings=("needs_verification",))], cache / "docs.sqlite3", {
                "fetched_at": "2000-01-01T00:00:00Z", "content_mode": "published_catalog",
                "catalog_generated_at": "2000-01-01", "source_url": MOVE_URL,
            })
            runtime = DocumentationRuntime(cache, auto_refresh=False)
            result = runtime.decorate(get_doc(runtime.path, MOVE_ID), verbose=True)
            self.assertEqual(result["content"], body.rstrip("\n"))
            self.assertEqual(result["url"], MOVE_URL)
            self.assertEqual(result["warnings"], ["needs_verification"])
            self.assertEqual(result["snapshot"]["catalog_generated_at"], "2000-01-01")
            self.assertEqual(runtime.status()["metadata"]["source_url"], MOVE_URL)
            runtime.close()


_HTTP_CHILD = r"""
from contextlib import contextmanager
import logging
from pathlib import Path
import sys
from mcp.server.mcpserver.exceptions import ToolError
import ufe_docs_mcp.runtime as runtime
import ufe_docs_mcp.server as server
from ufe_docs_mcp.remote import build_http_app, run_http

cache, port, scenario, private_details = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
logging.basicConfig(level=logging.WARNING)

def fail_source(**kwargs):
    raise OSError(private_details + ' ' + str(cache / 'source-download'))

# No test path can accidentally contact the publisher.
runtime.fetch_official_documents = fail_source

if scenario == 'start':
    @contextmanager
    def denied_lock(*args, **kwargs):
        raise PermissionError(13, private_details, str(cache / 'refresh-lock.sqlite3'))
        yield
    runtime._refresh_lock = denied_lock
elif scenario == 'reads':
    def failed_search(*args, **kwargs):
        raise OSError(private_details)
    def failed_document(*args, **kwargs):
        raise ValueError(private_details)
    def failed_topics(*args, **kwargs):
        raise ToolError(private_details)
    server.search_docs = failed_search
    server.get_doc = failed_document
    server.list_topics = failed_topics
elif scenario == 'status':
    def failed_status(*args, **kwargs):
        raise RuntimeError(private_details)
    runtime.index_status = failed_status

app = build_http_app(cache, auto_refresh=False, remote_refresh=True, rate_limit=0)
run_http(app, host='127.0.0.1', port=port)
"""


class HTTPPrivacyTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def _server(self, cache: Path, scenario: str = "source"):
        port = _free_port()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        env["PYTHONUNBUFFERED"] = "1"
        with tempfile.TemporaryFile(mode="w+b") as log:
            process = subprocess.Popen(
                [sys.executable, "-c", _HTTP_CHILD, str(cache), str(port), scenario, PRIVATE_DETAILS],
                cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=log,
            )
            base = f"http://127.0.0.1:{port}"
            try:
                # These clients talk only to the loopback fixture, never to a
                # workstation's configured external proxy.
                async with httpx2.AsyncClient(timeout=2.0, trust_env=False) as probe:
                    for _ in range(200):
                        if process.poll() is not None:
                            log.seek(0)
                            self.fail("Synthetic HTTP server exited: " + log.read().decode())
                        try:
                            if (await probe.get(base + "/healthz")).status_code == 200:
                                break
                        except httpx2.TransportError:
                            pass
                        await asyncio.sleep(0.05)
                    else:
                        self.fail("Synthetic HTTP server did not become healthy")
                async with httpx2.AsyncClient(timeout=15.0, trust_env=False) as client:
                    async with streamable_http_client(base + "/mcp", http_client=client) as (read, write):
                        async with ClientSession(read, write, read_timeout_seconds=15.0) as session:
                            await session.initialize()
                            yield session
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                log.seek(0)
                self.last_server_log = log.read().decode()

    def _safe(self, result, cache: Path) -> None:
        # Check the complete protocol result, including both text and structured
        # representations and SDK-generated error text.
        serialized = result.model_dump_json()
        self.assertNotIn(PRIVATE_MARKER, serialized)
        self.assertNotIn("private-fixture", serialized)
        self.assertNotIn(str(cache), serialized)

    def _payload(self, result, cache: Path) -> dict:
        self._safe(result, cache)
        self.assertFalse(result.is_error, result)
        self.assertIsNotNone(result.structured_content)
        text = "\n".join(block.text for block in result.content if block.type == "text")
        self.assertEqual(json.loads(text), result.structured_content)
        return result.structured_content

    async def test_failed_refresh_and_restarted_cached_reads_hide_private_diagnostics(self):
        with tempfile.TemporaryDirectory(prefix=PRIVATE_MARKER) as directory:
            cache = Path(directory)
            _seed_index(cache)
            async with self._server(cache) as session:
                accepted = self._payload(await session.call_tool("ufe_refresh_docs", {}), cache)
                self.assertTrue(accepted["accepted"])
                for _ in range(100):
                    status = self._payload(await session.call_tool("ufe_docs_status", {}), cache)
                    if status["freshness"]["state"] == "check_failed":
                        break
                    await asyncio.sleep(0.02)
                else:
                    self.fail("Synthetic failed refresh did not finish")
                self.assertTrue(status["available"])
                self.assertNotIn("path", status)
                self.assertIn("local logs", status["freshness"]["last_error"])
                for tool, arguments in (
                    ("ufe_search_docs", {"query": "sparrow"}),
                    ("ufe_get_doc", {"doc_id": MOVE_ID}),
                    ("ufe_list_topics", {}),
                ):
                    result = self._payload(await session.call_tool(tool, arguments), cache)
                    self.assertEqual(result["freshness"]["state"], "check_failed")
                    if tool == "ufe_get_doc":
                        self.assertEqual(result["content"], MOVE_BODY.rstrip("\n"))
                        self.assertEqual(result["url"], MOVE_URL)
            self.assertIn(PRIVATE_MARKER, self.last_server_log)
            self.assertIn(PRIVATE_MARKER, (cache / "refresh-state.json").read_text())
            async with self._server(cache) as session:
                restarted = self._payload(await session.call_tool("ufe_docs_status", {}), cache)
                self.assertEqual(restarted["freshness"]["state"], "check_failed")

    async def test_failed_refresh_start_returns_safe_actionable_error(self):
        with tempfile.TemporaryDirectory(prefix=PRIVATE_MARKER) as directory:
            cache = Path(directory)
            _seed_index(cache)
            async with self._server(cache, "start") as session:
                failure = await session.call_tool("ufe_refresh_docs", {})
                self._safe(failure, cache)
                self.assertTrue(failure.is_error)
                self.assertIn("write permissions", failure.content[0].text)
                status = self._payload(await session.call_tool("ufe_docs_status", {}), cache)
                self.assertEqual(status["freshness"]["state"], "check_failed")
            self.assertIn(PRIVATE_MARKER, self.last_server_log)

    async def test_unexpected_errors_cannot_leak_through_sdk_error_rendering(self):
        with tempfile.TemporaryDirectory(prefix=PRIVATE_MARKER) as directory:
            cache = Path(directory)
            _seed_index(cache)
            for scenario, calls in (
                ("reads", (("ufe_search_docs", {"query": "sparrow"}),
                           ("ufe_get_doc", {"doc_id": MOVE_ID}), ("ufe_list_topics", {}))),
                ("status", (("ufe_docs_status", {}),)),
            ):
                with self.subTest(scenario=scenario):
                    async with self._server(cache, scenario) as session:
                        for tool, arguments in calls:
                            failure = await session.call_tool(tool, arguments)
                            self._safe(failure, cache)
                            self.assertTrue(failure.is_error)
                            self.assertIn("local logs", failure.content[0].text)
                    self.assertIn(PRIVATE_MARKER, self.last_server_log)

    async def test_missing_or_corrupt_cache_does_not_disclose_its_location(self):
        with tempfile.TemporaryDirectory(prefix=PRIVATE_MARKER) as directory:
            for kind in ("missing", "corrupt"):
                with self.subTest(cache=kind):
                    cache = Path(directory) / kind
                    cache.mkdir()
                    if kind == "corrupt":
                        (cache / "docs.sqlite3").write_text(PRIVATE_DETAILS)
                    async with self._server(cache) as session:
                        status = self._payload(await session.call_tool("ufe_docs_status", {}), cache)
                        self.assertFalse(status["available"])
                        self.assertNotIn("path", status)
                        self.assertIn("sync", status["guidance"])
                        failure = await session.call_tool("ufe_get_doc", {"doc_id": MOVE_ID})
                        self._safe(failure, cache)
                        self.assertTrue(failure.is_error)

    async def test_user_validation_guidance_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix=PRIVATE_MARKER) as directory:
            cache = Path(directory)
            _seed_index(cache)
            async with self._server(cache) as session:
                failure = await session.call_tool("ufe_get_doc", {"doc_id": "invalid\nid"})
                self._safe(failure, cache)
                self.assertTrue(failure.is_error)
                self.assertIn("must not contain control characters", failure.content[0].text)


class StdioPrivacyTests(unittest.IsolatedAsyncioTestCase):
    _server = protocol.MCPProtocolTests._server

    async def test_stdio_status_and_cached_read_hide_legacy_private_errors(self):
        with tempfile.TemporaryDirectory(prefix=PRIVATE_MARKER) as directory:
            cache = Path(directory)
            _seed_legacy_failure(cache)
            async with self._server(cache) as session:
                for tool, arguments in (("ufe_docs_status", {}), ("ufe_get_doc", {"doc_id": MOVE_ID})):
                    result = await session.call_tool(tool, arguments)
                    self.assertFalse(result.is_error)
                    self.assertNotIn(PRIVATE_MARKER, result.model_dump_json())
                    self.assertNotIn("private-fixture", result.model_dump_json())
                    self.assertIn("local logs", result.structured_content["freshness"]["last_error"])


if __name__ == "__main__":
    unittest.main()
