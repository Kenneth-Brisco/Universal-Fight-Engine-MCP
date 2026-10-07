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
- `--allow-real-servers` starts the plugin's real `UFE3D` server; the grants cover the four read tools only, so evals never trigger a documentation refresh.
- Add `--model <model>`, `--runs <n>`, or `--case <glob>` to change what runs. Results and an HTML report are written to `evals/results/`, which is ignored by Git.

## Published results

Saved reports live in [docs/eval-reports/](../docs/eval-reports/). The October 7, 2026 run scored 0.99 with the plugin and 0.29 without (mean Δ +0.70); see [VERIFICATION.md](../VERIFICATION.md#plugin-eval-claude-plugin-eval).
