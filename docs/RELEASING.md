# Release and publication checklist

The complete source is on `main` in `Kenneth-Brisco/Universal-Fight-Engine-MCP`.
Installation instructions use that branch unless a specific revision is supplied.
Merging code, changing repository visibility, deploying a service, and publishing
a package are separate actions requiring the owner's authorization.

## Select and validate the source

1. Choose the exact reviewed commit and preserve unrelated work. Use a clean
   checkout; record the source commit and resulting archive or package contents.
2. Run the frozen environment and synthetic suite from [CONTRIBUTING.md](../CONTRIBUTING.md).
   Inspect CI for that revision, including Python 3.10/3.13 and Docker/HTTP checks.
   Investigate failures; do not treat a green run for another tree as proof.
3. Keep README, setup commands, repository URLs, and client names consistent with
   the chosen source. Rehearse installation in an isolated client configuration
   and verify status → search → get-document through MCP. Preserve the user's
   existing settings and report any client or manual-action limitations.

## Inspect distribution contents and privacy

- Build only from tracked source. The full checkout includes plugins, skills,
  and `uv.lock`; Python wheels/source distributions package the core server.
  Neither format includes the downloaded manual, local cache, or game assets.
- Inspect files and archive metadata for personal paths, emails, hostnames,
  credentials, and build-account details. Normalize archive ownership metadata
  when necessary, then verify member bytes against the approved source.
- Check author and committer identities, refs, logs, and artifacts. Preserve
  contributor attribution and use noreply email metadata. A clean reachable
  history does not prove retained GitHub objects were erased.
- The historical audit found a retained SHA-addressed object with a personal
  email, but no credential in the inspected material. Account for that residual
  privacy exposure before publication; removing a reference does not purge it.
  Timezone offsets are advisory, not security or publication blockers, and do
  not require a support request or another rewrite.

The [archived preparation record](history/RELEASE-PREPARATION.md) describes the
earlier audit's exact scope. It is evidence for its recorded revisions, not a
current installation guide or clearance for newly added material.

## Publish only with authorization

Keep the repository private until the owner explicitly authorizes visibility.
After authorized publication, verify anonymous clone/source-ZIP access, LICENSE,
setup links, and the optional marketplace, then repeat actual MCP queries from
the public installation. Private authenticated checks cannot prove anonymous access.

A source-only launch does not require paid hosting, a public MCP endpoint, a
package-registry upload, or a tag. If making a versioned release, update all
version-bearing manifests consistently and move the relevant Unreleased changelog
entries under the actual version and date. Do not invent release dates.

## Historical export audit

`release-export.json` records the source snapshot used during release preparation.
Ordinary contributor PRs do not update its blobs or pinned workflow fingerprint.
CI and commit-metadata checks continue on PRs and `main`; the fixed snapshot
comparison is reserved for the recorded preparation branch or an explicit manual
audit. Run that comparison against its recorded source, not an evolving `main`.
A future export audit needs a deliberately selected and reviewed new snapshot.
