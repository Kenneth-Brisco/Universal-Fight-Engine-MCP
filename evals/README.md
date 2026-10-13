# UFE3D plugin evals

Nine realistic UFE questions with checkable answers, run with `claude plugin eval` against the plugin and against a no-plugin baseline. The baseline has no web access, so the score difference (`Δ`) shows what the documentation tools add over the model's own knowledge.

Each case checks the exact UFE setting names with regex graders, the official manual URL that supports the answer, and correctness with a short judged rubric. Two cases target pages the publisher flags (`needs_verification`, `legacy_docs_differ`) and check that the warning reaches the user. One case asks about a feature the manual does not document and checks that the answer does not invent one. Whether the plugin's skill fired and whether a docs tool was called are reported as indicators, not scored.

## Before running

Eval runs use a temporary home directory. Each case's `scaffold.sh` copies your existing documentation index into it, so the plugin's server answers from that copy instead of downloading the manual for every run. The script stops if the index is missing or more than 20 hours old; refresh it first:

```bash
uv run --frozen ufe-docs-mcp sync
```

## Run

From the repository root:

```bash
claude plugin eval . --scaffold --allow-real-servers --allow-tools "mcp__plugin_ufe3d_UFE3D__ufe_search_docs" "mcp__plugin_ufe3d_UFE3D__ufe_get_doc" "mcp__plugin_ufe3d_UFE3D__ufe_list_topics" "mcp__plugin_ufe3d_UFE3D__ufe_docs_status" --max-cost-usd 10
```

- `--scaffold` runs each case's `scaffold.sh` (it only copies the local index).
- `--allow-real-servers` starts the plugin's real `UFE3D` server. The grants cover the four read tools and exclude explicit refresh. The scaffold's recent-index requirement avoids a normally due automatic check; read-tool permissions alone do not disable background refresh.
- Add `--model <model>`, `--runs <n>`, or `--case <glob>` to change what runs. Results and an HTML report are written to `evals/results/`, which is ignored by Git.

## Published results

Sanitized publication copies live in [docs/eval-reports/](../docs/eval-reports/). The October 7, 2026 run scored 0.99 with the plugin and 0.29 without (mean Δ +0.70); see [VERIFICATION.md](../VERIFICATION.md#plugin-eval-claude-plugin-eval). This was a nine-case comparison with a baseline that had no web access, not a measurement of development speed or a comparison against browsing. The generated report does not identify the resolved answering model.

## Preparing a report for publication

Generated reports can include machine paths and execution metadata inside model answers as well as the report header. Keep original run artifacts out of Git and prepare a reviewed publication copy:

- Remove personal emails, credentials, hostnames, absolute workspace/cache paths, exact execution times and billing details from both visible and collapsed content. Inspect the HTML source as well as the displayed report.
- When an answer includes a private value, replace just that value with an explicit marker such as `[temporary evaluation workspace]` and disclose the substitution in the report. Retain the rest of the answer, all scores, judgments, prompts and grader definitions.
- Retain the evaluation date, relevant client/model versions when actually recorded, model-identity limitations, case/run counts, configuration and baseline restrictions. Do not infer a resolved model from an alias.

Publishing a sanitized report does not rerun the evaluation or establish compatibility with a later release. Record any new tests separately with the version and scope actually checked.
