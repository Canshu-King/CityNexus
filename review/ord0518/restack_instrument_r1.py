"""ORD-0518 -- re-stack this order's work onto the rebased ORD-0477 candidate, by three-way merge.

ORD-0518 was written against ORD-0477 r2, and r2 was just rebased to r3 on a tip 103 commits newer
(ORD-0503, ORD-0527 and ORD-0532 all landed in the same family). The uncommitted ORD-0518 files were
held in `ord0518_hold/` before any of that moved, so this order's change set is exactly the difference
between the r2 blobs and those held files -- and the way to carry that onto r3 is the same three-way
merge used for r3, not a copy. Copying would overwrite ORD-0503's member doors and ORD-0527's
reference-state work with the versions this lane last saw, which is the mistake that made r2
unlandable in the first place.

Three versions per file:
  base   = ORD-0477 r2 (7c67f88c)          -- what this order's diff was cut against
  ours   = the rebased r3 tree              -- the tip plus ORD-0477
  theirs = the held ORD-0518 file           -- r2 plus ORD-0518

Files r2 does not have are additions and are copied whole. A conflict is left with markers, counted
and named; nothing here guesses at a resolution.

usage: python ord0518_restack_r1.py
"""
from __future__ import annotations

import pathlib
import subprocess

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = LANE / "ord0477cut_7862c6de"
HOLD = LANE / "ord0518_hold"
SCRATCH = LANE / "run/ord0518_restack"
REPORT = LANE / "run/ord0518_restack_r1.txt"
R2 = "7c67f88ce98d2f46f9590914d54c25f8d9bb7ca9"

MERGED = [
    "frontend/src/features/access/accessDoors.ts",
    "frontend/src/features/access/accessVocabulary.ts",
    "frontend/src/features/access/accessCopy.ts",
    "frontend/src/features/access/AccessPanel.tsx",
    "frontend/src/features/access/access.css",
    "frontend/e2e/qoder-ord0477-journey-list-sort.spec.ts",
]
ADDED = [
    "frontend/src/features/access/journeyOrderVerdict.ts",
    "frontend/e2e/qoder-0518-trip-order-said-out-loud.spec.ts",
]

lines: list[str] = ["r2=%s tree=%s hold=%s" % (R2, TREE.name, HOLD.name)]


def git(*args: str) -> bytes:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True)
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout


def write(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def merge(relative: str) -> None:
    ours = (TREE / relative).read_bytes()
    base = git("show", "%s:%s" % (R2, relative)).replace(b"\r\n", b"\n")
    theirs = (HOLD / relative).read_bytes().replace(b"\r\n", b"\n")
    if ours != git("show", "%s:%s" % (R2, relative)):
        # r3 is not r2 for this file, which is exactly the case the merge exists for
        pass
    scratch = SCRATCH / relative
    write(scratch / "base", base)
    write(scratch / "ours", ours)
    write(scratch / "theirs", theirs)
    done = subprocess.run(
        ["git", "merge-file", "-L", "ord0477-r3", "-L", "ord0477-r2", "-L", "ord0518",
         str(scratch / "ours"), str(scratch / "base"), str(scratch / "theirs")],
        capture_output=True,
    )
    merged = (scratch / "ours").read_bytes()
    hunks = merged.count(b"<<<<<<<")
    write(TREE / relative, merged)
    lines.append("%s base=%d r3=%d ord0518=%d merged=%d conflict_hunks=%d rc=%d" % (
        relative, len(base), len(ours), len(theirs), len(merged), hunks, done.returncode))


def add(relative: str) -> None:
    data = (HOLD / relative).read_bytes()
    exists_in_r2 = subprocess.run(
        ["git", "-C", REPO, "cat-file", "-e", "%s:%s" % (R2, relative)], capture_output=True
    ).returncode == 0
    write(TREE / relative, data)
    lines.append("%s ADDED bytes=%d was_in_r2=%s" % (relative, len(data), exists_in_r2))


for relative in MERGED:
    merge(relative)
for relative in ADDED:
    add(relative)

# this order's measurement artifacts, kept out of `run/` so they ship with the candidate
held_review = HOLD / "review_ord0518"
copied = 0
for source in sorted(held_review.iterdir()):
    if source.is_file():
        write(TREE / "review/ord0518" / source.name, source.read_bytes())
        copied += 1
lines.append("review/ord0518 copied_files=%d" % copied)

text = "\n".join(lines) + "\n"
REPORT.write_text(text, encoding="utf-8", newline="\n")
print(text)
