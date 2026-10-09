"""ORD-0395: land the gate numbers so the delivery block cites a file instead of a typed figure.

Everything here is recomputed from the four run logs and from this worktree's files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

WT = Path(r"D:/moodle/_qoder_lane_heyuegong_20261009/wt")
SCRATCH = Path(r"E:/heyuegong_0395")
PYTHON = Path(r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe")
LOGS = ("fullsuite_base.txt", "fullsuite_base2.txt", "fullsuite_mine.txt", "fullsuite_mine2.txt")


def reds_of(name: str) -> set[str]:
    text = (SCRATCH / name).read_text(encoding="utf-8", errors="replace")
    return {line.strip() for line in text.splitlines() if line.startswith("FAILED")}


def summary_of(name: str) -> str:
    text = (SCRATCH / name).read_text(encoding="utf-8", errors="replace")
    return next((line for line in reversed(text.splitlines()) if "passed" in line), "?")


base, base2 = reds_of(LOGS[0]), reds_of(LOGS[1])
mine, mine2 = reds_of(LOGS[2]), reds_of(LOGS[3])

rows: list[str] = [
    "ORD-0395 gate numbers. Computed by review/ord0395/suite_counts_r1.py from four run logs:",
    "fullsuite_base.txt and fullsuite_base2.txt ran the tree at the tip I based on;",
    "fullsuite_mine.txt and fullsuite_mine2.txt ran this branch. Same interpreter, same venv, same ignore list.",
    "Both runs passed --ignore=tests/test_v18_hermes_r20_transport_reliability_probe.py, whose import of",
    "the `mcp` package fails in this venv (scripts/hermes_r4_contract_probe.py) on both sides alike.",
    "",
]
for name in LOGS:
    rows.append(f"{name}: {summary_of(name)}")
    rows.append(f"{name}: red_arms={len(reds_of(name))}")

rows += [
    "",
    f"baseline_run1_and_run2_red_sets_identical={base == base2}",
    f"this_branch_run1_extra_red_arms={sorted(mine - base)}",
    f"this_branch_run2_extra_red_arms={sorted(mine2 - base2)}",
    f"this_branch_run2_red_set_equals_baseline={mine2 == base2}",
    "",
]

main_text = (WT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
rows.append(
    "custom_responses_in_main_py_that_declare_a_body_schema="
    + str(main_text.count('"content"'))
)

census = (WT / "review" / "ord0395" / "E2E_ARM_CENSUS_R1.txt").read_text(encoding="utf-8").splitlines()
start = next(i for i, line in enumerate(census) if line.startswith("sites that present no token"))
rows.append("e2e_sites_without_the_token_recounted_from_the_census=" + str(len([row for row in census[start + 1:] if row.strip()])))

rows.append("")
rows.append("collect_only (the order's gate: collect first, report the count):")
for label, tree in (("this_branch", WT), ("baseline_tree", Path(r"E:/heyuegong_0395/wt_base"))):
    run = subprocess.run(
        [
            str(PYTHON), "-m", "pytest", "tests/", "--collect-only", "-q", "-p", "no:cacheprovider",
            "--continue-on-collection-errors",
        ],
        cwd=str(tree / "backend"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    line = next((row for row in reversed(run.stdout.splitlines()) if "tests collected" in row), "?")
    rows.append(f"collect_only_{label}: {line.strip()}")

text = "\n".join(rows) + "\n"
out = WT / "review" / "ord0395" / "SUITE_COUNTS_R1.txt"
out.write_text(text, encoding="utf-8")
print(text)
print(f"lines_in_output={len(text.splitlines())}")
