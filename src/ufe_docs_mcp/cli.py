"""Command-line setup and stdio/HTTP entry points."""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys

from . import __version__
from .index import get_doc, list_topics, search_docs
from .runtime import DEFAULT_REFRESH_HOURS, DocumentationRuntime, sync_cache

SERVER_KEY = "UFE3D"
CLIENT_FORMATS = ("json", "claude-code", "codex", "cursor", "antigravity", "grok")


def default_cache_dir() -> Path:
    override = os.environ.get("UFE_DOCS_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "ufe-docs-mcp"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ufe-docs-mcp"
    return Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "ufe-docs-mcp"


def _default_port() -> int:
    try:
        return int(os.environ.get("PORT", "8000"))
    except ValueError:
        return 8000


def local_launch(cache_dir: Path) -> tuple[str, list[str]]:
    """The absolute interpreter and arguments that start this installation over stdio."""
    # Resolving a venv's Python symlink would bypass its installed packages.
    command = os.path.abspath(sys.executable)
    return command, ["-m", "ufe_docs_mcp", "--cache-dir", str(cache_dir), "serve"]


def client_config(fmt: str, cache_dir: Path, *, url: str | None = None, token_env: str | None = None) -> str:
    """Render the UFE3D entry in one client's native configuration format."""
    command, args = local_launch(cache_dir)
    if fmt == "codex":
        lines = [f"[mcp_servers.{SERVER_KEY}]"]
        if url:
            lines.append("url = " + json.dumps(url))
            if token_env:
                lines.append("bearer_token_env_var = " + json.dumps(token_env))
        else:
            lines += ["command = " + json.dumps(command), "args = " + json.dumps(args)]
        return "\n".join(lines)
    if fmt == "claude-code":
        entry: dict = {"type": "http", "url": url} if url else {"type": "stdio", "command": command, "args": args}
        if url and token_env:
            entry["headers"] = {"Authorization": f"Bearer ${{{token_env}}}"}
        # One shell-quoted JSON argument for `claude mcp add-json`.
        return f"claude mcp add-json --scope user {SERVER_KEY} '{json.dumps(entry)}'"
    if fmt == "cursor":
        entry = {"url": url} if url else {"type": "stdio", "command": command, "args": args}
        if url and token_env:
            entry["headers"] = {"Authorization": f"Bearer ${{env:{token_env}}}"}
        return json.dumps({"mcpServers": {SERVER_KEY: entry}}, indent=2)
    if fmt == "antigravity":
        entry = {"serverUrl": url} if url else {"command": command, "args": args}
        if url and token_env:
            # Antigravity documents no variable expansion in headers; the user pastes the token.
            entry["headers"] = {"Authorization": "Bearer <paste token>"}
        return json.dumps({"mcpServers": {SERVER_KEY: entry}}, indent=2)
    if fmt == "grok":
        if url:
            # Single quotes keep ${VAR} literal; Grok expands it when connecting.
            header = f" -H 'Authorization: Bearer ${{{token_env}}}'" if token_env else ""
            return f"grok mcp add {SERVER_KEY} {url}{header}"
        return f"grok mcp add {SERVER_KEY} {json.dumps(command)} -- " + " ".join(json.dumps(part) for part in args)
    entry = {"type": "http", "url": url} if url else {"command": command, "args": args}
    if url and token_env:
        entry["headers"] = {"Authorization": f"Bearer ${{{token_env}}}"}
    return json.dumps({"mcpServers": {SERVER_KEY: entry}}, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search official UFE documentation locally through MCP.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--cache-dir", type=Path, default=default_cache_dir())
    commands = parser.add_subparsers(dest="command", required=True)
    sync = commands.add_parser("sync", help="Download public docs and atomically rebuild the local index")
    sync.add_argument("--refresh-pages", action="store_true", help="Also fetch every raw page; respects the site's crawl delay")
    serve = commands.add_parser("serve", help="Run the MCP over stdio (default) or Streamable HTTP")
    serve.add_argument("--offline", action="store_true", help="Use an existing index only; never download")
    serve.add_argument("--refresh-hours", type=float, default=DEFAULT_REFRESH_HOURS, help="Automatic source-check interval, at least 1 hour (default: 24)")
    serve.add_argument("--no-auto-refresh", action="store_true", help="Disable automatic downloads; explicit refresh remains available online")
    http = serve.add_argument_group("HTTP transport")
    http.add_argument("--transport", choices=("stdio", "http"), default="stdio", help="stdio for local clients; http for a shared or hosted endpoint")
    http.add_argument("--host", default="127.0.0.1", help="HTTP bind address (default: 127.0.0.1)")
    http.add_argument("--port", type=int, default=_default_port(), help="HTTP port (default: $PORT or 8000)")
    http.add_argument("--path", default="/mcp", help="MCP endpoint path (default: /mcp)")
    http.add_argument("--token-file", type=Path, help="File of accepted bearer tokens; also read from UFE_DOCS_HTTP_TOKENS")
    http.add_argument("--allow-anonymous", action="store_true", help="Serve a non-loopback address without access tokens (or UFE_DOCS_ALLOW_ANONYMOUS=1)")
    http.add_argument("--allowed-host", action="append", default=[], help="Accepted Host header for DNS-rebinding protection (repeatable)")
    http.add_argument("--rate-limit", type=int, default=120, help="Requests per client per minute; 0 disables (default: 120)")
    http.add_argument("--trust-proxy", action="store_true", help="Rate-limit by X-Forwarded-For; only behind a trusted proxy")
    http.add_argument("--remote-refresh", action="store_true", help="Expose ufe_refresh_docs over HTTP (hidden by default)")
    http.add_argument("--stateless", action="store_true", help="Stateless HTTP sessions, for multi-replica deployments")
    commands.add_parser("status", help="Show local index coverage and source metadata")
    search = commands.add_parser("search", help="Try a documentation search without an MCP client")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--max-chars", type=int, default=12000)
    get = commands.add_parser("get", help="Read a cached document ID")
    get.add_argument("doc_id")
    get.add_argument("--start-line", type=int, default=1)
    get.add_argument("--max-lines", type=int, default=100)
    topics = commands.add_parser("topics", help="Browse the cached manual")
    topics.add_argument("--category")
    topics.add_argument("--offset", type=int, default=0)
    topics.add_argument("--limit", type=int, default=50)
    config = commands.add_parser("client-config", help="Print the UFE3D entry for a client's MCP configuration")
    config.add_argument("--format", choices=CLIENT_FORMATS, default="json")
    config.add_argument("--url", help="Configure a remote HTTP endpoint instead of this local installation")
    config.add_argument("--token-env", help="Environment variable holding the bearer token for --url")
    export = commands.add_parser("export-plugin", help="Write a Cursor or Antigravity plugin package that launches this installation")
    export.add_argument("client", choices=("cursor", "antigravity"))
    export.add_argument("--out", type=Path, required=True, help="Directory to create; must not already exist")
    export.add_argument("--url", help="Point the plugin at a remote HTTP endpoint instead")
    args = parser.parse_args(argv)
    cache_dir = args.cache_dir.expanduser().resolve()
    path = cache_dir / "docs.sqlite3"
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    try:
        if args.command == "serve":
            offline = args.offline or os.environ.get("UFE_DOCS_OFFLINE", "").lower() in ("1", "true", "yes")
            if args.transport == "http":
                from .remote import build_http_app, load_tokens, run_http
                app = build_http_app(
                    cache_dir, host=args.host, path=args.path, tokens=load_tokens(args.token_file),
                    allow_anonymous=args.allow_anonymous or os.environ.get("UFE_DOCS_ALLOW_ANONYMOUS", "").lower() in ("1", "true", "yes"), allowed_hosts=args.allowed_host,
                    rate_limit=args.rate_limit, trust_proxy=args.trust_proxy, offline=offline,
                    refresh_hours=args.refresh_hours, auto_refresh=not args.no_auto_refresh,
                    remote_refresh=args.remote_refresh, stateless=args.stateless,
                )
                run_http(app, host=args.host, port=args.port)
                return 0
            from .server import create_server
            create_server(cache_dir, offline=offline, refresh_hours=args.refresh_hours,
                          auto_refresh=not args.no_auto_refresh).run(transport="stdio")
            return 0
        if args.command == "sync":
            result = sync_cache(cache_dir, refresh_pages=args.refresh_pages)
        elif args.command == "status":
            result = DocumentationRuntime(cache_dir, auto_refresh=False).status()
        elif args.command == "search":
            result = DocumentationRuntime(cache_dir, auto_refresh=False).decorate(search_docs(path, args.query, args.limit, args.max_chars))
        elif args.command == "get":
            result = DocumentationRuntime(cache_dir, auto_refresh=False).decorate(get_doc(path, args.doc_id, args.start_line, args.max_lines))
        elif args.command == "topics":
            result = DocumentationRuntime(cache_dir, auto_refresh=False).decorate(list_topics(path, args.category, args.offset, args.limit))
        elif args.command == "export-plugin":
            from .packaging import export_plugin
            out = args.out.expanduser().resolve()
            result = {"client": args.client, "plugin_dir": str(out), "files": export_plugin(args.client, out, cache_dir, url=args.url)}
        else:
            if args.token_env and not args.url:
                raise ValueError("--token-env applies only with --url.")
            print(client_config(args.format, cache_dir, url=args.url, token_env=args.token_env))
            return 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"UFE Docs MCP: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
