# Repository guidance

## Purpose and scope

UFE3D-MCP supplies official UFE reference context to coding agents. The agent's own tools may implement requested game changes; this server does not inspect game projects, edit Unity assets, or verify gameplay. Preserve documentation provenance, publisher warnings, snapshot identity, freshness behavior, input bounds, offline behavior, and response-privacy guarantees.

Use `UFE3D-MCP` as the product/server name and `ufe3d-mcp` as the plugin/marketplace identifier. Keep `ufe-docs-mcp` as the executable/package, `ufe_docs_mcp` as the module, `ufe-docs` as the optional skill, and existing individual tool names. Older names are appropriate only in migration notes and honestly labeled historical evidence. Do not rewrite historical evaluation answers to simulate a fresh run.

## Changelog requirement

For every meaningful user-facing change, update `CHANGELOG.md` under **Unreleased** in the same pull request. Include functionality, installation, compatibility, privacy, important documentation, and migration changes. Group related commits into one useful entry; do not dump Git history. Explain omitted changelog entries for purely internal changes in the PR.

At an authorized release, use the actual version and release date. Do not invent dates or present unfinished work as shipped. Documentation-cache refreshes belong in freshness/update state, not the connector changelog.

## Implementation and verification

Read the affected code and applicable specification before editing. Keep changes scoped, preserve unrelated work, and test the final source revision. Typical checks:

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
git diff --check
```

Use synthetic fixtures for automated checks; do not start paid model runs, a live documentation crawl, or a full raw-page refresh without authorization. Report separately local execution, inspected CI, and historical claims. A configuration file, CLI search, or process-health response is not evidence of a completed client MCP tool call.

## Privacy and release discipline

Never commit personal paths, credentials, local caches, generated client settings, raw logs, or private game assets. Preserve safe operational errors in both transports. Use the current contributor's own verified GitHub noreply identity and UTC offsets for new commits; never attribute another contributor's work to the maintainer. Inspect author and committer metadata before publishing.

UTC is a metadata consistency convention. A timezone offset alone is not a security finding or a merge/publication blocker; report deviations as advisory. Assess retained personal email addresses separately from timezone offsets and credentials. Do not require history rewrites or a support request merely to eliminate timezone offsets, and do not claim retained GitHub objects have been erased.

Do not merge, rewrite history, create paid services, deploy, or change repository visibility without explicit authorization. The user-selected open-source home is `Kenneth-Brisco/Universal-Fight-Engine-MCP`; the complete candidate is PR #3's `fix/public-release-readiness` branch until authorized promotion. Keep the earlier export accounted for in `release-export.json` and `docs/RELEASE-EXPORT.md`, including documented repository-specific differences. Publication requires an audit of this repository's own history, refs, logs, artifacts, and commit metadata; an audit of another repository does not transfer here. Follow `CONTRIBUTING.md` for packaging and privacy checks.
