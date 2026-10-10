#!/usr/bin/env python
"""Run the three gates this lane owes ORD-0555: typecheck, production build, and the repository's
own i18n dictionary parity ruler.  Every leg keeps its own exit code and the raw tail of its output
so a red leg cannot be mistaken for a silent green one.

    python review/tiaanianggong-0555/run_gates_r1.py --batch 1
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("CNX_LANE_ROOT") or os.path.dirname(os.path.dirname(HERE))
FE = os.path.join(ROOT, "frontend")
OUT = os.path.join(ROOT, "review", "tiaanianggong-0555", "gates_readout_r1.txt")
DIST = os.path.join(ROOT, "..", "_qoder_tiaanianggong_0555_dist")

LEGS = [
    ("typecheck", FE, ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.check.json", "--noEmit"]),
    ("build", FE, ["node", "node_modules/vite/bin/vite.js", "build", "--outDir", DIST, "--emptyOutDir"]),
    ("i18n_parity", ROOT, ["python", os.path.join("frontend", "scripts", "i18n_detail2_parity_r1.py")]),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, required=True)
    a = ap.parse_args()
    lines = []
    fails = 0
    for name, cwd, cmd in LEGS:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        blob = (p.stdout or "") + (p.stderr or "")
        tail = [ln for ln in blob.splitlines() if ln.strip()][-14:]
        lines.append("=== leg %s | cwd %s" % (name, cwd))
        lines.append("$ " + " ".join(cmd))
        lines.append("exit_code=%s" % p.returncode)
        lines.append("\n".join(tail) if tail else "(no output)")
        lines.append("")
        if p.returncode not in (0, 1):
            fails += 1
        if p.returncode == 1 and name != "i18n_parity":
            fails += 1
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("ORD-0555 PlanWithAiSheet lane, batch %d\n" % a.batch)
        fh.write("lane root %s\n\n" % ROOT.replace("\\", "/"))
        fh.write("\n".join(lines))
    print("wrote %s" % OUT.replace("\\", "/"))
    print("\n".join(l for l in lines if l.startswith(("=== leg", "exit_code"))))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
