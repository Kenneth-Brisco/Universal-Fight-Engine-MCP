# UFE3D-MCP naming and onboarding verification

## Revision scope

This PR update follows privacy-preparation commit `51f824dd513100805c5b618016435ea69aab15ca` on `fix/public-release-readiness`. It changes the product/server registration to `UFE3D-MCP`, plugin/marketplace names to `ufe3d-mcp`, README positioning, agent-assisted setup, the optional development skill, and changelog maintenance. The executable, module, tool names, dependency lock, documentation corpus, and retrieval/freshness/privacy implementations are not renamed or replaced.

## Automated evidence to inspect

The CI run for the exact reviewed PR head is the execution record. Do not reuse a green run from the earlier privacy commit as proof of the naming revision. The existing workflow runs the full synthetic suite on Python 3.10 and 3.13, then builds the Docker image and checks bind policy and authenticated HTTP MCP behavior.

New naming/onboarding tests cover fixed expected identifiers, local/remote client configuration, marketplace and manifests, exported plugins, required setup/changelog guidance, and real stdio initialization plus status/search/retrieval. Existing HTTP tests and the smoke script verify the renamed health identity; initialization identity is also checked. No installed Claude/Codex settings are changed by these tests.

The local authoring container did not have the locked MCP dependencies or working external package access. Full-suite results must therefore come from inspected GitHub CI, not a claim of local execution. Check the current PR description for the exact run and outcome.

## Evidence limits

- The setup guide is a reviewed instruction sequence, not an automatic installer or a guarantee that every agent can configure every client.
- No separate setup skill is required. The existing development skill is optional and preserves explanation-only requests, source warnings, and permission boundaries.
- Synthetic SDK tests do not replace a fresh renamed plugin installation in Claude Code, Codex, Cursor, Antigravity, or Grok.
- No paid model session, live UFE documentation crawl, new hosted deployment, or real game-feature implementation was performed for this revision.
- Historical answers, scores, timestamps, and tool names in `VERIFICATION.md` and the evaluation report remain historical evidence; they are not relabeled as fresh runs.

## Release-copy boundary

The separate `Kenneth-Brisco/UFE3D-MCP` release copy previously recorded at `3a38ef96e7b5e172ffdcaa95d004384825ceb9e5` and its source-fingerprint audit predate this revision. They have not been updated by this PR change. The README therefore points reviewers to the development PR branch. A future public export must be independently synchronized, audited, and verified, with public installation links updated at publication. Both merge readiness and publication readiness require separate verdicts.
