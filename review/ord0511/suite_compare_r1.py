"""ORD-0511: compare this branch's backend suite pass with the control pass at the live tip."""

from pathlib import Path
import re

LANE = Path("D:/moodle/_qoder_n2b_ord0511_20260930")
RUNS = {
    "control_tip_0dd06928": "suite_control_r1.txt",
    "mine_ord0511": "suite_mine_r2.txt",
}

out, reds = [], {}
for label, name in RUNS.items():
    path = LANE / name
    if not path.exists():
        out.append(f"### {label} <- {name}: FILE NOT PRESENT")
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    ids = sorted(
        re.sub(r"^FAILED ", "", line.split(" - ")[0]).replace("tests/", "")
        for line in text.splitlines()
        if line.startswith("FAILED ")
    )
    summary = [line for line in text.splitlines() if re.search(r"\d+ (failed|passed)", line)]
    collected = re.findall(r"\d+ (?:error[s]? during collection|tests? collected)", text)
    reds[label] = ids
    out.append(f"### {label} <- {name}")
    out.append(f"    summary_line: {summary[-1].strip() if summary else 'NONE'}")
    out.append(f"    collection_fact: {collected or 'none reported'}")
    out.append(f"    red_ids_counted_here = {len(ids)}")
    out.extend(f"      {item}" for item in ids)
    out.append("")

if len(reds) == 2:
    c = set(reds["control_tip_0dd06928"])
    m = set(reds["mine_ord0511"])
    out.append("=== derived ===")
    out.append(f"mine_minus_control = {sorted(m - c)}")
    out.append(f"control_minus_mine = {sorted(c - m)}")
    out.append(
        "stay_family_red_on_mine = "
        + str([item for item in reds["mine_ord0511"] if "stay" in item])
    )
text = "\n".join(out)
(LANE / "suite_compare_r1.txt").write_text(text, encoding="utf-8")
print(text[-1500:])
