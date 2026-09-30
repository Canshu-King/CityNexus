"""ORD-0475 r3: re-produce the FIRST take of the M3 probe, kept under its own name.

The point of keeping it: a mutation probe can go red for a reason that has nothing to do with the arm
being tested.  Injecting `body.pop('plan_state')` right where the journey half of the share body is
built runs before the door ever writes that key, so `dict.pop` raises and the readings come back as
HTTP 500s on three arms at once.  Red is not the same thing as "this arm bit".
"""

from __future__ import annotations

import ast
import hashlib
import subprocess
from pathlib import Path

WT = Path("D:/moodle/_qoder_n2b_ord0466_20260929/wt")
MAIN = WT / "backend" / "app" / "main.py"
OUT = Path("D:/moodle/_qoder_n2b_ord0466_20260929")
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
BUILD = '    body = journey_schema(journey).model_dump(mode="json")'
INJECTED = "    body.pop('plan_state')  # ORD-0481 probe, WRONG anchor"


def git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args], cwd=WT, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


with open(MAIN, encoding="utf-8", newline="") as handle:
    text = handle.read()
NL = "\r\n" if "\r\n" in text else "\n"
pristine = sha(MAIN)
assert text.count(BUILD) == 1, "anchor not unique, refusing"

mutated = text.replace(BUILD, BUILD + NL + INJECTED, 1)
ast.parse(mutated)
with open(MAIN, "w", encoding="utf-8", newline="") as handle:
    handle.write(mutated)

proc = subprocess.run(
    [PY, "-m", "pytest", "tests/test_qoder_ord0466_version_share.py", "-q", "-p", "no:randomly"],
    cwd=WT / "backend",
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
git(["checkout", "--", "backend/app/main.py"])

lines = [
    f"exit={proc.returncode}",
    f"injected `{INJECTED.strip()}` immediately after `{BUILD.strip()}`",
    f"main.py restored byte-identical: {sha(MAIN) == pristine}",
    "",
]
for line in proc.stdout.splitlines():
    if (
        "AssertionError" in line
        or "E  " in line
        or "Status" in line
        or "status_code" in line
        or "passed" in line
        or "failed" in line
        or line.startswith("FAILED")
        or "Internal Server Error" in line
    ):
        lines.append(line.rstrip())
(OUT / "ord0475r3_mutant_M3badanchor.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines[:14]))
