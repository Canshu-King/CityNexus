"""ORD-0383 格三 readout: the unguarded 找回 write, measured before and after the predicate.

Run as:  python readout_r1.py <control-tree-with-the-unfixed-door> <candidate-tree>
It re-runs the four arms in each tree and writes READINGS_r1.json into the candidate tree.  The
control tree is expected to be a copy of the base tip with only this lane's test module added.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

BASE_TIP = "dccd13ad66ea35e9a6d7ca7a3d91a1ae9a579808"
TREE = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path("D:/moodle/_qoder_lane_ord0383_lock")
CTL = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("D:/moodle/_qoder_ord0383_lock_ctl")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
MODULE = "backend/tests/test_qoder_ord0383_undelete_write_lock.py"
ARMS = [
    "test_two_taps_fired_together_keep_the_invariant_and_one_audit_row_per_success",
    "test_the_two_taps_window_really_overlaps_instead_of_being_asserted",
    "test_a_tap_that_cannot_win_names_its_refusal_and_never_reaches_a_framework_five_hundred",
    "test_the_single_tap_path_is_unchanged_by_the_predicate",
]


def run(tree: pathlib.Path, targets: list[str]) -> dict[str, object]:
    env = {k: v for k, v in __import__("os").environ.items() if "PROXY" not in k.upper()}
    env["PYTHONPATH"] = f"{tree}:{tree / 'backend'}"
    out = subprocess.run(
        [PY, "-X", "utf8", "-m", "pytest", *targets, "-q", "-p", "no:cacheprovider", "-s"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(tree), env=env, check=False,
    )
    lines = out.stdout.splitlines()
    return {
        "exit_code": out.returncode,
        "verdict_line": next((l for l in reversed(lines) if " passed" in l or " failed" in l), ""),
        "readings": [l for l in lines if l.startswith("[ord0383]")],
        "failures": [l for l in lines if l.startswith("FAILED")],
    }


def main() -> None:
    per_arm = {"control_unfixed_base_tip": {}, "fixed": {}}
    for arm in ARMS:
        per_arm["control_unfixed_base_tip"][arm] = run(CTL / "base", [f"{MODULE}::{arm}"])
        per_arm["fixed"][arm] = run(TREE, [f"{MODULE}::{arm}"])

    suites = {}
    for name, log in (
        ("base", CTL / "SUITE__qoder_lane_ord0383_lock_base.log"),
        ("fixed", CTL / "SUITE__qoder_lane_ord0383_lock.log"),
    ):
        if not log.exists():
            suites[name] = "NOT_RUN_YET"
            continue
        text = log.read_text("utf-8", "replace")
        ids = sorted(
            line.replace("FAILED ", "").replace("ERROR ", "").split(" - ")[0].strip()
            for line in text.splitlines()
            if line.startswith(("FAILED", "ERROR"))
        )
        suites[name] = {
            "summary": next((l for l in reversed(text.splitlines()) if " passed" in l), ""),
            "red_nodeids": ids,
        }
    if isinstance(suites.get("base"), dict) and isinstance(suites.get("fixed"), dict):
        b, f = set(suites["base"]["red_nodeids"]), set(suites["fixed"]["red_nodeids"])
        suites["comparison"] = {"disappeared": sorted(b - f), "new_in_the_candidate": sorted(f - b)}

    collected = {}
    for name, path in (
        ("base", CTL / "CO__qoder_lane_ord0383_lock_base.txt"),
        ("fixed", CTL / "CO__qoder_lane_ord0383_lock.txt"),
    ):
        if path.exists():
            text = path.read_text("utf-8", "replace")
            collected[name] = next((l for l in reversed(text.splitlines()) if "collected" in l), "")

    payload = {
        "order": "ORD-0383 格三, ruled by the commander at 02:47 on 2026-09-29",
        "base_tip_read_by_this_lane": BASE_TIP,
        "defect_pinned_before_the_change": {
            "backend/app/main.py:3056": "journey.deleted_at = None  (an ORM assignment, no predicate)",
            "backend/app/main.py:3038": "Two taps at once are still unguarded, as in slice 1.",
        },
        "per_arm": per_arm,
        "whole_backend_suite": suites,
        "collect_only": collected,
        "store": "each pytest process declares its own temporary database in backend/tests/conftest.py; "
        "no path below names _preview.db or _live.db, and demo/reset is never called",
        "commands": {
            "arms": f"PYTHONPATH=<tree>:<tree>/backend {PY} -X utf8 -m pytest {MODULE} -q",
            "suite": f"PYTHONPATH=<tree>:<tree>/backend {PY} -X utf8 -m pytest backend/tests -q",
        },
    }
    out = TREE / "review/ord0383-undelete-lock/READINGS_r1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8", newline="\n")
    print(json.dumps(
        {
            "per_arm": {k: {a: v[a]["verdict_line"] for a in v} for k, v in per_arm.items()},
            "readings_fixed": per_arm["fixed"][ARMS[0]]["readings"],
            "comparison": suites.get("comparison"),
            "collect_only": collected,
        },
        ensure_ascii=False,
        indent=2,
    ))
    print(f"readout: {out} | sha256 {hashlib.sha256(out.read_bytes()).hexdigest()[:16]}", file=sys.stderr)


if __name__ == "__main__":
    main()
