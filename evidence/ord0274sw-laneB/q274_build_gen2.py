"""Build a byte-different NEXT generation that carries no behavioural change, then restore the source.

The measurement I need is three generations deep: a client already running the fixed code, facing a new
generation. `gen2` is the same source plus one comment line - the bundle hash changes, nothing else does.
The source is restored in a finally-block and verified byte-for-byte, and the restored state is printed
before anything else is reported, so a crash here cannot leave the lane dirty.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
SRC = LANE / "frontend" / "src" / "main.tsx"
ANCHOR = "const MAX_AUTOMATIC_CONVERGENCE_PER_SESSION = 2;"
COMMENT = "\n/* next-generation stand-in for ORD-0274 measurement; no behavioural change */\n"


def mod(name: str):
    html = (LANE / "frontend" / name / "index.html").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"/assets/index-[A-Za-z0-9_-]+\.js", html)
    return m.group(0) if m else None


def main() -> int:
    before = hashlib.sha256(SRC.read_bytes()).hexdigest()
    text = SRC.read_text(encoding="utf-8")
    if ANCHOR not in text:
        raise SystemExit("ABORT: anchor constant missing - refusing to edit blind")
    built = None
    try:
        SRC.write_text(text.replace(ANCHOR, ANCHOR + COMMENT, 1), encoding="utf-8", newline="\n")
        b = subprocess.run(["node", "node_modules/vite/bin/vite.js", "build", "--outDir", "dist_0274sw_gen2"],
                           cwd=str(LANE / "frontend"), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900)
        built = {"rc": b.returncode,
                 "tail": [l for l in (b.stdout or b.stderr).splitlines() if l.strip()][-3:]}
    finally:
        SRC.write_text(text, encoding="utf-8", newline="\n")
        after = hashlib.sha256(SRC.read_bytes()).hexdigest()
    print("restored byte-exact:", after == before)
    print("build:", built)
    print("gen1 module:", mod("dist_0274sw"), "| gen2 module:", mod("dist_0274sw_gen2"))
    print("generations distinguishable:", mod("dist_0274sw") != mod("dist_0274sw_gen2"))
    return 0 if after == before and built and built["rc"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
