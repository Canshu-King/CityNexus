#!/usr/bin/env python
"""A/B control for ORD-0557 (提案工): run the same three legs on the base generation's bytes of the
two files this lane touched, then restore this lane's committed bytes and prove the restore by blob
hash.  Exit codes come from subprocess directly -- a shell pipe would mask them.

    CNX_LANE_ROOT=D:/moodle/_qoder_tiaanianggong_0555 python run_control_0557_r1.py
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.environ.get("CNX_LANE_ROOT", "D:/moodle/_qoder_tiaanianggong_0555")
BASE = os.environ.get("CNX_LANE_BASE", "996f1b7588580a14fbbdec5301a6e4a7b70c93e4")
FE = os.path.join(ROOT, "frontend")
OUT = os.path.join(ROOT, "review", "tiaanianggong-0557", "control_readout_r1.txt")
FILES = ["frontend/src/i18n/LocaleContext.tsx", "frontend/src/features/planning/PlanWithAiSheet.tsx"]
LEGS = [
    ("typecheck_full", ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.typecheck.json", "--noEmit"]),
    ("typecheck_narrow", ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.check.json", "--noEmit"]),
    ("build", ["node", "node_modules/vite/bin/vite.js", "build", "--outDir",
               os.path.join(ROOT, "..", "_qoder_tiaanianggong_0557_ctl_dist"), "--emptyOutDir"]),
]


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def leg(cmd):
    p = subprocess.run(cmd, cwd=FE, capture_output=True, text=True, encoding="utf-8", errors="replace")
    blob = (p.stdout or "") + (p.stderr or "")
    keep = [ln for ln in blob.splitlines() if "error TS" in ln or "Rollup failed to resolve" in ln or "built in" in ln]
    return p.returncode, keep


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    lines = ["A/B control: the same three legs with this lane's two files reverted to base %s" % BASE,
             "exit codes are read from the process itself, not from a pipe", ""]
    rc = git("checkout", BASE, "--", *FILES)
    lines.append("checkout base rc=%d" % rc.returncode)
    for name, cmd in LEGS:
        code, keep = leg(cmd)
        lines.append("=== base leg %s" % name)
        lines.append("$ %s" % " ".join(cmd))
        lines.append("exit_code=%d" % code)
        lines.extend(keep[:6] or ["(no matching line)"])
        lines.append("")
    git("checkout", "HEAD", "--", *FILES)
    lines.append("=== restore proof (working tree blob vs committed blob)")
    same = True
    for f in FILES:
        wt = git("hash-object", f).stdout.strip()
        head = git("rev-parse", "HEAD:%s" % f).stdout.strip()
        same = same and wt == head and wt != ""
        lines.append("%s working=%s committed=%s equal=%s" % (f, wt, head, wt == head))
    st = git("status", "--porcelain").stdout.strip().replace("\n", " | ")
    lines.append("git_status_after_restore=%r" % st)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(l for l in lines if l.startswith(("=== base", "exit_code=", "frontend/", "git_status"))))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
