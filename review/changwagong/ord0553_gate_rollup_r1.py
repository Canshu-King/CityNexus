#!/usr/bin/env python3
"""ORD-0553 / 长瓦工 -- the gate readings, computed from this lane's own run artefacts.

Reads the captured stdout of each gate rather than restating numbers: a gate reported green here must
be green in the file the command wrote.
"""

import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "review", "changwagong")


def read(path):
    return io.open(path, encoding="utf-8", errors="replace").read() if os.path.exists(path) else ""


def rc_of(name):
    return read(os.path.join(ROOT, name)).strip().replace("rc=", "")


def includes(name):
    """The `include` array as the config file really writes it, not as this script remembers it."""
    raw = read(os.path.join(ROOT, "frontend", name))
    m = re.search(r'"include"\s*:\s*\[(.*?)\]', raw, re.S)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else ["NOT_FOUND"]


def git(*args):
    p = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True)
    return p.stdout.decode("utf-8", "replace").strip(), p.returncode


def main():
    tip, _ = git("rev-parse", "HEAD")
    parent, _ = git("rev-parse", "HEAD^")
    numstat, _ = git("diff", "--numstat", "HEAD^", "HEAD")
    tc = read(os.path.join(ROOT, "tc_all.txt"))
    bd = read(os.path.join(ROOT, "build.txt"))
    lines = [
        "# ORD-0553 长瓦工 -- gate readings on the rebased candidate (tip=%s, parent=%s)" % (tip, parent),
        "typecheck_all_rc=%s" % rc_of("tc_all_rc.txt"),
        "build_rc=%s" % rc_of("build_rc.txt"),
        "typecheck_all_output_bytes=%d" % len(tc.encode("utf-8")),
        "typecheck_all_output_lines=%d" % len([l for l in tc.splitlines() if l.strip()]),
        "build_ok_marker=%s" % (re.search(r"built in [0-9.]+m?s", bd).group(0) if re.search(r"built in [0-9.]+m?s", bd) else "MISSING"),
        "typecheck_targeted_include=%s" % includes("tsconfig.check.json"),
        "typecheck_full_include=%s" % includes("tsconfig.typecheck.json"),
        "numstat HEAD^..HEAD:",
    ]
    for ln in numstat.splitlines():
        lines.append("  " + ln)
    lines.append("arm_after=%s" % read(os.path.join(OUT, "ord0553_arm_after.txt")).splitlines()[0])
    lines.append("arm_control=%s" % read(os.path.join(OUT, "ord0553_arm_before_control.txt")).splitlines()[0])
    text = "\n".join(lines) + "\n"
    sys.stdout.buffer.write(text.encode("utf-8"))
    with io.open(os.path.join(OUT, "ord0553_gates_r1.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
