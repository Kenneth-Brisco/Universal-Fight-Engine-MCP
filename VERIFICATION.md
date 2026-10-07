# Verification — UFE Docs MCP 0.1.0

Verified October 7, 2026 UTC in the development environment.

## Result

The local stdio MCP was installed from its project and exercised through the official Python MCP client. The generated configuration launched successfully from a directory outside the project.

## Checks

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

## Live indexed coverage

- Public documents/sections: **223** (146 pages, 77 groups).
- Searchable chunks: **1010**.
- Source flags preserved: 23 `needs_verification`, 9 `legacy_docs_differ`.
- Unreleased material excluded according to the public application’s visibility rules.

## Source provenance

- Catalog: https://www.ufe3d.com/ufe2/docs/assets/site-data.json
- Catalog schema: `1.1.0`.
- Catalog-reported generation date: `2026-07-31`.
- HTTP Last-Modified: `Sun, 27 Sep 2026 23:55:16 GMT`.
- Retrieved: `2026-10-07T00:42:00.030415+00:00`.
- Catalog SHA-256: `91c1d37fd266fe6a491860c074d3393ea6d0de0c663bee52e16e7cf14a09b606`.
- Public application SHA-256: `431b68db0fdb06fae223282680f658fbfa43f09afc6ad26643deedcb4f65ebe0`.
- Mode: published bulk catalog plus the public group absent from that catalog. A full raw-page refresh is available but was not run.

## Actual MCP query checks

| Query | First returned document |
| --- | --- |
| `hitboxes hurtboxes` | `hitbox.start` |
| `input buffer frame links` | `move.links.group.move-links` |
| `rollback netcode` | `global.network` |
| `UFE.StartGame` | `more.coding-with-ufe` |
| `installation UFE 2.7.3` | `docs.installation` |

Searches, follow-up page retrieval, and complete topic pagination were executed through the SDK client with offline serving enabled.

## Environment and scope

- Python `3.12.14`, platform `linux`, SDK `mcp 2.3.0`.
- Negotiated MCP protocol: `2025-11-25`.
- The connector makes no embedding or model inference calls and requires no model API key.
- This verification does not claim installation in the user’s desktop client, a public deployment, or testing on every supported operating system.
- The distributed archive contains connector source, tests, configuration, and setup instructions. It excludes the downloaded documentation corpus, caches, and environment-specific paths.
