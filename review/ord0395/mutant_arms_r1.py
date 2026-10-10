"""ORD-0395: prove the new door bites, by breaking the tree three ways and recording what turns red.

Each mutant is applied to the working copy, the two reset doors are run, and the file is restored
from HEAD in the same step -- the restored tree is read back before the next mutant is applied, so a
half-reverted run cannot be mistaken for a green one.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

WT = Path(r"D:/moodle/_qoder_lane_heyuegong_20261009/wt")
PY = Path(r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe")
MAIN = WT / "backend" / "app" / "main.py"
DOORS = (
    "tests/test_qoder_ord0395_reset_403_three_way_r1.py",
    "tests/test_qoder_ord0389_reset_token_gate.py",
)

MUTANTS = (
    (
        "M1 drop one code from DEMO_RESET_REFUSALS",
        '    "DEMO_MODE_REQUIRED": "the deployment does not run the demo stage switch",\n',
        "",
    ),
    (
        "M2 delete the decorator's whole 403 declaration",
        '    responses={403: {"description": demo_reset_refusal_description()}},\n',
        "",
    ),
    (
        "M3 widen the door: the token guard stops refusing",
        "    if not presented:\n        return (\n            \"RESET_TOKEN_REQUIRED\",",
        "    return None  # MUTANT\n    if not presented:\n        return (\n            \"RESET_TOKEN_REQUIRED\",",
    ),
)


def pytest_summary() -> tuple[str, list[str]]:
    run = subprocess.run(
        [str(PY), "-m", "pytest", *DOORS, "-q", "--tb=no", "-rf"],
        cwd=str(WT / "backend"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    lines = run.stdout.splitlines()
    summary = next((line for line in reversed(lines) if "passed" in line or "failed" in line), "?")
    failed = [line for line in lines if line.startswith("FAILED")]
    return summary, failed


def restore() -> str:
    subprocess.run(["git", "checkout", "--", "backend/app/main.py"], cwd=str(WT), check=True)
    return subprocess.run(
        ["git", "status", "--porcelain", "backend/app/main.py"],
        cwd=str(WT),
        capture_output=True,
        text=True,
    ).stdout.strip()


rows = ["ORD-0395 mutant runs: does the new door bite? Both reset doors are run per mutant."]
for name, old, new in MUTANTS:
    text = MAIN.read_text(encoding="utf-8")
    if old not in text:
        rows.append(f"### {name}: NOT APPLIED -- the anchor was not found; no reading taken")
        continue
    MAIN.write_text(text.replace(old, new, 1), encoding="utf-8")
    summary, failed = pytest_summary()
    clean = restore()
    rows.append(f"### {name}")
    rows.append(f"result: {summary}")
    rows.append(f"restored_clean={clean == ''} (git status said: {clean or 'clean'})")
    for line in failed:
        rows.append(f"  {line}")

text = "\n".join(rows) + "\n"
out = WT / "review" / "ord0395" / "MUTANT_ARMS_R1.txt"
out.write_text(text, encoding="utf-8")
print(text)
print(f"lines_in_output={len(text.splitlines())}")
sys.exit(0)
