# Changelog

Meaningful user-facing changes to **UFE3D-MCP** are recorded here. Entries follow
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Update **Unreleased** in
the same PR as a meaningful change, grouping entries by user impact.

At an authorized versioned release, use the actual version and release date.
Routine documentation-cache refreshes are tracked by MCP freshness/update state,
not connector releases.

## Unreleased

### Added

- Local stdio and Streamable HTTP access to official UFE reference context,
  including search, document retrieval, topics, source links, and freshness warnings.
- Agent-assisted setup, a standalone setup guide, manual client instructions,
  and an optional `ufe-docs` development skill. No installation skill is required.
- Client configuration/plugin support and synthetic protocol, packaging,
  onboarding, freshness, and privacy checks.

### Changed

- Current documentation uses `main` and the `UFE3D-MCP` server / `ufe3d-mcp`
  plugin names. Removed obsolete setup guidance and personal origin-story copy.
- Moved development-stage verification and preparation records into a labeled
  history archive, preserving their results. Current verification and maintainer
  release instructions are separate from those records.
- Contributor checks cover commit metadata on PRs and `main` without requiring
  routine changes to rewrite the historical export manifest.

### Fixed

- Generated POSIX registration commands preserve literal paths, URLs, and token
  references containing quotes and shell metacharacters. Codex TOML supports
  Unicode paths while retaining required escaping.
- Setup preserves unrelated client settings and permissions and requires actual
  status, search, and document-retrieval calls to establish MCP verification.

### Security

- Stdio and HTTP responses omit local cache paths and raw operational exceptions,
  including persisted failures after restart, while retaining source passages,
  official URLs, publisher warnings, and actionable errors.
- Distribution guidance covers source contents, archive ownership metadata,
  evaluation redaction, and retained-object privacy limits. Generated settings
  and detailed local diagnostics still require redaction before sharing.
