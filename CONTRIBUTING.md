# Contributing

Open an issue or a pull request with a reproducible problem, the affected client,
and the expected result. Keep changes focused on UFE reference retrieval,
freshness, client setup, or the supported transports. Read [AGENTS.md](AGENTS.md)
for repository-agent guidance.

## Keep the changelog useful

Every meaningful user-facing change must update [CHANGELOG.md](CHANGELOG.md)
under **Unreleased** in the same pull request. Cover functionality, setup,
compatibility, privacy, and important documentation changes. Explain the user
impact and any migration action; group related commits rather than listing each
file edit. For purely internal changes with no user impact, state the reason for
omitting an entry in the PR.

At an authorized release, move entries under the actual version and release
date and create a fresh Unreleased section. Never invent past release dates or
claim unfinished work was released. Routine UFE documentation refreshes belong
in MCP freshness/update state rather than the connector changelog.

## Local checks

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
git diff --check
```

The test suite uses synthetic documentation and local MCP sessions. It does not
need a paid model session, a Unity installation, or the downloaded UFE manual.
New naming/onboarding checks must keep direct MCP use independent of skills.

## Names and workflow

The product/server is **UFE3D-MCP**; plugin and marketplace IDs are `ufe3d-mcp`.
The package/executable remains `ufe-docs-mcp`, the module `ufe_docs_mcp`, and the
optional development skill `ufe-docs`. Individual tool names stay unchanged.
Use older names only in migration instructions and historical evidence.

Lead with building and debugging features, but keep the boundary accurate: the
MCP supplies documentation context; the agent's own project tools implement and
verify requested changes. A planning-only question never authorizes editing.
The setup prompt and [setup guide](docs/SETUP.md) are the primary assisted path;
manual client directions remain available. Do not require a separate setup skill.

## Protect personal information

- Use your own GitHub-provided `noreply` commit email so GitHub attributes your
  contributions without publishing a personal email address. Configure it for
  this checkout with `git config --local user.email YOUR_GITHUB_NOREPLY_EMAIL`.
  Set `git config --local user.useConfigOnly true` to avoid Git inferring an
  identity from a workstation username and hostname.
- Check both author and committer fields before pushing:
  `git log -1 --format=fuller`. Git configuration changes do not rewrite old
  commits. Create new commits with UTC timestamps to avoid exposing a local
  timezone offset, for example with `TZ=UTC git commit`.
- Keep downloaded documentation databases, refresh state, virtual environments,
  exported machine-specific client configurations, tokens, logs, and personal
  game assets out of commits and archives.
- Normal MCP responses omit cache paths and use safe operational errors. Local
  diagnostic logs, `sync` output, and generated configuration can contain
  machine details. Redact those before sharing an issue or screenshot.
- Review evaluation reports as text before committing them. Remove temporary
  paths, account/session identifiers, tokens, costs, and precise operator times;
  describe any changes to recorded evidence. Do not rename historical output
  to make it appear that an old test used the new product identity.

Use [GitHub's commit-email guidance](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address)
to locate your account's actual private address. Preserve other contributors'
authorship when incorporating their work.

## Release artifacts

Build from the reviewed source revision in a clean checkout. Include only tracked
project files in a source archive, and inspect wheel/source-distribution contents
before publishing. Do not reuse an archive from an earlier preview or copy a
working directory with its local cache and environment.

The complete GitHub source checkout includes the plugins and `uv.lock`.
Python wheels and source distributions currently package the core server;
do not advertise them as complete plugin installations.

This PR's private development branch and the separate release repository are
different destinations. Changes here do not update a previous release export or
its pinned source-fingerprint audit. Before publication, export the reviewed
source, verify that destination's files and commit identity, update its audit
fingerprint, and replace preview installation links with the actual public
release location. Do not expose the original development history as a shortcut.

Keep documentation provenance and evaluation limitations visible. A passing
protocol test is evidence for that transport and source revision; it is not a
new model evaluation or proof of compatibility with an untested client.
