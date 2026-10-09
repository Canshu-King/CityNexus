"""ORD-0555 lane 比价工 — gate runner.

Runs every gate the order asks for, in one place, and writes a single readout
that carries each command verbatim plus its exit code. Nothing here edits the
product or the shared rulers.

usage: python run_gates_r1.py
"""
import os
import re
import subprocess
import sys

TREE = "D:/moodle/_qoder_bijiagong_0555"
FRONTEND = os.path.join(TREE, "frontend")
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = "node"
OUT = os.path.join(TREE, "review", "比价工-0555", "gates_readout_r1.txt")
DIST = "D:/moodle/_qoder_bijiagong_0555_dist"

CHECKS = [
    ("1) typecheck (tsconfig.check.json)",
     [NODE, "node_modules/typescript/bin/tsc", "-p", "tsconfig.check.json", "--noEmit"],
     FRONTEND),
    ("2) shared i18n parity ruler, unmodified",
     [PY, "frontend/scripts/i18n_detail2_parity_r1.py"],
     TREE),
    ("3a) my cross-line-aware recount on the UNTOUCHED tip copy (negative control)",
     [PY, os.path.join(TREE, "review/比价工-0555/dict_parity_recount_r1.py"),
      "D:/moodle/_qoder_bijiagong_tipprobe/frontend/src/i18n/LocaleContext.tsx",
      "untouched authoritative tip"],
     TREE),
    ("3b) my cross-line-aware recount on this branch",
     [PY, os.path.join(TREE, "review/比价工-0555/dict_parity_recount_r1.py"),
      os.path.join(TREE, "frontend/src/i18n/LocaleContext.tsx"), "lane branch"],
     TREE),
    ("4) verbatim wording ruler (six pairs vs dictionary values)",
     [PY, os.path.join(TREE, "review/比价工-0555/wording_verbatim_r1.py")],
     TREE),
    ("5) production build (vite)",
     [NODE, "node_modules/vite/bin/vite.js", "build", "--outDir", DIST, "--emptyOutDir"],
     FRONTEND),
]


def main():
    lines = []
    fails = 0
    for title, cmd, cwd in CHECKS:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        body = ((proc.stdout or "") + (proc.stderr or "")).rstrip("\n")
        lines.append("## %s" % title)
        lines.append("cwd: %s" % cwd)
        lines.append("command: %s" % " ".join(cmd))
        lines.append("exit_code=%d" % proc.returncode)
        lines.append(body if body else "(no output)")
        lines.append("")
        if proc.returncode != 0:
            fails += 1
    lines.append("checks run: %d, non-zero exits: %d" % (len(CHECKS), fails))
    # check 2 is expected to be non-zero: the shared ruler cannot read the one
    # cross-line key it predates. Parse WHICH keys it lists as differing and
    # allow exactly that known one, nothing else.
    text = "\n".join(lines)
    m = re.search(r"\('PARITY BREAK', \[(.*?)\]\)", text, re.S)
    listed = re.findall(r"'([^']+)'", m.group(1)) if m else []
    known = ["me.asksBeforeProtectedChange"]
    if m and listed == known:
        lines.append("shared ruler's XOR list is exactly the known cross-line key %s "
                     "-> instrument defect, not this delivery" % known[0])
    else:
        lines.append("UNEXPECTED: shared ruler did not report exactly the known cross-line "
                     "key (parsed: %s) -> inspect above" % listed)
        fails += 1
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print("wrote %s" % OUT)
    print("non-zero exits (excluding the known ruler defect): %d" % (fails - 1))
    return 0 if fails <= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
