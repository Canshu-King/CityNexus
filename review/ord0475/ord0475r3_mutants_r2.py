"""ORD-0475 r3 / ORD-0481: three product-level mutations, one per key arm, each biting its own arm.

An anchor is named per mutant because the first take of M3 injected its line before the door had
written `plan_state`, so `dict.pop` raised and the readings came back as HTTP 500s -- a real red, but
not the arm being tested.  M3 now retracts the value after the door commits it, which is the shape
ORD-0481 asked about: the payload stops answering a key the contract still promises.
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

# Where the journey half of the share body is built, and where the guest's two keys are committed.
BUILD = '    body = journey_schema(journey).model_dump(mode="json")'
COMMIT = '    body["active_plan"] = guest_plan.model_dump(mode="json") if guest_plan is not None else None'

MUTANTS = [
    ("M1_owner_key_vanishes", BUILD, "    body.pop('city_code')  # ORD-0475 arm 1 probe"),
    ("M2_undocumented_key_appears", BUILD, "    body['guest_note'] = 'x'  # ORD-0475 arm 2 probe"),
    ("M3_promised_key_retracted", COMMIT, "    body.pop('plan_state')  # ORD-0481 arm 3 probe"),
]


def git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args], cwd=WT, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_pytest(name: str) -> tuple[str, list[str]]:
    proc = subprocess.run(
        [PY, "-m", "pytest", "tests/test_qoder_ord0466_version_share.py", "-q", "-p", "no:randomly"],
        cwd=WT / "backend",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    (OUT / f"ord0475r3_mutant_{name}.txt").write_text(
        f"exit={proc.returncode}\n" + proc.stdout, encoding="utf-8"
    )
    hit = [
        line.strip()
        for line in proc.stdout.splitlines()
        if "test_qoder_ord0466_version_share.py:" in line and "AssertionError" in line
    ]
    tail = [line for line in proc.stdout.splitlines() if "passed" in line or "failed" in line]
    return (tail[-1].strip() if tail else "NO SUMMARY"), hit


with open(MAIN, encoding="utf-8", newline="") as handle:
    text = handle.read()
NL = "\r\n" if "\r\n" in text else "\n"
pristine = sha(MAIN)
log = [
    f"main.py sha256 before = {pristine}",
    f"newline as read = {NL!r}",
    f"anchor BUILD count = {text.count(BUILD)}",
    f"anchor COMMIT count = {text.count(COMMIT)}",
    "",
]
assert text.count(BUILD) == 1 and text.count(COMMIT) == 1, "anchors not unique, refusing"

for name, anchor, injected in MUTANTS:
    mutated = text.replace(anchor, anchor + NL + injected, 1)
    ast.parse(mutated)
    with open(MAIN, "w", encoding="utf-8", newline="") as handle:
        handle.write(mutated)
    summary, hits = run_pytest(name)
    log.append(f"### {name}: injected after the anchor -> `{injected.strip()}`")
    log.append(f"    {summary}")
    log.extend(f"    red at {line}" for line in hits)
    git(["checkout", "--", "backend/app/main.py"])
    log.append(f"    main.py restored byte-identical: {sha(MAIN) == pristine}")
    log.append("")

log.append(f"git status --porcelain = {git(['status', '--porcelain'])!r}")
(OUT / "ord0475r3_mutants_r1.txt").write_text("\n".join(log), encoding="utf-8")
print("\n".join(log))
