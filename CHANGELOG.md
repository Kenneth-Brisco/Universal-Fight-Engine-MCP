# Changelog

Meaningful user-facing changes to **UFE3D-MCP** are recorded here. Entries follow
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Update **Unreleased** in
the same PR as a meaningful change, grouping entries by user impact.

At an authorized versioned release, use the actual version and release date.
Routine documentation-cache refreshes are tracked by MCP freshness/update state,
not connector releases.

## Unreleased

### Added

- Search resolves serialized UFE field names from `.asset` files and engine code (`frameLinks`, `linkType`, `_blendingTime`, `hitStunOnBlock` and about 175 more) to their Inspector label and manual page. It reports stored enum values such as `LinkType`, `InputBufferType` and `ExecutionBufferType` in a labelled, versioned `field_matches` supplement that is kept separate from manual text.
- Clarification notes, with UFE 2.7.3 source references, for settings whose manual wording is easy to misread or incomplete: Allow Block Cancel, Allow Move Canceling, Startup Frame, Hit Stun Options, Required Moves, Reaction Clip (it also selects the preset hit effect), and Override Hit Effects. Gauge notes cover the automatic fill/drain settings that the Gauge Options page omits, when Reset every round actually runs (round end), what Only if active GOT tests, where Delta Value Type = Percentage applies (life damage and requirements, not gauge deltas), and a statically observed double application of On Parry gauge adjustments. Search passages show a one-sentence summary, and `ufe_get_doc` shows the full note.
- Enum values include the Inspector dropdown text (`NoConditions` is shown as "No Conditions").
- Search passages from pages with tutorial videos list them as `videos` links. Video content is not indexed.
- A deterministic retrieval-quality suite: `scripts/eval_retrieval.py` with `evals/retrieval/cases.json`.
- Confidentiality rules for users' games, in `AGENTS.md` (loaded by `CLAUDE.md` for Claude Code), `CONTRIBUTING.md`, and the `ufe-docs` skill.
  - Agents and contributors keep game titles, characters, moves, mechanics, assets, paths, and project code out of search queries, the repository, and GitHub posts.
  - Engine facts are recorded by file and class member, never line numbers.
  - A test rejects personal home paths in tracked files.

- Local stdio and Streamable HTTP access to official UFE reference context,
  including search, document retrieval, topics, source links, and freshness warnings.
- Agent-assisted setup, a standalone setup guide, manual client instructions,
  and an optional `ufe-docs` development skill. No installation skill is required.
- Client configuration/plugin support and synthetic protocol, packaging,
  onboarding, freshness, and privacy checks.

### Changed

- Search, document, and topic responses are compact by default. The repeated snapshot and freshness envelope fell from about 1.5 KB to under 0.5 KB. `verbose: true` and `ufe_docs_status` still return the full records, including the catalog-lag notice.
- Search ranking prefers passages that cover more of the question, Options sections, and passages defining a setting the question names. When a question names a page, its Options section comes first. Questions about gauge regeneration reach Gauge Options.
- Search no longer spends a result slot on a heading or a scrap of text clipped by `max_chars`; it reports truncation instead. It limits each page to two passages and understands cancel, chain, link, and "combo into" questions, so they reach the Move Links pages.

- Current documentation uses `main` and the `UFE3D-MCP` server / `ufe3d-mcp`
  plugin names. Removed obsolete setup guidance and the creator biography.
- Shortened the README to one setup and development path with explicit MCP
  verification. Advanced local options and plugin instructions are in SETUP.md.
- Moved development-stage verification and preparation records into a labeled
  history archive, preserving their results. Current verification and maintainer
  release instructions are separate from those records.
- Contributor checks cover commit metadata on PRs and `main` without requiring
  routine changes to rewrite the historical export manifest.

### Fixed

- Search no longer returns heading-only passages ("# Combo") or Related Pages link lists while other passages match. Page titles stay with their first section when the index is rebuilt.

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
