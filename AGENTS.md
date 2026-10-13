# Repository guidance

## Purpose and scope

UFE3D-MCP supplies official UFE reference context to coding agents. The agent's own tools may implement requested game changes; this server does not inspect game projects, edit Unity assets, or verify gameplay. Preserve documentation provenance, publisher warnings, snapshot identity, freshness behavior, input bounds, offline behavior, and response-privacy guarantees.

Use `UFE3D-MCP` as the product/server name and `ufe3d-mcp` as the plugin/marketplace identifier. Keep `ufe-docs-mcp` as the executable/package, `ufe_docs_mcp` as the module, `ufe-docs` as the optional skill, and existing individual tool names. Keep current instructions focused on these names; archived evidence retains the identifiers actually tested. Do not rewrite historical evaluation answers to simulate a fresh run.

## Changelog requirement

For every meaningful user-facing change, update `CHANGELOG.md` under **Unreleased** in the same pull request. Cover functionality, installation, compatibility, privacy, and important documentation. Group related commits into one useful entry; do not dump Git history. Explain omitted changelog entries for purely internal changes in the PR.

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

Do not merge, rewrite history, create paid services, deploy, or change repository visibility without explicit authorization. The canonical repository is `Kenneth-Brisco/Universal-Fight-Engine-MCP`, with the complete source on `main`. Keep current documentation focused on installation and use; preserve historical results in `docs/history/` without presenting them as current instructions. The export manifest is a historical snapshot; ordinary contributor changes do not update its blobs or fingerprint. Metadata checks and normal CI run on PRs and `main`. Follow `CONTRIBUTING.md` and `docs/RELEASING.md` for packaging, privacy, and publication checks.
