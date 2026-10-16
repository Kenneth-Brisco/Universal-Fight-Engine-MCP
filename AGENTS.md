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

## Users' games and projects are confidential

People use UFE3D-MCP while building their own games. Their projects are their intellectual property. Work on this repository often starts from one of them: a bug noticed in someone's game, an engine copy inside their Unity project, or a question about their move set. **Nothing that identifies or reveals a user's or contributor's game may enter this repository or its public GitHub surface.** This applies to the maintainer's own games too. The repository is public and open source; treat every committed byte and every GitHub post as published permanently.

### What counts as project information

- Game, studio, team, and working titles, including abbreviations, code names, and prefixes used in their code (for example a class or file prefix).
- Characters, fighters, stages, story, lore, factions, and their move lists and move names, when those names come from the project, even if they sound generic.
- Original or proprietary mechanics, balance values, frame data, design documents, art, audio, animations, and screenshots.
- Paths, folder and branch names, asset and prefab names, scene names, build names, and repository names from the project.
- Code from the project, including the project's own modifications to UFE engine files.
- Facts about the project's setup, such as which UFE version it runs, which files it has changed, or that a particular project exists.

### Where it must never appear

- Every tracked file: source code, the field reference data, tests, fixtures, evaluation cases and prompts, eval reports, documentation, `CHANGELOG.md`, `VERIFICATION.md`, and the specification.
- Commit messages, branch names, tags, pull request titles and descriptions, issues, review comments, release notes, and gists linked from them.
- Tool responses and server instructions shipped by this package.

### How to work when a task comes from a real project

- **Abstract the origin.** Write "a coding agent researching move links found…" rather than naming the game or its owner. Restate bug reports, eval cases, and verification tasks with generic fighting-game examples: jab, cross, low kick, launcher, Character A, Stage 1. Do not reuse the project's own move list even if the names look generic.
- **Engine source.** UFE is licensed software. When an engine copy inside someone's project is the only source available, record only stock UFE facts, and only as names, labels, ordinals, and short summaries in your own words; never copy code.
  - Stock UFE facts are field, enum, method, and class names, Inspector labels, and the UFE version.
  - Exclude any field, class, file, or behavior that is not part of stock UFE. Project copies are often modified, sometimes without obvious markers.
  - Reference a file relative to `Assets/UFE/Engine/` plus the class member (`ControlsScript.cs (GetHit)`), never line numbers, because a modified copy shifts them.
  - Never state where the copy lives or that it came from a particular project.
- **Live checks.** Verify behavior with generic tasks against the public manual and stock engine facts. Paid or headless agent runs used as evidence must use generic prompts. Keep their transcripts out of the repository unless they have been reviewed for project information.
- **Local scratch work** (caches, transcripts, copied engine files) stays outside the repository and is never committed, attached, or quoted.

### Check before every commit, push, and GitHub post

1. List the project-specific names known from your task context: game title, studio, prefixes, character and move names, paths. Then search the change and its message for each one, case-insensitively, for example `git grep -n -i -E 'name1|name2' $(git merge-base origin/main HEAD)`. Also search `git log origin/main..HEAD`. Do not commit that list of names anywhere.
2. Search for absolute home paths (`/Users/`, `/home/`, `C:\Users\`) and machine names. The test suite rejects home paths in tracked files.
3. Reread the pull request title, description, and any review or issue text before posting. They are not covered by the tests.

### If project information was already pushed

Stop and tell the maintainer exactly what leaked and where. Fix the current files and PR text in a new commit right away. Rewriting history, force-pushing, or deleting content requires the maintainer's explicit authorization. Do not claim the information has been erased: GitHub retains pushed commits and edited descriptions in its history.

## Privacy and release discipline

Never commit personal paths, credentials, local caches, generated client settings, raw logs, or private game assets. Preserve safe operational errors in both transports. Use the current contributor's own verified GitHub noreply identity and UTC offsets for new commits; never attribute another contributor's work to the maintainer. Inspect author and committer metadata before publishing.

UTC is a metadata consistency convention. A timezone offset alone is not a security finding or a merge/publication blocker; report deviations as advisory. Assess retained personal email addresses separately from timezone offsets and credentials. Do not require history rewrites or a support request merely to eliminate timezone offsets, and do not claim retained GitHub objects have been erased.

Do not merge, rewrite history, create paid services, deploy, or change repository visibility without explicit authorization. The canonical repository is `Kenneth-Brisco/Universal-Fight-Engine-MCP`, with the complete source on `main`. Keep current documentation focused on installation and use; preserve historical results in `docs/history/` without presenting them as current instructions. The export manifest is a historical snapshot; ordinary contributor changes do not update its blobs or fingerprint. Metadata checks and normal CI run on PRs and `main`. Follow `CONTRIBUTING.md` and `docs/RELEASING.md` for packaging, privacy, and publication checks.
