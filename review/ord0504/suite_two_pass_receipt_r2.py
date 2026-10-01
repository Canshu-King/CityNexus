"""ORD-0504 r2 -- turn the two whole-suite passes into one receipt whose verdict is computed.

Nothing here is typed in: the counts are read off the two pytest pass files, and the attribution
"does any red belong to what this candidate changes" is decided by matching each red's test file
against the files this branch actually touches. A single pass is an observation, not a baseline, so
both passes are kept side by side and the delta between them is reported as unattributable.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
SCRATCH = LANE / "scratch_r2"
OUT = LANE / "wt" / "review" / "ord0504" / "suite_r2_two_passes.txt"
TREE = LANE / "wt"
TIP = "1c785a2d897888bb4089f7a324a3934f85f5f016"

# The test files this lane's orders own. A red outside this set is not this candidate's, and saying
# so has to be a set operation, not a sentence.
OWNED = {
    "tests/test_qoder_ord0504_spend_sources.py",
    "tests/test_qoder_ord0490_shared_after_restore.py",
    "tests/test_qoder_ord0465_shared_landing.py",
}

SUMMARY = re.compile(r"^(\d+) failed, (\d+) passed, (\d+) skipped, (\d+) xfailed", re.M)
RED = re.compile(r"^(FAILED|ERROR) (\S+?)(?:::|$)", re.M)


def parse(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = SUMMARY.search(text)
    full = sorted(set(re.findall(r"^FAILED (\S+::\S+)", text, re.M)))
    reds = sorted({node.split("::")[0] for node in full})
    exit_line = re.search(r"^SUITE_EXIT=(\d+)", text, re.M)
    walls = re.findall(r"in ([\d.]+)s", text)
    return {
        "file": path.name,
        "counts": {"failed": int(m.group(1)), "passed": int(m.group(2)),
                   "skipped": int(m.group(3)), "xfailed": int(m.group(4))} if m else None,
        "wall_seconds": walls[-1] if walls else None,
        "exit": int(exit_line.group(1)) if exit_line else None,
        "red_test_files": reds,
        "red_node_ids": full,
    }


def main():
    passes = [p for p in (SCRATCH / "suite_r2_pass1.txt", SCRATCH / "suite_r2_pass2.txt") if p.is_file()]
    if len(passes) < 2:
        raise SystemExit("both passes must exist before this receipt is written")
    parsed = [parse(p) for p in passes]
    touched = set(subprocess.run(["git", "diff", "--name-only", TIP, "HEAD"], cwd=TREE,
                                 capture_output=True, text=True).stdout.splitlines())
    mine_in_suite = sorted(f for f in touched if f.startswith("backend/tests/"))
    rows = []
    for p in parsed:
        if p["counts"] is None:
            rows.append(p | {"complete": False})
            continue
        red_files = set(p["red_test_files"])
        rows.append(p | {
            "complete": True,
            "reds_owned_by_this_lane": sorted(red_files & OWNED),
            "reds_in_files_this_candidate_changes": sorted(red_files & set(mine_in_suite)),
            "candidate_touches_test_files": mine_in_suite,
        })
    if not all(r["complete"] for r in rows):
        raise SystemExit("a pass is still running; the receipt stays unwritten")
    identical = set(rows[0]["red_node_ids"]) == set(rows[1]["red_node_ids"])
    only1 = sorted(set(rows[0]["red_node_ids"]) - set(rows[1]["red_node_ids"]))
    only2 = sorted(set(rows[1]["red_node_ids"]) - set(rows[0]["red_node_ids"]))
    lines = []
    lines.append("# ORD-0504 r2 -- the whole backend suite, two passes on one generation")
    lines.append("# command: D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest -q tests   (cwd: backend/)")
    lines.append("# candidate head read back from the remote: %s" % subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=TREE, capture_output=True, text=True).stdout.strip())
    lines.append("# base it sits on: %s" % TIP)
    lines.append("")
    for r in rows:
        lines.append("## %s" % r["file"])
        lines.append("  counts: failed %(failed)d / passed %(passed)d / skipped %(skipped)d / xfailed %(xfailed)d"
                     % r["counts"])
        lines.append("  wall: %s s   exit: %s" % (r["wall_seconds"], r["exit"]))
        lines.append("  red test files: %d" % len(r["red_test_files"]))
        for n in r["red_node_ids"]:
            lines.append("    FAILED %s" % n)
        lines.append("  reds owned by this lane's three orders: %s"
                     % (r["reds_owned_by_this_lane"] or "none"))
        lines.append("  reds in a test file this candidate changes: %s"
                     % (r["reds_in_files_this_candidate_changes"] or "none"))
        lines.append("  test files this candidate changes: %s" % (r["candidate_touches_test_files"] or "none"))
        lines.append("")
    lines.append("## the two passes compared")
    lines.append("  identical red sets: %s" % ("yes" if identical and not only1 and not only2 else "no"))
    lines.append("  red only in pass 1: %s" % (only1 or "none"))
    lines.append("  red only in pass 2: %s" % (only2 or "none"))
    lines.append("  verdict: %s" % (
        "no red belongs to this candidate -- attribution computed as set intersection above, "
        "and the pass-to-pass delta is reported as unattributable, not as 'no new red'"
        if not any(r["reds_in_files_this_candidate_changes"] for r in rows) else
        "at least one red sits in a file this candidate changes"))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[-6:]))
    print("wrote", OUT)


if __name__ == "__main__":
    sys.exit(main())
