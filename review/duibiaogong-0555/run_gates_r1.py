"""Run the three gates for ORD-0555 lane duibiaogong and log every exit code truthfully.

Each command runs without a shell pipe so the recorded rc belongs to the command itself.
Usage: python review/duibiaogong-0555/run_gates_r1.py <stage-label>
"""

import datetime
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND = os.path.join(ROOT, "frontend")
OUT = os.path.join(ROOT, "review", "duibiaogong-0555", "gates_readout_%s.txt" % sys.argv[1] if len(sys.argv) > 1 else "")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
DIST = r"D:/moodle/_qoder_duibiaogong_0555_dist"


def run(label, cwd, argv, tail_lines=14):
    started = datetime.datetime.now().strftime("%H:%M:%S")
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = (proc.stdout or "") + (proc.stderr or "")
    lines = [ln for ln in body.splitlines() if ln.strip() != ""]
    out = [
        "### %s" % label,
        "cwd = %s" % cwd.replace("\\", "/"),
        "cmd = %s" % " ".join(argv),
        "started_local = %s" % started,
        "exit_code = %d" % proc.returncode,
        "nonempty_lines = %d" % len(lines),
        "tail:",
    ]
    out.extend("    " + ln for ln in lines[-tail_lines:])
    out.append("")
    return "\n".join(out)


def main():
    stage = sys.argv[1]
    tip = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"], capture_output=True, text=True).stdout.count("\n")
    parts = [
        "stage = %s" % stage,
        "tree_head = %s" % tip,
        "dirty_files = %d" % dirty,
        "python = %s" % PY,
        "",
        run("gate 1 i18n parity (shared ruler)", ROOT, [PY, os.path.join("frontend", "scripts", "i18n_detail2_parity_r1.py")]),
        run("gate 2 typecheck (frontend/package.json line 8 shape: tsconfig.typecheck.json)", FRONTEND,
            ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.typecheck.json", "--noEmit"]),
        run("gate 2b typecheck (old five-seed config, kept for continuity)", FRONTEND,
            ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.check.json", "--noEmit"]),
        run("gate 3 production build", FRONTEND, ["node", "node_modules/vite/bin/vite.js", "build", "--outDir", DIST, "--emptyOutDir"], 8),
    ]
    text = "\n".join(parts)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
