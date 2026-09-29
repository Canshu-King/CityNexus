#!/usr/bin/env python3
"""ORD-0440 - the coordinates a ledger block may quote, read out of git rather than typed.

Blob ids come from ``git ls-tree`` on the delivered ref (whose head was read back with
``git ls-remote``), and every ``path:line`` is the line where the quoted text actually sits inside
that blob. Run it before writing the block and paste only what it prints.
"""

from __future__ import annotations

import subprocess
import sys

LANE = sys.argv[1] if len(sys.argv) > 1 else "."
REF = sys.argv[2] if len(sys.argv) > 2 else "review/N3-ord0440-destructive-action-survey-r1"

FILES = [
    "frontend/src/features/discovery/DestinationPreparationPanel.tsx",
    "frontend/src/features/discovery/PrepAbandonSurvey.tsx",
    "frontend/src/features/discovery/prepAbandonSurveyCopy.ts",
    "frontend/src/features/discovery/prepAbandonSurvey.css",
    "review/n3_0440_evidence_r1/census_r2.json",
    "review/n3_0440_evidence_r1/walk/walk_zh.json",
    "review/n3_0440_evidence_r1/walk/walk_en.json",
    "review/n3_0440_evidence_r1/mutations_r5.json",
    "review/n3_0440_evidence_r1/mutations_r7.json",
    "review/n3_0440_evidence_r1/label_parity_r1.json",
    "review/n3_0440_evidence_r1/survey_pair_r1.json",
    "review/n3_0440_evidence_r1/pair_check_after_r1.json",
    "review/n3_0440_evidence_r1/_shift_source_reading.txt",
    "review/ord0440/walk_r1.cjs",
    "review/ord0440/mutations_r1.py",
    "review/ord0440/ord0440_destructive_census_r1.py",
    "review/ord0440/survey_pair_check_r1.py",
]

NEEDLES = [
    ("review/n3_0440_evidence_r1/walk/walk_zh.json", '"fail": 0'),
    ("review/n3_0440_evidence_r1/walk/walk_en.json", '"fail": 0'),
    ("review/n3_0440_evidence_r1/walk/walk_zh.json", "centre"),
    ("review/n3_0440_evidence_r1/mutations_r5.json", "G2 the sheet mounted"),
    ("review/n3_0440_evidence_r1/mutations_r7.json", "G3 the exit keeps naming"),
    ("review/n3_0440_evidence_r1/mutations_r7.json", "G4 the exit is already usable"),
    ("review/n3_0440_evidence_r1/label_parity_r1.json", "zh_byte_equal_to_tip_literal"),
    ("review/n3_0440_evidence_r1/survey_pair_r1.json", "keys_found"),
    ("review/n3_0440_evidence_r1/pair_check_after_r1.json", "values_not_found"),
    ("review/n3_0440_evidence_r1/census_r2.json", "usable_as_a_step_without_making_another_lane_red"),
    ("frontend/src/features/discovery/prepAbandonSurveyCopy.ts", "prepSurvey.stopAction"),
    ("frontend/src/features/discovery/DestinationPreparationPanel.tsx", "openSurvey"),
]


def git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=LANE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} exit={proc.returncode} {proc.stderr[:200]}")
    return proc.stdout


def main() -> int:
    head = git("rev-parse", REF).strip()
    remote = git("-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin", f"refs/heads/{REF}")
    remote_head = remote.split()[0] if remote else "NO_REMOTE_READBACK"
    print(f"ref={REF}")
    print(f"local_head={head} ls_remote_head={remote_head}")
    for path in FILES:
        out = git("ls-tree", REF, "--", path)
        if not out.strip():
            print(f"MISSING_IN_REF {path}")
            continue
        blob = out.split()[2]
        size = len(git("cat-file", "blob", blob).encode("utf-8", errors="replace"))
        print(f"blob={blob} bytes={size} path={path}")
    for path, needle in NEEDLES:
        out = git("ls-tree", REF, "--", path)
        if not out.strip():
            print(f"NEEDLE_SKIPPED {needle!r}: {path} not in ref")
            continue
        blob = out.split()[2]
        text = git("cat-file", "blob", blob).replace("\r", "")
        found = [i for i, line in enumerate(text.splitlines(), 1) if needle in line]
        if not found:
            print(f"NEEDLE_NOT_FOUND {needle!r} in {path}")
        for line in found[:1]:
            print(f"anchor {path}:{line} for {needle!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
