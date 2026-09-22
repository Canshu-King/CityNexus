#!/usr/bin/env python3
"""GATE_ACCEPTANCE_STREAK runner — the receipt shape the arbiter froze on 2026-09-22T15:58+08
(bus comment 5773071703), implemented so a lane cannot hand-wave it.

Frozen clauses this tool enforces mechanically (it refuses to sign what it did not observe):

  1. exact same product/test SHA        -> --sha is required and echoed into the receipt
  2. N CONSECUTIVE independent processes -> one subprocess per run, no reuse
  3. each process gets a fresh app-resolved temp DB
  4. receipt records run_index, exit_code, resolved_absolute_db_path,
     initial row counts, final row counts
  7. no two runs may silently share the same temp DB path -> checked, dupes are a hard fail
  8. one isolated GREEN is observation only                -> verdict needs N greens

Only SQLite targets are inspected for row counts; a non-SQLite resolved path is recorded as
`row_counts: NOT_APPLICABLE` rather than invented.  Nothing here deletes or mutates a database.

Usage (from the export tree's backend directory):

  python gate_streak.py --tree D:/moodle/_qoder_cmdr_ref_20260921/v_ord0211_pinned/backend \
      --node "tests/test_qoder_anywhere_gates.py::test_g3_five_concurrent_hydrations_of_one_county_converge_on_one_operation" \
      --sha 0a4cb23 --runs 10 --out ord0213/streak_g3.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
RECEIPT_PREFIX = "ORD-0211 test database: resolved="
COUNT_TABLES = ("journeys", "plan_versions", "travelers", "catalog_hydration_operations")
FORBIDDEN_BASENAMES = {"_live.db", "_preview.db"}
CLEAN_ENV_KEYS = (
    "CITYNEXUS_DATABASE_URL", "DATABASE_URL", "DEEPSEEK_API_KEY",
    "CITYNEXUS_AI_ENABLED", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_DEMO_MODE",
    "CITYNEXUS_LIVE_VALHALLA_URL", "CITYNEXUS_PHOTON_BASE_URL",
)


def db_path_from_receipt(line: str | None) -> Path | None:
    if not line or RECEIPT_PREFIX not in line:
        return None
    raw = line.split(RECEIPT_PREFIX, 1)[1].split("|", 1)[0].strip()
    return Path(raw)


def row_counts(path: Path | None) -> dict:
    """Read-only counts; an absent file means 'the app had not created it yet'."""
    if path is None:
        return {"error": "NO_RESOLVED_PATH_CAPTURED"}
    if not path.is_file():
        return {"absent": True}
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        return {"error": f"READ_ONLY_OPEN_FAILED: {type(exc).__name__}"}
    try:
        have = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        out: dict = {"absent": False, "table_count": len(have)}
        for t in COUNT_TABLES:
            out[t] = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] if t in have else "NO_TABLE"
        return out
    finally:
        con.close()


def run_once(backend: Path, node: str, extra: list[str]) -> dict:
    env = dict(os.environ)
    for k in CLEAN_ENV_KEYS:
        env.pop(k, None)
    proc = subprocess.run(
        [PYTHON, "-m", "pytest", node, "-p", "no:randomly", "--tb=line", "-rA", *extra],
        cwd=str(backend), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=1800,
    )
    blob = (proc.stdout or "") + (proc.stderr or "")
    receipt = next((ln.strip() for ln in blob.splitlines() if RECEIPT_PREFIX in ln), None)
    summary = next((ln.strip() for ln in reversed(blob.splitlines())
                    if "passed" in ln or "failed" in ln or "error" in ln), None)
    # Clause 10: read the TARGET NODE's own verdict, never the container command's exit.
    # pytest prints a per-node result line; `-rA` gives PASSED/FAILED/SKIPPED/ERROR by nodeid.
    node_name = node.split("::")[-1]
    node_line = next((ln for ln in blob.splitlines()
                      if node_name in ln and ln.split()[0] in
                      ("PASSED", "FAILED", "SKIPPED", "ERROR", "XFAIL", "XPASS")), None)
    if node_line:
        head = node_line.split()[0]
        node_outcome = {"PASSED": "GREEN", "FAILED": "RED", "SKIPPED": "SKIPPED",
                        "ERROR": "RED", "XFAIL": "XFAIL", "XPASS": "RED"}[head]
    else:
        node_outcome = "NOT_OBSERVED"  # no per-node report => never guess a verdict from the exit code
    return {"receipt_line": receipt, "db_path": db_path_from_receipt(receipt),
            "exit": proc.returncode, "summary": summary, "node_outcome": node_outcome,
            "tail": blob.strip()[-300:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True, help="exported backend dir (git archive export)")
    ap.add_argument("--node", required=True)
    ap.add_argument("--sha", required=True, help="exact commit under test (clause 1)")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--out", default=None)
    ap.add_argument("--pytest-arg", action="append", default=[], dest="extra")
    args = ap.parse_args()

    backend = Path(args.tree).resolve()
    if not (backend / "tests").is_dir():
        raise SystemExit(f"BAD_TREE: no tests/ under {backend} (point --tree at <export>/backend)")

    rows = []
    for i in range(args.runs):
        one = run_once(backend, args.node, list(args.extra))
        p = one.pop("db_path")
        before = row_counts(p)
        rows.append({
            "run_index": i + 1, "exit_code": one["exit"],
            "node_outcome": one["node_outcome"],
            "resolved_absolute_db_path": str(p) if p else None,
            "initial_row_counts": before, "one": one,
        })
        print(f"run {i+1}: exit={one['exit']} db={p} initial={before.get('journeys', before)}", flush=True)
        rows[-1]["final_row_counts"] = row_counts(p)

    paths = [r["resolved_absolute_db_path"] for r in rows]
    # Clause 10: green/red come from the TARGET NODE's verdict, never from the container exit.
    greens = sum(1 for r in rows if r["node_outcome"] == "GREEN")
    unobserved = [r["run_index"] for r in rows if r["node_outcome"] == "NOT_OBSERVED"]
    dupes = sorted({p for p in paths if p and paths.count(p) > 1})
    missing = [r["run_index"] for r in rows if not r["resolved_absolute_db_path"]]
    forbidden = [p for p in paths if p and Path(p).name in FORBIDDEN_BASENAMES]
    checks = {
        "all_runs_reported": len(rows) == args.runs,
        "all_green": greens == args.runs,
        "every_run_resolved_a_db": not missing,
        "no_two_runs_share_a_temp_db": not dupes,
        "no_forbidden_target": not forbidden,
        "every_run_has_a_target_verdict": not unobserved,
        "row_counts_recorded": all(
            isinstance(r["initial_row_counts"], dict) and isinstance(r["final_row_counts"], dict)
            for r in rows),
    }
    if forbidden:
        verdict = "ABORT_FORBIDDEN_TARGET"
    elif not checks["every_run_resolved_a_db"]:
        verdict = f"HARNESS_INVALID_no_resolved_db_path(run_index={missing})"
    elif not checks["every_run_has_a_target_verdict"]:
        verdict = f"HARNESS_INVALID_target_verdict_not_scoped(run_index={unobserved})"
    elif not checks["all_green"]:
        verdict = f"STREAK_NOT_MET({greens}/{args.runs}_green)"
    elif not checks["no_two_runs_share_a_temp_db"]:
        verdict = "STREAK_INVALID_shared_db_path"
    else:
        verdict = f"STREAK_MET({args.runs})"  # contract literal: STREAK_MET(<rounds>)
    receipt = {
        "clause_source": "bus 5773071703 GATE_ACCEPTANCE_STREAK (+ 5773588112 clauses 9/10)",
        "sha": args.sha, "target_nodeid": args.node, "run_shape": "single-node",
        "command": f"python -m pytest {args.node} --tb=line -rA -p no:randomly {' '.join(args.extra)}".strip(),
        "tree": str(backend), "node": args.node,
        "interpreter": PYTHON, "processes": args.runs,
        "green": greens, "red": args.runs - greens,
        "duplicate_db_paths": dupes, "runs_missing_db_path": missing,
        "runs_without_target_verdict": unobserved,
        "checks": checks, "verdict": verdict,
        "note": "clause 6 (no sleep/retry/concurrency reduction) cannot be proven by this tool; "
                "the delivering lane must state it and the diff must show it. "
                "A green streak alone is NOT closure of the root cause (arbiter's reverse clause): "
                "closure additionally needs reverse_mutation_required=true and a "
                "reverse_mutation_result in {KILLED, STREAK_BROKEN}.",
        "runs": [{k: v for k, v in r.items() if k != "one"} | {
            "summary": r["one"]["summary"], "receipt_line": r["one"]["receipt_line"]} for r in rows],
    }
    text = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print("receipt ->", out)
    print(text)
    return 0 if checks["all_green"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
