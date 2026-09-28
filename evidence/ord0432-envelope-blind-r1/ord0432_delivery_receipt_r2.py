"""ORD-0432 delivery artifact: every number in the ledger block is recomputed here.

Nothing in the output is typed: the suite counts are parsed out of the pytest logs that produced
them, the frontend counts come from running `tsc --listFiles` and `vite build` again against the
candidate tree, and the ref coordinate comes from a live `git ls-remote`. A hand-written summary of
these would be a claim, not a measurement.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

LANE = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0212")
WT = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\wt")
BUILD = Path(r"D:\moodle\_qoder_ai_ord0432_20260929\build\frontend")
PY = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
REMOTE = "ssh://git@ssh.github.com:443/Canshu-King/CityNexus.git"
REF = "refs/heads/review/Q-ord0432-robust-blind-to-major-1"
TASKS = Path.home() / "AppData/Local/Temp/qoder-cli/D--moodle"
OUT = LANE / "ORD0432_DELIVERY.json"

RUNS = {
    "candidate_complete": ("b6et7zz0t", TASKS / "804cc791-0ba0-493a-90cd-6dea5b2d380f/tasks/b6et7zz0t.output"),
    "candidate_my_file_ignored": ("b6xmlqpab", TASKS / "804cc791-0ba0-493a-90cd-6dea5b2d380f/tasks/b6xmlqpab.output"),
    "baseline_snap_complete": ("b2pysq7wv", TASKS / "804cc791-0ba0-493a-90cd-6dea5b2d380f/tasks/b2pysq7wv.output"),
    "baseline_snap_rerun": ("b2fhms9d9", TASKS / "25f8a9c7-4549-43ad-835e-b04e92c7411f/tasks/b2fhms9d9.output"),
    "candidate_second_sample": ("b1bzgzbzx", TASKS / "25f8a9c7-4549-43ad-835e-b04e92c7411f/tasks/b1bzgzbzx.output"),
}


def run(cmd, cwd=None, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def suite(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    summary = re.search(r"(\d+) failed.*?(\d+) passed.*?(\d+) skipped.*?(\d+) xfailed.*?in ([\d.]+)s",
                        text, re.S)
    reds = sorted(set(re.findall(r"^FAILED (\S+)", text, re.M)))
    return {"source_log": str(path), "parsed": bool(summary),
            "failed": int(summary.group(1)) if summary else None,
            "passed": int(summary.group(2)) if summary else None,
            "skipped": int(summary.group(3)) if summary else None,
            "xfailed": int(summary.group(4)) if summary else None,
            "seconds": float(summary.group(5)) if summary else None,
            "total_from_counts": sum(int(summary.group(i)) for i in range(1, 5)) if summary else None,
            "red_nodeids": reds}


def main() -> int:
    out: dict = {"interpreter": str(PY),
                 "interpreter_version": run([str(PY), "-V"]).stdout.strip()}
    out["ref_readback"] = {"ref": REF,
                           "sha": (run(["git", "ls-remote", REMOTE, REF]).stdout or "").split()[0]
                           if run(["git", "ls-remote", REMOTE, REF]).stdout else None}
    log = run(["git", "-C", str(WT), "log", "-2", "--format=%H %ad %s", "--date=iso"])
    out["candidate_commits"] = log.stdout.strip().splitlines()

    out["suite"] = {name: suite(path) for name, (_, path) in RUNS.items()}
    base = set(out["suite"]["baseline_snap_complete"]["red_nodeids"])
    cand = set(out["suite"]["candidate_complete"]["red_nodeids"])
    out["regression_check"] = {
        "candidate_only_nodeids": sorted(cand - base),
        "baseline_only_nodeids": sorted(base - cand),
        "candidate_is_subset_of_baseline": cand <= base,
        "my_new_file_nodeids": sorted(n for n in cand | base if "test_dsh_twin_disruption" in n),
    }
    union = set(base)
    for key in ("baseline_snap_rerun",):
        union |= set(out["suite"][key]["red_nodeids"])
    guardian = "tests/test_sol_guardian_projection.py"
    out["guardian_file_attribution"] = {
        "red_member_by_run": {name: sorted(n.split("::")[-1] for n in v["red_nodeids"]
                                           if n.startswith(guardian))
                              for name, v in out["suite"].items()},
        "candidate_only_against_baseline_union": sorted(
            (cand | set(out["suite"]["candidate_second_sample"]["red_nodeids"])) - union),
        "candidate_runs_whose_reds_fit_the_baseline_first_run": sorted(
            name for name, value in out["suite"].items()
            if name.startswith("candidate") and value["red_nodeids"] and set(value["red_nodeids"]) <= base),
        "same_file_red_on_unmodified_tree": bool(
            [n for n in out["suite"]["baseline_snap_rerun"]["red_nodeids"]
             if n.startswith(guardian)]),
    }

    tsc = run([str(BUILD / "node_modules/.bin/tsc.cmd"), "-p", "tsconfig.check.json",
               "--noEmit", "--listFiles"], cwd=BUILD)
    listed = [line for line in (tsc.stdout or "").splitlines() if line.strip()]
    out["frontend_typecheck"] = {
        "exit": tsc.returncode, "listFiles_lines": len(listed),
        "changed_files_seen": sorted(f for f in ("LiveRecovery.tsx", "displayVocabulary.ts")
                                     if any(f in line for line in listed))}

    dist = BUILD / "_dist_ord0432"
    hits = {}
    for needle in ("需要复核", "Major disruption open", "有重大变动没处理", "Server summary: review needed"):
        hits[needle] = sorted(p.name for p in (dist / "assets").glob("*.js")
                              if needle in p.read_text(encoding="utf-8", errors="replace"))
    out["bundle_contains_new_words"] = hits

    out["product_files_in_candidate"] = run(
        ["git", "-C", str(WT), "diff", "--name-only", "69b7cde497f101109ae67e038010dfed8f9accbf",
         "HEAD"]).stdout.strip().splitlines()
    out["scripts_parse"] = {p.name: bool(ast.parse(p.read_text(encoding="utf-8")))
                            for p in LANE.glob("ord0432_*.py")}

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"ref": out["ref_readback"], "regression_check": out["regression_check"],
                      "typecheck": out["frontend_typecheck"],
                      "suite_totals": {k: {kk: v[kk] for kk in ("failed", "passed", "total_from_counts", "parsed")}
                                       for k, v in out["suite"].items()}},
                     ensure_ascii=False, indent=1)[:2200])
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
