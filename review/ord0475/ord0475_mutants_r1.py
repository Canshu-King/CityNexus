"""ORD-0475: put each of V1's two key arms through a real product mutation and keep the reading.

The in-file counter-example (test_v7) proves the arithmetic; this proves the shipped door is the one
being guarded.  One line is inserted after the share body is built, pytest names the arm that bites,
then main.py is restored from the index and read back byte-for-byte.
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
ANCHOR = '    body = journey_schema(journey).model_dump(mode="json")'

MUTANTS = {
    "M1_owner_key_vanishes": "    body.pop('city_code')  # ORD-0475 mutation probe",
    "M2_undocumented_key_appears": "    body['guest_note'] = 'x'  # ORD-0475 mutation probe",
}


def git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args], cwd=WT, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_pytest(name: str) -> str:
    proc = subprocess.run(
        [PY, "-m", "pytest", "tests/test_qoder_ord0466_version_share.py", "-q"],
        cwd=WT / "backend",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    report = OUT / f"ord0475_mutant_{name}.txt"
    report.write_text(f"exit={proc.returncode}\n" + proc.stdout, encoding="utf-8")
    lines = [
        line
        for line in proc.stdout.splitlines()
        if any(k in line for k in ("passed", "failed", "AssertionError", "assert not", "E  "))
    ]
    return f"exit={proc.returncode} " + " | ".join(lines[-6:])


pristine = sha(MAIN)
ast.parse(MAIN.read_text(encoding="utf-8"))
log = [f"main.py sha256 before = {pristine}", ""]

with open(MAIN, encoding="utf-8", newline="") as handle:
    text = handle.read()
NL = "\r\n" if "\r\n" in text else "\n"
log.append(f"newline as read = {NL!r}")
assert text.count(ANCHOR) == 1, f"anchor found {text.count(ANCHOR)} times, refusing"

for name, injected in MUTANTS.items():
    mutated = text.replace(ANCHOR, ANCHOR + NL + injected, 1)
    ast.parse(mutated)
    with open(MAIN, "w", encoding="utf-8", newline="") as handle:
        handle.write(mutated)
    log.append(f"### {name}: injected `{injected.strip()}`")
    log.append(f"    {run_pytest(name)}")
    git(["checkout", "--", "backend/app/main.py"])
    log.append(f"    restored sha256 == pristine: {sha(MAIN) == pristine}")
    log.append("")

log.append(f"git status --porcelain = {git(['status', '--porcelain'])!r}")
(OUT / "ord0475_mutants_r1.txt").write_text("\n".join(log), encoding="utf-8")
print("\n".join(log))
