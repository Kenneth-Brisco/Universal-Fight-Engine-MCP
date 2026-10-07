---
title: UFE Docs MCP
emoji: 🥋
colorFrom: gray
colorTo: red
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: The official UFE manual as an MCP server for AI assistants
---

# UFE Docs MCP

An MCP server for the official Universal Fighting Engine manual. Assistants search and read the documentation with official source links, publisher warnings, and freshness notices.

- **MCP endpoint:** `/mcp` (Streamable HTTP)
- **Health check:** `/healthz`
- **Tools:** `ufe_search_docs`, `ufe_get_doc`, `ufe_list_topics`, `ufe_docs_status`

Most people should install the connector locally instead; see the project repository. This Space serves the same tools for assistants that only accept a URL.

The documentation belongs to its publisher. This is an independent community project.
