"""Record what the tree sweep did, what it broke, and how the damage was repaired - measured, not narrated.

Every line here is read off the filesystem or off git at run time, because a self-report written from
memory is how a lane hides its own mistake.  The point of this file is the third section: an
instrumented account of a junction being followed.

    python live_checks/cff87c64_sweep_report_r1.py
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

TARGET = Path("D:/moodle/CityNexus/frontend/node_modules")
SOURCE = Path("D:/moodle/_qoder_cmdr_ref_20260921/frontend/node_modules")
OUT = Path("review/ord0505/tree_sweep_and_repair_r1.txt")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8",
                           errors="replace").stdout.strip()


def entries(path: Path) -> int:
    try:
        return len(list(path.iterdir()))
    except OSError:
        return -1


def is_reparse(path: Path) -> bool:
    st = path.stat(follow_symlinks=False)
    return bool(getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main() -> int:
    rows = ["cff87c64 tree sweep, the damage it caused, and the repair - all measured at run time", ""]

    rows.append("A. worktrees")
    mine = [l for l in git("worktree", "list").splitlines()
            if any(k in l for k in ("ord0471", "ord0505", "ord0521", "ord0437"))]
    rows.append(f"   remaining registered for this lane now: {len(mine)}")
    for line in mine:
        rows.append(f"     {line[:104]}")
    rows.append(f"   disk free now: {subprocess.run(['df','-h','/d'],capture_output=True,text=True).stdout.splitlines()[-1].split()[3]}")

    rows.append("")
    rows.append("B. the junction hazard, as measured")
    links_shell = subprocess.run(["find", "D:/moodle/_qoder_cmdr_ctl0349/frontend", "-maxdepth", "1", "-type", "l"],
                                 capture_output=True, text=True).stdout.strip()
    rows.append(f"   control: `find <tree>/frontend -maxdepth 1 -type l` on a tree that DOES hold the"
                f" junction returns {links_shell.count(chr(10)) + (1 if links_shell else 0)} line(s)"
                " - so `-type l` is not a reliable junction detector, which is what let the sweep through")
    dependents = 0
    shapes = set()
    for p in list(Path("D:/moodle").glob("_qoder_*/frontend/node_modules")) + \
             list(Path("D:/moodle").glob("_qoder_*/wt/frontend/node_modules")):
        try:
            if is_reparse(p):
                dependents += 1
                shapes.add(entries(p))
        except OSError:
            continue
    rows.append(f"   trees whose frontend/node_modules is a reparse point onto the shared target: {dependents}")
    rows.append(f"   entry counts seen through those reparse points: {sorted(shapes)}"
                " - non-zero means every one of them resolves to the repaired install")

    rows.append("")
    rows.append("C. the repair")
    lock = json.loads((SOURCE / ".package-lock.json").read_text(encoding="utf-8"))
    repo = json.loads(Path("D:/moodle/CityNexus/frontend/package-lock.json").read_text(encoding="utf-8"))
    root = dict(repo["packages"][""].get("dependencies") or {})
    root.update(repo["packages"][""]["devDependencies"])
    mismatches = [
        f"{name}: lock {repo['packages'].get('node_modules/' + name, {}).get('version')} "
        f"vs source {lock['packages'].get('node_modules/' + name, {}).get('version')}"
        for name in root
        if repo["packages"].get("node_modules/" + name, {}).get("version")
        != lock["packages"].get("node_modules/" + name, {}).get("version")
    ]
    rows.append(f"   target entries now: {entries(TARGET)}")
    rows.append(f"   source entries      : {entries(SOURCE)}")
    rows.append(f"   target .package-lock sha256[:16]: {sha16(TARGET / '.package-lock.json')}")
    rows.append(f"   source .package-lock sha256[:16]: {sha16(SOURCE / '.package-lock.json')}")
    rows.append(f"   root dependencies of the repo lock not matched by the source: {len(mismatches)}")
    for m in mismatches[:5]:
        rows.append(f"     {m}")
    for tool, cmd in (("typescript", "node node_modules/typescript/bin/tsc --version"),
                      ("openapi-typescript", "node node_modules/openapi-typescript/bin/cli.js --version")):
        out = subprocess.run(cmd.split(), cwd="D:/moodle/CityNexus/frontend", capture_output=True, text=True)
        rows.append(f"   {tool}: {(out.stdout or out.stderr).strip().splitlines()[-1] if (out.stdout or out.stderr).strip() else 'rc=' + str(out.returncode)}")
    rows.append("")
    rows.append("   the rule this leaves behind: a worktree holding a junction is unlinked with")
    rows.append("   `cmd /c rmdir <link>` BEFORE `git worktree remove`; `find -type l` is not a")
    rows.append("   detector for Windows junctions, and `git worktree remove` will write through one.")
    OUT.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
