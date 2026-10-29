"""Measure the broad frontend typecheck at the current tip and write the receipt the gate cites.

Runs the same command the new CI step will run, records the interpreter, the tip, the config, the
file count the config actually pulls in, and the exit code.  A clean receipt is what makes adding
the step a strengthening rather than a freshly planted red.
"""

import io
import json
import shutil
import subprocess
import sys

FRONTEND = r"D:\moodle\_cmdr_rescue_v3_1022\frontend"
TREE = r"D:\moodle\_cmdr_rescue_v3_1022"
RECEIPT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_gozero\bx172-broad-typecheck.txt"


def git(*args):
    return subprocess.run(
        ["git", "-C", TREE] + list(args), capture_output=True, text=True, errors="replace"
    ).stdout.strip()


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # npx is a .cmd shim on Windows, so a bare "npx" argv reaches neither shell and dies with
    # FileNotFoundError.  Resolve the shim to its absolute path once and reuse it.
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx is None:
        print("ABORT no npx on PATH; the command the CI step will run cannot be measured here")
        return 3
    listing = subprocess.run(
        [npx, "tsc", "-p", "tsconfig.typecheck.json", "--noEmit", "--listFilesOnly"],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
        errors="replace",
    )
    files = [line for line in listing.stdout.splitlines() if line.strip()]
    in_src = [line for line in files if "src/" in line.replace("\\", "/") or "\\src\\" in line]
    run = subprocess.run(
        [npx, "tsc", "-p", "tsconfig.typecheck.json", "--noEmit"],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=900,
    )
    node = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
    lines = [
        "BROAD FRONTEND TYPECHECK bx172",
        "TIP %s" % git("rev-parse", "HEAD"),
        "NODE %s" % node,
        "COMMAND %s tsc -p tsconfig.typecheck.json --noEmit" % npx,
        "EXIT_CODE %d" % run.returncode,
        "LISTED_FILES_TOTAL %d" % len(files),
        "LISTED_FILES_UNDER_SRC %d" % len(in_src),
        "CONFIG_INCLUDE %s" % json.dumps(
            json.loads(io.open(FRONTEND + r"\tsconfig.typecheck.json", encoding="utf-8").read())["include"]
        ),
        "NARROW_CONFIG_INCLUDE_COUNT 5 (frontend/tsconfig.check.json lists five files by name)",
        "OUTPUT_HEAD %r" % (run.stdout or run.stderr)[:200],
    ]
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0 if run.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
