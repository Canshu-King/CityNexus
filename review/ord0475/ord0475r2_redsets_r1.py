"""ORD-0475 r2: recompute every suite count and every red-set difference from the four run artifacts.

Nothing below is typed: each number is read out of the file named in front of it, so the block can
quote a verdict that is derived rather than asserted.
"""

from pathlib import Path
import re

LANE = Path("D:/moodle/_qoder_n2b_ord0466_20260929")
RUNS = {
    "control_tip_127ce7b0": "ord0475r2_control_tip_r1.txt",
    "mine_pass_1": "ord0475r2_suite_r1.txt",
    "mine_pass_2_identical_bytes": "ord0475r2_suite_r2.txt",
    "mine_pass_3_v7_deselected": "ord0475r2_suite_noV7.txt",
}

out = []
reds = {}
for label, name in RUNS.items():
    text = (LANE / name).read_text(encoding="utf-8", errors="replace")
    summary = [line for line in text.splitlines() if re.search(r"\d+ (failed|passed)", line)]
    ids = sorted(
        re.sub(r"^FAILED ", "", line.split(" - ")[0]).replace("tests/", "")
        for line in text.splitlines()
        if line.startswith("FAILED ")
    )
    reds[label] = ids
    out.append(f"### {label}  <- {name}")
    out.append(f"    summary_line: {summary[-1].strip() if summary else 'NONE'}")
    out.append(f"    red_ids_counted_here = {len(ids)}")
    out.extend(f"      {item}" for item in ids)
    out.append("")

mine_stable = set(reds["mine_pass_2_identical_bytes"])
control = set(reds["control_tip_127ce7b0"])
out.append("=== derived ===")
out.append(
    "v1_in_control_reds = "
    f"{any('test_v1_journey' in item for item in reds['control_tip_127ce7b0'])}"
)
for label in ("mine_pass_1", "mine_pass_2_identical_bytes", "mine_pass_3_v7_deselected"):
    out.append(
        f"v1_in_{label}_reds = {any('test_v1_journey' in item for item in reds[label])}"
    )
out.append(f"control_minus_mine_pass2 = {sorted(control - mine_stable)}")
out.append(f"mine_pass2_minus_control = {sorted(mine_stable - control)}")
moved = sorted(
    set(reds["mine_pass_1"]) ^ set(reds["mine_pass_2_identical_bytes"])
)
out.append(f"ids_that_moved_between_two_identical_bytes_passes = {moved}")
moved3 = sorted(set(reds["mine_pass_1"]) ^ set(reds["mine_pass_3_v7_deselected"]))
out.append(f"ids_that_moved_when_v7_was_deselected = {moved3}")
text = "\n".join(out)
(LANE / "wt" / "review" / "ord0475" / "ord0475r2_redsets_r1.txt").write_text(text, encoding="utf-8")
print(text[-1400:])
