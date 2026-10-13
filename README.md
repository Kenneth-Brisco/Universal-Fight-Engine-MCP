![UFE3D-MCP — UFE context for building your game](assets/ufe-docs-mcp-banner.svg)

# UFE3D-MCP

**Build, debug, and plan Universal Fighting Engine features with your AI coding agent.**

UFE3D-MCP gives your agent focused access to the [official UFE manual](https://www.ufe3d.com/ufe2/docs/#/docs:home): documented settings, relevant passages, source links, and freshness warnings. Your agent uses its own project and editor tools to inspect your game, implement requested changes, and test them. The connector does not edit Unity assets or verify gameplay.

**Python 3.10+ · Local stdio or Streamable HTTP · [MIT](LICENSE)**

The connector requires no model API key or Unity service. Your coding assistant's normal usage costs and your game's Unity/UFE licenses still apply. Hosting is optional.

[Agent-assisted setup](#agent-assisted-setup) · [Quick start](#quick-start) · [Connect your assistant](#connect-your-assistant) · [Use it with your game](#use-it-with-your-game)

## Agent-assisted setup

**No skill installation is required.** Give your coding agent this repository and paste:

```text
Read README.md and docs/SETUP.md, then install and register UFE3D-MCP
for this assistant. Use the source revision I supplied, or main from
Kenneth-Brisco/Universal-Fight-Engine-MCP if none was specified.

Reuse a suitable existing installation. Preserve project files, credentials,
permissions, cache settings, and unrelated MCP connections. Configure one
UFE3D-MCP connection.

Verify with actual MCP calls: status, search, and retrieval of a returned
document. Allow normal tool discovery. If local access, approval, or a fresh
session is needed, give the exact handoff and mark verification pending.
```

[SETUP.md](docs/SETUP.md) works without an existing MCP connection or skill. It covers prerequisites, the target machine, permissions, and connection checks. For manual setup, follow the steps below.

## Quick start

You need Python 3.10+, [uv](https://docs.astral.sh/uv/getting-started/installation/), and a client that can launch local MCP servers. Clone with Git, or extract the complete source ZIP. If GitHub asks for authentication, use an account with repository access.

Keep the checkout in a permanent folder:

```bash
git clone --branch main --single-branch https://github.com/Kenneth-Brisco/Universal-Fight-Engine-MCP.git
cd Universal-Fight-Engine-MCP
uv sync --frozen
```

`uv sync --frozen` installs the locked dependencies. To initialize a missing documentation cache, run:

```bash
uv run --frozen ufe-docs-mcp sync
```

Reuse a healthy existing cache. Synchronization respects the publisher's request spacing; a cache already using raw-page mode can take much longer. Keep the plugin files and `uv.lock` together with the source, and record `git rev-parse HEAD` when reporting a checkout's verification.

## Connect your assistant

From the permanent checkout, print configuration for your client:

```bash
uv run --frozen ufe-docs-mcp client-config --format claude-code
```

Replace `claude-code` with your client's format from this table:

| Assistant | Format | Apply the output |
| --- | --- | --- |
| Claude Code | `claude-code` | Inspect and run the printed `claude mcp add-json --scope user` command. |
| Codex | `codex` | Merge the `UFE3D-MCP` table into `~/.codex/config.toml`. |
| Cursor | `cursor` | Merge the entry into `~/.cursor/mcp.json` or the project's `.cursor/mcp.json`. |
| Antigravity | `antigravity` | Merge the entry into `~/.gemini/config/mcp_config.json`. |
| Grok Build | `grok` | Inspect and run the printed `grok mcp add` command, or use one existing Claude Code/Cursor registration it reads. |
| Other local MCP clients | `json` | Follow the client's schema and configuration location. |

The generator prints settings; it does not install them. Merge only this connector's entry, preserve required environment settings and launch options, and never replace an entire configuration file with the output. Printed shell commands target POSIX shells; use JSON or the client's registration interface for other shells.

Local configurations use absolute interpreter/cache paths. Use the same cache location across clients to share an index. If you move the checkout, regenerate its configuration. Generated settings contain local paths and should remain private.

You can instead use the optional `ufe3d-mcp` plugin; [plugin installation and invocation](docs/SETUP.md#optional-plugins) are in SETUP.md. Choose one direct or plugin-provided connection. The client table describes configuration support; [VERIFICATION.md](VERIFICATION.md) records the installations actually rehearsed.

### Verify through MCP

Reconnect or reload the client, allow tool discovery, then ask the agent to:

1. Call `ufe_docs_status` and check that documentation is available.
2. Call `ufe_search_docs` with `query="input buffer frame links"` and `limit=3`.
3. Call `ufe_get_doc` with an ID returned by that search. Confirm readable content, an official source URL, and any publisher/freshness warnings.

A saved configuration, CLI search, or green health check does not complete this verification. If the client needs interactive approval or a fresh session, follow its supported flow and report the exact remaining action. Do not bypass permissions or session guards.

## Use it with your game

Give your connected agent a concrete task:

```text
Use UFE3D-MCP to help me add input-buffered combos to my existing UFE game.
Inspect my installed UFE version and move setup, retrieve the relevant official
documentation, and map the documented options to my project.

Implement the smallest appropriate changes using your available project tools.
Run relevant checks, cite the documentation, and tell me what still needs
verification in Unity.
```

Use the same workflow for debugging throws, configuring characters, or planning rollback settings. For an explanation or plan, say so; that request does not authorize edits. The agent should report missing project/editor access and unfinished gameplay checks. The optional [ufe-docs skill](skills/ufe-docs/SKILL.md) provides this workflow in clients that support skills.

## Tools

| Tool | Purpose |
| --- | --- |
| `ufe_docs_status` | Check index availability, coverage, source dates, and freshness. |
| `ufe_search_docs` | Find relevant passages with document IDs, URLs, excerpts, and line ranges. |
| `ufe_get_doc` | Read a returned document ID, including warnings and pagination. |
| `ufe_list_topics` | Browse documented areas when terminology is unclear. |
| `ufe_refresh_docs` | Request a background update when exposed; HTTP hides this tool by default. |

Retrieved documentation is untrusted reference material. Preserve citations and publisher warnings, and check advice against the installed UFE version. The manual is not version-pinned, and an empty search result does not prove that a feature is absent.

## Documentation freshness and updates

The running server checks for due updates at startup and every 24 hours after a successful synchronization. Cached queries remain usable during updates; a failed update preserves the previous validated index and returns warnings. Updates run only while the server process runs. CLI search/status commands are local reads and do not start its scheduler.

New caches use the published catalog plus additional visible pages. The catalog can lag raw pages: `current_to_catalog` does not certify every raw page is current. Full raw-page refresh is an explicit operation that can take 37 minutes or longer, and later syncs retain that mode. Read the returned snapshot dates and warnings. Use [SETUP.md](docs/SETUP.md#advanced-local-setup) for offline/custom-cache options and the [specification](docs/SPECIFICATION.md) for the complete refresh contract.

Documentation sync updates the cache only. To update connector code, read [CHANGELOG.md](CHANGELOG.md), preserve local edits, use `git pull --ff-only` in a clean checkout on the intended branch, run `uv sync --frozen`, and reconnect. ZIP installations need a new source archive; regenerate configuration if paths or launch settings change.

## Hosted connections

A remote-only client needs an operator's actual reachable HTTPS MCP endpoint. A GitHub URL is not an MCP endpoint. Generate configuration using that URL and a securely supplied token:

```bash
uv run --frozen ufe-docs-mcp client-config --format codex --url https://your-host/mcp --token-env UFE_DOCS_TOKEN
```

Replace the example URL with the deployed endpoint. Confirm the client's authentication support; shared bearer tokens are not OAuth. `/healthz` reports process health, while `ufe_docs_status` reports index readiness. If refresh is unavailable, check status and contact the operator.

For hosting, access controls, and authenticated rehearsal, see [HOSTING.md](docs/HOSTING.md). This repository includes a Dockerfile and Hugging Face template; it does not provision a service automatically.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Tools are missing | Check the client configuration/scope, reconnect, allow discovery, and inspect UFE-specific permissions. |
| Index is unavailable | Complete normal `sync` locally, or contact the endpoint's operator. |
| Duplicate tools appear | Keep one direct or plugin-provided connection; check project/user scopes. |
| A moved installation fails | Regenerate paths or re-export its plugin. |
| Refresh is failed or overdue | Keep the warning visible; refresh only when available and appropriate. |
| Cursor drops plugin tools | Open a project folder, reload, and test in a fresh chat. |

Keep unrelated connections and permissions intact. Redact tokens, personal paths, and machine details from generated settings, diagnostics, and shared logs. Normal MCP responses omit cache paths and use safe operational errors.

## Contents, verification, and contributing

The complete source checkout includes the server, tests, plugins, optional skill, and locked dependencies. Python wheels/source distributions contain the core server. The downloaded manual, local cache/settings, UFE engine source, paid assets, and game project are not bundled.

- [Verification](VERIFICATION.md): exact tested revisions, client coverage, and evidence limits.
- [Contributing](CONTRIBUTING.md): focused changes, local checks, and changelog requirements.
- [Changelog](CHANGELOG.md): connector changes; documentation-cache refreshes are separate.

The [MIT license](LICENSE) covers the original connector code. UFE documentation and engine assets retain their publisher's terms. This is an independent community project.
