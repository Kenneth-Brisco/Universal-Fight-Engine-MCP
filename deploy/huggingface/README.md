---
title: UFE3D-MCP
emoji: 🥋
colorFrom: gray
colorTo: red
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: UFE reference context for AI-assisted game development
---

# UFE3D-MCP

Give your coding agent official UFE reference context while it builds, debugs, and plans game features. The MCP retrieves relevant manual sections, source links, publisher warnings, and freshness notices; the agent's own project/editor tools implement and test requested changes.

- **MCP endpoint:** `/mcp` (Streamable HTTP)
- **Health check:** `/healthz`
- **Tools:** `ufe_search_docs`, `ufe_get_doc`, `ufe_list_topics`, `ufe_docs_status`

This is a deployment template, not an automatically provisioned endpoint. Deploy the reviewed source revision. The intended open-source home is [Universal-Fight-Engine-MCP](https://github.com/Kenneth-Brisco/Universal-Fight-Engine-MCP); its complete candidate remains on PR #3's `fix/public-release-readiness` branch until authorized promotion. Follow that checkout's README and release-parity report before deploying. This template is not evidence of a hosted endpoint.

`/healthz` reports whether the process is running; `ufe_docs_status` reports index readiness. Automatic refresh continues while the server process runs. After restart, a persistent cache is reused and checked when due; a missing cache needs a new download. Source-check dates and publisher-catalog dates are separate, so a recent catalog check does not certify every raw page is current.

Access is configured by the operator through bearer tokens or deliberate anonymous access. Shared bearer tokens are not OAuth. Normal MCP responses omit local cache paths and raw exceptions; host logs and runtime state remain private operational files.

The documentation belongs to its publisher. This is an independent community project, not an official UFE product.
