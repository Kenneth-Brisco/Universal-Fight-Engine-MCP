# Verification — UFE Docs MCP

## Release preparation — October 13, 2026 UTC

Fresh deterministic verification of the privacy and documentation corrections,
using Linux, Python 3.12.14, and the locked MCP SDK 2.3.0 environment:

- `uv sync --frozen` installed the locked environment successfully.
- **72 tests passed** with `uv run --frozen python -m unittest discover -s tests -v`.
- Nine privacy regressions exercise real stdio and loopback HTTP MCP sessions.
  They cover old persisted error text after restart, failed refreshes, startup
  permission failures, missing/corrupt caches, unexpected SDK errors, and both
  text and structured tool results. Source passages, official links, publisher
  warnings, and actionable input validation remain available.
- HTTP tests connect directly to their loopback servers; inherited proxy
  settings cannot divert test traffic.
- The configured server name `UFE3D`, plugin ID `ufe3d`, manifest schemas, and
  generated client formats are covered by the deterministic suite.
- An independent read-only review found no actionable defect in the shared
  response-privacy boundary or the unchanged synchronization/cancellation flow.
- Documentation links, Markdown fences, and `git diff --check` passed.
- A clean extraction of the complete 120-file source archive installed with
  `uv sync --frozen --offline`. Version, empty-cache status, and generated
  `UFE3D` client configuration checks passed from outside the checkout.
- Wheel and source-distribution builds installed and passed the core CLI checks
  with dependencies from `uv.lock`. Those Python distributions do not bundle
  the full plugin checkout or its lockfile; the GitHub source archive does.
- `scripts/smoke_http.py` passed against a real offline loopback server: rejected
  unauthenticated access, four titled read tools, and an authenticated MCP
  status call. The temporary token file was removed and no token appeared in
  the inspected server logs.
- Source and Python distribution inspection found no personal email, old
  branding, secrets, downloaded cache, or personal filesystem paths. Privacy
  regression tests deliberately include clearly synthetic paths and addresses.

These checks did not call an LLM or fetch the publisher's live documentation.
They do not replace the historical live-client records below, or claim a new
desktop-client installation, hosted deployment, or measured model improvement.

The October 7 records below are historical evidence for the versions tested. They distinguish deterministic tests, real client tool calls, and a model-assisted evaluation; they do not establish that every client has been retested against subsequent release changes.

Publication copies omit personal workstation details, temporary workspace paths, exact execution times and billing metadata. Test dates, relevant versions, source provenance, results and limitations are retained.

## 0.2.0: multi-client plugins and Streamable HTTP

Recorded **October 7, 2026 UTC** on macOS 26.5.1 (arm64), Python 3.13.9, MCP SDK 2.3.0. Client versions: Claude Code 2.1.292, Codex CLI 0.161.0, Cursor Agent 2026.10.01, Antigravity CLI 1.2.17, Grok Build 1.0.46.

> **Names and evidence:** most client and automated checks in this section preceded the rename from server `ufe_docs` / plugin `ufe-docs` to server `UFE3D` / plugin `ufe3d`. The later Claude plugin evaluation below used `UFE3D`. Historical records retain the names used in each check; current Claude Code tool IDs use `mcp__UFE3D__…` or, for the plugin, `mcp__plugin_ufe3d_UFE3D__…`.

### Automated checks

| Check | Result |
| --- | --- |
| Unit and protocol suite | **61 tests passed** (44 existing, 17 new), on macOS and in GitHub Actions on Python 3.10 and 3.13. |
| Streamable HTTP over a real loopback socket | Discovery shows the four read tools with titles; search, read, and an actionable unknown-ID error work; `ufe_refresh_docs` appears only with `--remote-refresh`. |
| HTTP access control | No header, a wrong token, and a non-Bearer scheme each return `401` with `WWW-Authenticate`; the correct token works; `/healthz` stays open. Binding beyond loopback without tokens or `--allow-anonymous` fails at startup. |
| Rate limiting | Window, recovery after 60 seconds, per-client separation, health exemption, and resistance to a forged left-most `X-Forwarded-For`. |
| Manifests | Root `plugin.json` and `mcp.json` validated against the Agent Plugins 1.0 schemas; names, versions, and the then-current `ufe_docs` server key agreed across manifests; no root `.mcp.json`. |
| Client configuration | Every `client-config` format renders local and remote entries; JSON and TOML parse; exported Antigravity manifests contain only `name` and `description`. |
| Validators | `claude plugin validate --strict` passes for the marketplace and plugin manifests. `grok plugin validate` accepts the repository. `agy plugin validate` accepts the exported Antigravity package. |

### Plugin eval (claude plugin eval)

Sanitized report: [docs/eval-reports/2026-10-07-ufe3d-plugin-eval.html](docs/eval-reports/2026-10-07-ufe3d-plugin-eval.html). Download it or open it locally; GitHub shows HTML files as source. Scores, questions, answers and judgments are preserved, with two temporary paths replaced by an explicit redaction marker.

Run on **October 7, 2026 UTC** with Claude Code 2.1.293, 9 cases × 3 runs × 2 arms. The run notes identify the default model's `opus` alias at `xhigh` effort and judge `haiku`; the generated report does not record the resolved answering model. The plugin's real `UFE3D` server answered from a copy of the local index in every run; the shared index was not refreshed during the eval.

| Case | With plugin | Without | Docs tool used | Skill fired |
| --- | --- | --- | --- | --- |
| air-recovery-type-flagged | 1.00 | 0.00 | 3/3 | 3/3 |
| hitbox-collision-types | 1.00 | 0.13 | 3/3 | 3/3 |
| input-buffer-and-frame-links | 1.00 | 0.11 | 3/3 | 3/3 |
| plinking-delay | 1.00 | 0.17 | 3/3 | 3/3 |
| rollback-balancing | 1.00 | 0.40 | 3/3 | 3/3 |
| teleport-flagged | 0.94 | 0.06 | 3/3 | 3/3 |
| tested-unity-versions | 1.00 | 0.00 | 3/3 | 3/3 |
| throw-collider-requirement | 1.00 | 0.75 | 3/3 | 3/3 |
| undocumented-feature | 1.00 | 1.00 | 3/3 | 3/3 |
| **Overall** | **0.99** | **0.29** | | mean Δ **+0.70** |

Reading the result: without the plugin, the model usually could not name UFE's exact settings, values, tested Unity versions, or official page, and never surfaced the publisher's verification flags. With the plugin it did so in 26 of 27 runs; one teleport run omitted the flag. Both arms declined to invent an undocumented "Roman Cancel" option, so that case shows no difference. The baseline had no web access, so the comparison is against the model's own knowledge, not against browsing.

These nine selected cases do not establish performance across all UFE questions or other models. The report's case threshold was 0%; assess the reported scores and individual judgments, not the automatic case-pass count. Tool use and skill activation are indicators, not scored correctness graders.

### TLS fix

A live sync in the macOS test environment initially failed with `CERTIFICATE_VERIFY_FAILED` because its python.org Python installation lacked a configured CA bundle. Source requests were changed to verify against the operating system trust store through `truststore`. A fetch of `robots.txt` then succeeded without an `SSL_CERT_FILE` override.

### Live client checks

"Live call" means the assistant's model invoked the tool and the tool result appeared in the client's event stream.

| Client | Local (stdio) | Plugin | Remote (HTTP, bearer token) |
| --- | --- | --- | --- |
| Claude Code | Live call (earlier `claude-opus-5-5` acceptance run; registration still connects) | Installed from the repository marketplace: 1 skill, 1 MCP server. Loaded with `--plugin-dir`: `plugin:ufe-docs:ufe_docs` connected with five tools; live `ufe_docs_status` call returned 223 documents, `current_to_catalog` | Live `ufe_search_docs` call; token from an environment variable |
| Codex | Live `ufe_search_docs` call; read-only tool ran without prompting under `default_tools_approval_mode = "writes"` | Installed from the repository marketplace; live `ufe_docs_status` call through the plugin's server | Live `ufe_get_doc` call with `bearer_token_env_var` |
| Cursor | Live `ufe_search_docs` call through Cursor Agent CLI with a trusted workspace and headless allow rule `Mcp(ufe_docs:ufe_search_docs)` | The Cursor app loaded the exported plugin, connected `plugin-ufe-docs-ufe_docs`, and registered all five tools and the server instructions. Live `ufe_search_docs` and `ufe_get_doc` calls used that plugin server; the answer cited Move Links, Linked Moves, and Global Advanced and retained catalog-lag and version notes. An initial plugin-discovery timeout cleared after opening a folder and reloading. The Cursor Agent CLI does not load local plugins | Live `ufe_search_docs` call with `Bearer ${env:UFE_DOCS_TOKEN}` |
| Antigravity | — | Exported package installed; the agent loaded `ufe-docs_ufe_docs` and attempted `ufe_docs_status`. **Headless mode denied the call** because MCP tools require a permission it cannot prompt for; an interactive session asks. Not overridden | Not tested |
| Grok Build | Picked up from Claude Code settings automatically; doctor: handshake and five tools; live `ufe_docs_status` call returned 223 documents | Installed from the repository: skill only; the server comes from MCP settings | `${UFE_DOCS_TOKEN}` header expanded by Grok; doctor: four tools; live `ufe_list_topics` call |

The remote client checks used a clean copy of the Docker image's source files, `uv sync --frozen --no-dev`, `PORT=7860`, `--trust-proxy`, and an empty cache. The server refused to start on `0.0.0.0` without an access policy, then with a token it bootstrapped the documentation (four requests, crawl delay respected) and served every remote check above. The token did not appear in the inspected server logs or client transcripts.

**Container evidence:** GitHub Actions (`.github/workflows/ci.yml`) built the image, checked that it refused to start without an access policy, and passed the authenticated MCP smoke test (`scripts/smoke_http.py`, offline). Tests also passed on Python 3.10 and 3.13 there. No hosting deployment was made.

Without an allow rule, headless Cursor and Antigravity runs reject MCP calls they cannot prompt for. Cursor reported the read tools as not read-only when rejecting them, so headless runs need an explicit `Mcp(server:tool)` rule; interactive sessions ask.

### Remaining

- Fresh client sessions using the final release's `UFE3D` / `ufe3d` names across the supported integrations; the post-rename evaluation above covers Claude's plugin only.
- A live tool call in an interactive Antigravity session.
- A deployment, once hosting is approved.
- Claude Desktop and claude.ai custom connectors against a hosted HTTPS URL.


## 0.1.0 preview

### Automatic freshness checks

Recorded **October 7, 2026 UTC** after the freshness implementation and review fixes, using Linux, Python 3.12.14 and MCP SDK 2.3.0.

| Check | Result |
| --- | --- |
| Complete automated suite | **44 tests passed**, with **48 parameterized subtest checks**, zero failures, and zero errors. |
| Official SDK protocol | Three subprocess tests passed: document operations; empty offline cache; successful explicit raw refresh against original controlled fixtures. All five tools were exercised. |
| Background freshness | Recent caches avoid fetching; due and idle-server updates run without blocking cached reads. |
| Failures and recovery | Source/build failure preserves previous DB bytes; retry delay persists; another client's success clears an old error; interrupted updates recover. |
| Multiple clients | Two spawned processes share one synchronization lock while cached reads remain usable. An accepted refresh owns its lock before acknowledgment. |
| Source modes | Raw mode persists across updates and corrupt-index recovery. Failed raw upgrades do not replace the last successful mode. |
| Provenance and metadata | Concurrent publication keeps each response attached to its actual snapshot; changed warning flags count as changed documentation. |
| Auxiliary state failure | Failure to save history after publication reports a persistence warning while retaining the successful updated index. |
| Network guards | Offline operations and the controlled online-refresh fixture made no socket/DNS attempts. The explicit online protocol fixture recorded exactly one synthetic raw-source request. |

The tests use original synthetic documentation for changes, failures, and concurrency. The controlled online protocol test replaces only the source adapter in its child process; it exercises the real SDK, stdio server, refresh tool, index publication, and follow-up reads without contacting a live site.

Run the suite for the checkout being tested; counts may differ from this historical record:

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
```

#### Recorded live-source synchronization

A foreground sync using the shared coordinator completed on **October 7, 2026 UTC**. It fetched the official crawl rules, public application, catalog, and supplemental public Move Links page. It returned `sync_outcome: unchanged`, updating the source-check time without inventing a documentation-change event.

- Documents/sections: **223** (146 pages, 77 groups).
- Searchable chunks: **1,010**.
- Source flags: 23 `needs_verification`, nine `legacy_docs_differ`.
- Content mode: `published_catalog`; one supplemental raw page was fetched.
- Catalog generation date remains `2026-07-31`, distinct from the latest fetch time.
- Catalog and public-application hashes match the original provenance recorded below.
- Recorded index revision: `857f56a2d337083619174a80be1b94a44255a2f0a8ada5c5a67ade9c44a775e4`.

A full live raw-page refresh was not run. Its selection, persistence, update behavior, and protocol path were tested with controlled fixtures; the 37-minute-or-longer estimate comes from the observed source count and ten-second crawl delay.

#### Scope of the preview checks

These preview checks exercised the connector through the Python SDK. They did not establish installation in a desktop client or native macOS/Windows behavior. Later client checks are recorded in the 0.2.0 section above.

For a live demonstration, connect the intended client, confirm the expected tools appear, ask a UFE question, inspect actual search and page-retrieval calls, and confirm that the answer cites those sources and surfaces freshness information. The connector does not validate a Unity project or prove that generated code works in the installed UFE release. These preview checks did not measure development speed, token savings or model quality.

See [SPECIFICATION.md](docs/SPECIFICATION.md) for the implemented behavior and acceptance contract.

### Original implementation verification

The following records the initial implementation checks earlier on October 7, 2026, before automatic freshness and the fifth tool were added. The original archive-install check applies to that earlier source package.

#### Result

The local stdio MCP was installed from its project and exercised through the official Python MCP client. The generated configuration launched successfully from a directory outside the project.

#### Checks

- 21 focused automated tests passed, including 32 parameterized subtests.
- Real MCP initialization and all four tool schemas passed.
- Offline tests used socket/DNS guards and observed no network attempts.
- The live official-site synchronization completed and published a local index.
- All 223 public navigation IDs were compared with independently discovered IDs: no omissions, unexpected IDs, or canonical URL mismatches.
- The additional public Move Links page was retrieved and its official route verified.
- Invalid inputs and unknown document IDs return actionable MCP tool errors.
- A failed index rebuild preserves the previous usable database.
- Plugin and MCP manifests passed their Agent Plugins 1.0 JSON schemas.
- A clean extraction of the distributable installed successfully with locked production dependencies; version, generated interpreter configuration, and empty-cache status checks passed.

#### Live indexed coverage

- Public documents/sections: **223** (146 pages, 77 groups).
- Searchable chunks: **1010**.
- Source flags preserved: 23 `needs_verification`, 9 `legacy_docs_differ`.
- Unreleased material excluded according to the public application’s visibility rules.

#### Source provenance

- Catalog: https://www.ufe3d.com/ufe2/docs/assets/site-data.json
- Catalog schema: `1.1.0`.
- Catalog-reported generation date: `2026-07-31`.
- HTTP Last-Modified: `Sun, 27 Sep 2026 23:55:16 GMT`.
- Retrieved: October 7, 2026 UTC.
- Catalog SHA-256: `91c1d37fd266fe6a491860c074d3393ea6d0de0c663bee52e16e7cf14a09b606`.
- Public application SHA-256: `431b68db0fdb06fae223282680f658fbfa43f09afc6ad26643deedcb4f65ebe0`.
- Mode: published bulk catalog plus the public group absent from that catalog. A full raw-page refresh is available but was not run.

#### Actual MCP query checks

| Query | First returned document |
| --- | --- |
| `hitboxes hurtboxes` | `hitbox.start` |
| `input buffer frame links` | `move.links.group.move-links` |
| `rollback netcode` | `global.network` |
| `UFE.StartGame` | `more.coding-with-ufe` |
| `installation UFE 2.7.3` | `docs.installation` |

Searches, follow-up page retrieval, and complete topic pagination were executed through the SDK client with offline serving enabled.

#### Environment and scope

- Python `3.12.14`, platform `linux`, SDK `mcp 2.3.0`.
- Negotiated MCP protocol: `2025-11-25`.
- The connector makes no embedding or model inference calls and requires no model API key.
- These initial checks did not establish a desktop-client installation, a public deployment, or testing on every supported operating system.
- The archive-install result applied to the initial implementation package. Release archives must be rebuilt and checked from the release source; the earlier archive is not evidence for subsequent versions.
