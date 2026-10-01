"""CMDR 15:30 item 7: shed the worktrees this lane no longer needs, one proof at a time.

Ordered by risk, not by convenience:

1. the ORD-0471 tree is removed only AFTER its `frontend/node_modules` junction is unlinked, because
   `git worktree remove --force` follows junctions and would reach into another tree's files;
2. the ORD-0521 r1 tree holds one untracked file that is the raw record of a method error of mine (a
   `git archive` "base" that measured 38 reds where the real worktree measured 11), so it is moved
   aside first rather than deleted with the tree;
3. the ORD-0505 r4 tree is the abandoned re-cut: never pushed, superseded by r5, and its receipts are
   copied out before the forced removal so the record of an attempt survives;
4. the shared pristine base is dirty only in line endings, proven with --ignore-cr-at-eol before any
   removal.

Kept: the ORD-0505 r3 tree (named "keep" in the ruling) and the ORD-0505 r5 tree (the live candidate).
Never touched: `_qoder_r_ord0437` (a branch that is not this lane's) and the repository-wide stash.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MAIN = "D:/moodle/_qoder_ord0505r5_20261001/wt"
ARCHIVE = Path("D:/moodle/_qoder_scratch/superseded_receipts")


def git(*args: str, cwd: str = MAIN) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def show(label: str, result: subprocess.CompletedProcess) -> None:
    out = (result.stdout + result.stderr).strip().replace("\r\n", "\n")
    print(f"{label}: rc={result.returncode} {out[:160] or '(ok)'}")


def dirty_beyond_line_endings(tree: str) -> int:
    check = git("diff", "--ignore-cr-at-eol", "--numstat", cwd=tree)
    return len([l for l in check.stdout.splitlines() if l.strip()])


def junctions(tree: str) -> list[str]:
    scan = subprocess.run(["find", ".", "-maxdepth", "3", "-type", "l"], cwd=tree,
                          capture_output=True, text=True)
    return [l for l in scan.stdout.splitlines() if l.strip()]


def main() -> int:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    print("avail before:", git("status", "-sb").stdout.strip()[:1], end=" ")
    print(subprocess.run(["df", "-h", "/d"], capture_output=True, text=True).stdout.splitlines()[-1].split()[3])

    # 1. ORD-0471 tree: unlink the junction first, prove the target, then remove
    tree = "D:/moodle/_qoder_ord0471_20260930/wt"
    links = junctions(tree)
    print(f"{tree}: junctions={links}")
    for link in links:
        unlink = subprocess.run(["rm", str(Path(tree) / link.lstrip("./"))], capture_output=True, text=True)
        show(f"  unlink {link}", unlink)
    target = Path("D:/moodle/CityNexus/frontend/node_modules")
    print(f"  junction target still populated: {len(list(target.iterdir()))} entries")
    show("  remove 0471 tree", git("worktree", "remove", tree))

    # 2. ORD-0521 r1 tree: move the superseded base reading aside, then remove both r1 trees
    stale = Path("D:/moodle/_qoder_ord0521_20261001/wt/review/ord0521_suite_base_r2.txt")
    if stale.exists():
        moved = subprocess.run(["mv", str(stale), str(ARCHIVE / "ord0521_suite_base_r2.txt")],
                               capture_output=True, text=True)
        show("  archived the archive-base receipt", moved)
    show("  remove 0521 r1 tree", git("worktree", "remove", "D:/moodle/_qoder_ord0521_20261001/wt"))
    show("  remove 0521 r1 base", git("worktree", "remove", "D:/moodle/_qoder_ord0521_20261001/base"))

    # 3. ORD-0505 r2 tree (clean, its ref is published)
    show("  remove 0505 r2 tree", git("worktree", "remove", "D:/moodle/_qoder_ord0505r2_20261001/wt"))

    # 4. ORD-0505 r4 base (dirty in line endings only) and r4 tree (abandoned re-cut)
    base4 = "D:/moodle/_qoder_ord0505r4_20261001/base"
    print(f"  r4 base: dirty-beyond-line-endings files = {dirty_beyond_line_endings(base4)}")
    if dirty_beyond_line_endings(base4) == 0:
        show("  remove r4 base", git("worktree", "remove", "--force", base4))
    else:
        print("  r4 base has real changes - NOT removing it")

    tree4 = "D:/moodle/_qoder_ord0505r4_20261001/wt"
    kept = 0
    for src in sorted(Path(tree4, "review/ord0505").glob("*_r4.txt")):
        subprocess.run(["cp", str(src), str(ARCHIVE / src.name)], check=False)
        kept += 1
    print(f"  r4 tree: {kept} receipts copied out to {ARCHIVE}, junctions={junctions(tree4)}")
    show("  remove r4 tree", git("worktree", "remove", "--force", tree4))
    subprocess.run(["rmdir", "/d/moodle/_qoder_ord0505r4_20261001/wt"], capture_output=True)
    subprocess.run(["rmdir", "/d/moodle/_qoder_ord0505r4_20261001/base"], capture_output=True)
    subprocess.run(["rmdir", "/d/moodle/_qoder_ord0505r4_20261001"], capture_output=True)

    git("worktree", "prune")
    remaining = [l for l in git("worktree", "list").stdout.splitlines()
                 if any(k in l for k in ("ord0471", "ord0505", "ord0521", "ord0437"))]
    print("remaining this-lane trees:")
    for line in remaining:
        print("  " + line[:110])
    print("avail after:", subprocess.run(["df", "-h", "/d"], capture_output=True, text=True).stdout.splitlines()[-1].split()[3])
    return 0


if __name__ == "__main__":
    sys.exit(main())
