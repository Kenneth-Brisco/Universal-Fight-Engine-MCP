---
title: UFE Docs MCP
emoji: 🥋
colorFrom: gray
colorTo: red
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Community MCP connector for the official UFE manual
---

# UFE Docs MCP

An MCP server for the official Universal Fighting Engine manual. Assistants search and read the documentation with official source links, publisher warnings, and freshness notices.

- **MCP endpoint:** `/mcp` (Streamable HTTP)
- **Health check:** `/healthz`
- **Tools:** `ufe_search_docs`, `ufe_get_doc`, `ufe_list_topics`, `ufe_docs_status`

For source code and local installation, see [UFE3D-MCP](https://github.com/Kenneth-Brisco/UFE3D-MCP). This Space exposes the HTTP transport for clients that support Streamable HTTP and the configured authentication method.

`/healthz` reports whether the process is running; `ufe_docs_status` reports whether its documentation index is ready. Automatic refresh continues while the Space's server process runs. After a restart, an available persistent cache is reused and checked when due; a missing cache needs a new download. Source-check dates and publisher-catalog dates are reported separately, so a recent check is not a guarantee that every raw documentation page is current.

Access is configured by the operator through accepted bearer tokens or explicit anonymous access. Shared bearer tokens are not OAuth. Normal MCP responses omit local cache paths and raw internal exception details; host logs and runtime state remain private operational files.

The documentation belongs to its publisher. This is an independent community project.
