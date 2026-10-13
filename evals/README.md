# UFE3D-MCP plugin evals

Nine realistic UFE questions with checkable answers, run with `claude plugin eval` against the plugin and against a no-plugin baseline. The baseline has no web access, so the score difference (`Δ`) shows what the documentation tools add over the model's own knowledge in these selected cases—not performance on a game implementation.

Each case checks exact UFE setting names with regex graders, the official manual URL supporting the answer, and correctness with a short judged rubric. Two cases target pages the publisher flags (`needs_verification`, `legacy_docs_differ`) and check that the warning reaches the user. One case asks about a feature the manual does not document and checks that the answer does not invent one. Skill invocation and documentation tool use are reported as indicators, not scored.

## Before running

These evaluations use paid model execution when run against a billed provider. Run only with explicit authorization and a bounded budget. They are not required for ordinary setup or the synthetic CI suite.

Eval runs use a temporary home directory. Each case's `scaffold.sh` copies your existing documentation index into it, so the plugin's server answers from that copy instead of downloading the manual for every run. The script stops if the index is missing or more than 20 hours old; a normal `uv run --frozen ufe-docs-mcp sync` can refresh it. An already raw-mode cache retains raw mode and may take much longer. Coordinate that operation rather than forcing another crawl silently.

## Run the current plugin

The plugin/marketplace ID is `ufe3d-mcp` and the server is `UFE3D-MCP`. Confirm the installed Claude CLI's flags and actual namespaced tools before executing this POSIX-shell example from the repository root:

```bash
claude plugin eval . --scaffold --allow-real-servers --allow-tools "mcp__plugin_ufe3d-mcp_UFE3D-MCP__ufe_search_docs" "mcp__plugin_ufe3d-mcp_UFE3D-MCP__ufe_get_doc" "mcp__plugin_ufe3d-mcp_UFE3D-MCP__ufe_list_topics" "mcp__plugin_ufe3d-mcp_UFE3D-MCP__ufe_docs_status" --max-cost-usd 10
```

This invocation is configuration-derived, not a newly completed paid evaluation. If the installed client normalizes tool identifiers differently, use the observed exact names and its documented permission syntax; do not disable permission checks. Update the corresponding `used-docs-tool.md` observer definitions together with the exact grants so tool-use indicators measure the current connector rather than an obsolete namespace.

- `--scaffold` runs each case's script, which copies local cache files.
- `--allow-real-servers` starts the plugin's real server. Grants cover the four read tools and exclude explicit refresh. The recent-index check avoids a normally due automatic update, but read permissions alone do not disable the server's background refresher.
- Add supported model/run/case flags to bound the task. Results go to the gitignored `evals/results/` directory.

## Historical results

Sanitized publication copies live in [docs/eval-reports/](../docs/eval-reports/). The October 7, 2026 run scored 0.99 with the plugin and 0.29 without (mean Δ +0.70); see [the archived evaluation record](../docs/history/VERIFICATION.md#plugin-eval-claude-plugin-eval). This was a nine-case comparison with a baseline that had no web access, not a development-speed measurement or a comparison against browsing. The generated report does not identify the resolved answering model.

Archived records retain the configuration used in each run. Keep their answers, tool names, and scores intact. A changed skill or connector revision needs its own evaluation; updating observer definitions does not rerun, re-score, or rename saved reports.

## Preparing a report for publication

Generated reports may contain machine paths and execution metadata inside answers as well as headers. Keep original artifacts out of Git and prepare a reviewed publication copy:

- Remove personal emails, credentials, hostnames, absolute workspace/cache paths, exact execution times and billing details from visible and collapsed content. Inspect the HTML source.
- Replace only private values with explicit markers such as `[temporary evaluation workspace]`, disclosing the substitution. Retain answers, scores, judgments, prompts, and grader definitions otherwise.
- Retain the evaluation date, recorded client/model versions, identity limitations, case/run counts, configuration, and baseline restrictions. Do not infer a resolved model from an alias or relabel old tool names.

Publishing a sanitized report does not rerun it or establish compatibility with a later release. Record new checks separately with the version and scope actually exercised.
