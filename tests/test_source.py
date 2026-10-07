"""Original fixtures exercise public navigation and source boundaries."""
import unittest

from ufe_docs_mcp.source import (
    SourceError, _allowed_url, app_nodes, content_url,
    documents_from_catalog, visibility_rules,
)


APP = """
const hiddenNodeIds = new Set(['example.hidden']);
nodes.forEach((n) => {
  if (n.id === "example.private" || n.id.startsWith("example.private.")) hiddenNodeIds.add(n.id);
});
const injectedNodes = [
  {id:'example.added', title:'Added Page', editor_family:'Examples',
   content_source_path:'Documentation/content/example/added.md'},
];
injectedNodes.forEach((node) => upsertNode(node));
"""


def node(doc_id="example.visible", content="# Example\nOriginal demonstration content."):
    return {
        "id": doc_id, "title": "Example", "editor_family": "Examples",
        "node_type": "page", "body_markdown": content,
        "content_source_path": "Documentation/content/example/visible.md",
    }


class SourceTests(unittest.TestCase):
    def test_public_filtering_and_missing_injected_page(self):
        catalog = {"schema_version": "1.1.0", "nodes": [
            node(), node("example.hidden"), node("example.private"), node("example.private.child")
        ]}
        fetched = []

        def fetch(url):
            fetched.append(url)
            return "# Added Page\n**Needs verification:** Yes\nOriginal added text."

        docs, meta = documents_from_catalog(catalog, APP, fetch)
        self.assertEqual({d.doc_id for d in docs}, {"example.visible", "example.added"})
        self.assertEqual(meta["excluded_nonpublic_count"], 3)
        self.assertEqual(len(fetched), 1)
        added = next(d for d in docs if d.doc_id == "example.added")
        self.assertIn("needs_verification", added.warnings)
        self.assertNotIn("**Needs verification:", added.content)
        self.assertEqual(added.url, "https://www.ufe3d.com/ufe2/docs/#/example:added")

    def test_injected_body_is_fetched_not_executed(self):
        script = APP.replace("title:'Added Page'", "title:'Added Page', body_markdown:'RUN_SHELL_COMMAND'")
        docs, _ = documents_from_catalog(
            {"schema_version": "1.1.0", "nodes": [node()]}, script,
            lambda _: "# Actual public page\nUse the documented setting.",
        )
        self.assertEqual(len(app_nodes(script)), 1)
        self.assertNotIn("RUN_SHELL_COMMAND", " ".join(d.content for d in docs))

    def test_unknown_visibility_logic_or_schema_rejected(self):
        with self.assertRaises(SourceError):
            visibility_rules(APP + "hiddenNodeIds.add(computeHiddenId());")
        with self.assertRaises(SourceError):
            visibility_rules("const noVisibilityMetadata = true;")
        with self.assertRaises(SourceError):
            documents_from_catalog({"schema_version": "2.0", "nodes": [node()]}, APP, lambda _: "unused")

    def test_content_path_and_origin_limits(self):
        self.assertEqual(content_url("Documentation\\content\\EXAMPLE\\page.md"),
                         "https://www.ufe3d.com/ufe2/docs/content/example/page.md")
        for value in ("../secret.md", "/root/file.md", "https://example.invalid/a.md", "example/%2e%2e/private.md"):
            with self.subTest(value=value), self.assertRaises(SourceError):
                content_url(value)
        for url in (
            "http://www.ufe3d.com/ufe2/docs/a", "https://example.invalid/ufe2/docs/a",
            "https://www.ufe3d.com@127.0.0.1/ufe2/docs/a", "https://www.ufe3d.com/ufe2/docs/../secret",
            "https://www.ufe3d.com/ufe2/docs/%2e%2e/secret", "https://www.ufe3d.com/doku.php",
        ):
            self.assertFalse(_allowed_url(url), url)

    def test_refresh_fetches_every_visible_page_and_propagates_failure(self):
        calls = []

        def fetch(url):
            calls.append(url)
            return "# Refreshed\nCurrent source text."

        docs, meta = documents_from_catalog(
            {"schema_version": "1.1.0", "nodes": [node()]}, APP, fetch, refresh_pages=True
        )
        self.assertEqual(len(calls), 2)
        self.assertTrue(all("Current source text." in d.content for d in docs))
        self.assertEqual(meta["content_mode"], "raw_pages")
        with self.assertRaises(SourceError):
            documents_from_catalog(
                {"schema_version": "1.1.0", "nodes": [node()]}, APP, lambda _: ""
            )


if __name__ == "__main__":
    unittest.main()
