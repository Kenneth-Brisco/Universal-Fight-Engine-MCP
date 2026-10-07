"""Local, lexical retrieval over source-attributed documentation.

This module treats document text as data. It never runs source examples, loads
plugins from documents, or sends content to a language model.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Iterator
from urllib.parse import urlsplit


SCHEMA_VERSION = 1
CHUNK_CHARS = 2_000
MAX_QUERY_CHARS = 500
MAX_QUERY_TERMS = 32
MAX_SEARCH_RESULTS = 20
MAX_SEARCH_CHARS = 30_000
MAX_PAGE_LINES = 200
MAX_PAGE_CHARS = 50_000
MAX_TOPICS = 100
MAX_DOCUMENT_CHARS = 2_000_000
MAX_DOCUMENTS = 10_000

_WORDS = re.compile(r"[^\W_]+(?:_[^\W_]+)*", re.UNICODE)
_MARKDOWN_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_SETEXT_HEADING = re.compile(r"^ {0,3}(=+|-+)\s*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_STOPWORDS = frozenset(
    "a an and are as at be been being but by can could did do does for from "
    "had has have how i if in into is it its me my of on or our please should "
    "show tell than that the their them there these they this those to use "
    "using was we were what when where which who why will with would you your".split()
)


@dataclass(frozen=True)
class Document:
    """One source page. ``source_version`` must be explicit, never inferred."""

    doc_id: str
    title: str
    url: str
    content: str
    category: str = ""
    source_version: str | None = None
    warnings: tuple[str, ...] = ()


def _text(value: object, name: str, max_length: int, *, empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if len(value) > max_length or (not empty and not value.strip()):
        raise ValueError(f"{name} must contain 1 to {max_length} characters")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{name} must not contain control characters")
    return value


def _integer(value: object, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _validated_documents(documents: list[Document]) -> list[tuple[Document, str, int]]:
    if not isinstance(documents, list) or not 1 <= len(documents) <= MAX_DOCUMENTS:
        raise ValueError(f"documents must be a nonempty list of at most {MAX_DOCUMENTS} pages")
    validated: list[tuple[Document, str, int]] = []
    seen: set[str] = set()
    for document in documents:
        if not isinstance(document, Document):
            raise ValueError("Every page must be a Document")
        _text(document.doc_id, "doc_id", 256)
        _text(document.title, "title", 512)
        _text(document.url, "url", 4_096)
        _text(document.category, "category", 256, empty=True)
        if document.source_version is not None:
            _text(document.source_version, "source_version", 256)
        parsed = urlsplit(document.url)
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError(f"Document {document.doc_id!r} needs an absolute HTTP(S) source URL")
        if document.doc_id in seen:
            raise ValueError(f"Duplicate doc_id: {document.doc_id}")
        seen.add(document.doc_id)
        if not isinstance(document.content, str) or not document.content.strip():
            raise ValueError(f"Document {document.doc_id!r} has no content")
        if len(document.content) > MAX_DOCUMENT_CHARS or "\x00" in document.content:
            raise ValueError(f"Document content exceeds limits: {document.doc_id}")
        if not isinstance(document.warnings, (tuple, list)) or len(document.warnings) > 20:
            raise ValueError("warnings must contain at most 20 strings")
        for warning in document.warnings:
            _text(warning, "warning", 1_000)
        digest = hashlib.sha256(document.content.encode("utf-8")).hexdigest()
        validated.append((document, digest, len(document.content.splitlines())))
    return validated


def _headings(lines: list[str]) -> dict[int, str]:
    """Locate Markdown sections, excluding headings inside fenced examples."""
    headings: dict[int, str] = {}
    hierarchy: list[tuple[int, str]] = []
    fence_char: str | None = None
    fence_length = 0
    for number, line in enumerate(lines):
        fence = _FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if fence_char is None:
                fence_char, fence_length = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
            continue
        if fence_char:
            continue
        match = _MARKDOWN_HEADING.match(line)
        if match:
            depth, title = len(match.group(1)), match.group(2)
        elif line.strip() and number + 1 < len(lines) and _SETEXT_HEADING.match(lines[number + 1]):
            depth = 1 if lines[number + 1].lstrip().startswith("=") else 2
            title = line.strip()
        else:
            continue
        while hierarchy and hierarchy[-1][0] >= depth:
            hierarchy.pop()
        hierarchy.append((depth, title))
        headings[number] = " / ".join(item[1] for item in hierarchy)[:512]
    return headings


def _chunks(content: str) -> Iterator[tuple[str, int, int, str]]:
    lines = content.splitlines()
    headings = _headings(lines)
    heading = ""
    start = 0
    pending: list[str] = []
    size = 0
    for number, line in enumerate(lines):
        if pending and (number in headings or size + len(line) + 1 > CHUNK_CHARS):
            passage = "\n".join(pending)
            if passage.strip():
                yield heading, start + 1, number, passage
            pending, size = [], 0
        if number in headings:
            heading = headings[number]
        if not pending:
            start = number
        pending.append(line)
        size += len(line) + (1 if len(pending) > 1 else 0)
    if pending:
        passage = "\n".join(pending)
        if passage.strip():
            yield heading, start + 1, len(lines), passage


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE documents (
            doc_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            source_version TEXT,
            warnings TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            line_count INTEGER NOT NULL
        );
        CREATE TABLE chunks (
            chunk_id INTEGER PRIMARY KEY,
            doc_id TEXT NOT NULL REFERENCES documents(doc_id),
            title TEXT NOT NULL,
            heading TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            content TEXT NOT NULL
        );
        CREATE INDEX chunks_document ON chunks(doc_id);
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            title, heading, content,
            content='chunks', content_rowid='chunk_id',
            tokenize="unicode61 remove_diacritics 2 tokenchars '_'"
        );
        CREATE TABLE index_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """
    )


def build_index(documents: list[Document], path: Path, metadata: dict) -> dict:
    """Replace an index atomically, only after validation and a successful build.

    A failed validation, SQLite build, or replacement leaves any existing index
    intact. The source text and explicit warning/version metadata are preserved.
    """
    validated = _validated_documents(documents)
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a dictionary")
    try:
        metadata_json = json.dumps(metadata, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("metadata must be JSON serializable") from error
    if len(metadata_json) > 100_000:
        raise ValueError("metadata exceeds 100000 characters")
    # Decode once so callers cannot mutate the returned/stored nested metadata.
    clean_metadata = json.loads(metadata_json)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with closing(sqlite3.connect(temporary)) as connection:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            _create_schema(connection)
            chunk_count = 0
            for document, digest, line_count in validated:
                connection.execute(
                    "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (document.doc_id, document.title, document.url, document.content,
                     document.category, document.source_version, json.dumps(list(document.warnings)),
                     digest, line_count),
                )
                for heading, start_line, end_line, passage in _chunks(document.content):
                    connection.execute(
                        "INSERT INTO chunks (doc_id, title, heading, start_line, end_line, content) VALUES (?, ?, ?, ?, ?, ?)",
                        (document.doc_id, document.title, heading, start_line, end_line, passage),
                    )
                    chunk_count += 1
            connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')")
            combined = json.dumps(sorted((document.doc_id, digest) for document, digest, _ in validated), ensure_ascii=False)
            status = {
                "available": True,
                "schema_version": SCHEMA_VERSION,
                "indexed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "document_count": len(validated),
                "chunk_count": chunk_count,
                "content_hash": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
                "source_versions": sorted({document.source_version for document, _, _ in validated if document.source_version is not None}),
                "metadata": clean_metadata,
            }
            connection.execute("INSERT INTO index_metadata VALUES ('status', ?)", (json.dumps(status, ensure_ascii=False),))
            connection.commit()
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Built index failed its SQLite integrity check")
        os.replace(temporary, path)
        return {**status, "path": str(path)}
    finally:
        # SQLite removes its journal on normal close; clean up failed builds too.
        for candidate in (temporary, Path(str(temporary) + "-journal")):
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                pass


def _read_connection(path: Path) -> sqlite3.Connection:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Documentation index not found: {path}")
    connection = sqlite3.connect(path.absolute().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        row = connection.execute("SELECT value FROM index_metadata WHERE key='status'").fetchone()
        if row is None or json.loads(row[0]).get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported documentation index; rebuild it")
    except (sqlite3.DatabaseError, ValueError, TypeError, AttributeError) as error:
        connection.close()
        raise ValueError("Invalid or unsupported documentation index; rebuild it") from error
    return connection


def _document_fields(row: sqlite3.Row) -> dict:
    return {
        "doc_id": row["doc_id"],
        "title": row["title"],
        "url": row["url"],
        "category": row["category"],
        "source_version": row["source_version"],
        "warnings": json.loads(row["warnings"]),
        "content_hash": row["content_hash"],
    }


def _query_terms(query: str) -> list[str]:
    if not isinstance(query, str):
        raise ValueError("query must be a string")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"query must contain at most {MAX_QUERY_CHARS} characters")
    terms: list[str] = []
    for match in _WORDS.finditer(query):
        word = match.group().casefold()
        if word not in _STOPWORDS and word not in terms:
            terms.append(word)
        if len(terms) >= MAX_QUERY_TERMS:
            break
    return terms


def _passage_within_budget(content: str, start_line: int, budget: int) -> tuple[str, int, bool, bool]:
    """Prefer complete source lines; mark the rare partial long line explicitly."""
    if len(content) <= budget:
        return content, start_line + len(content.split("\n")) - 1, False, False
    selected: list[str] = []
    used = 0
    for line in content.split("\n"):
        cost = len(line) + (1 if selected else 0)
        if used + cost > budget:
            break
        selected.append(line)
        used += cost
    if selected:
        return "\n".join(selected), start_line + len(selected) - 1, True, False
    return content[:budget], start_line, True, True


def search_docs(path: Path, query: str, limit: int = 5, max_chars: int = 12_000) -> dict:
    """Search safe, quoted lexical terms with BM25 title/heading boosts.

    ``max_chars`` bounds the sum of passage text lengths, not JSON metadata.
    Source URLs are copied exactly; this function never invents anchors.
    """
    limit = _integer(limit, "limit", 1, MAX_SEARCH_RESULTS)
    max_chars = _integer(max_chars, "max_chars", 100, MAX_SEARCH_CHARS)
    terms = _query_terms(query)
    results: list[dict] = []
    truncated = False
    with closing(_read_connection(path)) as connection:
        if not terms:
            return {"query": query, "terms": [], "results": [], "truncated": False}
        # Only extracted word tokens become quoted FTS literals. The user's
        # operators, quotes, parentheses, column syntax and SQL are never run.
        expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        rows = connection.execute(
            """SELECT d.doc_id, d.title, d.url, d.category, d.source_version,
                      d.warnings, d.content_hash, c.heading, c.start_line,
                      c.end_line, c.content, bm25(chunks_fts, 5.0, 3.0, 1.0) AS rank
               FROM chunks_fts
               JOIN chunks c ON c.chunk_id = chunks_fts.rowid
               JOIN documents d ON d.doc_id = c.doc_id
               WHERE chunks_fts MATCH ?
               ORDER BY rank, c.chunk_id LIMIT ?""",
            (expression, limit + 1),
        ).fetchall()
        remaining = max_chars
        for row in rows[:limit]:
            if remaining <= 0:
                truncated = True
                break
            passage, end_line, clipped, partial_line = _passage_within_budget(row["content"], row["start_line"], remaining)
            results.append({
                **_document_fields(row),
                "heading": row["heading"],
                "start_line": row["start_line"],
                "end_line": end_line,
                "content": passage,
                "truncated": clipped,
                "partial_line": partial_line,
            })
            remaining -= len(passage)
            truncated = truncated or clipped
        truncated = truncated or len(rows) > limit
    return {"query": query, "terms": terms, "results": results, "truncated": truncated}


def get_doc(path: Path, doc_id: str, start_line: int = 1, max_lines: int = 100) -> dict:
    """Read complete source lines, with a continuation line for large pages.

    At most 200 lines and 50000 content characters are returned. A single line
    exceeding the character ceiling produces a clear error, never a silently
    altered source line. Use search for a marked excerpt of such a long line.
    """
    _text(doc_id, "doc_id", 256)
    start_line = _integer(start_line, "start_line", 1, 2_147_483_647)
    max_lines = _integer(max_lines, "max_lines", 1, MAX_PAGE_LINES)
    with closing(_read_connection(path)) as connection:
        row = connection.execute("SELECT * FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown document: {doc_id}")
        lines = row["content"].splitlines()
        selected: list[str] = []
        used = 0
        for line in lines[start_line - 1 : start_line - 1 + max_lines]:
            cost = len(line) + (1 if selected else 0)
            if used + cost > MAX_PAGE_CHARS:
                if not selected:
                    raise ValueError(f"Source line {start_line} exceeds the {MAX_PAGE_CHARS}-character page limit; use search for an excerpt")
                break
            selected.append(line)
            used += cost
        end_line = start_line + len(selected) - 1 if selected else None
        next_line = end_line + 1 if end_line is not None and end_line < len(lines) else None
        return {
            **_document_fields(row),
            "total_lines": len(lines),
            "start_line": start_line,
            "end_line": end_line,
            "content": "\n".join(selected),
            "next_start_line": next_line,
        }


def list_topics(path: Path, category: str | None = None, offset: int = 0, limit: int = 50) -> dict:
    """List source pages with exact-category filtering and stable pagination."""
    if category is not None:
        _text(category, "category", 256, empty=True)
    offset = _integer(offset, "offset", 0, 2_147_483_647)
    limit = _integer(limit, "limit", 1, MAX_TOPICS)
    clause = " WHERE category=?" if category is not None else ""
    parameters: tuple = (category,) if category is not None else ()
    with closing(_read_connection(path)) as connection:
        total = connection.execute("SELECT count(*) FROM documents" + clause, parameters).fetchone()[0]
        rows = connection.execute(
            "SELECT doc_id, title, url, category, source_version, warnings, content_hash, line_count "
            "FROM documents" + clause + " ORDER BY title COLLATE NOCASE, doc_id LIMIT ? OFFSET ?",
            (*parameters, limit, offset),
        ).fetchall()
        topics = [{**_document_fields(row), "total_lines": row["line_count"]} for row in rows]
    next_offset = offset + len(topics) if offset + len(topics) < total else None
    return {"topics": topics, "category": category, "offset": offset, "limit": limit, "total": total, "next_offset": next_offset}


def index_status(path: Path) -> dict:
    """Report persisted build/source metadata without opening a writable DB."""
    path = Path(path)
    if not path.is_file():
        return {"available": False, "path": str(path), "reason": "Index file does not exist"}
    with closing(_read_connection(path)) as connection:
        status = json.loads(connection.execute("SELECT value FROM index_metadata WHERE key='status'").fetchone()[0])
    return {**status, "path": str(path)}
