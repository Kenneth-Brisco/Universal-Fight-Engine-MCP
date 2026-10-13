# Changelog

Meaningful user-facing changes to **UFE3D-MCP** are recorded here. This changelog starts with the unreleased work; existing package version strings do not establish a published release date. No retrospective release dates are invented.

Entries follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Add an entry under **Unreleased** in the same PR as a meaningful change, grouped by its effect on users rather than by commit or file. At publication, move the entries under the actual version and release date and open a new Unreleased section. Routine documentation-cache refreshes are tracked by MCP freshness/update metadata, not this file.

## Unreleased

### Added

- Copy-paste agent-assisted setup and feature-development prompts, with a standalone setup guide and manual client instructions as the fallback. No separate setup skill is required.
- Contributor and repository-agent requirements to maintain this changelog with meaningful user-facing changes and explicit migration notes.
- Automated naming, manifest, onboarding, and real MCP identity regression coverage.

### Changed

- Product and MCP registration are now **`UFE3D-MCP`**; plugin and marketplace identifiers are **`ufe3d-mcp`**. The executable/package remains `ufe-docs-mcp`, the module remains `ufe_docs_mcp`, and individual tool names are unchanged.
- README and optional `ufe-docs` development skill lead with building, debugging, and planning UFE features using retrieved reference context. Project changes and verification still require the agent's own tools and the user's authorization.
- Preview instructions select the current PR branch rather than an older release copy. New publication/export and client verification are separate release steps.

### Fixed

- Clarified included connector source versus separately downloaded documentation/cache files, complete plugin checkout requirements, local versus hosted refresh, and evidence limits.
- Kept unrelated client settings and permissions explicitly outside setup/migration scope; setup success requires actual status, search, and retrieval calls rather than configuration alone.

### Security

- Preserved the response-privacy fixes in this PR: cache filesystem paths and raw operational exceptions are not returned over stdio or HTTP, including older persisted failures after restart.
- Preserved sanitized evaluation metadata without relabeling historical results as new evaluations. Local diagnostics and generated configuration still need redaction before sharing.

### Migration

Existing users should inspect older `UFE3D`, `ufe_docs`, or `ufe-docs` entries and confirm they launch this connector. Generate the new `UFE3D-MCP` entry, preserve intended cache/environment/transport/token references and explicit options, and remove or disable only the superseded UFE connection. Check scopes and plugin-provided duplicates. Keep a private rollback copy and leave unrelated settings intact.

For plugins, reinstall or re-export **`ufe3d-mcp`** instead of `ufe3d`. The Claude plugin invocation becomes `/ufe3d-mcp:ufe-docs`. Review UFE-specific permission references for the new namespace without granting broader access. Reconnect and verify through actual MCP calls. No automatic rename or client configuration mutation is performed by the server itself.
