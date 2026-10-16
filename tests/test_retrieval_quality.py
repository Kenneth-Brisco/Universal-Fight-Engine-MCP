"""Retrieval-quality behavior, using original synthetic pages only.

Page IDs mirror the official manual's structure so the field reference's
mappings can be exercised, but every sentence here is invented for the tests.
"""

from pathlib import Path
import json
import tempfile
import unittest

from ufe_docs_mcp import reference
from ufe_docs_mcp.index import Document, _chunks, build_index, search_docs
from ufe_docs_mcp.runtime import CATALOG_LAG_WARNING, DocumentationRuntime

URL = "https://example.invalid/docs/"


def _page(doc_id: str, title: str, overview: str, options: list[str], related: list[str] = (), extra: str = "") -> Document:
    lines = [f"# {title}", "## Overview", overview, "## Options"]
    lines += [f"- **{name}** - {text}" for name, text in options]
    if related:
        lines += ["## Related Pages"] + [f"- [{name}]({name.lower().replace(' ', '-')}.md)" for name in related]
    return Document(doc_id, title, URL + doc_id, "\n".join(lines) + "\n" + extra, category="Move")


PAGES = [
    _page("global.match.combo", "Combo", "Tune the practice combo counter and combo damage scaling.", [
        ("Display Mode", "Shows the combo counter in a sample corner."),
        ("Damage Scaling", "Reduces combo damage after each sample hit."),
        ("Combo Decay", "Shortens combo hit stun on long combo strings."),
    ], related=["Combo Options", "Combo Rules", "Combo Counter", "Combo Display"]),
    _page("move.links.group.move-links", "Move Links", "Set the frame window in which this practice move may be followed.", [
        ("Frame Links", "The frames during which the follow-up window is open."),
        ("Link Conditions", "Whether the follow-up needs a confirmed strike."),
    ], extra=(
        "\n## Video Tutorial\n\n<div class=\"doc-video\">\n"
        "<iframe src=\"https://www.youtube-nocookie.com/embed/AbCdEf12345\" title=\"Practice links tutorial\" "
        "loading=\"lazy\" allowfullscreen></iframe>\n</div>\n"
    )),
    _page("move.links.group.linked-moves", "Linked Moves", "Choose the destination moves for an open window.", [
        ("Allow Block Cancel", "An invented description of the guard option."),
        ("Startup Frame", "Where the destination move begins."),
    ]),
    _page("move.active.group.hit.group.hit-stun-options", "Hit Stun Options", "How long the sample target stays stunned.", [
        ("Hit Stun Type", "How the invented stun length is measured."),
        ("Hit Stun on Hit", "Stun applied when the sample hit lands."),
        ("Hit Stun on Block", "Stun applied when the sample hit is guarded."),
    ], related=["Hit", "Hit Effects"]),
    _page("global.match.round", "Round", "Round timer for the sample match.", [
        ("Timer", "Seconds per invented round."),
    ], related=["Combo", "Hit Stun Options", "Move Links"]),
]


class RetrievalQualityTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cache = Path(directory.name)
        self.path = self.cache / "docs.sqlite3"
        build_index(PAGES, self.path, {"fetched_at": "2000-01-01T00:00:00+00:00", "content_mode": "published_catalog"})

    def _ids(self, query, limit=3):
        return [result["doc_id"] for result in search_docs(self.path, query, limit)["results"]]

    def test_heading_only_lines_join_the_following_section(self):
        chunks = list(_chunks("# Title\n## Overview\nBody text.\n## Options\n- **A** - b\n"))
        self.assertEqual([chunk[0] for chunk in chunks], ["Title / Overview", "Title / Options"])
        self.assertTrue(chunks[0][3].startswith("# Title\n## Overview\nBody text."))
        self.assertEqual(chunks[0][1], 1)

    def test_cancel_and_combo_into_questions_reach_move_links(self):
        for query in ("how do I make a jab cancel into a cross combo",
                      "combo a light attack into a special move",
                      "chain one practice move into another"):
            with self.subTest(query=query):
                self.assertTrue(any(i.startswith("move.links") for i in self._ids(query)), self._ids(query))

    def test_one_document_cannot_fill_every_result(self):
        for query in ("combo", "combo damage scaling counter decay", "hit stun"):
            with self.subTest(query=query):
                ids = self._ids(query, 5)
                self.assertLessEqual(max(ids.count(i) for i in ids), 2, ids)

    def test_related_pages_and_heading_only_passages_are_not_returned(self):
        for query in ("combo", "hit stun options", "move links", "round timer"):
            with self.subTest(query=query):
                for result in search_docs(self.path, query, 10)["results"]:
                    self.assertFalse(result["heading"].endswith("Related Pages"), result)
                    self.assertTrue(any(line.strip() and not line.startswith("#")
                                        for line in result["content"].splitlines()), result)

    def test_heading_only_rows_from_an_older_index_are_skipped(self):
        # Indexes built by the previous chunker contain heading-only rows;
        # simulate one directly instead of rebuilding with the new chunker.
        import sqlite3
        # The heading's word appears nowhere else, so neither the per-page cap
        # nor other passages can hide a failure of the heading-only filter.
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO chunks (doc_id, title, heading, start_line, end_line, content) "
                "VALUES ('global.match.round', 'Round', 'Zephyrquill', 1, 1, '# Zephyrquill')")
            connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')")
        self.assertEqual(search_docs(self.path, "zephyrquill", 10)["results"], [])

    def test_related_pages_remain_a_fallback_when_nothing_else_matches(self):
        build_index([Document("only.links", "Index", URL, "# Index\n## Related Pages\n- [Lantern](lantern.md)\n")],
                    self.path, {})
        self.assertEqual(search_docs(self.path, "lantern")["results"][0]["doc_id"], "only.links")

    def test_budget_never_spends_a_slot_on_a_heading_scrap(self):
        full = search_docs(self.path, "combo damage scaling hit stun", 3, 30000)["results"]
        budget = len(full[0]["content"]) + 15  # leaves room only for a heading
        clipped = search_docs(self.path, "combo damage scaling hit stun", 3, budget)
        self.assertEqual(len(clipped["results"]), 1)
        self.assertTrue(clipped["truncated"])

    def test_options_section_ranks_for_a_question_naming_the_page(self):
        top = search_docs(self.path, "hit stun options", 1)["results"][0]
        self.assertEqual(top["doc_id"], "move.active.group.hit.group.hit-stun-options")
        self.assertEqual(top["heading"], "Hit Stun Options / Options")

    def test_serialized_field_names_resolve_with_labelled_supplement(self):
        response = search_docs(self.path, "hitStunOnBlock")
        self.assertEqual(response["results"][0]["doc_id"], "move.active.group.hit.group.hit-stun-options")
        match = response["field_matches"][0]
        self.assertEqual((match["field"], match["label"]), ("hitStunOnBlock", "Hit Stun on Block"))
        self.assertIn("not official manual text", response["field_reference_notice"])
        self.assertTrue(match["source_ref"] and match["ufe_version"])
        # Official passages are never altered by the supplement.
        self.assertNotIn("hitStunOnBlock", response["results"][0]["content"])

    def test_enum_values_are_reported_in_declaration_order(self):
        match = search_docs(self.path, "linkType")["field_matches"][0]
        self.assertEqual(match["enum"]["name"], "LinkType")
        self.assertEqual([(v["name"], v["value"]) for v in match["enum"]["values"]],
                         [("HitConfirm", 0), ("CounterMove", 1), ("NoConditions", 2)])
        # The Inspector dropdown text, so an agent can name the exact entry.
        self.assertEqual([v["label"] for v in match["enum"]["values"]],
                         ["Hit Confirm", "Counter Move", "No Conditions"])

    def test_plain_words_do_not_trigger_field_lookups(self):
        self.assertEqual(reference.match_fields("hits and options for a move"), [])
        self.assertEqual(reference.match_fields("how does gravity work"), [])
        self.assertEqual(reference.match_fields("framelinks")[0]["field"], "frameLinks")
        self.assertEqual(reference.match_fields("_blendingTime")[0]["field"], "_blendingTime")

    def test_clarification_notes_attach_to_matching_passages(self):
        result = next(r for r in search_docs(self.path, "allow block cancel")["results"]
                      if r["doc_id"] == "move.links.group.linked-moves")
        note = next(n for n in result["clarifications"] if n["field"] == "allowBlockCancel")
        # Passages carry a one-sentence summary; the full note with code
        # references comes with a field lookup or the page itself.
        self.assertEqual(note["status"], "unofficial_clarification")
        self.assertTrue(note["summary"] and note["ufe_version"])
        self.assertNotIn("code_behavior", note)
        full = reference.clarifications_for("move.links.group.linked-moves")
        self.assertTrue(all(n["source_refs"] and n["code_behavior"] for n in full))
        # Searching the field itself reports the full note once, in field_matches.
        response = search_docs(self.path, "allowBlockCancel")
        self.assertIn("code_behavior", response["field_matches"][0]["clarifications"][0])
        self.assertFalse(any(n["field"] == "allowBlockCancel"
                             for r in response["results"] for n in r.get("clarifications", [])))

    def test_video_embeds_are_reported_as_links(self):
        result = next(r for r in search_docs(self.path, "frame links")["results"]
                      if r["doc_id"] == "move.links.group.move-links")
        self.assertEqual(result["videos"], [{
            "youtube_id": "AbCdEf12345", "title": "Practice links tutorial",
            "url": "https://www.youtube.com/watch?v=AbCdEf12345",
        }])

    def test_reference_data_is_well_formed(self):
        data = reference._data()
        for field in data["fields"]:
            self.assertTrue(field["field"] and field["label"] and field["doc_id"] and field["source_ref"], field)
            if field.get("enum"):
                self.assertIn(field["enum"], data["enums"], field)
        for name, entry in data["enums"].items():
            self.assertEqual([v["value"] for v in entry["values"]], list(range(len(entry["values"]))), name)
        # References name a file and class member, never install-specific
        # line numbers.
        text = json.dumps(data)
        self.assertNotRegex(text, r"\.cs:\d")
        for field in data["fields"]:
            self.assertRegex(field["source_ref"], r"^[\w/]+\.cs \([\w, ]+\)$", field)
        for note in data["clarifications"]:
            self.assertEqual(note["status"], "unofficial_clarification")
            self.assertTrue(note["source_refs"] and note["ufe_version"] and note["label"])

    def test_responses_are_compact_unless_verbose(self):
        runtime = DocumentationRuntime(self.cache, offline=True)
        compact = runtime.decorate(search_docs(self.path, "combo"))
        verbose = runtime.decorate(search_docs(self.path, "combo"), verbose=True)
        self.assertEqual(set(compact["snapshot"]), {"id", "fetched_at", "content_mode"})
        self.assertNotIn(CATALOG_LAG_WARNING, compact["freshness"].get("warnings", []))
        self.assertIn(CATALOG_LAG_WARNING, verbose["freshness"]["warnings"])
        self.assertNotIn("content_hash", compact["results"][0])
        envelope = {k: v for k, v in compact.items() if k != "results"}
        self.assertLess(len(json.dumps(envelope)), 500)
        self.assertGreater(len(json.dumps(verbose)), len(json.dumps(compact)))


if __name__ == "__main__":
    unittest.main()
