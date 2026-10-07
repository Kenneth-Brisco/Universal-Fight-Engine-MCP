![UFE Docs MCP — UFE documentation, inside your coding assistant](assets/ufe-docs-mcp-banner.svg)

# UFE Docs MCP

**The Universal Fighting Engine manual, available through your coding assistant.**

Search the [official UFE documentation](https://www.ufe3d.com/ufe2/docs/#/docs:home), read relevant sections, and keep source links attached to the answer while you build your game. Connect through Claude, Codex, Cursor, Antigravity, Grok, or any assistant with MCP support, locally or through a hosted endpoint.

**v0.2.0 preview · Python 3.10+ · stdio and Streamable HTTP MCP · Plugins for Claude Code, Codex, Cursor, Antigravity, and Grok · [MIT](LICENSE)**

[Quick start](#quick-start) · [Connect your assistant](#connect-your-assistant) · [Hosted endpoint](#hosted-endpoint) · [Tools](#tools) · [Freshness](#documentation-freshness) · [Troubleshooting](#troubleshooting)

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
- **Maintain the reference:** automatically refresh while the MCP is running, request an immediate refresh, and see update failures or overdue checks in tool results.

**This release focuses on documentation.** It runs independently of Unity and a UFE installation. Reading your project's configurations, editing moves or characters, and running checks inside Unity are outside its current scope.

The connector uses local keyword search. It makes no model or embedding calls and needs no model API key of its own. Retrieved text still consumes context tokens in the assistant that uses it.

## Why use this with Claude Code or Codex?

Your assistant does the reasoning and coding. **UFE Docs MCP gives it dedicated access to the UFE manual:** reusable search, section retrieval, official source links, line ranges, and documentation warnings. Once connected, those tools are available across your UFE questions without repeatedly supplying the documentation URL and asking for a new crawl.

Providing links manually or using the assistant's other research tools also works. This connector makes the UFE reference workflow convenient and repeatable. It does not increase the model's intelligence or guarantee correct code, faster answers, or lower token costs. The assistant must still interpret the retrieved text and check behavior against your installed UFE version.

That division matches [MCP's host/client/server architecture](https://modelcontextprotocol.io/docs/learn/architecture): the assistant uses the tools; the documentation server supplies context.

### Does Unity charge extra? Which model does it use?

**This connector requires no additional Unity service or AI model.** It is an independent local Python program and runs without Unity or UFE installed. The connector code is MIT licensed and has no paid service subscription in this implementation.

It searches a local database, with no LLM, embeddings service, or model-provider API calls. Use the model you already run through a client with local stdio MCP support. Your assistant's normal subscription, API charges, usage limits, and context-token consumption still apply. Any Unity or UFE licensing needed to build your game is separate.

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

There are two ways to connect, and both run the same server:

- **MCP connection:** add the `ufe_docs` server to your assistant's MCP settings. You get the five tools.
- **Plugin:** install the UFE Docs plugin. It adds the same server **plus a skill** that teaches the assistant the search → read → cite → flag-warnings workflow.

Generate configuration **after placing the checkout in its permanent location**. Generated entries point at this checkout's Python environment and the shared documentation cache with absolute paths, so every assistant on the machine shares one index.

`client-config --format <client>` prints the entry in each client's own format: `json`, `claude-code`, `codex`, `cursor`, `antigravity`, or `grok`.

| Assistant | MCP connection | Plugin |
| --- | --- | --- |
| **Claude Code** (and Claude Desktop through plugins) | `client-config --format claude-code` prints a ready `claude mcp add-json --scope user …` command | `claude plugin marketplace add <checkout>` then `claude plugin install ufe-docs@ufe-docs` |
| **Codex** (CLI and the ChatGPT desktop app; the IDE extension has no plugin support) | `client-config --format codex` prints a `[mcp_servers.ufe_docs]` table for `~/.codex/config.toml` | `codex plugin marketplace add <checkout>` then `codex plugin add ufe-docs@ufe-docs` |
| **Cursor** | `client-config --format cursor` prints an entry for `~/.cursor/mcp.json` or `.cursor/mcp.json` | `ufe-docs-mcp export-plugin cursor --out ~/.cursor/plugins/local/ufe-docs`, then reload Cursor |
| **Antigravity** (CLI, IDE, 2.0) | `client-config --format antigravity` prints an entry for `~/.gemini/config/mcp_config.json` | `ufe-docs-mcp export-plugin antigravity --out <dir>` then `agy plugin install <dir>` |
| **Grok Build** | Reads your Claude Code (`~/.claude.json`) and Cursor MCP settings automatically. Otherwise `client-config --format grok` prints a `grok mcp add` command | `grok plugin install <checkout>` adds the skill; the server comes from the MCP connection |
| **Any other MCP client** | `client-config` prints a generic `mcpServers` JSON entry | — |

Run each command from the checkout with `uv run --frozen ufe-docs-mcp …`. For example:

```bash
uv run --frozen ufe-docs-mcp client-config --format codex
```

How the plugins launch the server:

- **Claude Code and Codex plugins** live in this repository (`.claude-plugin/plugin.json`, and the Agent Plugins `plugin.json` + `mcp.json`). They start the server with `uv run --frozen` from the installed plugin folder, so `uv` must be installed. The first start builds the plugin's own environment.
- **Cursor and Antigravity plugins** are generated by `export-plugin`. Antigravity's plugin manifest accepts only a name and description, and neither client documents a plugin-root variable for this layout, so the exported package points at this checkout with absolute paths. Re-export if you move the checkout.

Restart or reconnect the assistant after changing its MCP settings or installing a plugin. Clients may ask you to approve the server or its tools the first time. The four read tools are annotated read-only, so clients that auto-approve read-only tools (for example Codex with `default_tools_approval_mode = "writes"`) run them without prompting; `ufe_refresh_docs` still asks.

[Example JSON](examples/client-config.json) shows the generic format with placeholder paths.

**Compatibility depends on the host application.** A model name alone does not establish MCP support; the host app must launch local stdio servers or connect to a remote URL. See [Verification](#verification-and-coverage) for what was actually tested.

## Hosted endpoint

The same server runs over **Streamable HTTP** for assistants that only accept a URL (for example claude.ai on the web, ChatGPT, or the Grok API), or for a team that wants one shared instance.

```bash
UFE_DOCS_HTTP_TOKENS="<long random token>" uv run --frozen ufe-docs-mcp serve --transport http --port 8000
```

- The MCP endpoint is `/mcp` and a health check is at `/healthz`.
- **Access:** set one or more bearer tokens (`UFE_DOCS_HTTP_TOKENS`, comma-separated, or `--token-file`) for a private endpoint. To publish an open endpoint deliberately, pass `--allow-anonymous` (or `UFE_DOCS_ALLOW_ANONYMOUS=1`). Without either, the server refuses to listen beyond loopback.
- **Rate limit:** 120 requests per client per minute by default (`--rate-limit`). Behind a hosting proxy, add `--trust-proxy` to key on the address the proxy appended to `X-Forwarded-For`.
- **Refresh:** the server keeps its own snapshot current with the automatic schedule. `ufe_refresh_docs` is hidden over HTTP so remote callers cannot trigger requests to the publisher's site; `--remote-refresh` exposes it.
- **Clients:** `client-config --format <client> --url https://your-host/mcp --token-env UFE_DOCS_TOKEN` prints a remote entry that reads the token from an environment variable.

A `Dockerfile` is included and targets a Hugging Face Docker Space or any container host. See [docs/HOSTING.md](docs/HOSTING.md) for hosting options and the deployment checklist. Nothing in this repository deploys automatically.

## Tools

| Tool | Use it to | Returned context |
| --- | --- | --- |
| `ufe_search_docs` | Find relevant documentation passages. | Document IDs, source URLs, excerpts, and line ranges. |
| `ufe_get_doc` | Read a document or continue through a longer page. | Page content, source details, warnings, and pagination. |
| `ufe_list_topics` | Browse the indexed manual, optionally by category. | Titles, document IDs, and topic pagination. |
| `ufe_docs_status` | Check readiness, coverage, and source dates. | Index status, snapshot metadata, and documentation warnings. |
| `ufe_refresh_docs` | Request a background update without leaving your assistant. Local servers only, unless a hosted server enables `--remote-refresh`. | Whether the request was accepted, current status, and freshness information. |

Search defaults to five results and a 12,000-character passage budget. Use returned pagination fields when more page or topic context is needed.

Search, read, and topic results include `snapshot` metadata captured with the returned content and a `freshness` envelope. Status includes the same information. `freshness.last_update` summarizes detected additions, removals, and changes, including changed documentation warnings. The server instructs assistants to surface relevant update and freshness notices; presentation depends on the host and model.

Other useful prompts:

```text
Use UFE Docs to find the hitbox and hurtbox documentation. Read the relevant
section and show the official source links.

Use UFE Docs to find the rollback networking documentation. Identify any
version notes or verification warnings before recommending settings.
```

## Documentation freshness

**The MCP checks for a due update at startup and keeps its local snapshot refreshed while running. The default interval is 24 hours after a successful sync.** Cached queries stay usable during background updates. A missing, invalid, or overdue snapshot triggers a check; a recent snapshot does not cause another download on each question.

Every successful documentation result identifies its snapshot and reports freshness. An overdue check means the content **may** have changed; it does not prove that UFE published an update. A failed check is visible and automatically retried after 15 minutes. The previous validated index stays available when source retrieval or index construction fails.

| Operation | What it does |
| --- | --- |
| Search, read, or browse through MCP | Reads the local index immediately; schedules an update if due and includes freshness information. |
| Running online MCP server | Checks its local due time every 30 seconds; downloads on the configured interval, not every 30 seconds. |
| `ufe_refresh_docs()` | Requests an immediate background sync. Check `ufe_docs_status` for completion. |
| `ufe_refresh_docs(refresh_pages=true)` | Requests all known public raw pages. This can take about 37 minutes or longer. |
| `sync` | Runs a foreground synchronization using the same cache lock and state as the MCP. |
| `sync --refresh-pages` | Runs a foreground full raw-page refresh. |
| Offline mode | Performs no source checks or downloads, even when a refresh is requested. |

An already-running refresh is not queued or upgraded by another request. Wait for it to finish before requesting a different mode. Claude, Codex, and a CLI sync sharing the same cache are coordinated so only one synchronization runs at a time.

Automatic refresh runs only while the local MCP process is running. It cannot check the site or notify you after the client stops it. On the next connection it checks whether an update is due. CLI `search`, `get`, `topics`, and `status` are local reads and do not start a background updater; their policy fields describe that CLI process.

For a routine update:

```bash
uv run --frozen ufe-docs-mcp sync
```

**Scope matters:** ordinary new installations use UFE's published bulk catalog plus public pages needed to complete its visible navigation. The catalog may lag edits to individual raw pages. A `current_to_catalog` status means the check is recent within that scope; it does not certify that every raw page is current.

When you need a full raw-page refresh:

```bash
uv run --frozen ufe-docs-mcp sync --refresh-pages
```

At the observed 223-page/section coverage and the site's crawl delay, a full raw-page refresh can take **about 37 minutes or longer**. Once a cache has been fully refreshed from raw pages, later automatic and manual updates retain raw-page mode so an older catalog cannot silently replace it. Those later updates can take the same amount of time. Use a separate cache folder if you want a new catalog-mode index.

Both modes produce snapshots. Raw pages can change during or after a full sync, so there is no continuously-latest guarantee. Inspect source dates, content mode, `freshness.warnings`, and `freshness.last_update` in the returned context. This release delivers notices through tool results; it does not send desktop notifications or messages to people.

### Documentation updates and connector updates are separate

The automatic updater downloads documentation. It does not update the MCP's Python code, dependencies, Unity, or your installed UFE package. If UFE changes the catalog format or public visibility rules, the current connector reports the failure and keeps the usable snapshot. A compatible connector release is then needed.

For a Git checkout, install a connector update with `git pull --ff-only`, then `uv sync --frozen`, and restart the MCP client. Regenerate the configuration if the installation path changes. ZIP recipients need a new code archive. The [specification](docs/SPECIFICATION.md) records the freshness contract and the [verification report](VERIFICATION.md) records what was actually exercised.

## Verification and coverage

Recorded verification on **October 7, 2026 UTC**:

| Check | Recorded result |
| --- | --- |
| Public manual coverage | 223 pages/sections: 146 pages and 77 groups. |
| Search index | 1,010 searchable chunks. |
| Automated verification | 61 tests passed in 0.2.0, covering stdio, Streamable HTTP, access control, rate limiting, plugin manifests, and client configuration. |
| MCP protocol | Initialization, all five tools, successful explicit raw refresh, search/read flow, pagination, and actionable errors exercised with the official SDK client. |
| Offline behavior | Socket/DNS guards observed no network attempts during offline tests. |
| Freshness behavior | Background updates, persisted retries, multiple clients, failed updates, corrupt-index recovery, metadata changes, and snapshot provenance exercised with controlled fixtures. |
| Latest live-source sync | October 7, 2026 at 16:26 UTC: unchanged content, with a renewed source-check time. |

Version 0.2.0 was also exercised on macOS through Claude Code, Codex, Cursor's agent CLI, Antigravity, and Grok Build, locally and against the HTTP server; live tool calls succeeded in Claude Code, Codex, and Grok, and the Cursor and Antigravity gaps are recorded. Full provenance, sample query results, and environment details are in [VERIFICATION.md](VERIFICATION.md).

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
| Freshness says `check_failed` or `check_due` | Read the warning and source-check date. Retry with `ufe_refresh_docs` or `sync`; automatic retries wait 15 minutes after a failed attempt. |
| A refresh says another sync is running | Keep using cached docs and check status. Request a full raw-page refresh after the current operation finishes. |
| An earlier installation uses a previous cache location | Run `uv sync --frozen`, synchronize once, and regenerate the client configuration. |

## Advanced setup

<details>
<summary>Change or disable automatic updates</summary>

The default is one automatic sync every 24 hours while the MCP runs. To use a six-hour interval:

```bash
uv run --frozen ufe-docs-mcp serve --refresh-hours 6
```

For a client connection, append `"--refresh-hours", "6"` after `"serve"` in the generated arguments. Intervals must be finite and at least one hour.

Append `"--no-auto-refresh"` to disable automatic downloading, including initial bootstrap. Explicit `ufe_refresh_docs` remains available online. Use `"--offline"` when all documentation network access must be disabled.

</details>

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
