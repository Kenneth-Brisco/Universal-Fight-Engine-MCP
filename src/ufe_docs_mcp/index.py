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
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Iterator
from urllib.parse import urlsplit

from . import reference


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
    # Words that appear on nearly every page of this manual or in nearly every
    # question about it, and so only dilute ranking.
    + "ufe find setting settings manual".split()
)


_PREFIX_MIN_CHARS = 5
# Stems shorter than the minimum that are still safe and useful as prefixes.
_PREFIX_STEMS = frozenset(("link",))
_CANDIDATES = 400
_MAX_PER_DOC = 2
# A budget-clipped passage with less body text than this is dropped.
_MIN_CLIPPED_BODY = 120
# Section headings used throughout the UFE manual. Options sections hold the
# settings themselves; Related Pages sections are link lists for navigation.
_SECTION_KINDS = {
    "options": "options", "overview": "overview",
    "related pages": "related", "video tutorial": "video",
}
_KIND_WEIGHTS = {"options": 1.25, "overview": 1.0, "body": 1.0, "video": 0.4}
# Curated query concepts for fighting-game vocabulary the manual words
# differently. Each adds terms; it never removes the user's own words.
_LINK_WORDS = r"cancel\w*|chain\w*|follow[- ]?ups?"
# "move" as a noun right after a qualifier or determiner, so "after the other
# player moves" (a verb) and "after the move connects" (a hit confirm) do not
# count as a move prerequisite.
_MOVE_NOUN = r"moves?\b(?!\s+(?:connect|hit|land|whiff|miss)\w*)"
_CONCEPTS = (
    ("move_links", re.compile(
        r"\b(?:" + _LINK_WORDS + r")|\bcombo\w*\b.*\binto\b|\binto\b.*\bcombo\w*\b"
    ), ("link",), "move.links", re.compile(r"cancel\w*|chain\w*|follow\w*|ups?|combo\w*")),
    ("required_moves", re.compile(
        r"\bprerequisite\w*|\brequire\w*\b.*\bmoves?\b|\bafter\b.*\b(?:another|previous|specific|preceding)\s+" + _MOVE_NOUN
        + r"|\bonly\b.*\bafter\b.*\b(?:a|an|the|another|that|this|one)\s+(?:(?:specific|particular|certain|previous|preceding|other|given|opening)\s+)?"
        + _MOVE_NOUN
    ), ("required", "prerequisite"), "move.links.group.required-moves",
        re.compile(r"prerequisite\w*|require\w*|only|after|another|previous|specific|other|preceding|moves?")),
    ("gauge_flow", re.compile(
        r"\b(?:regen\w*|refill\w*|recharg\w*|recover\w*|passive\w*|drain\w*|auto\w*[- ]?fill\w*)\b.*\b(?:gauge|meter|stamina|energy)\b"
        r"|\b(?:gauge|meter|stamina|energy)\b.*\b(?:regen\w*|refill\w*|recharg\w*|recover\w*|drain\w*|fill\w*)\b"
    ), ("gauge",), "character.gauge",
        re.compile(r"regen\w*|refill\w*|recharg\w*|recover\w*|passive\w*|drain\w*|fill\w*|auto\w*|gauge\w*|meter\w*|stamina|energy")),
    ("hit_stop", re.compile(r"\bhit[- ]?stop\b|\bhit[- ]?freeze\b|\bfreez\w*"), ("freezing",), None, None),
    ("hit_stun", re.compile(r"\bhitstun\b"), ("hit", "stun"), None, None),
    ("block_stun", re.compile(r"\bblockstun\b"), ("block", "stun"), None, None),
)
_BOLD_LABEL = re.compile(r"\*\*\[?([^*\]\n]{3,80})\]?(?:\([^)\n]*\))?\*\*")
_VIDEO_EMBED = re.compile(r'<iframe\b[^>]*\bsrc="https://www\.youtube(?:-nocookie)?\.com/embed/([A-Za-z0-9_-]{6,20})"[^>]*>', re.IGNORECASE)
_VIDEO_TITLE = re.compile(r'\btitle="([^"<>]{1,200})"')


class RequestValidationError(ValueError):
    """An actionable input/size error whose message is safe for MCP clients.

    Construct messages only from fixed field names and numeric bounds. Internal
    exceptions, filenames and source text must never be wrapped in this type.
    """


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
        raise RequestValidationError(f"{name} must be a string")
    if len(value) > max_length or (not empty and not value.strip()):
        raise RequestValidationError(f"{name} must contain 1 to {max_length} characters")
    if any(ord(char) < 32 for char in value):
        raise RequestValidationError(f"{name} must not contain control characters")
    return value


def _integer(value: object, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RequestValidationError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise RequestValidationError(f"{name} must be between {minimum} and {maximum}")
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
    """Split at headings. A heading with no body of its own (such as a page
    title directly followed by its first section) stays with the next section,
    so no passage consists only of headings."""
    lines = content.splitlines()
    headings = _headings(lines)
    heading = ""
    start = 0
    pending: list[str] = []
    size = 0
    has_body = False
    for number, line in enumerate(lines):
        oversized = size + len(line) + 1 > CHUNK_CHARS
        if pending and ((number in headings and has_body) or oversized):
            passage = "\n".join(pending)
            if passage.strip():
                yield heading, start + 1, number, passage
            pending, size, has_body = [], 0, False
        if number in headings:
            heading = headings[number]
        elif line.strip() and not _SETEXT_HEADING.match(line):
            has_body = True
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
                "index_revision": _revision_hash({document.doc_id: _document_revision(document) for document, _, _ in validated}),
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


def _revision_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _document_revision(document: Document) -> str:
    return _revision_hash({
        "doc_id": document.doc_id, "title": document.title, "url": document.url,
        "category": document.category, "source_version": document.source_version,
        "warnings": list(document.warnings),
        "content_hash": hashlib.sha256(document.content.encode("utf-8")).hexdigest(),
    })


def document_revisions(path: Path) -> dict[str, str]:
    """Fingerprint content and meaningful metadata for update summaries."""
    with closing(_read_connection(path)) as connection:
        return {row["doc_id"]: _revision_hash(_document_fields(row))
                for row in connection.execute("SELECT * FROM documents")}


def snapshot_from_status(status: dict) -> dict:
    """Small provenance record; fetched_at is not the publisher's edit date."""
    metadata = status.get("metadata", {})
    result = {
        "indexed_at": status.get("indexed_at"),
        "fetched_at": metadata.get("fetched_at"),
        "content_mode": metadata.get("content_mode", "unknown"),
        "catalog_generated_at": metadata.get("catalog_generated_at"),
        "content_hash": status.get("content_hash"),
        "index_revision": status.get("index_revision"),
    }
    result["id"] = _revision_hash(result)
    return result


def _snapshot(connection: sqlite3.Connection) -> dict:
    # This connection also supplies the passages, even if another process
    # publishes a replacement database during the read.
    status = json.loads(connection.execute("SELECT value FROM index_metadata WHERE key='status'").fetchone()[0])
    return snapshot_from_status(status)


def _query_terms(query: str) -> list[str]:
    if not isinstance(query, str):
        raise RequestValidationError("query must be a string")
    if len(query) > MAX_QUERY_CHARS:
        raise RequestValidationError(f"query must contain at most {MAX_QUERY_CHARS} characters")
    terms: list[str] = []
    for match in _WORDS.finditer(query):
        word = match.group().casefold()
        # Single letters are possessives ("UFE's") or initials, never topics.
        if len(word) > 1 and word not in _STOPWORDS and word not in terms:
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


def _chunk_kind(heading: str, content: str) -> str:
    """Classify a passage by its own section heading and body."""
    if all(not line.strip() or _MARKDOWN_HEADING.match(line) for line in content.splitlines()):
        return "heading_only"
    section = heading.rsplit(" / ", 1)[-1].strip().casefold()
    return _SECTION_KINDS.get(section, "body")


def _concepts(query: str) -> list[tuple[tuple[str, ...], str | None, re.Pattern | None]]:
    """Return (extra terms, home page ID prefix, trigger-word pattern) for each matching concept."""
    folded = query.casefold()
    return [(extra, home, trigger) for _name, pattern, extra, home, trigger in _CONCEPTS if pattern.search(folded)]


def _fts_literal(term: str) -> str:
    quoted = '"' + term.replace('"', '""') + '"'
    # Prefix matching lets "link" find links/linked/linkable and "cancel" find
    # cancelling. Short words stay exact so they do not match unrelated terms.
    return quoted + "*" if len(term) >= _PREFIX_MIN_CHARS or term in _PREFIX_STEMS else quoted


def _term_pattern(term: str) -> re.Pattern:
    suffix = r"\w*" if len(term) >= _PREFIX_MIN_CHARS or term in _PREFIX_STEMS else r"\b"
    return re.compile(r"\b" + re.escape(term) + suffix, re.IGNORECASE)


def _videos(content: str) -> list[dict]:
    """Video embeds are links only; titles come from the page's own markup."""
    videos: list[dict] = []
    for match in _VIDEO_EMBED.finditer(content):
        video_id = match.group(1)
        if any(video["youtube_id"] == video_id for video in videos):
            continue
        title = _VIDEO_TITLE.search(match.group(0))
        videos.append({
            "youtube_id": video_id,
            "title": title.group(1) if title else None,
            "url": "https://www.youtube.com/watch?v=" + video_id,
        })
    return videos[:5]


def search_docs(path: Path, query: str, limit: int = 5, max_chars: int = 12_000) -> dict:
    """Search safe, quoted lexical terms, then rerank for useful passages.

    BM25 (with title/heading boosts) supplies candidates. Reranking prefers
    passages that cover more of the question and Options sections, drops
    heading-only and Related Pages link lists while other passages match, and
    limits each document to two passages so one page cannot fill every slot.
    Serialized UFE field names (for example ``frameLinks``) resolve through the
    supplementary field reference, reported separately in ``field_matches``.

    ``max_chars`` bounds the sum of passage text lengths, not JSON metadata.
    Source URLs are copied exactly; this function never invents anchors.
    """
    limit = _integer(limit, "limit", 1, MAX_SEARCH_RESULTS)
    max_chars = _integer(max_chars, "max_chars", 100, MAX_SEARCH_CHARS)
    terms = _query_terms(query)
    field_matches = reference.match_fields(query)
    results: list[dict] = []
    truncated = False
    with closing(_read_connection(path)) as connection:
        snapshot = _snapshot(connection)
        if not terms:
            return {"query": query, "terms": [], "results": [], "truncated": False, "snapshot": snapshot}
        # Each group is one requirement of the question: a query word together
        # with any curated synonyms, or a field's Inspector label words.
        groups: list[tuple[str, ...]] = []
        field_words = {word for match in field_matches for word in match["query_words"]}
        for term in terms:
            if term not in field_words:
                groups.append((term,))
        concept_homes: list[tuple[str, re.Pattern]] = []
        for extra, home, trigger in _concepts(query):
            groups.append(extra)
            if home:
                concept_homes.append((home, trigger))
        target_docs: dict[str, list[str]] = {}
        for match in field_matches:
            label_text = match["label"]
            if match.get("label_in_manual") is False and match.get("doc_id"):
                # The manual never shows this label; search by its page instead.
                page = connection.execute("SELECT title FROM documents WHERE doc_id=?", (match["doc_id"],)).fetchone()
                label_text = page["title"] if page else label_text
            label_terms = tuple(_query_terms(label_text))
            if label_terms:
                groups.append(label_terms)
            if match.get("doc_id"):
                target_docs.setdefault(match["doc_id"], []).append(match["label"])
        search_terms: list[str] = []
        for group in groups:
            for term in group:
                if term not in search_terms:
                    search_terms.append(term)
        if not search_terms:
            return {"query": query, "terms": terms, "results": [], "truncated": False,
                    "snapshot": snapshot, **_field_payload(field_matches)}
        # Only extracted word tokens become quoted FTS literals. The user's
        # operators, quotes, parentheses, column syntax and SQL are never run.
        expression = " OR ".join(_fts_literal(term) for term in search_terms[:MAX_QUERY_TERMS * 2])
        rows = connection.execute(
            """SELECT d.doc_id, d.title, d.url, d.category, d.source_version,
                      d.warnings, d.content_hash, c.heading, c.start_line,
                      c.end_line, c.content, c.chunk_id, bm25(chunks_fts, 5.0, 3.0, 1.0) AS rank
               FROM chunks_fts
               JOIN chunks c ON c.chunk_id = chunks_fts.rowid
               JOIN documents d ON d.doc_id = c.doc_id
               WHERE chunks_fts MATCH ?
               ORDER BY rank, c.chunk_id LIMIT ?""",
            (expression, _CANDIDATES),
        ).fetchall()
        patterns = [[_term_pattern(term) for term in group] for group in groups]
        folded_query = " ".join(query.casefold().split())
        # Weight each requirement by its rarest term, so a specific word
        # ("plinking") counts for more than generic ones ("setting", "find").
        total = connection.execute("SELECT count(*) FROM chunks").fetchone()[0] or 1
        frequency: dict[str, int] = {}
        for term in dict.fromkeys(search_terms + terms):
            frequency[term] = connection.execute(
                "SELECT count(*) FROM chunks_fts WHERE chunks_fts MATCH ?", (_fts_literal(term),)
            ).fetchone()[0]
        weights = [max(math.log(1 + total / (1 + frequency.get(term, 0))) for term in group) for group in groups]
        weight_sum = sum(weights) or 1.0
        homes = [home for home, _trigger in concept_homes]
        triggers = [trigger for _home, trigger in concept_homes]
        # Distinctive topic words: query words (other than a concept's own
        # trigger words) that appear in at most three page titles. A page
        # titled with one ("Throw Tutorial" for "cancel a throw") is boosted
        # as much as a concept's home pages, so the question's own topic is
        # not displaced by the concept.
        titles = [row[0] for row in connection.execute("SELECT title FROM documents")]
        topic_terms = []
        for term in terms:
            if any(trigger.fullmatch(term) for trigger in triggers):
                continue
            pattern = _term_pattern(term)
            if 0 < sum(1 for title in titles if pattern.search(title)) <= 3:
                topic_terms.append(pattern)
        # A question quoting an exact setting label is about that setting.
        # Three words or more ("Allow Move Canceling"), so a two-word phrase
        # such as "special move" does not switch the concept off.
        if any(len(label.split()) >= 3 and label.casefold() in " ".join(query.casefold().split())
               for row in rows for label in _BOLD_LABEL.findall(row["content"])):
            homes = []
        scored: list[tuple[float, int, sqlite3.Row]] = []
        boosted: list[tuple[float, int, sqlite3.Row]] = []
        fallback: list[tuple[float, int, sqlite3.Row]] = []
        best_rank: dict[str, float] = {}
        for row in rows:
            best_rank[row["doc_id"]] = min(best_rank.get(row["doc_id"], 0.0), row["rank"])
        page_text: dict[str, str] = {}
        for row in rows:
            kind = _chunk_kind(row["heading"], row["content"])
            if kind == "heading_only":
                continue  # The section's own passage carries this heading.
            # The question names this page ("gauge options", "hit stun
            # options"): judge relevance for the page as a whole, so its
            # Options section is preferred over an Overview that merely
            # repeats more of the question's words.
            title_terms = _query_terms(row["title"])
            named = bool(title_terms) and all(
                any(_term_pattern(term).fullmatch(word) or word == term for term in terms) for word in title_terms)
            if named:
                if row["doc_id"] not in page_text:
                    page = connection.execute("SELECT title, content FROM documents WHERE doc_id=?", (row["doc_id"],)).fetchone()
                    page_text[row["doc_id"]] = page["title"] + " " + page["content"]
                text, base = page_text[row["doc_id"]], -best_rank[row["doc_id"]]
            else:
                text, base = " ".join((row["title"], row["heading"], row["content"])), -row["rank"]
            covered = sum(weight for weight, group in zip(weights, patterns) if any(p.search(text) for p in group))
            score = base * (0.5 + covered / weight_sum) * _KIND_WEIGHTS.get(kind, 1.0)
            # A named page, or a concept whose home is this page family
            # ("cancel into" -> Move Links).
            if named:
                score *= 1.6
            concept_boosted = any(row["doc_id"] == home or row["doc_id"].startswith(home + ".") for home in homes)
            if concept_boosted:
                score *= 2.0
            elif homes and any(pattern.search(row["title"]) for pattern in topic_terms):
                score *= 1.5
            # The question quotes a setting this passage defines ("Execution
            # Buffer Type"); multiword labels only, so "Move" alone never counts.
            if any(label.casefold() in folded_query for label in _BOLD_LABEL.findall(row["content"])
                   if " " in label.strip()):
                score *= 1.8
            labels = target_docs.get(row["doc_id"])
            if labels:
                score *= 3.0
                if any("**" + label.casefold() in row["content"].casefold() for label in labels):
                    score *= 1.5
            entry = (score, row["chunk_id"], row)
            if concept_boosted and kind != "related":
                boosted.append(entry)
            else:
                (fallback if kind == "related" else scored).append(entry)
        # A concept points at a page family; it claims at most two boosted
        # passages, and the rest of that family competes unboosted.
        boosted.sort(key=lambda entry: (-entry[0], entry[1]))
        scored += boosted[:2] + [(score / 2.0, chunk_id, row) for score, chunk_id, row in boosted[2:]]
        # A concept question spans a page family, so prefer more pages over a
        # second passage from one page; a single-topic question keeps more of
        # its own page.
        ranked = _diverse(scored or fallback, limit + 1, 0.5 if homes else 0.75)
        videos_by_doc: dict[str, list[dict]] = {}
        matched_fields = frozenset(match["field"] for match in field_matches)
        attached: set[tuple[str, str, str]] = set()  # each note once per response
        remaining = max_chars
        for row in ranked[:limit]:
            if remaining <= 0:
                truncated = True
                break
            passage, end_line, clipped, partial_line = _passage_within_budget(row["content"], row["start_line"], remaining)
            if clipped and results and _body_chars(passage) < _MIN_CLIPPED_BODY:
                # The budget is spent: after the first result, a heading or a
                # scrap of a section is not evidence. Stop and report truncation.
                truncated = True
                break
            result = {
                **_document_fields(row),
                "heading": row["heading"],
                "start_line": row["start_line"],
                "end_line": end_line,
                "content": passage,
                "truncated": clipped,
                "partial_line": partial_line,
            }
            if row["doc_id"] not in videos_by_doc:
                document = connection.execute("SELECT content FROM documents WHERE doc_id=?", (row["doc_id"],)).fetchone()
                videos_by_doc[row["doc_id"]] = _videos(document["content"])
            if videos_by_doc[row["doc_id"]]:
                result["videos"] = videos_by_doc[row["doc_id"]]
            # A long section can span passages; notes apply to the whole section.
            section = "\n".join([row["title"], row["heading"]] + [part["content"] for part in connection.execute(
                "SELECT content FROM chunks WHERE doc_id=? AND heading=? ORDER BY chunk_id",
                (row["doc_id"], row["heading"]),
            )])
            notes = [note for note in reference.clarifications_for(row["doc_id"], section, brief=True, exclude=matched_fields)
                     if (row["doc_id"], note["field"], note["label"]) not in attached]
            attached.update((row["doc_id"], note["field"], note["label"]) for note in notes)
            if notes:
                result["clarifications"] = notes
            results.append(result)
            remaining -= len(passage)
            truncated = truncated or clipped
        truncated = truncated or len(ranked) > limit
    return {"query": query, "terms": terms, "results": results, "truncated": truncated,
            "snapshot": snapshot, **_field_payload(field_matches)}


def _body_chars(passage: str) -> int:
    return sum(len(line.strip()) for line in passage.splitlines()
               if line.strip() and not _MARKDOWN_HEADING.match(line))


def _diverse(entries: list[tuple[float, int, sqlite3.Row]], count: int, decay: float = 0.75) -> list[sqlite3.Row]:
    """Greedy selection that scales a document's score by ``decay`` for each
    passage it already contributed and allows at most two per document."""
    pending = sorted(entries, key=lambda entry: (-entry[0], entry[1]))
    used: dict[str, int] = {}
    selected: list[sqlite3.Row] = []
    while pending and len(selected) < count:
        best = max(
            (index for index, entry in enumerate(pending) if used.get(entry[2]["doc_id"], 0) < _MAX_PER_DOC),
            key=lambda index: (pending[index][0] * decay ** used.get(pending[index][2]["doc_id"], 0), -pending[index][1]),
            default=None,
        )
        if best is None:
            break
        row = pending.pop(best)[2]
        used[row["doc_id"]] = used.get(row["doc_id"], 0) + 1
        selected.append(row)
    return selected


def _field_payload(field_matches: list[dict]) -> dict:
    if not field_matches:
        return {}
    return {
        "field_matches": [{key: value for key, value in match.items() if key != "query_words"} for match in field_matches],
        "field_reference_notice": reference.NOTICE,
    }


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
        snapshot = _snapshot(connection)
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
                    raise RequestValidationError(f"Source line {start_line} exceeds the {MAX_PAGE_CHARS}-character page limit; use search for an excerpt")
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
            "snapshot": snapshot,
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
        snapshot = _snapshot(connection)
        total = connection.execute("SELECT count(*) FROM documents" + clause, parameters).fetchone()[0]
        rows = connection.execute(
            "SELECT doc_id, title, url, category, source_version, warnings, content_hash, line_count "
            "FROM documents" + clause + " ORDER BY title COLLATE NOCASE, doc_id LIMIT ? OFFSET ?",
            (*parameters, limit, offset),
        ).fetchall()
        topics = [{**_document_fields(row), "total_lines": row["line_count"]} for row in rows]
    next_offset = offset + len(topics) if offset + len(topics) < total else None
    return {"topics": topics, "category": category, "offset": offset, "limit": limit, "total": total, "next_offset": next_offset, "snapshot": snapshot}


def index_status(path: Path) -> dict:
    """Report persisted build/source metadata without opening a writable DB."""
    path = Path(path)
    if not path.is_file():
        return {"available": False, "path": str(path), "reason": "Index file does not exist"}
    with closing(_read_connection(path)) as connection:
        status = json.loads(connection.execute("SELECT value FROM index_metadata WHERE key='status'").fetchone()[0])
    return {**status, "path": str(path)}
