"""Exercise the Streamable HTTP transport over a real socket, offline.

The child server binds a loopback port and serves original synthetic docs in
offline mode, so no documentation source is contacted.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from ufe_docs_mcp.remote import (
    BearerTokenMiddleware, RateLimitMiddleware, build_http_app, is_loopback, load_tokens,
)
from test_mcp_protocol import MOVE_ID, MOVE_URL, TOOLS, _seed_index

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "test-token-0123456789abcdef"
READ_TOOLS = TOOLS - {"ufe_refresh_docs"}


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class HTTPTransportTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def _http_server(self, cache_dir: Path, *extra: str, tokens: str = ""):
        port = _free_port()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        env["UFE_DOCS_HTTP_TOKENS"] = tokens
        env["PYTHONUNBUFFERED"] = "1"
        process = subprocess.Popen(
            [sys.executable, "-m", "ufe_docs_mcp", "--cache-dir", str(cache_dir), "serve",
             "--transport", "http", "--port", str(port), "--offline", *extra],
            cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        base = f"http://127.0.0.1:{port}"
        try:
            async with httpx2.AsyncClient(trust_env=False) as probe:
                for _ in range(200):
                    if process.poll() is not None:
                        self.fail("HTTP server exited: " + process.stderr.read().decode())
                    try:
                        if (await probe.get(base + "/healthz")).status_code == 200:
                            break
                    except httpx2.TransportError:
                        await asyncio.sleep(0.05)
                else:
                    self.fail("HTTP server did not become healthy")
            yield base
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            process.stderr.close()

    @asynccontextmanager
    async def _session(self, base: str, token: str | None = None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with httpx2.AsyncClient(headers=headers, timeout=15.0, trust_env=False) as client:
            async with streamable_http_client(base + "/mcp", http_client=client) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=15.0) as session:
                    await session.initialize()
                    yield session

    @staticmethod
    def _payload(result) -> dict:
        if result.structured_content is not None:
            return result.structured_content
        return json.loads(result.content[0].text)

    async def test_anonymous_loopback_serves_read_tools_without_refresh(self):
        with tempfile.TemporaryDirectory(prefix="ufe-http-") as temp_dir:
            cache = Path(temp_dir)
            _seed_index(cache)
            async with self._http_server(cache) as base:
                async with httpx2.AsyncClient(trust_env=False) as probe:
                    health = (await probe.get(base + "/healthz")).json()
                self.assertEqual(health["status"], "ok")
                self.assertEqual(health["server"], "UFE3D")
                async with self._session(base) as session:
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    self.assertEqual(set(tools), READ_TOOLS)
                    for name, tool in tools.items():
                        with self.subTest(tool=name):
                            self.assertTrue(tool.title)
                            self.assertTrue(tool.annotations.title)
                            self.assertTrue(tool.annotations.read_only_hint)
                            self.assertFalse(tool.annotations.destructive_hint)
                    search = self._payload(await session.call_tool("ufe_search_docs", {"query": "sparrow uppercut"}))
                    self.assertEqual(search["results"][0]["doc_id"], MOVE_ID)
                    self.assertEqual(search["results"][0]["url"], MOVE_URL)
                    document = self._payload(await session.call_tool("ufe_get_doc", {"doc_id": MOVE_ID}))
                    self.assertIn("face the paper moon", document["content"])
                    unknown = await session.call_tool("ufe_get_doc", {"doc_id": "does.not.exist"})
                    self.assertTrue(unknown.is_error)
                    missing = await session.call_tool("ufe_refresh_docs", {})
                    self.assertTrue(missing.is_error)

    async def test_bearer_tokens_gate_mcp_but_not_health(self):
        with tempfile.TemporaryDirectory(prefix="ufe-http-auth-") as temp_dir:
            cache = Path(temp_dir)
            _seed_index(cache)
            async with self._http_server(cache, tokens=TOKEN) as base:
                async with httpx2.AsyncClient(trust_env=False) as probe:
                    self.assertEqual((await probe.get(base + "/healthz")).status_code, 200)
                    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
                    for headers in ({}, {"Authorization": "Bearer wrong-token-0123456789"}, {"Authorization": "Basic " + TOKEN}):
                        with self.subTest(headers=headers):
                            denied = await probe.post(base + "/mcp", json=body, headers=headers)
                            self.assertEqual(denied.status_code, 401)
                            self.assertIn("bearer", denied.headers["www-authenticate"].lower())
                async with self._session(base, TOKEN) as session:
                    status = self._payload(await session.call_tool("ufe_docs_status", {}))
                    self.assertTrue(status["available"])
                    self.assertEqual(status["document_count"], 2)

    async def test_remote_refresh_flag_exposes_refresh_tool(self):
        with tempfile.TemporaryDirectory(prefix="ufe-http-refresh-") as temp_dir:
            cache = Path(temp_dir)
            _seed_index(cache)
            async with self._http_server(cache, "--remote-refresh") as base:
                async with self._session(base) as session:
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    self.assertEqual(set(tools), TOOLS)
                    refresh = tools["ufe_refresh_docs"]
                    self.assertFalse(refresh.annotations.read_only_hint)
                    self.assertFalse(refresh.annotations.destructive_hint)
                    rejected = await session.call_tool("ufe_refresh_docs", {})
                    self.assertTrue(rejected.is_error)  # offline server never downloads


class HTTPPolicyTests(unittest.IsolatedAsyncioTestCase):
    def test_public_bind_requires_tokens_or_explicit_anonymous(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "allow-anonymous"):
                build_http_app(Path(temp_dir), host="0.0.0.0", offline=True)
            self.assertIsNotNone(build_http_app(Path(temp_dir), host="0.0.0.0", offline=True, allow_anonymous=True))
            self.assertIsNotNone(build_http_app(Path(temp_dir), host="0.0.0.0", offline=True, tokens=[TOKEN]))
            with self.assertRaises(ValueError):
                build_http_app(Path(temp_dir), path="/healthz", offline=True)

    def test_loopback_detection(self):
        for host in ("127.0.0.1", "::1", "[::1]", "localhost"):
            self.assertTrue(is_loopback(host), host)
        for host in ("0.0.0.0", "10.0.0.5", "example.com"):
            self.assertFalse(is_loopback(host), host)

    def test_token_loading(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "tokens"
            token_file.write_text("second-token-0123456789\n\n", encoding="utf-8")
            self.assertEqual(
                load_tokens(token_file, {"UFE_DOCS_HTTP_TOKENS": f" {TOKEN} ,"}),
                [TOKEN, "second-token-0123456789"],
            )
        self.assertEqual(load_tokens(None, {}), [])
        with self.assertRaisesRegex(ValueError, "16"):
            load_tokens(None, {"UFE_DOCS_HTTP_TOKENS": "short"})

    async def _call(self, app, path="/mcp", headers=(), client=("203.0.113.9", 1234)):
        sent = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        scope = {"type": "http", "path": path, "headers": list(headers), "client": client}
        await app(scope, receive, send)
        return sent[0]["status"] if sent else None

    async def test_rate_limit_window_and_health_exemption(self):
        async def ok(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        now = [1000.0]
        limited = RateLimitMiddleware(ok, 2, clock=lambda: now[0])
        self.assertEqual([await self._call(limited) for _ in range(3)], [200, 200, 429])
        self.assertEqual(await self._call(limited, path="/healthz"), 200)
        self.assertEqual(await self._call(limited, client=("198.51.100.1", 1)), 200)
        now[0] += 61
        self.assertEqual(await self._call(limited), 200)

        proxied = RateLimitMiddleware(ok, 1, trust_proxy=True, clock=lambda: now[0])
        # A client cannot dodge the limit by forging the left-most forwarded address.
        self.assertEqual(await self._call(proxied, headers=[(b"x-forwarded-for", b"6.6.6.6, 192.0.2.7")]), 200)
        self.assertEqual(await self._call(proxied, headers=[(b"x-forwarded-for", b"7.7.7.7, 192.0.2.7")]), 429)
        self.assertEqual(await self._call(proxied, headers=[(b"x-forwarded-for", b"192.0.2.8")]), 200)

    async def test_bearer_middleware(self):
        async def ok(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        guarded = BearerTokenMiddleware(ok, [TOKEN])
        self.assertEqual(await self._call(guarded), 401)
        self.assertEqual(await self._call(guarded, headers=[(b"authorization", f"Bearer {TOKEN}".encode())]), 200)
        self.assertEqual(await self._call(guarded, headers=[(b"authorization", f"bearer {TOKEN}".encode())]), 200)
        self.assertEqual(await self._call(guarded, headers=[(b"authorization", b"Bearer nope")]), 401)
        self.assertEqual(await self._call(guarded, path="/healthz"), 200)


if __name__ == "__main__":
    unittest.main()
