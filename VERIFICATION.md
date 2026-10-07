# Verification — UFE Docs MCP

## 0.2.0: multi-client plugins and Streamable HTTP

Verified **October 7, 2026 UTC** on macOS 26.5.1 (arm64), Python 3.13.9 from the python.org installer, MCP SDK 2.3.0. Client versions: Claude Code 2.1.292, Codex CLI 0.161.0, Cursor Agent 2026.10.01, Antigravity CLI 1.2.17, Grok Build 1.0.46.

### Automated checks

| Check | Result |
| --- | --- |
| Unit and protocol suite | **61 tests passed** (44 existing, 17 new), on macOS and in GitHub Actions on Python 3.10 and 3.13. |
| Streamable HTTP over a real loopback socket | Discovery shows the four read tools with titles; search, read, and an actionable unknown-ID error work; `ufe_refresh_docs` appears only with `--remote-refresh`. |
| HTTP access control | No header, a wrong token, and a non-Bearer scheme each return `401` with `WWW-Authenticate`; the correct token works; `/healthz` stays open. Binding beyond loopback without tokens or `--allow-anonymous` fails at startup. |
| Rate limiting | Window, recovery after 60 seconds, per-client separation, health exemption, and resistance to a forged left-most `X-Forwarded-For`. |
| Manifests | Root `plugin.json` and `mcp.json` validate against the Agent Plugins 1.0 schemas; names, versions, and the `ufe_docs` server key agree across manifests; no root `.mcp.json`. |
| Client configuration | Every `client-config` format renders local and remote entries; JSON and TOML parse; exported Antigravity manifests contain only `name` and `description`. |
| Validators | `claude plugin validate --strict` passes for the marketplace and plugin manifests. `grok plugin validate` accepts the repository. `agy plugin validate` accepts the exported Antigravity package. |

### TLS fix

The first live sync on this Mac failed with `CERTIFICATE_VERIFY_FAILED`: the python.org Python has no CA bundle file. Source requests now verify against the operating system trust store through `truststore`. A fetch of `robots.txt` succeeded with no `SSL_CERT_FILE` override.

### Live client checks

"Live call" means the assistant's model invoked the tool and the tool result appeared in the client's event stream.

| Client | Local (stdio) | Plugin | Remote (HTTP, bearer token) |
| --- | --- | --- | --- |
| Claude Code | Live call (earlier `claude-opus-5-5` acceptance run; registration still connects) | Installed from the repository marketplace: 1 skill, 1 MCP server. Loaded with `--plugin-dir`: `plugin:ufe-docs:ufe_docs` connected with five tools; live `ufe_docs_status` call returned 223 documents, `current_to_catalog` | Live `ufe_search_docs` call; token from an environment variable |
| Codex | Live `ufe_search_docs` call; read-only tool ran without prompting under `default_tools_approval_mode = "writes"` | Installed from the repository marketplace; live `ufe_docs_status` call through the plugin's server | Live `ufe_get_doc` call with `bearer_token_env_var` |
| Cursor | Live `ufe_search_docs` call (Cursor Agent CLI, signed in, workspace trusted, headless allow rule `Mcp(ufe_docs:ufe_search_docs)` in the folder's `.cursor/cli.json`) | Not tested: the Cursor app is not installed, and the Cursor Agent CLI does not load plugins | Live `ufe_search_docs` call with `Bearer ${env:UFE_DOCS_TOKEN}` |
| Antigravity | — | Exported package installed; the agent loaded `ufe-docs_ufe_docs` and attempted `ufe_docs_status`. **Headless mode denied the call** because MCP tools require a permission it cannot prompt for; an interactive session asks. Not overridden | Not tested |
| Grok Build | Picked up from Claude Code settings automatically; doctor: handshake and five tools; live `ufe_docs_status` call returned 223 documents | Installed from the repository: skill only; the server comes from MCP settings | `${UFE_DOCS_TOKEN}` header expanded by Grok; doctor: four tools; live `ufe_list_topics` call |

The remote server ran exactly as the `Dockerfile` would: a clean copy of the image's files, `uv sync --frozen --no-dev`, `PORT=7860`, `--trust-proxy`, and an empty cache. It refused to start on `0.0.0.0` without an access policy, then with a token it bootstrapped the documentation itself (four requests, crawl delay respected) and served every remote check above. The token never appeared in server logs or client transcripts.

**Container build:** not run on this machine, because Docker Desktop's data is archived on an external drive. GitHub Actions builds it instead (`.github/workflows/ci.yml`): the image built, refused to start without an access policy, and passed the authenticated MCP smoke test (`scripts/smoke_http.py`, offline). Tests also passed on Python 3.10 and 3.13 there. No hosting deployment was made.

Without an allow rule, headless Cursor and Antigravity runs reject MCP calls they cannot prompt for. Cursor reported the read tools as not read-only when rejecting them, so headless runs need an explicit `Mcp(server:tool)` rule; interactive sessions ask.

Test installations in Codex, Antigravity, Claude Code, and Grok were removed afterwards, and their configuration files were compared with pre-test backups.

### Remaining

- The Cursor app's plugin install, and a live call in an interactive Antigravity session.
- A deployment, once hosting is approved.
- Claude Desktop and claude.ai custom connectors against a hosted HTTPS URL.


## 0.1.0 preview

### Current freshness release

Verified **October 7, 2026 at 16:31:39 UTC** in the development environment, after the freshness implementation and review fixes.

| Check | Result |
| --- | --- |
| Complete automated suite | **44 tests passed**, with **48 parameterized subtest checks**, zero failures, and zero errors. |
| Runtime | The unittest runner reported 3.077 seconds; test discovery and setup brought the recorded total to 3.720 seconds. |
| Official SDK protocol | Three subprocess tests passed: document operations; empty offline cache; successful explicit raw refresh against original controlled fixtures. All five tools were exercised. |
| Background freshness | Recent caches avoid fetching; due and idle-server updates run without blocking cached reads. |
| Failures and recovery | Source/build failure preserves previous DB bytes; retry delay persists; another client's success clears an old error; interrupted updates recover. |
| Multiple clients | Two spawned processes share one synchronization lock while cached reads remain usable. An accepted refresh owns its lock before acknowledgment. |
| Source modes | Raw mode persists across updates and corrupt-index recovery. Failed raw upgrades do not replace the last successful mode. |
| Provenance and metadata | Concurrent publication keeps each response attached to its actual snapshot; changed warning flags count as changed documentation. |
| Auxiliary state failure | Failure to save history after publication reports a persistence warning while retaining the successful updated index. |
| Network guards | Offline operations and the controlled online-refresh fixture made no socket/DNS attempts. The explicit online protocol fixture recorded exactly one synthetic raw-source request. |

The tests use original synthetic documentation for changes, failures, and concurrency. The controlled online protocol test replaces only the source adapter in its child process; it exercises the real SDK, stdio server, refresh tool, index publication, and follow-up reads without contacting a live site.

Reproduce the suite from this checkout:

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
```

The final result was also captured with a file-backed unittest runner that counts subtests. An earlier attempt to run that recorder through standard input could not start the multiprocessing test's child; using a real file entry point resolved that runner limitation without changing the coordination test.

#### Current live-source synchronization

A foreground sync using the new shared coordinator completed at **2026-10-07T16:26:13.259957+00:00**. It fetched the official crawl rules, public application, catalog, and supplemental public Move Links page. It returned `sync_outcome: unchanged`, updating the source-check time without inventing a documentation-change event.

- Documents/sections: **223** (146 pages, 77 groups).
- Searchable chunks: **1,010**.
- Source flags: 23 `needs_verification`, nine `legacy_docs_differ`.
- Content mode: `published_catalog`; one supplemental raw page was fetched.
- Catalog generation date remains `2026-07-31`, distinct from the latest fetch time.
- Catalog and public-application hashes match the original provenance recorded below.
- Current index revision: `857f56a2d337083619174a80be1b94a44255a2f0a8ada5c5a67ade9c44a775e4`.

A full live raw-page refresh was not run. Its selection, persistence, update behavior, and protocol path were tested with controlled fixtures; the 37-minute-or-longer estimate comes from the observed source count and ten-second crawl delay.

#### Remaining presenter-specific rehearsal

This verifies the connector in Linux with Python 3.12.14 and MCP SDK 2.3.0. It does not establish installation in the user's actual Claude Code, Claude Desktop, or Codex client, nor native macOS/Windows behavior.

Before the livestream, connect the intended client, confirm all five tools appear, ask a real UFE question, inspect actual search and page-retrieval calls, and confirm that the answer cites those sources and surfaces freshness information. The connector does not validate a Unity project or prove that generated code works in the installed UFE release. No measured speed, token-saving, or model-quality claim is made.

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
- Retrieved: `2026-10-07T00:42:00.030415+00:00`.
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
- This verification does not claim installation in the user’s desktop client, a public deployment, or testing on every supported operating system.
- The distributed archive contains connector source, tests, configuration, and setup instructions. It excludes the downloaded documentation corpus, caches, and environment-specific paths.
