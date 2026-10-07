# UFE Docs MCP specification

Status: implementation contract for the private v0.1.0 preview. Updated October 7, 2026 UTC.

## Purpose and scope

Give an MCP-capable coding assistant repeatable access to the public Universal Fighting Engine manual. The assistant supplies the model, reasoning, and coding workflow; this local Python server supplies documentation context.

The server searches documentation, reads pages with source links, browses topics, reports provenance and freshness, and synchronizes its local index. It does not inspect a Unity project, edit assets, change moves or characters, execute Unity checks, or verify game behavior. No LLM, embeddings service, model API key, Unity service, or Unity installation is required by this connector.

There is no hosted HTTPS endpoint, account service, desktop notification service, or background process that survives the MCP client's shutdown. The host must support local stdio tools. Successful protocol tests do not establish successful installation in every host application or operating system.

## Tool contract

| Tool | Inputs and bounds | Effect and result |
| --- | --- | --- |
| `ufe_search_docs` | `query`: 1–500 characters; `limit`: 1–20, default 5; `max_chars`: 100–30,000, default 12,000. | Searches the local keyword index. Returns passages, exact source URLs, document IDs, line ranges, truncation indicators, snapshot, and freshness. The character budget bounds passage text, excluding JSON metadata. |
| `ufe_get_doc` | `doc_id`: 1–256 characters; `start_line`: at least 1, default 1; `max_lines`: 1–200, default 100. | Returns a cached page segment, source metadata, warnings, and `next_start_line`. Page content is capped at 50,000 characters, with actionable handling of an oversized individual line. Includes snapshot and freshness. |
| `ufe_list_topics` | Optional category up to 256 characters; `offset`: at least 0, default 0; `limit`: 1–100, default 50. | Returns indexed titles and IDs, total count, and `next_offset`, with snapshot and freshness. |
| `ufe_docs_status` | No inputs. | Reports availability, coverage, source metadata, refresh activity, freshness warnings, update summaries, and guidance. |
| `ufe_refresh_docs` | `refresh_pages`: boolean, default false. | Requests an immediate background synchronization. Returns `accepted`, `reason`, and current status. Does not wait for the download to finish. Offline and closed runtimes reject the request with an actionable tool error. |

The first four tools are annotated as reads. The refresh tool is annotated as modifying the local cache, nondestructive, and idempotent. Online tools can interact with the public documentation source; offline tool annotations close that external interaction. Tool arguments cannot select an arbitrary source URL or execute a shell command.

`accepted: true` means the runtime acquired the cache's synchronization lock and started the worker. It does not mean synchronization has finished. If a refresh is already running, the new request is rejected with `accepted: false` and `reason: already_running`; it is not queued or upgraded. In particular, wait for a catalog sync to finish before requesting a full raw-page refresh. Check `ufe_docs_status` and the completed content mode before relying on the result.

## Documentation source and coverage

The adapter uses the official site's published catalog and public application's navigation metadata. It parses JavaScript literals as data and applies the site's explicit visibility rules; it does not execute the downloaded JavaScript. Hidden unreleased nodes are excluded. Unknown catalog schemas or unsupported visibility rules produce an error requiring an adapter update.

Network access is restricted to the fixed `https://www.ufe3d.com` origin, its `/ufe2/docs/` paths, and `/robots.txt`. Redirects must remain within the allowed scope. Responses are bounded, request timeouts apply, and the source's robots policy and crawl delay are respected. A subsequent coordinated sync also observes the previous sync's recorded request spacing.

Observed coverage is documented in [VERIFICATION.md](../VERIFICATION.md). It describes the indexed manual's visible navigation, including groups and pages. It is not a complete generated C# API reference or a promise to include every page on other UFE websites. Individual pages do not supply a pinned engine version; returned `source_version` is not inferred.

### Source modes

| Mode | Source content | Limit |
| --- | --- | --- |
| `published_catalog` | Current bulk catalog plus raw public pages needed to complete visible navigation. Default for a new cache. | Individual raw pages can be edited before the bulk catalog is regenerated. |
| `raw_pages` | Every known public raw Markdown page fetched during a full sync. | Pages can change during or after synchronization; there is no simultaneous upstream snapshot or continuously-latest guarantee. |

Full raw refresh is explicitly selected with `refresh_pages=true` or `sync --refresh-pages`. At the recorded coverage and crawl delay it may take 37 minutes or longer. After successful raw-mode publication, later automatic and manual syncs keep that mode. The last successful mode is also recorded in update history so recovery of a corrupt index can retain it. If both the index and that history are lost, the directory is effectively a new cache and defaults to catalog mode. The connector must not replace a known raw-page snapshot silently with potentially older catalog content. A separate cache can be used for catalog mode.

## Freshness policy

1. **Default interval:** 24 hours after the source was last successfully fetched. `serve --refresh-hours N` changes the interval; N must be finite and at least one hour.
2. **Startup and continued operation:** the running server checks whether synchronization is due at startup, during tool use, and on a local 30-second scheduler tick. A scheduler tick normally reads only local metadata; it is not a network request every 30 seconds.
3. **No valid snapshot:** an online, automatically refreshing server starts an initial download. MCP initialization remains responsive. Queries receive warming or recovery guidance until an index is available.
4. **Recent valid snapshot:** cached queries return immediately without starting a new source request for each question.
5. **Overdue or unknown source time:** a check is due. Missing, malformed, naive, or future `fetched_at` values cannot prove freshness. `indexed_at` is not a substitute for a source-fetch time.
6. **During an update:** the existing validated index remains readable. A replacement is published atomically after complete source retrieval, validation, and index construction.
7. **Failure:** source retrieval, parser, or index-construction failure keeps the previous index and exposes the error. Automatic retry is delayed 15 minutes from failure completion. Attempt state is persisted so reconnecting does not bypass the delay. An interrupted attempt retries 15 minutes after its recorded start once its process lock has been released.
8. **Explicit refresh:** an online tool or CLI request may retry without waiting for the automatic interval or failure backoff. It still uses the shared lock and source request spacing.
9. **Offline:** `serve --offline` or the existing `UFE_DOCS_OFFLINE` setting disables bootstrap, automatic checks, and explicit MCP refresh. Offline queries may use a saved snapshot and must report offline freshness. A separate explicit CLI `sync` is an online command.
10. **Automatic refresh disabled:** `serve --no-auto-refresh` suppresses automatic downloads, including bootstrap, while allowing an explicit online refresh.
11. **Process lifetime:** refresh operates only while the local MCP server runs. A stopped client cannot receive source changes or notices. The next start evaluates the persisted source time and retry state.

CLI `search`, `get`, `topics`, and `status` perform local reads without starting the scheduler. Their `automatic_refresh` policy field describes that CLI process. CLI `sync` performs foreground synchronization through the same coordinator used by MCP.

## Snapshot and freshness responses

Every successful search, page retrieval, and topic listing includes a compact `snapshot` record read through the same SQLite connection that produced the result. If another process replaces the index during retrieval, the response still identifies the snapshot that actually supplied its passages.

Snapshot fields include `id`, `indexed_at`, `fetched_at`, `content_mode`, `catalog_generated_at`, `content_hash`, and `index_revision`. `content_hash` identifies the indexed document bodies and IDs. `index_revision` also fingerprints titles, URLs, categories, source-version values, and warning flags, so metadata-only changes are detectable.

Freshness is separate from availability:

| `freshness.state` | Meaning |
| --- | --- |
| `current_to_catalog` | The snapshot was fetched within the configured interval, in catalog mode. Raw-page currency is not certified. |
| `current_to_raw_pages` | The raw-page snapshot was fetched within the interval. Its recorded retrieval time still applies. |
| `check_due` | A source check is overdue or its time/scope is unknown. This is not proof that upstream content changed. |
| `refreshing` | An update is running; returned passages still have their own snapshot identity. |
| `check_failed` | The last relevant check failed, was interrupted, or its state is unreadable. A usable index may still exist. |
| `offline` | This runtime deliberately performs no source checks or downloads. |
| `unavailable` | There is no usable index for this online runtime. Status explains warming or recovery. |

Other fields include the response snapshot's source-fetch time and age, check-overdue flag, configured interval, automatic-refresh flag, last attempt, next automatic check, last error, and warnings. A process's old remembered failure is cleared when another client records a later successful refresh of the shared cache.

`freshness.last_update` records the most recent detected content or metadata changes, with detection time, counts of added/changed/removed documents, up to five example IDs, and the resulting revision. An initial index is marked as an initial download. A synchronization with no changes updates the source-check time without inventing a new content-change event.

The server's instructions tell the assistant to surface relevant freshness warnings and newly detected changes. The host and model control their presentation. The connector itself does not send Discord messages, emails, desktop popups, or notifications while disconnected.

## Coordination and failure handling

Each cache uses a nonblocking SQLite transaction on a stable `refresh-lock.sqlite3` file, separate from the `docs.sqlite3` index. The CLI and multiple MCP client processes use that same lock. Process exit releases the OS-backed lock, so no stale lock file must be deleted. An accepted asynchronous request retains ownership when it transfers work to its thread.

The index is replaced only after the new database has passed validation. Readers continue using their open connection to the previous database during publication. Update history is stored separately in atomically replaced `refresh-state.json`.

If saving that history fails after a new index has already been published, the synchronization remains successful and reports a separate persistence warning. It must not claim the documentation update failed or roll back the valid new content. The index's own snapshot metadata continues to establish its provenance.

## Documentation, connector, and engine versions

Automatic synchronization changes the documentation cache only. It does not update executable connector code, dependencies, the user's Unity installation, the UFE package, or project assets.

If the source adapter needs an update, its actionable failure is retained in freshness output. The maintainer must publish compatible connector code. Users update their checkout or obtain a new source archive, install the locked environment, and restart the client. Advice from the current manual must still be checked against the installed engine version.

## Acceptance and release evidence

The focused automated suite must exercise:

- Recent caches with no source calls; due updates while cached reads remain usable.
- Idle-process scheduling, missing/corrupt indexes, and invalid or future source times.
- New content and metadata-only updates with accurate change summaries.
- Source failure with unchanged old database bytes, persisted retry delay, and recovery by another client.
- Two processes coordinating one source fetch; accepted refresh requests retaining their lock.
- Interrupted attempts and post-publication history-write failure.
- Raw-page mode preservation and explicit full-refresh selection.
- Old/new snapshot provenance during concurrent publication.
- Real stdio discovery and invocation of all five tools, their schemas/annotations, actionable errors, and zero network attempts in offline mode.

Tests use original synthetic documentation and controlled source responses for failure and update scenarios. A normal live-source synchronization verifies the real adapter separately; it is not a substitute for deterministic failure tests.

Before a livestream demonstration, confirm in the presenter's actual assistant that it connects, displays the tools, calls search and page retrieval, and cites the retrieved source material. Any claim of reduced time, cost, or tokens requires a comparable measured run with the same task and model. See the [verification report](../VERIFICATION.md) for the completed checks and remaining host-specific verification.
