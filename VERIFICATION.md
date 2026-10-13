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
