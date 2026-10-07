"""Command-line setup and stdio entry point."""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys

from . import __version__
from .index import build_index, get_doc, index_status, list_topics, search_docs
from .source import fetch_official_documents


def default_cache_dir() -> Path:
    override = os.environ.get("UFE_DOCS_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "IncogLabs" / "ufe-docs-mcp"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "IncogLabs" / "ufe-docs-mcp"
    return Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "incoglabs" / "ufe-docs-mcp"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search official UFE documentation locally through MCP.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--cache-dir", type=Path, default=default_cache_dir())
    commands = parser.add_subparsers(dest="command", required=True)
    sync = commands.add_parser("sync", help="Download public docs and atomically rebuild the local index")
    sync.add_argument("--refresh-pages", action="store_true", help="Also fetch every raw page; respects the site's crawl delay")
    serve = commands.add_parser("serve", help="Run the MCP over stdio; first use downloads the docs in the background")
    serve.add_argument("--offline", action="store_true", help="Use an existing index only; never download")
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
    config = commands.add_parser("client-config", help="Print client configuration for this installed Python environment")
    config.add_argument("--format", choices=("json", "codex"), default="json")
    args = parser.parse_args(argv)
    cache_dir = args.cache_dir.expanduser().resolve()
    path = cache_dir / "docs.sqlite3"
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    try:
        if args.command == "serve":
            from .server import create_server
            offline = args.offline or os.environ.get("UFE_DOCS_OFFLINE", "").lower() in ("1", "true", "yes")
            create_server(cache_dir, offline=offline).run(transport="stdio")
            return 0
        if args.command == "sync":
            docs, metadata = fetch_official_documents(refresh_pages=args.refresh_pages, report=logging.info)
            result = build_index(docs, path, metadata)
        elif args.command == "status":
            result = index_status(path)
        elif args.command == "search":
            result = search_docs(path, args.query, args.limit, args.max_chars)
        elif args.command == "get":
            result = get_doc(path, args.doc_id, args.start_line, args.max_lines)
        elif args.command == "topics":
            result = list_topics(path, args.category, args.offset, args.limit)
        else:
            # Resolving a venv's Python symlink would bypass its installed packages.
            command = os.path.abspath(sys.executable)
            command_args = ["-m", "ufe_docs_mcp", "--cache-dir", str(cache_dir), "serve"]
            if args.format == "codex":
                print('[mcp_servers.ufe_docs]\ncommand = ' + json.dumps(command) + '\nargs = ' + json.dumps(command_args))
                return 0
            result = {"mcpServers": {"ufe_docs": {"command": command, "args": command_args}}}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"UFE Docs MCP: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
