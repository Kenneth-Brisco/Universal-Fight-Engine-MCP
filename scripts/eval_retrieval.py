"""Score UFE3D-MCP retrieval quality against a local documentation index.

Usage: python scripts/eval_retrieval.py [--cache DIR] [--cases FILE] [--json]

Runs every case in evals/retrieval/cases.json offline (no network) through the
same search and response decoration that the MCP tools use, and prints a
per-case pass/fail table and an overall score. The cache directory defaults to
the platform cache used by `ufe-docs-mcp sync`; it is copied to a temporary
directory first so the evaluation never modifies it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

from ufe_docs_mcp.index import search_docs
from ufe_docs_mcp.runtime import DocumentationRuntime

try:
    from ufe_docs_mcp.cli import default_cache_dir
except ImportError:  # pragma: no cover - older releases
    default_cache_dir = None

ROOT = Path(__file__).resolve().parents[1]
_HEADING_LINE = re.compile(r"^ {0,3}#{1,6}\s+\S")


def _heading_only(content: str) -> bool:
    return all(not line.strip() or _HEADING_LINE.match(line) for line in content.splitlines())


def _body_chars(content: str) -> int:
    return sum(len(line.strip()) for line in content.splitlines() if line.strip() and not _HEADING_LINE.match(line))


def _related_pages(result: dict) -> bool:
    return result["heading"].rsplit(" / ", 1)[-1].strip().casefold() == "related pages"


def _search(runtime: DocumentationRuntime, query: str, limit: int, max_chars: int = 12_000) -> dict:
    return runtime.decorate(search_docs(runtime.path, query, limit, max_chars))


def run_case(runtime: DocumentationRuntime, case: dict, defaults: dict) -> tuple[bool, list[str]]:
    limit = case.get("limit", defaults.get("limit", 3))
    response = _search(runtime, case["query"], limit, case.get("max_chars", 12_000))
    results = response["results"]
    ids = [result["doc_id"] for result in results]
    failures: list[str] = []
    if "expect_doc_in_top" in case and case["expect_doc_in_top"] not in ids:
        failures.append(f"{case['expect_doc_in_top']} not in top {limit}: {ids}")
    if "forbid_doc_in_top" in case and case["forbid_doc_in_top"] in ids:
        failures.append(f"{case['forbid_doc_in_top']} should not be in top {limit}: {ids}")
    if "expect_doc_prefix_in_top" in case and not any(i.startswith(case["expect_doc_prefix_in_top"]) for i in ids):
        failures.append(f"no {case['expect_doc_prefix_in_top']}* in top {limit}: {ids}")
    if "expect_heading_suffix" in case:
        wanted = case.get("expect_doc_in_top")
        if not any(r["doc_id"] == wanted and r["heading"].endswith(case["expect_heading_suffix"]) for r in results):
            failures.append(f"no '{case['expect_heading_suffix']}' chunk of {wanted}")
    if case.get("forbid_heading_only") and any(_heading_only(r["content"]) or _body_chars(r["content"]) < 40 for r in results):
        failures.append("heading-only chunk in results")
    if case.get("forbid_related_pages") and any(_related_pages(r) for r in results):
        failures.append("Related Pages chunk in results")
    if "max_chunks_per_doc" in case:
        worst = max((ids.count(i) for i in ids), default=0)
        if worst > case["max_chunks_per_doc"]:
            failures.append(f"{worst} chunks from one document")
    if case.get("expect_no_field_matches") and response.get("field_matches"):
        failures.append(f"unexpected field matches: {[m['field'] for m in response['field_matches']]}")
    if case.get("expect_any_result") and not results:
        failures.append("no results")
    if "expect_enum" in case:
        enums = {}
        for match in response.get("field_matches", []):
            if match.get("enum"):
                enums[match["enum"]["name"]] = [value["name"] for value in match["enum"]["values"]]
        for name, values in case["expect_enum"].items():
            if enums.get(name) != values:
                failures.append(f"enum {name} values {enums.get(name)} != {values}")
    if "expect_enum_labels" in case:
        labels = {match["enum"]["name"]: [value.get("label") for value in match["enum"]["values"]]
                  for match in response.get("field_matches", []) if match.get("enum")}
        for name, values in case["expect_enum_labels"].items():
            if labels.get(name) != values:
                failures.append(f"enum {name} labels {labels.get(name)} != {values}")
    if "expect_clarification_field" in case:
        notes = [note.get("field") for result in results for note in result.get("clarifications", [])]
        notes += [note.get("field") for match in response.get("field_matches", []) for note in match.get("clarifications", [])]
        if case["expect_clarification_field"] not in notes:
            failures.append(f"no clarification note for {case['expect_clarification_field']}")
    if "max_envelope_chars" in case:
        # Everything repeated on every call regardless of the passages:
        # snapshot, freshness, query echo and flags.
        envelope = len(json.dumps({k: v for k, v in response.items() if k != "results"}, ensure_ascii=False))
        if envelope > case["max_envelope_chars"]:
            failures.append(f"{envelope} envelope characters > {case['max_envelope_chars']}")
    if "expect_video_pointer" in case:
        videos = [video.get("youtube_id") for result in results for video in result.get("videos", [])]
        if case["expect_video_pointer"] not in videos:
            failures.append(f"no video pointer {case['expect_video_pointer']}")
    return not failures, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=default_cache_dir() if default_cache_dir else None)
    parser.add_argument("--cases", type=Path, default=ROOT / "evals/retrieval/cases.json")
    parser.add_argument("--json", action="store_true", help="print machine-readable results")
    args = parser.parse_args(argv)
    if args.cache is None or not (args.cache / "docs.sqlite3").is_file():
        parser.error("no documentation index found; run `ufe-docs-mcp sync` or pass --cache")
    suite = json.loads(args.cases.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as directory:
        cache = Path(directory)
        for name in ("docs.sqlite3", "refresh-state.json"):
            if (args.cache / name).is_file():
                shutil.copy2(args.cache / name, cache / name)
        runtime = DocumentationRuntime(cache, offline=True)
        outcomes = []
        for case in suite["cases"]:
            passed, failures = run_case(runtime, case, suite.get("defaults", {}))
            outcomes.append({"id": case["id"], "issue": case["issue"], "passed": passed, "failures": failures})
    by_issue: dict[str, list[bool]] = {}
    for outcome in outcomes:
        by_issue.setdefault(outcome["issue"], []).append(outcome["passed"])
    score = sum(outcome["passed"] for outcome in outcomes) / len(outcomes)
    summary = {
        "score": round(score, 2), "passed": sum(o["passed"] for o in outcomes), "total": len(outcomes),
        "by_issue": {issue: f"{sum(values)}/{len(values)}" for issue, values in by_issue.items()},
        "cases": outcomes,
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for outcome in outcomes:
            mark = "PASS" if outcome["passed"] else "FAIL"
            detail = "" if outcome["passed"] else "  " + "; ".join(outcome["failures"])
            print(f"{mark}  {outcome['issue']:<14} {outcome['id']}{detail}")
        print(f"\nScore {summary['score']:.2f} ({summary['passed']}/{summary['total']})  "
              + "  ".join(f"{k} {v}" for k, v in summary["by_issue"].items()))
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
