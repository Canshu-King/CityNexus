"""ORD-0395 ruling three: the A/B reading, and the two cells that turned out not to be mine.

Written after the fact, because the first reading was wrong: my branch's suite run carried two reds the
baseline run did not, and I was about to call them my regression. Running those two cells alone, in a
tree that contains none of my commits, says the opposite -- so this file records both contexts for both
trees, which is the only shape that makes the claim checkable.

A run that produced no summary line is not a failure: it means nothing matched, which is the case for my
new cell in the baseline tree, where the file does not exist yet. That is named, not left as a "?".
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

LANE = Path("D:/moodle/_qoder_lane_heyuegong_20261009")
TREES = {
    "my_branch": Path("D:/moodle/_qoder_lane_heyuegong_20261009/wt"),
    "baseline_parent": Path("E:/hg_0395/wt_base"),
}
CELLS = (
    "tests/test_qoder_ord0479_dictionary_key_shape.py::test_H07_the_two_forbidden_shortcuts_were_not_taken",
    "tests/test_qoder_ord0495_gitshow_portable.py::test_G07_the_converted_cell_skips_in_an_export_and_asserts_in_a_repo",
    "tests/test_contract.py::test_the_served_only_statuses_are_registered_by_name_and_still_exact",
)
PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"

rows = ["ORD-0395 ruling three -- isolated runs of the contested cells, one tree per block."]

for label, tree in TREES.items():
    head = subprocess.run(["git", "-C", str(tree), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    rows.append(f"### {label} (HEAD {head})")
    for cell in CELLS:
        run = subprocess.run([PY, "-m", "pytest", cell, "-q", "--tb=line"], cwd=str(tree / "backend"),
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        summary = next((line for line in reversed(run.stdout.splitlines())
                        if "passed" in line or "failed" in line or "skipped" in line), "")
        if not summary:
            # No summary line means nothing ran: in the baseline tree this cell does not exist yet.
            # Printing "?" there would read as a silent failure, so the absence is named instead.
            summary = "NOT_PRESENT in this tree (the file or the cell does not exist, so nothing ran)"
        reason = next((line for line in run.stdout.splitlines() if "AssertionError" in line), "")
        rows.append(f"   {cell.split('::')[-1][:58]}")
        rows.append(f"      {summary.strip()}")
        if reason:
            rows.append(f"      {reason.strip()[:170]}")

rows.append("")
for name in ("suite_base_r3.txt", "suite_mine_r3.txt", "suite_mine_r3b.txt"):
    text = (LANE / name).read_text(encoding="utf-8", errors="replace")
    summary = next((line for line in reversed(text.splitlines()) if "passed" in line), "?")
    reds = sorted({line.strip() for line in text.splitlines() if line.startswith("FAILED")})
    rows.append(f"{name}: {summary.strip()} red_arms={len(reds)}")

out = LANE / "AB_READINGS_R3.txt"
text = "\n".join(rows) + "\n"
out.write_text(text, encoding="utf-8")
print(text)
