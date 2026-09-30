"""ORD-0475 r3: compare three suite passes by red set -- control at the tip, and two identical-byte
passes of this lane's branch -- and name every id that moves between the two identical passes."""

from pathlib import Path
import re

LANE = Path("D:/moodle/_qoder_n2b_ord0466_20260929")
RUNS = {
    "control_tip_dcb90ccc": "ord0475r3_suite_control.txt",
    "mine_pass_1": "ord0475r3_suite_mine.txt",
    "mine_pass_2_identical_bytes": "ord0475r3_suite_mine_pass2.txt",
}

out, reds = [], {}
for label, name in RUNS.items():
    text = (LANE / name).read_text(encoding="utf-8", errors="replace")
    ids = sorted(
        re.sub(r"^FAILED ", "", line.split(" - ")[0]).replace("tests/", "")
        for line in text.splitlines()
        if line.startswith("FAILED ")
    )
    summary = [line for line in text.splitlines() if re.search(r"\d+ (failed|passed)", line)]
    reds[label] = ids
    out.append(f"### {label}  <- {name}")
    out.append(f"    summary_line: {summary[-1].strip() if summary else 'NONE'}")
    out.append(f"    red_ids_counted_here = {len(ids)}")
    out.extend(f"      {item}" for item in ids)
    out.append("")

c = set(reds["control_tip_dcb90ccc"])
p1 = set(reds["mine_pass_1"])
p2 = set(reds["mine_pass_2_identical_bytes"])
stable = p1 & p2

out.append("=== derived ===")
for label in RUNS:
    out.append(
        f"v1_is_red_in_{label} = "
        + str(any("test_v1_journey" in item for item in reds[label]))
    )
out.append(f"control_minus_stable_mine = {sorted(c - stable)}")
out.append(f"stable_mine_minus_control = {sorted(stable - c)}")
out.append(f"ids_that_moved_between_two_identical_bytes_passes = {sorted(p1 ^ p2)}")
text = "\n".join(out)
(LANE / "ord0475r3_redsets_r2.txt").write_text(text, encoding="utf-8")
print(text[-1200:])
