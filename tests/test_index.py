"""Focused tests using entirely original, synthetic documentation."""

import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from ufe_docs_mcp.index import (
    Document,
    MAX_PAGE_CHARS,
    build_index,
    get_doc,
    index_status,
    list_topics,
    search_docs,
)


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "docs.sqlite3"
        self.move = Document(
            doc_id="synthetic.moves.jab",
            title="Synthetic jab configuration",
            url="https://example.invalid/docs/moves/jab#existing-fragment",
            content=(
                "# Synthetic jab configuration\n"
                "An invented example for testing.\n"
                "\n"
                "## Startup window\n"
                "The practice jab starts after seven simulation steps.\n"
                "Use ExampleEngine.ConfigureJab() to inspect the sample.\n"
                "\n"
                "## Recovery window\n"
                "Recovery lasts nine steps in this synthetic example.\n"
            ),
            category="moves",
            source_version=None,
            warnings=("needs_verification", "legacy_docs_differ"),
        )
        self.audio = Document(
            doc_id="synthetic.sound",
            title="Audio settings",
            url="https://example.invalid/docs/audio",
            content="# Audio settings\nChoose the practice bell sample.\nThe sample has no engine-specific meaning.\n",
            category="presentation",
            source_version="fixture-v1",
        )
        build_index([self.move, self.audio], self.path, {"fixture": "original synthetic text"})

    def test_status_and_exact_source_hash(self):
        status = index_status(self.path)
        self.assertTrue(status["available"])
        self.assertEqual(status["document_count"], 2)
        self.assertGreaterEqual(status["chunk_count"], 4)
        self.assertEqual(status["source_versions"], ["fixture-v1"])
        self.assertEqual(status["metadata"], {"fixture": "original synthetic text"})
        self.assertEqual(len(status["content_hash"]), 64)
        self.assertTrue(status["indexed_at"].endswith("+00:00"))
        document = get_doc(self.path, self.move.doc_id)
        self.assertEqual(document["content_hash"], hashlib.sha256(self.move.content.encode()).hexdigest())
        self.assertIsNone(document["source_version"])

    def test_search_returns_correct_source_heading_and_exact_lines(self):
        result = search_docs(self.path, "How do I configure ConfigureJab()?")
        self.assertTrue(result["results"])
        passage = result["results"][0]
        self.assertEqual(passage["doc_id"], self.move.doc_id)
        self.assertEqual(passage["url"], self.move.url)
        self.assertIn("Startup window", passage["heading"])
        lines = self.move.content.splitlines()
        self.assertEqual(passage["content"], "\n".join(lines[passage["start_line"] - 1 : passage["end_line"]]))
        self.assertEqual(passage["warnings"], ["needs_verification", "legacy_docs_differ"])
        self.assertFalse(passage["partial_line"])

    def test_api_names_and_punctuation_are_literal_search_data(self):
        self.assertEqual(search_docs(self.path, "ExampleEngine.ConfigureJab()") ["results"][0]["doc_id"], self.move.doc_id)
        for query in ("\" OR * NEAR()", "title:jab AND NOT sound", "jab'); DROP TABLE documents; --", "{}[]:!@#$%^&*()", "\"\"", "", "the and how to"):
            with self.subTest(query=query):
                self.assertIsInstance(search_docs(self.path, query)["results"], list)
        self.assertEqual(index_status(self.path)["document_count"], 2)
        self.assertEqual(get_doc(self.path, self.audio.doc_id)["title"], self.audio.title)

    def test_document_pagination_preserves_lines_and_continuations(self):
        lines = self.move.content.splitlines()
        page = get_doc(self.path, self.move.doc_id, start_line=4, max_lines=2)
        self.assertEqual(page["content"], "\n".join(lines[3:5]))
        self.assertEqual((page["start_line"], page["end_line"], page["next_start_line"]), (4, 5, 6))
        last = get_doc(self.path, self.move.doc_id, start_line=8, max_lines=100)
        self.assertEqual(last["content"], "\n".join(lines[7:]))
        self.assertIsNone(last["next_start_line"])
        beyond = get_doc(self.path, self.move.doc_id, start_line=999)
        self.assertEqual(beyond["content"], "")
        self.assertIsNone(beyond["end_line"])
        self.assertIsNone(beyond["next_start_line"])

    def test_list_pagination_filter_and_warning_propagation(self):
        first = list_topics(self.path, limit=1)
        self.assertEqual(first["topics"][0]["doc_id"], self.audio.doc_id)
        self.assertEqual(first["next_offset"], 1)
        second = list_topics(self.path, offset=first["next_offset"], limit=1)
        self.assertEqual(second["topics"][0]["doc_id"], self.move.doc_id)
        self.assertIsNone(second["next_offset"])
        self.assertEqual(second["topics"][0]["warnings"], list(self.move.warnings))
        filtered = list_topics(self.path, category="moves")
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(filtered["topics"][0]["doc_id"], self.move.doc_id)
        self.assertEqual(list_topics(self.path, category="' OR 1=1 --")["total"], 0)

    def test_limits_are_validated(self):
        calls = (
            lambda: search_docs(self.path, "x" * 501),
            lambda: search_docs(self.path, "jab", limit=21),
            lambda: search_docs(self.path, "jab", limit=True),
            lambda: search_docs(self.path, "jab", max_chars=30_001),
            lambda: get_doc(self.path, self.move.doc_id, max_lines=201),
            lambda: get_doc(self.path, self.move.doc_id, start_line=0),
            lambda: list_topics(self.path, offset=-1),
            lambda: list_topics(self.path, limit=101),
        )
        for call in calls:
            with self.subTest(call=call), self.assertRaises(ValueError):
                call()

    def test_search_content_budget_and_long_line_are_explicit(self):
        long = Document("synthetic.long", "Long fixture", "https://example.invalid/long", "quartz " * 1_000)
        build_index([long], self.path, {})
        results = search_docs(self.path, "quartz", max_chars=100)
        self.assertLessEqual(sum(len(passage["content"]) for passage in results["results"]), 100)
        self.assertTrue(results["truncated"])
        self.assertTrue(results["results"][0]["partial_line"])
        self.assertEqual(results["results"][0]["content"], long.content[:100])

    def test_page_character_cap_keeps_complete_lines(self):
        lines = ["t" * 10_000 for _ in range(8)]
        long = Document("synthetic.long", "Long fixture", "https://example.invalid/long", "\n".join(lines))
        build_index([long], self.path, {})
        page = get_doc(self.path, long.doc_id)
        self.assertLessEqual(len(page["content"]), MAX_PAGE_CHARS)
        self.assertEqual(page["content"], "\n".join(lines[:4]))
        self.assertEqual(page["next_start_line"], 5)

    def test_heading_detection_ignores_code_fences(self):
        content = "# Guide\n## Real section\n```python\n# pretend heading\nneedle_in_code = 1\n```\n"
        doc = Document("synthetic.code", "Code fixture", "https://example.invalid/code", content)
        build_index([doc], self.path, {})
        passage = search_docs(self.path, "needle_in_code")["results"][0]
        self.assertEqual(passage["heading"], "Guide / Real section")
        # The bare page title has no body of its own, so it stays with the
        # first section instead of becoming a heading-only passage.
        self.assertEqual(passage["content"], "\n".join(content.splitlines()))

    def test_invalid_rebuild_preserves_previous_file_byte_for_byte(self):
        before = self.path.read_bytes()
        invalid_sets = [[], [self.move, self.move], [Document("empty", "Empty", "https://example.invalid/empty", "")]]
        for documents in invalid_sets:
            with self.subTest(documents=documents), self.assertRaises(ValueError):
                build_index(documents, self.path, {})
            self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(search_docs(self.path, "ConfigureJab")["results"][0]["doc_id"], self.move.doc_id)

    def test_failed_sqlite_build_preserves_previous_file(self):
        before = self.path.read_bytes()
        with mock.patch("ufe_docs_mcp.index._create_schema", side_effect=sqlite3.OperationalError("synthetic build failure")):
            with self.assertRaises(sqlite3.OperationalError):
                build_index([self.audio], self.path, {})
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(Path(self.directory.name).glob("*.tmp")), [])

    def test_failed_replace_preserves_previous_file(self):
        before = self.path.read_bytes()
        with mock.patch("ufe_docs_mcp.index.os.replace", side_effect=OSError("synthetic replacement failure")):
            with self.assertRaises(OSError):
                build_index([self.audio], self.path, {})
        self.assertEqual(self.path.read_bytes(), before)

    def test_successful_rebuild_replaces_stale_documents(self):
        old_hash = index_status(self.path)["content_hash"]
        build_index([self.audio], self.path, {"revision": 2})
        self.assertNotEqual(index_status(self.path)["content_hash"], old_hash)
        self.assertEqual(list_topics(self.path)["total"], 1)
        self.assertEqual(search_docs(self.path, "ConfigureJab")["results"], [])
        with self.assertRaises(KeyError):
            get_doc(self.path, self.move.doc_id)

    def test_missing_reads_never_create_an_index(self):
        path = Path(self.directory.name) / "missing.sqlite3"
        self.assertFalse(index_status(path)["available"])
        with self.assertRaises(FileNotFoundError):
            search_docs(path, "jab")
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
