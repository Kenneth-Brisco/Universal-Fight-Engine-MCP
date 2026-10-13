# Verify a UFE3D-MCP installation

Follow [SETUP.md](SETUP.md) to install the connector, then use this checklist in
the intended assistant. No skill is required for direct MCP use.

1. Record the source commit, target machine/client, registration scope, and
   transport. Confirm that paths belong to the machine launching a local server,
   or that the operator supplied a real remote endpoint.
2. Register one `UFE3D-MCP` connection, directly or through `ufe3d-mcp`. Preserve
   cache/environment settings, token references, permissions, and unrelated MCP
   connections. Confirm that project and user scopes do not create duplicates.
3. Reconnect the client and allow normal deferred-tool discovery. Use its actual
   tool identifiers and supported permission syntax. Report required interactive
   approval or a fresh session as a precise handoff, not as completed verification.
4. Call `ufe_docs_status`, then `ufe_search_docs`, then `ufe_get_doc` with an ID
   returned by that search. Confirm readable source content, official URLs, and
   applicable publisher/freshness warnings. Do not force a refresh to obtain a pass.
5. Report **installed**, **configured**, **connected**, and **verified via MCP**
   separately. Mark unfinished steps **PENDING/BLOCKED** with the next action.

The synthetic tests cover fixed identifiers, configuration formats, manifests,
exported plugins, and actual stdio/HTTP protocol behavior with controlled data.
They do not change existing client settings, install the connector in every app,
run paid model sessions, or verify a game project.

[VERIFICATION.md](../VERIFICATION.md) records tested revisions and evidence limits.
Historical authoring notes are retained in the [evidence archive](history/README.md).
