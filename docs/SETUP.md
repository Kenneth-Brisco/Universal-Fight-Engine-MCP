# Set up UFE3D-MCP with your agent

This is a standalone setup guide, not a skill or a running MCP connection. Give it and the [README](../README.md) from the same reviewed revision to a coding agent with the necessary local tools. Keep the manual client instructions available as a fallback.

## Goal and authority

Install or reuse the requested connector revision, register **UFE3D-MCP** in the intended assistant, and verify status, search, and document retrieval through actual MCP calls. Do not alter the game project as part of setup. Setup does not authorize commits, pushes, deployments, repository publication, paid model sessions, or security-policy bypasses.

A setup prompt cannot grant computer access, credentials, admin rights, or a missing client capability. Stop only the blocked step and explain the exact action required. Complete independent safe steps where possible.

## 1. Identify where the connection will run

Determine the target assistant, operating system, current workspace, and available terminal/configuration access. Distinguish the user's machine from a cloud workspace, container, or remote host; installation in one is not installation in another.

Inspect existing UFE registrations and plugin-provided servers without printing unrelated credentials. Resolve project/local/user scopes. Local stdio needs a host that can launch a process on the installation machine. A remote-only client needs an already deployed, reachable HTTP endpoint and supported authentication. Do not invent an endpoint or deploy one during setup. GitHub and documentation URLs are not MCP endpoints.

## 2. Select and preserve the intended source

Use the user's provided checkout/ref and read its applicable repository instructions. Record `git rev-parse HEAD`, branch, remote, and dirty/clean state without copying private data into a public report. Preserve existing edits and unrelated worktrees.

The intended open-source repository is `Kenneth-Brisco/Universal-Fight-Engine-MCP`. Until authorized promotion, use PR #3's complete `fix/public-release-readiness` branch as shown in the README. Record its exact commit and inspect [release parity and evidence](RELEASE-EXPORT.md). Do not substitute the original `main`, the earlier `UFE3D-MCP` export, or the staging backup. Private access remains necessary until publication; a 404 can mean insufficient access, not a missing repository.

Maintainers must follow the [publication checklist](RELEASE-EXPORT.md#before-publishing-this-repository) when promoting this preview. Merging the stacked PR into its feature-branch base alone does not install the complete candidate on `main`. End-user setup never performs that promotion or changes repository visibility.

Place a new checkout or extracted source ZIP in a durable user-selected development location. Reuse an appropriate existing one. Never hard-code the maintainer's home directory, hostname, or timezone. Keep generated configuration and caches private.

## 3. Install and initialize locally

Inspect Git, Python 3.10+, uv, and the target client. Use official prerequisite installation guidance and normal permissions. Ask for an unavoidable interactive login or administrator approval rather than disabling safeguards or requesting secrets in chat.

From the intended checkout:

```bash
uv sync --frozen
uv run --frozen ufe-docs-mcp status
```

Reuse a healthy cache. A missing cache needs a normal initial sync:

```bash
uv run --frozen ufe-docs-mcp sync
uv run --frozen ufe-docs-mcp search "input buffer frame links" --limit 3
```

Respect source request spacing. Do not force `--refresh-pages` or `refresh_pages=true` during setup. An existing raw-mode cache retains that mode; its normal refresh can also be long. Coordinate a necessary long refresh with the user rather than changing or deleting the cache. CLI success is useful preparation, not proof of an MCP connection.

Do not disable TLS checks. Preserve necessary environment settings, such as a user's corporate certificate configuration, without copying secrets into output.

## 4. Generate and register one connection

Use `uv run --frozen ufe-docs-mcp client-config --format <client>` and the [client table](../README.md#connect-your-assistant). The generator only prints configuration. Inspect it before applying it with the client's supported registration interface or a precise configuration edit.

Choose an appropriate scope. For a user who wants this across game projects, user scope is reasonable when supported; honor an explicit project-only request. Local paths must exist on the machine that launches the server. Preserve the intended cache path, environment, token references, arguments, transport, and unrelated settings. Keep a private rollback copy before changing configuration. Do not overwrite an entire configuration file with one entry.

Earlier server names include `UFE3D`, `ufe_docs`, and `ufe-docs`; the old plugin identifier is `ufe3d`. Verify the launch target before touching any such entry. Migrate only this connector to `UFE3D-MCP`, or reinstall/re-export the optional `ufe3d-mcp` plugin. Avoid both direct and plugin-provided registrations for the same connector. Update UFE-specific permission references only through the client's supported syntax. Do not grant broad wildcard tools or bypass permission prompts to obtain a pass.

Client/plugin naming is not the executable name: the executable stays `ufe-docs-mcp`, the module stays `ufe_docs_mcp`, and tool names such as `ufe_docs_status` remain unchanged. POSIX shell commands emitted by the generator are not automatically valid in every shell; use JSON or the native UI/CLI for other environments.

For a real remote endpoint supplied by its operator, generate using `--url` and, when supported, `--token-env`. Keep bearer tokens out of chat/logs and confirm the target client's authentication support. Do not assume every generic JSON client expands the same environment syntax.

## 5. Prove the connection in the intended client

Reload/reconnect as documented by the installed client. Permit normal deferred-tool discovery. If this session cannot load a newly saved registration, use a supported fresh session on the same machine or provide the exact user handoff. Do not remove nesting guards, disable approvals, or start repeated paid child sessions.

In the recorded Claude Code 2.1.296 plugin rehearsal, the first `claude mcp list` connection check timed out; one reconnect succeeded, with the client reporting a cached legacy-protocol fallback. After confirming the locked installation and launch paths, retry the check once. If it still fails, inspect redacted local diagnostics and leave verification pending; do not increase permissions or repeat paid sessions to obtain a pass. A successful connection check must still be followed by the tool calls below.

Through the actual registered MCP:

1. Discover `ufe_docs_status`, `ufe_search_docs`, `ufe_get_doc`, and `ufe_list_topics`. A local server normally also exposes `ufe_refresh_docs`; HTTP intentionally hides it by default.
2. Call `ufe_docs_status`. Record availability, snapshot mode, retrieval time, and freshness warnings; distinguish the publisher's catalog generation date from retrieval time.
3. Call `ufe_search_docs` with `query="input buffer frame links"`, `limit=3`, and a modest passage budget.
4. Call `ufe_get_doc` with a document ID actually returned by that search. Confirm readable context, official source URLs, pagination, and applicable publisher warnings.

Do not trigger a refresh just to prove the connection. Auto-refresh may legitimately start if the cache is due; do not promise that a status call is always network-free. If the cache is warming, report the observed state. Never substitute a web search or CLI output for MCP evidence.

## 6. Report the result and hand off to development

Report the target client/machine category, tested revision, registration name/scope, actual MCP checks, and exact remaining actions. Redact private local paths, usernames, credentials, and host identifiers from shareable output.

Use distinct labels: **installed**, **configured**, **connected**, and **verified via MCP**. Mark incomplete verification **PENDING/BLOCKED**, with its reason. A saved configuration or green process-health route alone is not a verified documentation query.

Once verified, use this task prompt:

```text
Use UFE3D-MCP to help me implement [feature] in this project. Inspect the
relevant project context and UFE version, retrieve the documentation needed,
make the requested scoped changes with your project tools, and run relevant
checks. Cite the sources and identify anything still requiring Unity testing.
```

A plugin skill is optional. For manual setup or a host without skill support, the direct MCP connection and prompt are sufficient. See [README](../README.md) and [CHANGELOG](../CHANGELOG.md) for compatibility and migration information.
