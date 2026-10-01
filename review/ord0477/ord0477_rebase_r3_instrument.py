"""ORD-0477 r3: rebase the delivered candidate onto the current authority tip, file by file.

Why this script exists instead of a `git rebase`: the shared working tree is frozen and dirty and the
authority line is single-writer, so nothing here may check anything out. Everything is done on
extracted blobs inside this lane's own export of the tip, and every merge is a real three-way merge
whose result is reported per file -- clean or conflicted, with the conflict hunks counted. A conflicted
file is left with markers and named, so the resolution is a decision I make and record, not a hunch the
tool swallows.

The second reason: ORD-0477 r2 stored `backend/app/main.py` with CRLF, because that is how the tip held
it then. ORD-0532 converted the file to LF and pinned `*.py text eol=lf` in `.gitattributes`, so a
byte-for-byte replay of r2 would rewrite the whole file again -- which is the exact shape of the
RECUT_ABORT the landing sequencer reported. Base and our side are therefore normalised to the tip's own
line endings before merging, so the only differences left are differences of *content*.

usage: python ord0477_rebase_r3.py
"""
from __future__ import annotations

import pathlib
import subprocess

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
OUT = LANE / "ord0477cut_7862c6de"          # this lane's export of the current tip
SCRATCH = LANE / "run/ord0477_rebase_r3"
REPORT = LANE / "run/ord0477_rebase_r3.txt"

BASE = "be0ffee216c7d24e48652427d290da848a9195cf"   # the tip r2 was cut on
MINE = "7c67f88ce98d2f46f9590914d54c25f8d9bb7ca9"   # ORD-0477 r2, frozen
TIP = "7862c6de5565c02c20ec2dccaa9da18960603e06"    # ORD-0532 r2: the line is here now

MODIFIED = [
    "backend/app/main.py",
    "backend/app/schemas.py",
    "backend/tests/test_qoder_ord0402_recycle_bin.py",
    "contracts/openapi.yaml",
    "frontend/src/features/access/AccessPanel.tsx",
    "frontend/src/features/access/access.css",
    "frontend/src/features/access/accessCopy.ts",
    "frontend/src/features/access/accessDoors.ts",
    "frontend/src/features/access/accessVocabulary.ts",
    "frontend/src/generated/api.ts",
]
ADDED = [
    "backend/tests/test_qoder_ord0477_journey_sort.py",
    "frontend/e2e/qoder-ord0477-journey-list-sort.spec.ts",
]
# evidence this order shipped: r2's readings are history, they move over verbatim and nothing rewrites
# them (FREEZE_DOOR_REGENERATION_V1 says the same about baseline artifacts)
EVIDENCE = [
    "review/ord0402-readouts/make_list_door_baseline_artifact_r2.py",
    "review/ord0402-readouts/LIST_DOOR_BASELINE_r3.json",
]

lines = ["base=%s mine=%s tip=%s" % (BASE, MINE, TIP)]


def git(*args: str) -> bytes:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True)
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout


def tip_uses_lf(path: str) -> bool:
    data = git("show", "%s:%s" % (TIP, path))
    return b"\r\n" not in data


def write(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def merge(path: str) -> None:
    tip_bytes = git("show", "%s:%s" % (TIP, path))
    lf = tip_uses_lf(path)
    base_bytes = git("show", "%s:%s" % (BASE, path))
    mine_bytes = git("show", "%s:%s" % (MINE, path))
    if lf:
        base_bytes = base_bytes.replace(b"\r\n", b"\n")
        mine_bytes = mine_bytes.replace(b"\r\n", b"\n")
    scratch = SCRATCH / path
    write(scratch / "base", base_bytes)
    write(scratch / "tip", tip_bytes)
    write(scratch / "mine", mine_bytes)
    done = subprocess.run(
        ["git", "merge-file", "-L", "tip", "-L", "base", "-L", "ord0477-r2",
         str(scratch / "tip"), str(scratch / "base"), str(scratch / "mine")],
        capture_output=True,
    )
    merged = (scratch / "tip").read_bytes()
    conflicts = merged.count(b"<<<<<<<")
    lines.append(
        "%s endings=%s base_bytes=%d mine_bytes=%d tip_bytes=%d merged_bytes=%d conflict_hunks=%d rc=%d"
        % (path, "lf" if lf else "crlf", len(base_bytes), len(mine_bytes), len(tip_bytes), len(merged), conflicts, done.returncode)
    )
    write(OUT / path, merged)


def add(path: str) -> None:
    data = git("show", "%s:%s" % (MINE, path))
    exists = subprocess.run(["git", "-C", REPO, "cat-file", "-e", "%s:%s" % (TIP, path)], capture_output=True).returncode == 0
    write(OUT / path, data)
    lines.append("%s ADDED bytes=%d already_on_tip=%s" % (path, len(data), exists))


def evidence(path: str) -> None:
    data = git("show", "%s:%s" % (MINE, path))
    exists = (OUT / path).exists()
    write(OUT / path, data)
    lines.append("%s EVIDENCE bytes=%d was_in_tip_export=%s" % (path, len(data), exists))


for path in MODIFIED:
    merge(path)
for path in ADDED:
    add(path)
for path in EVIDENCE:
    evidence(path)

text = "\n".join(lines) + "\n"
REPORT.write_text(text, encoding="utf-8", newline="\n")
print(text)
print("wrote", REPORT)
