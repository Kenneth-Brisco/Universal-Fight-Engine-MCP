# Canonical repository and release parity

**`Kenneth-Brisco/Universal-Fight-Engine-MCP` is the user-selected open-source
home for UFE3D-MCP.** The complete candidate is PR #3's
`fix/public-release-readiness` branch. The original `main` is not the complete
candidate. The repository remains private; no merge, publication, deployment,
or history rewrite is authorized by preparing these files.

## Everything from the earlier export is accounted for

The comparison baseline is the earlier private `Kenneth-Brisco/UFE3D-MCP`
candidate at `60d8d798f86fe93609509e98d4f94b7315a34841`. That export came from
this repository's tested PR #3 head
`0b9809867d48d8eb9910a78f2f42013d2cb62c3c`, with PR base
`656a7cca57fe3a9f38700c7866455ca3e58f59c2`. It is now a historical comparison
record, not the intended installation or publication destination.

The [manifest](../release-export.json) accounts for **all 129 baseline paths**.
No connector capability, test, skill, evaluation record, or other baseline file
is omitted. Runtime modules, dependencies, lock file, tests, optional skill,
evaluation material, assets, and the original CI workflow are byte-identical.
The repository URL in the Claude plugin manifest now selects the canonical home.
Documentation combines the export's setup/evidence and archive-privacy
improvements with the correct repository and PR branch. AGENTS guidance and the
three release-audit files are adapted to that same decision. Each differing
file is identified in the manifest; stale instructions are not copied verbatim.

The audit workflow pins the manifest hash, reconstructs the immutable comparison
tree from recorded Git blobs/modes, and checks the exact current tracked-file
list and expected blobs. Manifest/workflow control files are explicitly marked
to avoid self-referential hashes. The original export's immutable
[report](https://github.com/Kenneth-Brisco/UFE3D-MCP/blob/60d8d798f86fe93609509e98d4f94b7315a34841/docs/RELEASE-EXPORT.md),
[manifest](https://github.com/Kenneth-Brisco/UFE3D-MCP/blob/60d8d798f86fe93609509e98d4f94b7315a34841/release-export.json),
and [audit](https://github.com/Kenneth-Brisco/UFE3D-MCP/actions/runs/38347370614)
remain historical evidence. No import of that repository's Git history is needed.

When updating this candidate, regenerate the expected-current blobs and review
all documented differences; keep the comparison commit/tree fixed unless a new
baseline is explicitly chosen. Update the manifest hash in the audit workflow.
A later candidate needs fresh validation; a prior successful audit is not proof
of a changed revision.

## Executed evidence and its exact scope

The tested implementation at source `0b9809867d48d8eb9910a78f2f42013d2cb62c3c`
and the earlier export `60d8d798f86fe93609509e98d4f94b7315a34841` have these records:

- Frozen local Python 3.13.9 suite: 85 tests passed with no SQLite ResourceWarnings.
- [Source CI 38344195977](https://github.com/Kenneth-Brisco/Universal-Fight-Engine-MCP/actions/runs/38344195977)
  passed Python 3.10/3.13 and Docker/HTTP checks. Its generated merge commit
  `887beebdecc20ecc201149b103967d42c22e97a5` has the recorded PR base/head as
  parents and a tree identical to the tested head.
- [Earlier export CI 38347367757](https://github.com/Kenneth-Brisco/UFE3D-MCP/actions/runs/38347367757)
  passed Python 3.10/3.13 and Docker/HTTP checks at exact export commit `60d8d79`.
  Python 3.10 skipped three TOML tests requiring Python 3.11+; Python 3.13 skipped
  none. Neither run emitted SQLite ResourceWarnings.
- A fresh clone of that export installed with `uv sync --frozen`. MCP SDK clients
  made 16 successful tool calls over stdio and 16 over authenticated loopback
  HTTP: status, search, returned-document retrieval, pagination, topics, publisher
  warnings, and safe unknown-document errors. Missing/wrong HTTP tokens returned
  401. Health returned 200; HTTP refresh remained hidden by default.
- Real cache: 223 documents / 1,010 chunks, revision
  `857f56a2d337083619174a80be1b94a44255a2f0a8ada5c5a67ade9c44a775e4`,
  catalog dated 2026-07-31. The authorized normal sync used the published catalog
  and one supplemental raw page, respecting request spacing. Export rehearsals
  reused isolated copies and left database/refresh-state bytes unchanged. There
  was no full raw refresh or paid model session.
- Queries covered input-buffer/frame links, rollback balancing, hitbox collision
  types, and air recovery. Official URLs and `needs_verification` /
  `legacy_docs_differ` flags remained visible; cache paths were absent from MCP
  responses. These checks do not establish game implementation correctness.
- Claude Code 2.1.296 connected through generated `UFE3D-MCP` registration in
  empty isolated profiles. Existing Claude/Codex settings were fingerprinted
  unchanged. Actual tool calls used the SDK; no paid model conversation was run.
- Wheel/source-distribution contents were inspected. The initial local source
  archive contained the build account in tar ownership headers. Its local copy
  was normalized to empty owner/group names, uid/gid zero, and the source commit
  timestamp, preserving member bytes. Future builds need this same inspection.
  No package was uploaded. These core-server packages are not complete plugins.

Current repository-selection changes are documentation, metadata, and audit
changes. Match new CI and local validation to their exact PR head; the historical
runs above must not be relabeled as new-head execution. The client table lists
configuration support, not newly proven installations in every app. Renamed
plugin installation, conversational calls in another app, a public HTTPS service,
and a Unity feature implementation require their own relevant checks.

## Privacy scope: this repository needs its own publication audit

The earlier export's tracked content, visual/HTML metadata, and built package
contents were inspected without finding real credentials or operator identifiers
in file content. Generic container paths and explicitly synthetic privacy-test
fixtures remained. Official passages, URLs, warnings, and historical evaluation
names were preserved. That result does not clear this repository's history.

At source head `0b9809867d48d8eb9910a78f2f42013d2cb62c3c`, the reachable-history
metadata check found 16 older commits with non-UTC offsets; 13 also used
non-noreply email metadata. Values are intentionally not reproduced here.
The audit workflow verifies the current commit's noreply/UTC metadata
and reports historical metadata concerns separately. **A green parity/current-
commit audit is not publication privacy approval.** The workflow does not audit
all historical file contents, private PR references, logs, or retained artifacts.
An unsigned commit must not be described as cryptographically signed.

The other repository's retained `private-release-history-backup` artifact
(ID `11782643238`, run `38331617316`) and addressable older objects are findings
about `Kenneth-Brisco/UFE3D-MCP` only. Its five original retained logs were scanned
without credential/operator markers; its backup contained a non-UTC commit.
Those observations neither prove nor disprove this repository's retained-data
privacy. No history, artifact, log, or backup was deleted during consolidation.

## Before publishing this repository

1. Review and validate the exact PR #3 head, including file parity, setup, tests,
   and commit identity. Keep the repository private during preparation.
2. Audit this repository's historical content, commit metadata, branches/tags,
   PR references, Actions logs, and artifacts. Address sensitive findings through
   an explicitly authorized plan that preserves attribution. Changing new commit
   settings does not sanitize old commits, and a clean branch log cannot confirm
   that older GitHub objects were removed. Involve GitHub support if necessary.
3. With separate authorization, promote the approved complete candidate to the
   intended default/release ref, choose the actual release version/date, and
   update preview links within this same repository. Do not switch repositories
   merely to avoid completing these checks.
4. Rehearse any additional client/plugin or hosted claims, then obtain explicit
   publication/visibility authorization. Verify anonymous installation after
   publication is authorized. Do not infer gameplay correctness from retrieval.
