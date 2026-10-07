# IncogLabs UFE Docs MCP

**Version 0.1.0 · Python 3.10+ · Local stdio MCP**

Search the [official Universal Fighting Engine manual](https://www.ufe3d.com/ufe2/docs/#/docs:home) from your coding assistant. This documentation connector retrieves relevant passages, source links, and page context from a local search index. It works independently of a Unity project or UFE installation.

The connector uses the official Python MCP SDK, pinned to `mcp==2.3.0`. It performs local keyword search without embeddings, model inference, API keys, or an inference bill. Retrieved text still uses context tokens in the assistant that calls it.

## Get started on macOS

Clone this repository or extract the code ZIP into its final location. You need Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

From that folder:

```bash
uv sync --frozen
uv run --frozen ufe-docs-mcp sync
uv run --frozen ufe-docs-mcp search "input buffer frame links"
uv run --frozen ufe-docs-mcp status
```

`uv.lock` records the dependency resolution. Initial synchronization takes several requests; the site asks for a 10-second delay between them. Subsequent searches read the local index.

### Connect your assistant

For clients that accept an `mcpServers` JSON configuration:

```bash
uv run --frozen ufe-docs-mcp client-config
```

For Codex TOML configuration:

```bash
uv run --frozen ufe-docs-mcp client-config --format codex
```

Merge the generated entry into your client's existing MCP configuration, preserving its other servers and settings. Reconnect or restart the client as needed. The generator uses the Python interpreter from this installed environment and an absolute cache path. Generate the configuration after placing the folder in its final location; regenerate it if you move the folder or recreate its environment.

[examples/client-config.json](examples/client-config.json) shows the shape only. Its placeholder paths must be replaced; the generator is the easier option.

This server is model-neutral: it does not call a model provider. Your assistant must support tool use through a client that can launch **local stdio MCP servers**. Claude Code, Claude Desktop, and Codex provide this kind of integration; a suitable local model can also use it through an MCP-capable host. Compatibility depends on the client and its tool integration, and this release has not been tested inside every client. A hosted connector that expects an HTTPS URL needs a separate hosting solution; none is included here.

Client references: [Claude Code](https://code.claude.com/docs/en/mcp), [Claude Desktop](https://modelcontextprotocol.io/docs/develop/connect-local-servers), [Codex](https://developers.openai.com/codex/mcp/), and [LM Studio](https://lmstudio.ai/docs/app/mcp).

Try asking your assistant:

> Use UFE Docs to explain input buffering and frame links. Retrieve the relevant pages, cite the official links, and preserve any documentation verification warnings.

## Available tools

| Tool | Purpose |
| --- | --- |
| `ufe_search_docs` | Find relevant passages by question, topic, or API name. Results include document IDs, source URLs, and line ranges. |
| `ufe_get_doc` | Read a cached document by ID, with line pagination for longer pages. |
| `ufe_list_topics` | Browse titles and IDs, optionally filtered by category. |
| `ufe_docs_status` | Check readiness, coverage, source dates, and documentation warnings. |

Search defaults to five results and a 12,000-character passage budget. Use returned pagination fields to continue reading documents or topic lists. These tools read documentation; they do not inspect your project, edit assets, or validate game behavior.

## Synchronization and offline use

If you connect before running `sync`, `serve` starts the initial download in the background. The MCP handshake remains immediate. While the index is warming, check `ufe_docs_status`. Existing snapshots stay local until you explicitly synchronize again:

```bash
uv run --frozen ufe-docs-mcp sync
```

**Freshness:** An existing index does not automatically refresh when you reconnect or ask a question. Default sync downloads the published bulk catalog and any additional public page needed to complete its visible navigation. The bulk catalog may lag edits to individual raw pages. Check `ufe_docs_status` for the snapshot's retrieval date and content mode. Both sync modes produce a snapshot; neither guarantees continuously current documentation.

An optional full raw-page refresh fetches every known public Markdown page at synchronization time:

```bash
uv run --frozen ufe-docs-mcp sync --refresh-pages
```

At the observed 223-page/section coverage and 10-second crawl delay, this can take **about 37 minutes or longer**. Use ordinary `sync` for routine setup.

After an initial sync, offline serving prevents documentation downloads:

```bash
uv run --frozen ufe-docs-mcp serve --offline
```

For an offline client connection, append `"--offline"` after `"serve"` in its generated arguments. An empty offline cache needs a successful online sync before queries work.

On macOS, the default index is `~/Library/Caches/IncogLabs/ufe-docs-mcp/docs.sqlite3`. Set `UFE_DOCS_CACHE_DIR` or place the global `--cache-dir` option **before** the command:

```bash
uv run --frozen ufe-docs-mcp --cache-dir /absolute/path/to/ufe-docs-cache sync
uv run --frozen ufe-docs-mcp --cache-dir /absolute/path/to/ufe-docs-cache client-config
```

Use the same cache location for synchronization and serving.

## Coverage and source quality

The October 7, 2026 UTC verification indexed **223 public pages/sections**: 146 pages and 77 groups, producing **1,010 searchable chunks**. Counts can change as the official manual changes.

This coverage describes the public navigation of the indexed manual. It is not a complete generated reference for every UFE C# API or every page linked elsewhere on the publisher's websites. An absent search result does not establish that an API does not exist.

The catalog reports `generated_at: 2026-07-31`; retrieval dates are recorded separately. The observed manual discusses UFE 2.7.3, but individual pages are **not pinned to an engine version**. Match advice to your installed UFE release.

The snapshot contains 23 `needs_verification` flags and nine `legacy_docs_differ` flags. These are the publisher's documentation signals, retained in results. The connector follows the public application's visibility rules and excludes its hidden unreleased material.

Sources:

- [Official manual](https://www.ufe3d.com/ufe2/docs/#/docs:home)
- [Published catalog](https://www.ufe3d.com/ufe2/docs/assets/site-data.json)
- [Public application](https://www.ufe3d.com/ufe2/docs/assets/app.js?v=20260721)
- [Official release notes](https://www.ufe3d.com/ufe2/changelog.html)
- [Site crawl rules](https://www.ufe3d.com/robots.txt)

## Installation without uv

From the extracted project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
ufe-docs-mcp sync
ufe-docs-mcp client-config
```

This uses the pinned SDK dependency but does not apply `uv.lock` to transitive dependencies. Prefer the uv setup for the recorded dependency resolution.

## Sharing and license

Share the code ZIP with the setup instructions, or grant repository access to the intended recipients. Each recipient installs it and retrieves documentation into their own local cache. Vendor documentation, engine code, and cached databases are not bundled in the distributable.

IncogLabs' original connector code is [MIT licensed](LICENSE). UFE content retains its own ownership and terms; this project's MIT license does not relicense it. This is an independent community project, unaffiliated with the UFE publisher. No public hosting or installation on a recipient's machine is performed by downloading the ZIP.
