"""ORD-0475 r3: compare my branch's suite pass against the control pass at the tip, by red set."""

from pathlib import Path
import re

LANE = Path("D:/moodle/_qoder_n2b_ord0466_20260929")
RUNS = {
    "control_tip_dcb90ccc": "ord0475r3_suite_control.txt",
    "mine_r3": "ord0475r3_suite_mine.txt",
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
m = set(reds["mine_r3"])
out.append("=== derived ===")
for label in RUNS:
    out.append(
        f"v1_is_red_in_{label} = "
        + str(any("test_v1_journey" in item for item in reds[label]))
    )
out.append(f"control_minus_mine = {sorted(c - m)}")
out.append(f"mine_minus_control = {sorted(m - c)}")
text = "\n".join(out)
(LANE / "ord0475r3_redsets_r1.txt").write_text(text, encoding="utf-8")
print(text[-700:])
