#!/usr/bin/env python
"""ORD-0557 lane gates for PlanWithAiSheet (提案工): the full typecheck ORD-0560 recognises, the
narrow one, the production build, and the shared dictionary parity ruler.

Each leg keeps its own exit code plus the raw tail, so a red leg cannot read as a silent green one.
`--control` re-runs the same legs on the base generation (CNX_LANE_BASE) by pointing the ruler at a
second copy of LocaleContext.tsx -- the parity ruler and the typecheck both read the tree, so the
control is done by swapping that one file in and restoring it, and the restore is verified.

    CNX_LANE_ROOT=D:/moodle/_qoder_tiaanianggong_0555 python run_gates_0557_r1.py
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.environ.get("CNX_LANE_ROOT") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.environ.get("CNX_LANE_BASE", "996f1b7588580a14fbbdec5301a6e4a7b70c93e4")
FE = os.path.join(ROOT, "frontend")
OUTDIR = os.path.join(ROOT, "review", "tiaanianggong-0557")
OUT = os.path.join(OUTDIR, "gates_readout_r1.txt")
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
DIST = os.path.join(ROOT, "..", "_qoder_tiaanianggong_0557_dist")

LEGS = [
    ("typecheck_full", ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.typecheck.json", "--noEmit"]),
    ("typecheck_narrow", ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.check.json", "--noEmit"]),
    ("build", ["node", "node_modules/vite/bin/vite.js", "build", "--outDir", DIST, "--emptyOutDir"]),
]


def run(name, cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    blob = (p.stdout or "") + (p.stderr or "")
    tail = [ln for ln in blob.splitlines() if ln.strip()][-16:]
    return "=== leg %s | cwd %s\n$ %s\nexit_code=%s\n%s\n" % (
        name, str(cwd).replace("\\", "/"), " ".join(cmd), p.returncode, "\n".join(tail) if tail else "(no output)")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.makedirs(OUTDIR, exist_ok=True)
    chunks = ["ORD-0557 PlanWithAiSheet (提案工) gates, branch generation", "lane root %s" % ROOT.replace("\\", "/"), ""]

    for name, cmd in LEGS:
        chunks.append(run(name, cmd, FE))
    chunks.append(run("i18n_parity", ["python", os.path.join("frontend", "scripts", "i18n_detail2_parity_r1.py")], ROOT))
    chunks.append(run("lane_gate_rows", ["python", os.path.join(ROOT, "..", "_qoder_tiaanianggong_0555_tools", "i18n_0557_plan_with_ai_r1.py"), "--rows"], ROOT))
    chunks.append(run("lane_gate_verify", ["python", os.path.join(ROOT, "..", "_qoder_tiaanianggong_0555_tools", "i18n_0557_plan_with_ai_r1.py"), "--verify"], ROOT))

    # control: same parity ruler on the base generation's dictionary
    before = open(os.path.join(ROOT, DICT_REL), "rb").read()
    subprocess.run(["git", "-C", ROOT, "checkout", BASE, "--", DICT_REL], check=True)
    chunks.append("=== control: parity ruler on base %s" % BASE)
    chunks.append(run("i18n_parity_base", ["python", os.path.join("frontend", "scripts", "i18n_detail2_parity_r1.py")], ROOT))
    subprocess.run(["git", "-C", ROOT, "checkout", "HEAD", "--", DICT_REL], check=True)
    after = open(os.path.join(ROOT, DICT_REL), "rb").read()
    chunks.append("restore_identical=%s" % (before == after))
    st = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"], capture_output=True, text=True)
    chunks.append("git_status_after_restore=%r" % st.stdout)

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(chunks))
    print("wrote %s" % OUT.replace("\\", "/"))
    for ln in "\n".join(chunks).splitlines():
        if ln.startswith(("=== ", "exit_code=", "restore_identical=", "git_status_after_restore=")):
            print(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
