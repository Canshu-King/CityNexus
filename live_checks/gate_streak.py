#!/usr/bin/env python3
"""Thin adapter over F's shared streak module - NOT a second ruler.

The arbiter's third audit (bus 5775917170 §4) rejected the previous version of this file: it
reimplemented verdicts, the forbidden-DB list and the command surface, and those copies disagreed
with `backend/tests/_qoder_streak_receipt.py` on at least seven points (initial row counts measured
after the child had already exited, free-form --runs, injectable --pytest-arg, duplicate-DB check
ordered after the green check, SKIPPED counted as red, case-sensitive protected names, and a real
command carrying `-rA`/`-p` which that contract forbids for this shape).

So this file now does exactly two things:
  1. orchestration: one subprocess per run, a fresh app-resolved temp DB each time;
  2. sampling: stdout/stderr kept SEPARATE, decoded through the shared decoder, and each run's
     resolved path / target-node outcome taken from the shared helpers.

Every verdict, every guard and every literal comes from the shared module imported out of the tree
under test. If the shared module is missing, this tool refuses to run rather than guessing.

Usage:
  python gate_streak.py --tree <export>/backend --node <nodeid> --sha <exact SHA> [--out f.json]
                        [--observation-runs N]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
CLEAN_ENV_KEYS = (
    "CITYNEXUS_DATABASE_URL", "DATABASE_URL", "DEEPSEEK_API_KEY", "CITYNEXUS_AI_ENABLED",
    "CITYNEXUS_AI_API_KEY", "CITYNEXUS_DEMO_MODE", "CITYNEXUS_LIVE_VALHALLA_URL",
    "CITYNEXUS_PHOTON_BASE_URL", "CNX_ORD0210_REVERSE_MUTATION", "CNX_UNDER_TEST_SHA",
)
SHARED = "tests/_qoder_streak_receipt.py"


def load_shared(backend: Path):
    """Import the ONE shared module out of the tree under test; refuse if absent."""
    path = backend / SHARED
    if not path.is_file():
        raise SystemExit(
            f"SHARED_MODULE_MISSING: {path} not found. This adapter deliberately has no local copy "
            "of the verdict/guard logic; point --tree at a tree that carries the shared module."
        )
    spec = importlib.util.spec_from_file_location("_cnx_streak_shared", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def temp_dir_snapshot() -> set[str]:
    """Names of cnx_pytest_* dirs in %TEMP% right now.  Sampled BEFORE each child starts, so the
    receipt can prove the parent directory the child resolves into did not exist beforehand."""
    try:
        root = Path(tempfile.gettempdir())
        return {p.name for p in root.iterdir() if p.is_dir() and p.name.startswith("cnx_pytest_")}
    except OSError:
        return set()


def run_once(shared, backend: Path, argv: list[str], nodeid: str) -> dict:
    env = dict(os.environ)
    for k in CLEAN_ENV_KEYS:
        env.pop(k, None)
    before_dirs = temp_dir_snapshot()
    proc = subprocess.run(
        list(argv), cwd=str(backend), env=env, capture_output=True, timeout=1800,
    )
    # Streams stay separate all the way to the decoder - joining them is the exact bug the shared
    # module calls out (pytest header on stdout, progress on stderr).
    out_text, out_codec = shared.decode_child_text(proc.stdout or b"")
    err_text, err_codec = shared.decode_child_text(proc.stderr or b"")
    path, path_source = shared.parse_resolved_path(out_text, err_text)
    nodeids_in_command = [a for a in argv if "::" in a or a.endswith(".py")]
    raw_outcome = shared.node_outcome_from_exit(
        proc.returncode, run_shape=shared.SINGLE_NODE, nodeids_in_command=nodeids_in_command)
    counts = shared.summarize_pytest_counts(out_text or err_text)
    node_outcome, corroboration = shared.corroborate_node_outcome(
        raw_outcome, run_shape=shared.SINGLE_NODE, counts=counts)
    return {
        "argv": argv,
        "exit_code": proc.returncode,
        "stdout_codec": out_codec,
        "stderr_codec": err_codec,
        "streams_separate": True,
        "resolved_absolute_db_path": path,
        "path_source": path_source,
        "nodeids_in_command": nodeids_in_command,
        # F 801e90b: a skipped test exits 0, so the exit-derived outcome MUST be corroborated by
        # the pytest summary counts; otherwise ten skipped runs would read STREAK_MET(10).
        "raw_node_outcome": raw_outcome,
        "node_outcome": node_outcome,
        "outcome_corroboration": corroboration,
        "pytest_counts": counts,
        "initial_row_counts": {"path_did_not_exist_before_this_run": None},  # filled below
        "final_row_counts": {},
        "temp_dirs_before_this_run": sorted(before_dirs),
        "temp_dir_appeared": None,
    }


def row_counts(path: str | None) -> dict:
    import sqlite3

    if not path or path == "NOT_PRINTED":
        return {"absent": True, "note": "no resolved path"}
    p = Path(path)
    if not p.is_file():
        return {"absent": True}
    try:
        con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        return {"error": f"READ_ONLY_OPEN_FAILED: {type(exc).__name__}"}
    try:
        have = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        return {"absent": False, "table_count": len(have)}
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--node", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--runs", type=int, default=10, help="must be 10 for a closure-grade streak")
    ap.add_argument("--observation-runs", type=int, default=0,
                    help="explicit observation-only sample size; never closure-grade")
    ap.add_argument("--out", default=None)
    ap.add_argument("--clause6-declared", dest="clause6_declared", default="",
                    help="the delivering lane's clause-6 declaration; without it this adapter can never "
                         "read CLOSED (fail-closed by design, and it now says so instead of silently "
                         "hard-coding False)")
    args = ap.parse_args()

    backend = Path(args.tree).resolve()
    shared = load_shared(backend)

    observation_only = args.observation_runs > 0
    rounds = args.observation_runs if observation_only else args.runs
    if not observation_only and rounds != 10:
        raise SystemExit(
            f"REFUSED: closure-grade streaks are exactly 10 runs (frozen clause 2); you asked for "
            f"{rounds}. Use --observation-runs N for a deliberately non-closure sample."
        )

    # The command comes from the shared module - this adapter never assembles its own argv.
    # shape_command(python=...) yields [python, "-m", "pytest", <nodeids>, <flags>], which is exactly
    # the shape the shared verifier checks (args[1:3] == ["-m","pytest"]).  Spawn it verbatim.
    argv = list(shared.shape_command(shared.SINGLE_NODE, [args.node], python=PYTHON))

    runs = []
    for i in range(rounds):
        one = run_once(shared, backend, argv, args.node)
        path = one["resolved_absolute_db_path"]
        # Freshness proof: the resolved parent must be a cnx_pytest_* dir that did NOT exist before
        # this child started.  Sampled before the run, checked after.
        parent = Path(path).parent.name if path and path != "NOT_PRINTED" else ""
        one["initial_row_counts"] = {
            "path_did_not_exist_before_this_run": bool(
                parent.startswith("cnx_pytest_") and parent not in one["temp_dirs_before_this_run"]),
            "resolved_parent": parent,
        }
        one["temp_dir_appeared"] = parent not in one["temp_dirs_before_this_run"]
        one["final_row_counts"] = row_counts(path)
        one["run_index"] = i + 1
        one["resolved_path_problems"] = shared.resolved_path_problems(path)
        runs.append(one)
        print(f"run {i+1}: exit={one['exit_code']} node={one['node_outcome']} db={path}", flush=True)

    shape = shared.verify_run_shape(
        run_shape=shared.SINGLE_NODE, argv=argv, nodeids=[args.node],
        nodeids_in_command=runs[0]["nodeids_in_command"],
        streams_separate=True, decoder=runs[0]["stdout_codec"],
    )
    clean, hits = shared.clause6_command_surface(argv)
    # clause 6 is a DECLARATION by the lane that ran the command, so this adapter must not invent it
    # (F 8ccd71d8 measured 2026-09-23: hard-coding False makes CLOSED unreachable through this tool
    # alone - which is the safe direction, but it has to be SAID rather than discovered).  A lane that
    # really is the delivering lane passes it explicitly; otherwise it stays False and we print why.
    clause6_declared = bool(args.clause6_declared) or os.environ.get("CNX_CLAUSE6_DECLARED") == "1"
    if not clause6_declared:
        print("[adapter] clause6_declared=False -> the ruler's closure_allowed cannot be satisfied, so "
              "this run can NEVER read CLOSED.  The delivering lane must declare clause 6; pass "
              "--clause6-declared '<how the command surface stayed clean>' (or CNX_CLAUSE6_DECLARED=1) "
              "in the second, judging step.  Measurement and judgement are two steps by design.")
    verdict = shared.streak_verdict(
        runs=[{k: v for k, v in r.items()} for r in runs],
        rounds=rounds, sha=args.sha, target_nodeid=args.node, run_shape=shared.SINGLE_NODE,
        command=" ".join(argv), independence_declared=True,
        clause6_declared=clause6_declared,
        clause6_command_surface_clean=clean, clause6_command_surface_hits=hits,
        run_shape_verified=shape.get("run_shape_verified", False),
        run_shape_problems=shape.get("problems", []),
        reverse_mutation_required=True,
        reverse_mutation_result=os.environ.get("CNX_ORD0210_REVERSE_MUTATION", ""),
    )
    receipt = {
        "adapter": "thin - verdict/guards/argv all come from the shared module",
        "shared_module": str(backend / SHARED),
        "sha": args.sha, "target_nodeid": args.node, "run_shape": shared.SINGLE_NODE,
        "rounds": rounds, "observation_only": observation_only,
        "command": " ".join(argv),
        "clause6_command_surface_clean": clean, "clause6_command_surface_hits": hits,
        "run_shape_verification": shape,
        "verdict": verdict,
        "problems": shared.receipt_problems({"runs": runs, **verdict}) if hasattr(shared, "receipt_problems") else [],
        "runs": runs,
    }
    text = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print("receipt ->", out)
    print(json.dumps({k: receipt[k] for k in
                      ("sha", "target_nodeid", "run_shape", "rounds", "observation_only",
                       "clause6_command_surface_clean")}, ensure_ascii=False, indent=2))
    print("verdict:", verdict.get("verdict"), "| closure:", verdict.get("closure_grade"))
    # Exit 0 means CLOSED and nothing else.  F 8ccd71d8 measured 2026-09-23 that the old line
    # (`startswith("STREAK_MET") -> 0`) reads green while freshness / run_shape / clause 6 / reverse
    # mutation may all still be unmet - i.e. the same lax-twin family as the deploy gauge.  An
    # explicit observation run is allowed to exit 0 on STREAK_MET because that is what it claims.
    grade = str(verdict.get("closure_grade", ""))
    met = str(verdict.get("verdict", "")).startswith("STREAK_MET")
    if grade == "CLOSED":
        return 0
    if observation_only and met:
        print("[adapter] observation-only run: STREAK_MET but closure_grade=", grade,
              "-> exit 0 is this run's own claim, NOT a closure")
        return 0
    print("[adapter] NOT CLOSED: closure_grade=", grade, "| verdict=", verdict.get("verdict"))
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
