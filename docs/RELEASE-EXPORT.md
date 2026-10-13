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
`0b9809867d48d8eb9910a78f2f42013d2cb62c3c`. Its historical PR base is represented
in the rewritten history by `99a42414411bcb95ac0724acf147ebacdf731e24`; the
pre-rewrite base SHA is intentionally not repeated here. This preserves the
comparison's provenance without providing a direct pointer to former personal
email metadata. The export is a historical comparison record, not the intended
installation or publication destination. Removing this pointer does not purge
GitHub's retained objects or earlier copies of this document.

The [manifest](../release-export.json) accounts for **all 129 baseline paths**.
No connector capability, test, skill, evaluation record, or other baseline file
is omitted. Runtime modules, dependencies, lock file, tests, optional skill,
evaluation material, assets, and the original CI workflow are byte-identical.
`VERIFICATION.md` adds historical revision labels and corrects naming context;
its recorded test counts, evaluation answers, and results are preserved.
The repository URL in the Claude plugin manifest now selects the canonical home.
Documentation combines the export's setup/evidence and archive-privacy
improvements with the correct repository and PR branch. AGENTS guidance and the
three release-audit files are adapted to that same decision. Each differing
file is identified in the manifest; stale instructions are not copied verbatim.

On the preparation branch, the audit workflow pins the manifest hash, reconstructs the immutable comparison
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

## Audit lifecycle and future contributions

The workflow checks commit metadata on all PRs and on pushes to `main` and
`fix/public-release-readiness`. The fixed export-parity step runs automatically
only for the preparation branch (a PR whose head is that branch, or a push to
it). A manual workflow run can opt into **Verify the recorded export snapshot**
for the selected ref. Its default is metadata-only outside the preparation
branch. Each step checks the commit actually selected by the workflow.

After promotion, this manifest remains evidence for the prepared snapshot.
Ordinary contributor PRs and pushes to `main` do not need to rewrite the old
129-file manifest or its pinned hash when files change. They still receive
metadata checks and the normal Python/container CI. A deliberate later export
audit must first record and review its new candidate differences; opting into
the historical parity check on changed source should fail.

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
configuration support, not newly proven installations in every app.

A later preparation rehearsal used the same unchanged plugin/runtime files in
an empty Claude Code 2.1.296 profile: the local marketplace validated, and
`ufe3d-mcp@ufe3d-mcp` installed and was enabled. The first plugin connection check
timed out at 30 seconds; one reconnect succeeded in about eight seconds. The
reconnect log reported cached legacy-protocol fallback. The plugin manifest's
exact launch command separately passed SDK status → search → get-document calls
against the isolated 223-document cache with offline mode enabled. This proves
installation/connection and the server command's retrieval path, not a paid
conversational invocation of the optional skill. Existing client settings were
fingerprinted unchanged. Record this limitation when repeating the rehearsal;
do not suppress an unsuccessful first attempt or repeatedly retry a broken setup.

Conversational calls in another app, a public HTTPS service, and a Unity feature
implementation require their own relevant checks.

## Privacy scope: this repository needs its own publication audit

The earlier export's tracked content, visual/HTML metadata, and built package
contents were inspected without finding real credentials or operator identifiers
in file content. Generic container paths and explicitly synthetic privacy-test
fixtures remained. Official passages, URLs, warnings, and historical evaluation
names were preserved. That result does not clear this repository's history.

The UTC/noreply cleanup normalizes all 18 commits in the four branch histories
at the pre-cleanup head. Sixteen had non-UTC offsets; thirteen used non-noreply
email metadata. Kenneth confirmed ownership of the eight commits whose former
email GitHub did not associate with his account. Both author and committer now
use his verified noreply identity and `+0000`. Author names, absolute timestamp
seconds, commit messages, parent relationships, and every commit's file tree
were verified unchanged. The subsequent audit-record commit also uses UTC and
noreply metadata. No branches were merged and no product files were rewritten.

The rewritten equivalent of the pre-cleanup PR #3 head is
`2ea9b158f8aafdacc91adcd9067e3a13b07e8e95`;
its corresponding base is `99a42414411bcb95ac0724acf147ebacdf731e24`.
Historical test/run identifiers above retain their original meanings. The
rewritten equivalent of tested implementation `0b98098` is
`c57a0fb7ba0bbd2c0d97fca9b3712dd89387b7b9` with the same tree.
The metadata rewrite removed eight old commit signatures; none had been shown
verified by GitHub. Rewritten commits are unsigned. Profile attribution is not
cryptographic signature verification.

The release audit checks noreply identity on every PR update and pushes to the
default/preparation branches. Fixed-snapshot parity is limited to the preparation
branch or an explicit manual export audit, as described above.
**Non-UTC offsets are advisory, not merge or publication blockers.** UTC remains
the convention for new commits; the owner has explicitly accepted the old
timezone offset as non-blocking. The workflow does not inspect every retained
GitHub object or authorize publication.

### Completed repository audit and residual privacy

At cleanup head `a665b309cce8e9c1cd381faee2fd4e53cef66fbb`, a fresh remote mirror
covered four branches and all three PR head/merge refs: 22 reachable commits,
all using UTC/noreply metadata. Targeted historical-file scans found only
explicitly synthetic privacy-test paths and no actual operator paths or known
personal email strings in file contents. Twenty retained pre-cleanup Actions
logs were checked without known private-email, operator, or credential matches.
This repository's Actions artifact inventory was empty. These are scoped checks,
not a guarantee that every possible secret or external copy has been discovered.

The next five completed post-cleanup workflow logs also had no targeted privacy
matches. Two superseded runs were canceled within two seconds and their logs
were unavailable; their contents were not claimed as inspected. Current source
files were rescanned, including SVG/HTML metadata; only the deliberate synthetic
paths in `tests/test_privacy.py` matched the operator-path pattern.

The frozen local suite passed 85 tests. [CI 38349499088](https://github.com/Kenneth-Brisco/Universal-Fight-Engine-MCP/actions/runs/38349499088)
passed Python 3.10/3.13 and Docker/HTTP checks, and the generated merge tree
matched that exact head. [Parity/metadata audit 38349499135](https://github.com/Kenneth-Brisco/Universal-Fight-Engine-MCP/actions/runs/38349499135)
also passed. These runs apply to `a665b309`; later preparation commits need their
own checks and must not borrow this result as proof of execution.

An authenticated request could still retrieve an old SHA-addressed commit with
former personal email metadata. The repository was private; this did not
demonstrate anonymous access or an authorization bypass. Old metadata includes
ordinary email addresses, timestamps, and a numeric timezone offset. No exposed
credential was found in the inspected material. Email retention is a residual
privacy consideration (spam, phishing, or identity correlation), not evidence
of account compromise. A timezone offset is shared by many places and can be
configured independently of physical location; it does not identify a country.

There is **no timezone-based release blocker and no required support request**.
No additional rewrite is required by this finding. Before changing visibility,
the owner should account for the possibility that retained personal email
metadata becomes accessible; do not claim it was purged. GitHub's
[retained-data guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
explains why rewritten branch history does not establish removal of all old
objects. A new discovery of credentials would require its own assessment.

Use a fresh clone after this rewrite. Preserve uncommitted work separately;
do not merge or push an old local branch back into the normalized history.
A private local rollback bundle and complete old-to-new mapping were retained
outside all repositories; neither was uploaded as a branch, tag, or artifact.
Existing user checkouts and client settings were left untouched.

The other repository's retained `private-release-history-backup` artifact
(ID `11782643238`, run `38331617316`) and addressable older objects are findings
about `Kenneth-Brisco/UFE3D-MCP` only. Its five original retained logs were scanned
without credential/operator markers; its backup contained a non-UTC commit.
Those observations neither prove nor disprove this repository's retained-data
privacy. No history, artifact, log, or backup was deleted during consolidation.

## Before publishing this repository

The MIT license, complete source, locked dependencies, source provenance,
contribution guide, Unreleased changelog, manual/agent setup, and transport tests
are already included. The scope of the initial open-source offering is the
source checkout with local stdio and operator-hosted HTTP support. A public
hosted endpoint, package-registry upload, and paid model evaluation are optional
follow-ups, not requirements for publishing this source repository.

1. Validate the final PR #3 head with frozen tests, parity, and commit-identity
   checks. Match every claimed CI/client result to the revision actually tested.
   Keep the repository private and the PR ready for review. Any required review
   or evidence-posting step must respect the owner's separate posting authority.
2. With separate merge/promotion authorization, bring the **complete stacked
   candidate** onto the intended default branch. PR #3 currently targets PR #2's
   branch, so merging #3 alone does not update `main`. Either promote the stack
   in the appropriate order or use an explicitly approved direct promotion of
   the complete candidate. Verify the resulting default-branch tree against the
   approved candidate; do not accidentally release the original incomplete `main`.
3. In that approved promotion, replace private-preview wording and
   `fix/public-release-readiness` setup references in README/SETUP with the chosen
   public default/release ref, then refresh the parity manifest and its workflow
   fingerprint for the final preparation snapshot. Confirm that ordinary PRs and
   `main` pushes run metadata/normal CI without the historical parity gate;
   manually opt into parity when checking the approved final snapshot itself.
   Rehearse that exact checkout. If creating a versioned release,
   use the actual version/date, update all version-bearing manifests consistently,
   and move the relevant Unreleased entries. A tag or PyPI upload is not required
   just to make the MIT-licensed source public.
4. Obtain explicit visibility authorization, with the residual personal-email
   privacy detail above understood. The timezone detail is already accepted as
   non-blocking; no support request is required. Recheck for any newly introduced
   files, refs, logs, or artifacts since this audit rather than repeating history
   rewrites. Keep the unrelated export and staging repositories private.
5. Immediately after authorized publication, verify anonymous access to the
   default branch, LICENSE, setup guide, clone/source ZIP, and optional marketplace.
   Repeat status → search → get-document against the public installation. Before
   publication, private authenticated testing cannot prove anonymous access.

Client claims remain limited to the recorded evidence. Additional app-specific
rehearsals are required before describing those apps as freshly verified, but
are not blockers for source publication with the current qualified client table.
Do not infer gameplay correctness from documentation retrieval tests.
