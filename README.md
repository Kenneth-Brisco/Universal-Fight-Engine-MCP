![UFE Docs MCP — UFE documentation, inside your coding assistant](assets/ufe-docs-mcp-banner.svg)

# UFE Docs MCP

**The Universal Fighting Engine manual, available through your coding assistant.**

Search the [official UFE documentation](https://www.ufe3d.com/ufe2/docs/#/docs:home), read relevant sections, and keep source links attached to the answer while you build your game. Connect through Claude, Codex, or another assistant with local MCP support.

**v0.1.0 preview · Python 3.10+ · Local stdio MCP · [MIT](LICENSE)**

[Quick start](#quick-start) · [Connect your assistant](#connect-your-assistant) · [Tools](#tools) · [Freshness](#documentation-freshness) · [Troubleshooting](#troubleshooting)

## Start with a real UFE question

After connecting the MCP, try this in your assistant:

```text
Use UFE Docs to explain how input buffering and frame links affect move chaining.
Retrieve the relevant sections, cite the official source URLs, and flag any
documentation verification notes.
```

The assistant can search for relevant passages, follow a result to its document, and use that source material while helping you work through the implementation.

## What it supports

- **Search the manual:** find passages about moves, hitboxes, input buffering, networking, and other documented UFE topics.
- **Read in context:** retrieve longer pages and sections with line pagination.
- **Keep the evidence:** results carry official source URLs, document IDs, and the publisher's verification warnings.
- **Inspect the snapshot:** see which documentation is indexed and when it was retrieved.

**This release focuses on documentation.** It runs independently of Unity and a UFE installation. Reading your project's configurations, editing moves or characters, and running checks inside Unity are outside its current scope.

The connector uses local keyword search. It makes no model or embedding calls and needs no model API key of its own. Retrieved text still consumes context tokens in the assistant that uses it.

## Quick start

You need **Python 3.10+**, [uv](https://docs.astral.sh/uv/getting-started/installation/), and a client that can launch local MCP servers. Use Git for the clone command, or extract a supplied code ZIP into a permanent folder.

**Current preview:** the implementation is on `feat/ufe-docs-mcp` while [PR #1](https://github.com/Kenneth-Brisco/Universal-Fight-Engine-MCP/pull/1) is open. Clone that branch explicitly. Access to a private copy of the repository requires an authorized GitHub account.

```bash
git clone --branch feat/ufe-docs-mcp --single-branch https://github.com/Kenneth-Brisco/Universal-Fight-Engine-MCP.git
cd Universal-Fight-Engine-MCP

uv sync --frozen
uv run --frozen ufe-docs-mcp sync
uv run --frozen ufe-docs-mcp search "input buffer frame links"
```

`uv sync --frozen` installs the locked environment. The documentation sync then builds your local index; the final command checks that search returns relevant passages and source links. The site requests a **10-second delay between requests**, so allow the initial sync to finish.

Once installed, connect the same server to your preferred assistant.

## Connect your assistant

Generate the configuration **after placing the checkout in its permanent location**. The generated command points to that checkout's Python environment and an absolute cache path.

### Codex

```bash
uv run --frozen ufe-docs-mcp client-config --format codex
```

Merge the printed TOML entry into your existing Codex MCP configuration. See the [official Codex MCP setup](https://developers.openai.com/codex/mcp/) for your client.

### Claude and clients using MCP JSON

```bash
uv run --frozen ufe-docs-mcp client-config
```

Merge the printed `mcpServers` entry into your client's existing configuration, preserving its other servers. Reconnect or restart the client as required; the client launches the server for you.

[Example JSON](examples/client-config.json) shows the format. Its paths are placeholders; use the generator for your actual installation.

**Compatibility depends on the host application.** This package provides a local **stdio** server, which an MCP-capable client launches as a process. It does not include a hosted HTTPS endpoint. A local model can use it through a host with MCP and tool support; a model name alone does not establish compatibility.

Client references: [Claude Code](https://code.claude.com/docs/en/mcp), [Claude Desktop](https://modelcontextprotocol.io/docs/develop/connect-local-servers), [Codex](https://developers.openai.com/codex/mcp/), and [LM Studio](https://lmstudio.ai/docs/app/mcp). See [Verification](#verification-and-coverage) for the environment actually tested.

## Tools

| Tool | Use it to | Returned context |
| --- | --- | --- |
| `ufe_search_docs` | Find relevant documentation passages. | Document IDs, source URLs, excerpts, and line ranges. |
| `ufe_get_doc` | Read a document or continue through a longer page. | Page content, source details, warnings, and pagination. |
| `ufe_list_topics` | Browse the indexed manual, optionally by category. | Titles, document IDs, and topic pagination. |
| `ufe_docs_status` | Check readiness, coverage, and source dates. | Index status, snapshot metadata, and documentation warnings. |

Search defaults to five results and a 12,000-character passage budget. Use returned pagination fields when more page or topic context is needed.

Other useful prompts:

```text
Use UFE Docs to find the hitbox and hurtbox documentation. Read the relevant
section and show the official source links.

Use UFE Docs to find the rollback networking documentation. Identify any
version notes or verification warnings before recommending settings.
```

## Documentation freshness

**This MCP serves a local snapshot. An existing index stays in use until you explicitly sync it.** Reconnecting or asking a question does not automatically fetch updates.

| Operation | What it does |
| --- | --- |
| Search, read, or browse | Reads the current local index. |
| `sync` | Downloads the current published bulk catalog and any additional public page needed for its visible navigation. |
| `sync --refresh-pages` | Fetches every known public raw Markdown page during that synchronization. |
| First online connection without an index | Starts an initial download in the background; check `ufe_docs_status` while it warms up. |

For a routine update:

```bash
uv run --frozen ufe-docs-mcp sync
```

The bulk catalog may lag edits to individual raw pages. When you need a full raw-page refresh:

```bash
uv run --frozen ufe-docs-mcp sync --refresh-pages
```

At the observed 223-page/section coverage and the site's crawl delay, a full raw-page refresh can take **about 37 minutes or longer**. Both modes produce a snapshot; inspect its retrieval date and content mode with `ufe_docs_status` or the CLI `status` command.

## Verification and coverage

Recorded verification on **October 7, 2026 UTC**:

| Check | Recorded result |
| --- | --- |
| Public manual coverage | 223 pages/sections: 146 pages and 77 groups. |
| Search index | 1,010 searchable chunks. |
| Automated verification | 21 tests with 32 parameterized subtests passed. |
| MCP protocol | Initialization, all four tools, search/read flow, pagination, and actionable errors exercised with the official SDK client. |
| Offline behavior | Socket/DNS guards observed no network attempts during offline tests. |

The later naming cleanup also passed frozen installation, configuration generation, platform cache-path selection, and both existing MCP protocol tests. Full provenance, sample query results, and environment details are in [VERIFICATION.md](VERIFICATION.md).

This coverage follows the public navigation of the indexed manual. It is not a complete generated reference for every UFE C# API or every page elsewhere on the publisher's websites. An absent search result does not establish that an API does not exist.

The observed manual discusses **UFE 2.7.3**, but individual pages are not pinned to an engine version. The catalog reports a generation date of `2026-07-31`; retrieval dates are recorded separately. Match advice to your installed UFE release.

Publisher warnings stay attached to the results. The verified snapshot included 23 `needs_verification` flags and nine `legacy_docs_differ` flags. Hidden unreleased material is excluded according to the public application's visibility rules.

## Troubleshooting

| What you see | What to check |
| --- | --- |
| The assistant cannot see the tools | Merge the generated entry into its MCP settings, reconnect, and confirm that the client supports local stdio servers. |
| The index is not ready | Finish `sync`, then check `ufe_docs_status` or run `uv run --frozen ufe-docs-mcp status`. |
| A moved checkout no longer starts | Regenerate the configuration; its Python and cache paths are absolute. |
| The CLI and assistant show different snapshots | Use the same cache location for both, then regenerate the client entry if needed. |
| An earlier installation uses a previous cache location | Run `uv sync --frozen`, synchronize once, and regenerate the client configuration. |

## Advanced setup

<details>
<summary>Offline use</summary>

After a successful initial sync, offline serving prevents documentation downloads:

```bash
uv run --frozen ufe-docs-mcp serve --offline
```

For a client connection, append `"--offline"` after `"serve"` in its generated arguments. An empty offline cache needs a successful online sync before queries work.

</details>

<details>
<summary>Cache locations and a custom cache folder</summary>

| Platform | Default index location |
| --- | --- |
| macOS | `~/Library/Caches/ufe-docs-mcp/docs.sqlite3` |
| Windows | `%LOCALAPPDATA%\ufe-docs-mcp\docs.sqlite3` |
| Linux | `${XDG_CACHE_HOME:-~/.cache}/ufe-docs-mcp/docs.sqlite3` |

Set `UFE_DOCS_CACHE_DIR` or place the global `--cache-dir` option **before** the subcommand. Replace the example path with your chosen absolute folder:

```bash
uv run --frozen ufe-docs-mcp --cache-dir /absolute/path/to/ufe-docs-cache sync
uv run --frozen ufe-docs-mcp --cache-dir /absolute/path/to/ufe-docs-cache client-config
```

Use the same cache location for synchronization and serving.

</details>

<details>
<summary>Installation without uv (macOS or Linux)</summary>

From the downloaded project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
ufe-docs-mcp sync
ufe-docs-mcp client-config
```

This pins the MCP SDK but does not apply `uv.lock` to transitive dependencies. The uv path above uses the recorded dependency resolution.

</details>

## Community, sources, and license

Created by **Kenneth Brisco** while building a fighting game with UFE. Feedback about installation, missing documentation, and useful UFE questions is welcome. For a reproducible report, include your operating system, MCP client, the command or query, and the output of `ufe_docs_status`.

Share the connector code and setup instructions. Each recipient retrieves documentation into their own local cache. Vendor documentation, engine code, and cached databases are excluded from the distributable.

Official sources: [UFE manual](https://www.ufe3d.com/ufe2/docs/#/docs:home) · [Published catalog](https://www.ufe3d.com/ufe2/docs/assets/site-data.json) · [Public application](https://www.ufe3d.com/ufe2/docs/assets/app.js?v=20260721) · [Release notes](https://www.ufe3d.com/ufe2/changelog.html) · [Crawl rules](https://www.ufe3d.com/robots.txt).

The original connector code is [MIT licensed](LICENSE). UFE content retains its publisher's ownership and terms. This is an independent community project, unaffiliated with the UFE publisher.
