# Contributing

Open an issue or a pull request with a reproducible problem, the affected client,
and the expected result. Keep changes focused on documentation retrieval,
freshness, client setup, or the supported transports.

## Local checks

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
git diff --check
```

The test suite uses synthetic documentation and local MCP sessions. It does not
need a paid model session, a Unity installation, or the downloaded UFE manual.

## Protect personal information

- Use your own GitHub-provided `noreply` commit email so GitHub attributes your
  contributions without publishing a personal email address. Configure it for
  this checkout with `git config --local user.email YOUR_GITHUB_NOREPLY_EMAIL`.
  Set `git config --local user.useConfigOnly true` to avoid Git inferring an
  identity from a workstation username and hostname.
- Check both author and committer fields before pushing:
  `git log -1 --format=fuller`. Git configuration changes do not rewrite old
  commits. Create new commits with UTC timestamps if you want to avoid exposing
  a local timezone offset, for example with `TZ=UTC git commit`.
- Keep downloaded documentation databases, refresh state, virtual environments,
  exported machine-specific client configurations, tokens, logs, and personal
  game assets out of commits and archives.
- Normal MCP responses omit cache paths and use safe operational errors. Local
  diagnostic logs, `sync` output, and generated configuration can contain
  machine details. Redact those before sharing an issue or screenshot.
- Review evaluation reports as text before committing them. Remove temporary
  paths, account/session identifiers, tokens, costs, and precise operator times;
  describe any changes to recorded evidence.

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

Keep documentation provenance and evaluation limitations visible. A passing
protocol test is evidence for that transport and source revision; it is not a
new model evaluation or proof of compatibility with an untested client.
