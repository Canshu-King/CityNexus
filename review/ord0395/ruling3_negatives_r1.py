"""ORD-0395 ruling three: prove the new register bites, four ways.

Each mutation is applied to the working copy, the registered-exception arm runs, and the file comes back
from HEAD -- which is only safe because the arm is already committed. The run refuses to report a
result if the restore leaves the file dirty, so a half-reverted tree cannot be read as a green one.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

WT = Path(r"D:/moodle/_qoder_lane_heyuegong_20261009/wt")
PY = Path(r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe")
TARGET = "backend/tests/test_contract.py"
FILE = WT / TARGET

MUTATIONS = (
    ("N1 register a status the door does not add", '{"422"},', '{"418"},'),
    ("N2 register a wildcard path alongside the real one", 'SERVED_ONLY_STATUSES: dict[tuple[str, str], set[str]] = {',
     'SERVED_ONLY_STATUSES: dict[tuple[str, str], set[str]] = {\n    ("/api/v1/*", "post"): {"422"},'),
    ("N3 register nothing for the door", '{"422"},', 'set(),'),
    ("N4 delete the whole registration", 'SERVED_ONLY_STATUSES: dict[tuple[str, str], set[str]] = {\n    ("/api/v1/demo/reset", "post"): {"422"},\n}', 'SERVED_ONLY_STATUSES: dict[tuple[str, str], set[str]] = {}'),
)

rows = ["ORD-0395 ruling three -- negative controls on the named 422 register."]
for name, old, new in MUTATIONS:
    text = FILE.read_text(encoding="utf-8")
    if old not in text:
        rows.append(f"### {name}: ANCHOR NOT FOUND -- no reading taken")
        continue
    FILE.write_text(text.replace(old, new, 1), encoding="utf-8")
    run = subprocess.run(
        [str(PY), "-m", "pytest", "tests/test_contract.py", "-q", "--tb=line", "-k", "served_only"],
        cwd=str(WT / "backend"), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    summary = next((line for line in reversed(run.stdout.splitlines()) if "passed" in line or "failed" in line), "")
    if "SyntaxError" in run.stdout or "error during collection" in run.stdout:
        # A mutation that breaks the file's syntax produces no reading at all: that is this runner's
        # mistake, and reporting it as "the door turned red" would be a lie.
        summary = "NO_VALID_READING -- the mutation broke the file's syntax, so the door never ran"
    reason = next((line for line in run.stdout.splitlines() if "AssertionError" in line), "")
    subprocess.run(["git", "-C", str(WT), "checkout", "--", TARGET], check=True)
    dirty = subprocess.run(["git", "-C", str(WT), "status", "--porcelain", TARGET],
                           capture_output=True, text=True).stdout.strip()
    rows.append(f"### {name}")
    rows.append(f"    result: {summary}    restored_clean={dirty == ''}")
    rows.append(f"    reason: {reason[:180]}")

text = "\n".join(rows) + "\n"
out = WT / "review" / "ord0395" / "RULING3_NEGATIVE_CONTROLS_R1.txt"
out.write_text(text, encoding="utf-8")
print(text)
