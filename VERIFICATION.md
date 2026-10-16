# UFE3D-MCP verification

Verification applies to the revision and environment actually tested. A generated
configuration, a running process, and a completed MCP query are different checks.
Use [the setup guide](docs/SETUP.md) to verify your own installation.

## Verified main baseline

Source: [`7c0140f193eb5914eaea07f5a22a33d5c8901c2c`](https://github.com/Kenneth-Brisco/Universal-Fight-Engine-MCP/commit/7c0140f193eb5914eaea07f5a22a33d5c8901c2c).
Its complete file tree matches the tested `d41dc17dc74379c1e602f5232016a277d603f604`
candidate. These results are a recorded baseline, not a claim that later commits
have been tested by the same run.

| Check | Recorded result |
| --- | --- |
| [CI on main](https://github.com/Kenneth-Brisco/Universal-Fight-Engine-MCP/actions/runs/38358407765) | Python 3.13: 85 tests passed. Python 3.10: 85 cases completed with three expected TOML skips. No ResourceWarnings in the inspected log. |
| Docker and HTTP | Container build, rejection of a public bind without an access policy, health response, unauthorized-request rejection, discovery of four read tools, and an actual MCP status call passed. The smoke test used an empty offline cache. |
| [Metadata audit](https://github.com/Kenneth-Brisco/Universal-Fight-Engine-MCP/actions/runs/38358407804) | Noreply commit-metadata checks passed. Historical export parity was correctly skipped on `main`. |
| Local synthetic suite on `d41dc17` | 85 tests passed on Python 3.13.9 with warnings enabled and no ResourceWarnings. |

The synthetic suite covers generated client configurations, manifests, stdio and
HTTP sessions, search and retrieval, refresh coordination, failure handling, and
response privacy. It uses temporary fixtures without a paid model or live crawl.
For later revisions, inspect their own CI results and record the exact source.

## Real-cache and client evidence

The recorded isolated rehearsal at
[`8293ea0565eacaab93ac9bc054d5afaecf13433c`](https://github.com/Kenneth-Brisco/Universal-Fight-Engine-MCP/commit/8293ea0565eacaab93ac9bc054d5afaecf13433c)
used a real cache containing 223 documents/sections and 1,010 chunks. Sixteen
stdio and sixteen authenticated loopback HTTP calls passed, including status,
search, and retrieval. Offline serving preserved the cache; missing and incorrect
HTTP tokens were rejected. No full refresh or paid model session was run.

Claude Code 2.1.296 connected through the generated `UFE3D-MCP` registration.
The `ufe3d-mcp@ufe3d-mcp` plugin installed and connected after one retry; its
manifest launch also passed SDK status/search/retrieval checks. These are bounded
installation and protocol results, not a new conversational model evaluation.
The [archived rehearsal details](docs/history/RELEASE-PREPARATION.md) retain the
exact conditions and limitations.

Configuration generation for Codex, Cursor, Antigravity, Grok, and generic MCP
clients does not establish a fresh installation in every app. Claude Desktop,
a public HTTPS endpoint, and actual game-feature implementation require separate
checks. A connector test does not verify Unity behavior or gameplay.

## Retrieval quality and live-manual check

These checks ran on 2026-10-15 for the retrieval-quality change (branch `fix/retrieval-quality`, based on `acb7d01`). They are not results for later commits.

| Check | Result |
| --- | --- |
| Retrieval suite (`scripts/eval_retrieval.py`, 56 cases) on a real cache: snapshot `0cebaa7a…`, published catalog generated 2026-07-31, 223 documents | `main` 0.25 (14/56). This change 1.00 (56/56). The change also scored 1.00 on an index rebuilt with the new chunking (1,010 → 787 passages). |
| Synthetic suite | 102 tests passed on Python 3.13. Three timing-sensitive tests failed once while four agent sessions loaded the machine, and passed on rerun and in the next full run. |
| Real-cache stdio session (offline, copy of the cache) | `ufe_search_docs` for the jab→cross question returned Linked Moves, Move Links, and Hit Confirm Options. The envelope fell from 1,574 to 475 characters. `frameLinks` and `allowBlockCancel` resolved to their pages; `ufe_get_doc` returned the Linked Moves clarifications. |
| Live manual, compared in a browser | Linked Moves, Advanced, Hit Stun Options, Animation Options (character), and Effect Options matched the cached text word for word. Each label used by the field mappings checked here was present on its mapped page. |
| Field reference | 180 fields, 23 enums, and 14 notes were read from UFE 2.7.3 engine source. A script checked each field and label against the source, and each note's claims were rechecked by hand. References name the file and class member. |
| Raw pages vs catalog | 10 pages fetched at the site's 10-second crawl delay. All 9 catalog pages matched their raw Markdown line for line, differing only in line endings. The 10th is fetched raw already. |

### Agent round trip

Eight common move-set change tasks were defined, such as "make a jab cancel into a cross only on hit" and "let the player block out of a slow kick". The answer to each was first found in the live manual in a browser, including with the site's own search. The site search returned nothing for "combo into", "frameLinks", "hit stun block", or "return to idle".

Each task was then given to a fresh headless Claude Code agent (Sonnet 5.5) attached only to an offline copy of the real cache, with no web, shell, or file tools. Every task ran against `main` and against this branch.

- **Named settings:** both versions named the right settings (keyword rubric 20/20 each).
- **Factual errors on `main`:**
  - It guessed that `inputBufferType: 2` means Custom. It means None.
  - It recommended Allow Move Canceling to block out of a move, and dismissed Allow Block Cancel.
  - It could not say whether Required Moves blocks standalone use.
- **Gaps on the first branch pass, all fixed here:**
  - The hit-effect preset selector was not found.
  - "Execution Buffer Type" ranked below Move Links pages.
  - Allow Move Canceling was still suggested for blocking out of a move.
  - Enum dropdown text was missing.

  Each gap became an `agent-gaps` retrieval case. On a re-run of those four tasks, each answer was correct and attributed the code-derived facts to the labelled supplement.

The 20 agent runs cost $2.79 in total.

The paid plugin evaluation (0.99 / 0.29 on October 7) was not rerun for this change.

## Source and evaluation limits

The cache covers visible manual navigation, not every UFE website or C# API.
Publisher warning flags and source dates remain visible in tool responses.
Catalog freshness does not certify that every raw page is current; an absent
search result does not prove that a feature is absent.

Selected model evaluations used a baseline without web access. Their scores do
not establish superiority to browsing, time/token savings, or gameplay correctness.
See [evaluation instructions](evals/README.md) and [archived records](docs/history/README.md).

## Reproduce checks for a checkout

```bash
uv sync --frozen
uv run --frozen python -m unittest discover -s tests -v
git diff --check
```

Then follow [onboarding verification](docs/ONBOARDING-VERIFICATION.md) for actual
MCP calls in the intended client. Record client/version, source commit, transport,
cache scope, results, and any remaining manual action. Never substitute historical
results for those checks.
