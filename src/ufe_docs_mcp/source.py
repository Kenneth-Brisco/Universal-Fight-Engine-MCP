"""Read the public UFE manual's own catalog, without crawling search engines.

Only published navigation is indexed. JavaScript is parsed as data, never run.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import Counter
from datetime import datetime, timezone
from typing import Callable

from .index import Document

BASE_URL = "https://www.ufe3d.com/ufe2/docs/"
ORIGIN = "https://www.ufe3d.com"
USER_AGENT = "UFE-Docs-MCP/0.1 (+documentation-only local cache)"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
JS_STRING = r'''(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')'''


class SourceError(RuntimeError):
    """The documentation source could not be safely or completely loaded."""


def _allowed_url(url: str) -> bool:
    p = urllib.parse.urlsplit(url)
    decoded_path = urllib.parse.unquote(p.path)
    return (
        p.scheme == "https"
        and p.netloc == "www.ufe3d.com"
        and not p.fragment
        and not any(part in (".", "..") for part in decoded_path.split("/"))
        and "\\" not in decoded_path
        and (p.path == "/robots.txt" or p.path.startswith("/ufe2/docs/"))
    )


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _allowed_url(newurl):
            raise SourceError("The source redirected outside the official UFE documentation.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class OfficialSource:
    """One sync's bounded, rate-limited access to the fixed official origin."""

    def __init__(self, report: Callable[[str], None] | None = None, *, not_before: float | None = None):
        self.report = report or (lambda _: None)
        self.opener = urllib.request.build_opener(_SafeRedirect())
        self.delay = 10.0
        self.last_request = 0.0
        self.not_before = not_before
        self.robots: urllib.robotparser.RobotFileParser | None = None

    def fetch(self, url: str) -> tuple[str, dict[str, str]]:
        if not _allowed_url(url):
            raise SourceError("Only the fixed official UFE documentation origin is allowed.")
        if self.robots is not None and not self.robots.can_fetch(USER_AGENT, url):
            raise SourceError("The official site's robots policy disallows this documentation URL.")
        remaining = self.delay - (time.monotonic() - self.last_request)
        if self.not_before is not None:
            remaining = max(remaining, self.not_before - time.time())
            self.not_before = None
        if remaining > 0:
            time.sleep(remaining)
        self.report("Fetching " + url)
        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/markdown, text/plain, text/html, */*;q=0.5",
            "Cache-Control": "no-cache",
        })
        self.last_request = time.monotonic()
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise SourceError("A documentation response exceeded the 16 MiB limit.")
                content_type = response.headers.get("Content-Type", "")
                if "text/html" in content_type and not url.endswith("/docs/"):
                    raise SourceError("Expected documentation data but received an HTML page.")
                return raw.decode("utf-8-sig"), {
                    "last_modified": response.headers.get("Last-Modified", ""),
                    "etag": response.headers.get("ETag", ""),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
        except (urllib.error.URLError, TimeoutError, UnicodeError) as exc:
            raise SourceError(f"Could not retrieve official documentation: {exc}") from exc

    def load_robots(self) -> None:
        # A missing robots file permits fetching; a denial or network failure does not.
        try:
            text, _ = self.fetch(ORIGIN + "/robots.txt")
        except SourceError as exc:
            if isinstance(exc.__cause__, urllib.error.HTTPError) and exc.__cause__.code == 404:
                text = "User-agent: *\nAllow: /\n"
            else:
                raise
        robots = urllib.robotparser.RobotFileParser()
        robots.parse(text.splitlines())
        delay = robots.crawl_delay(USER_AGENT)
        if delay is None:
            delay = robots.crawl_delay("*")
        if delay is not None:
            if delay > 60:
                raise SourceError("The site's crawl delay exceeds this connector's supported interval.")
            self.delay = max(1.0, float(delay))
        self.robots = robots


def _js_literal(value: str) -> str:
    try:
        result = ast.literal_eval(value)
    except (ValueError, SyntaxError) as exc:
        raise SourceError("The documentation app's literal format changed.") from exc
    if not isinstance(result, str):
        raise SourceError("Expected a string in the public navigation metadata.")
    return result


def visibility_rules(app: str) -> tuple[set[str], set[str]]:
    """Extract the app's explicit hidden IDs and hidden prefixes, without eval."""
    match = re.search(r"\bhiddenNodeIds\s*=\s*new\s+Set\s*\(\s*\[([\s\S]*?)\]\s*\)", app)
    if match is None:
        raise SourceError("Public navigation visibility rules changed; the connector needs an update.")
    hidden = {_js_literal(s.group()) for s in re.finditer(JS_STRING, match.group(1))}
    prefixes: set[str] = set()
    known_adds = 0
    pattern = r"if[ \t]*\(([^\r\n]*?)\)[ \t]*hiddenNodeIds\.add\(n\.id\)\s*;"
    for condition in re.finditer(pattern, app):
        expression = condition.group(1)
        comparisons = list(re.finditer(r"n\.id\s*===\s*(" + JS_STRING + ")", expression))
        starts = list(re.finditer(r"n\.id\.startsWith\(\s*(" + JS_STRING + r")\s*\)", expression))
        remainder = re.sub(r"n\.id\s*===\s*" + JS_STRING, "", expression)
        remainder = re.sub(r"n\.id\.startsWith\(\s*" + JS_STRING + r"\s*\)", "", remainder)
        if re.sub(r"[\s|()]", "", remainder) or not (comparisons or starts):
            raise SourceError("An unfamiliar public visibility condition needs adapter review.")
        hidden.update(_js_literal(m.group(1)) for m in comparisons)
        prefixes.update(_js_literal(m.group(1)) for m in starts)
        known_adds += 1
    for literal in re.finditer(r"hiddenNodeIds\.add\(\s*(" + JS_STRING + r")\s*\)", app):
        hidden.add(_js_literal(literal.group(1)))
        known_adds += 1
    if len(re.findall(r"hiddenNodeIds\.add\(", app)) != known_adds:
        raise SourceError("The source uses an unsupported public visibility rule.")
    return hidden, prefixes


def _object_body(script: str, start: int) -> str:
    depth = 0
    quote = None
    escaped = False
    for i in range(start, len(script)):
        c = script[i]
        if quote:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == quote:
                quote = None
        elif c in "\"'`":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return script[start:i + 1]
    raise SourceError("Incomplete public navigation metadata.")


def app_nodes(app: str) -> list[dict]:
    """Read static public nodes added/repaired by the website's own navigator."""
    nodes = []
    calls = []
    for match in re.finditer(r"ensureNode\(\s*(" + JS_STRING + r")\s*,\s*\{", app):
        calls.append((_js_literal(match.group(1)), match.end() - 1))
    for match in re.finditer(r"upsertNode\(\s*\{", app):
        calls.append((None, match.end() - 1))
    injected = re.search(r"\binjectedNodes\s*=\s*\[", app)
    if injected:
        position = injected.end()
        while position < len(app):
            while position < len(app) and app[position] in " \t\r\n,":
                position += 1
            if position >= len(app) or app[position] == "]":
                break
            if app[position] != "{":
                raise SourceError("The website's added public pages need an adapter update.")
            calls.append((None, position))
            position += len(_object_body(app, position))
    for node_id, start in calls:
        body = _object_body(app, start)
        node = {}
        for key in ("id", "title", "breadcrumb", "node_type", "parent", "editor_family", "content_source_path"):
            value = re.search(r"\b" + key + r"\s*:\s*(" + JS_STRING + ")", body)
            if value:
                node[key] = _js_literal(value.group(1))
        if node_id:
            node["id"] = node_id
        if node.get("id") and node.get("content_source_path"):
            nodes.append(node)
    return nodes


def content_url(source_path: str) -> str:
    path = re.sub(r"^Documentation/content/", "", source_path.replace("\\", "/"), flags=re.I).lower()
    if not re.fullmatch(r"[a-z0-9_./-]+\.md", path) or any(p in ("", ".", "..") for p in path.split("/")):
        raise SourceError("Invalid documentation content path in the public catalog.")
    return BASE_URL + "content/" + path


def page_url(doc_id: str) -> str:
    if not re.fullmatch(r"[a-z0-9_.-]+", doc_id):
        raise SourceError("Invalid public document identifier.")
    return BASE_URL + "#/" + doc_id.replace(".", ":")


def _raw_metadata(body: str, node: dict) -> dict:
    result = dict(node)
    for key, label in (("needs_verification", "Needs verification"), ("legacy_docs_differ", "Legacy docs differ")):
        match = re.search(r"^\*\*" + label + r":\*\*\s*(Yes|No)\s*$", body, re.M)
        if match:
            result[key] = match.group(1) == "Yes"
    # Like the official renderer, separate metadata from the document body.
    result["body_markdown"] = re.sub(
        r"^\*\*(?:Breadcrumb|Node type|Needs verification|Legacy docs differ):\*\*[^\r\n]*(?:\r?\n)?",
        "", body, flags=re.M,
    ).lstrip("\r\n")
    return result


def documents_from_catalog(
    catalog: dict,
    app: str,
    fetch_markdown: Callable[[str], str],
    *,
    refresh_pages: bool = False,
) -> tuple[list[Document], dict]:
    if not isinstance(catalog, dict) or catalog.get("schema_version") != "1.1.0":
        raise SourceError("Unsupported documentation catalog schema; the connector needs an update.")
    raw_nodes = catalog.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes or len(raw_nodes) > 5000:
        raise SourceError("Invalid or empty documentation catalog.")
    hidden, prefixes = visibility_rules(app)

    def visible(doc_id: str) -> bool:
        return doc_id not in hidden and not any(doc_id.startswith(p) for p in prefixes)

    nodes: dict[str, dict] = {}
    excluded = 0
    for node in raw_nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            raise SourceError("Invalid documentation node.")
        doc_id = node["id"]
        if doc_id in nodes:
            raise SourceError("Duplicate document identifiers in the source catalog.")
        if visible(doc_id):
            nodes[doc_id] = dict(node)
        else:
            excluded += 1
    additions = 0
    for patch in app_nodes(app):
        doc_id = patch["id"]
        if not visible(doc_id):
            continue
        if doc_id not in nodes:
            nodes[doc_id] = dict(patch)
            additions += 1
        else:
            old = nodes[doc_id]
            if old.get("content_source_path") != patch["content_source_path"]:
                old.pop("body_markdown", None)
            old.update(patch)
    docs = []
    page_types: Counter = Counter()
    warning_counts: Counter = Counter()
    raw_count = 0
    for doc_id, original_node in nodes.items():
        node = dict(original_node)
        raw_url = content_url(node.get("content_source_path", ""))
        if refresh_pages or not node.get("body_markdown"):
            node = _raw_metadata(fetch_markdown(raw_url), node)
            raw_count += 1
        body = node.get("body_markdown")
        if not isinstance(body, str) or not body.strip() or len(body) > 512_000:
            raise SourceError(f"Missing or invalid content for public document {doc_id}.")
        if node.get("is_placeholder"):
            raise SourceError(f"Public document {doc_id} is marked as a placeholder.")
        warnings = tuple(key for key in ("needs_verification", "legacy_docs_differ") if node.get(key))
        warning_counts.update(warnings)
        page_types[node.get("node_type", "page")] += 1
        docs.append(Document(
            doc_id=doc_id,
            title=str(node.get("title") or doc_id),
            url=page_url(doc_id),
            content=body,
            category=str(node.get("editor_family") or "Documentation"),
            source_version=None,
            warnings=warnings,
        ))
    if not docs:
        raise SourceError("No public documentation remained after filtering.")
    return docs, {
        "source_url": BASE_URL,
        "catalog_url": BASE_URL + "assets/site-data.json",
        "catalog_schema_version": catalog["schema_version"],
        "catalog_generated_at": catalog.get("generated_at"),
        "catalog_node_count": len(raw_nodes),
        "excluded_nonpublic_count": excluded,
        "app_added_node_count": additions,
        "public_document_count": len(docs),
        "page_types": dict(page_types),
        "source_warning_counts": dict(warning_counts),
        "raw_pages_fetched": raw_count,
        "content_mode": "raw_pages" if refresh_pages else "published_catalog",
        "version_note": "The current manual is not a version-pinned API reference; check package-specific behavior in your project.",
    }


def fetch_official_documents(
    *, refresh_pages: bool = False, report: Callable[[str], None] | None = None,
    not_before: float | None = None,
) -> tuple[list[Document], dict]:
    source = OfficialSource(report, not_before=not_before)
    source.load_robots()
    app, app_headers = source.fetch(BASE_URL + "assets/app.js")
    text, catalog_headers = source.fetch(BASE_URL + "assets/site-data.json")
    try:
        catalog = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise SourceError("The official documentation catalog is not valid JSON.") from exc
    docs, metadata = documents_from_catalog(
        catalog, app, lambda url: source.fetch(url)[0], refresh_pages=refresh_pages
    )
    metadata.update({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "catalog_last_modified": catalog_headers["last_modified"],
        "catalog_etag": catalog_headers["etag"],
        "catalog_sha256": catalog_headers["sha256"],
        "app_sha256": app_headers["sha256"],
        "crawl_delay_seconds": source.delay,
    })
    return docs, metadata
