"""Smoke-test a running UFE3D-MCP HTTP endpoint.

Usage: python scripts/smoke_http.py BASE_URL [--expect-index]
Reads the bearer token from UFE_DOCS_TOKEN. Checks the health route, that the
MCP endpoint rejects a missing token, and that an authenticated client sees
the four read tools with titles. With --expect-index it also searches.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

READ_TOOLS = {"ufe_search_docs", "ufe_get_doc", "ufe_list_topics", "ufe_docs_status"}


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--expect-index", action="store_true")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    token = os.environ["UFE_DOCS_TOKEN"]

    # Probe the explicit endpoint directly, including loopback inside CI;
    # inherited proxy settings must not receive test requests or bearer tokens.
    async with httpx2.AsyncClient(timeout=15.0, trust_env=False) as probe:
        health = await probe.get(base + "/healthz")
        assert health.status_code == 200 and health.json()["server"] == "UFE3D-MCP", health.text
        denied = await probe.post(base + "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert denied.status_code == 401, denied.status_code
    print("health ok; unauthenticated request rejected")

    async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=30.0, trust_env=False) as client:
        async with streamable_http_client(base + "/mcp", http_client=client) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=30.0) as session:
                initialized = await session.initialize()
                assert initialized.server_info.name == "UFE3D-MCP", initialized.server_info.name
                tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                assert set(tools) == READ_TOOLS, sorted(tools)
                assert all(tool.title for tool in tools.values())
                status = (await session.call_tool("ufe_docs_status", {})).structured_content
                print(f"tools ok: {sorted(tools)}; index available: {status['available']}")
                if args.expect_index:
                    search = (await session.call_tool("ufe_search_docs", {"query": "move links", "limit": 1})).structured_content
                    assert search["results"], search
                    print("search ok:", search["results"][0]["doc_id"])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
