"""ORD-0417 lane: build the trimmed witnesses for the r7 gate re-run.

Three files, each assembled from a run log rather than retyped:
  GATE_R7_ARMS_R25.json          -- per-arm name + status, joined against the `--list` denominator;
  GATE_R7_LIST_ARMS_R25.txt      -- that denominator itself, so the count cannot be argued later;
  GATE_R7_RED_414EN_RUNS_R1.txt  -- the arm's result lines from four runs (first pass, quiet re-run,
                                    control with my cell removed, probe copy), plus the A5 text.
The point of putting all four runs in one file is that the red is only meaningful next to the control:
same arm, same tree, cell deleted, identical `lost` -- so the sentence is not what cost the control.
"""
import io
import json
import re
import sys

BASE = r"D:/moodle/_qoder_b_ord0417_20260928/evidence"
G = f"{BASE}/gate"
OUT = f"{BASE}/gate_pack_r7"

import os

os.makedirs(OUT, exist_ok=True)

RESULT = re.compile(
    r"^\s*(ok|x|-)\s+\d+\s+\[chromium\]\s+›\s+\S*(qoder-ord0417-tap-names-the-stop|_tmp_ord0417_pill_probe)\.spec\.ts:\d+:\d+\s+›\s+(.+?)\s*$"
)

runs = {
    "r25_first_pass_full_17_arms": f"{G}/ord0417r25r7gate.log",
    "r26_quiet_rerun_of_the_red_arm": f"{G}/ord0417r26repro414en.log",
    "r27_control_cell_removed": f"{G}/ord0417r27ctrl414en.log",
    "r30_probe_copy_of_the_arm": f"{G}/ord0417r30pillprobe3.log",
}

lines_out = []
for tag, path in runs.items():
    text = io.open(path, encoding="utf-8", errors="replace").read().splitlines()
    lines_out.append(f"=== {tag} :: {os.path.basename(path)} ===")
    for l in text:
        if RESULT.match(l) or "lost a reachable control" in l or "no name was painted on the glass" in l:
            lines_out.append(l.rstrip())
        if re.match(r"^\s+\d+ (passed|failed|skipped)", l) or re.match(r"^\s+\d+ (passed|failed)", l):
            lines_out.append(l.rstrip())
    lines_out.append("")

for name in ("PILLPROBE_414en.json", "ATTRIB_414en_tip_vs_ctrl.json", "ARMS_r25r7gate.json",
             "R20_GEOMETRY_ROWS.json"):
    src = io.open(f"{G}/{name}", encoding="utf-8").read()
    dst = {
        "PILLPROBE_414en.json": "GATE_R7_PILLPROBE_414EN_R1.json",
        "ATTRIB_414en_tip_vs_ctrl.json": "GATE_R7_ATTRIBUTION_414EN_R1.json",
        "ARMS_r25r7gate.json": "GATE_R7_ARMS_R25.json",
        "R20_GEOMETRY_ROWS.json": "GATE_R20_GEOMETRY_ROWS_R1.json",
    }[name]
    io.open(f"{OUT}/{dst}", "w", encoding="utf-8", newline=chr(10)).write(src)

io.open(f"{OUT}/GATE_R7_RED_414EN_RUNS_R1.txt", "w", encoding="utf-8", newline=chr(10)).write(
    chr(10).join(lines_out) + chr(10))
io.open(f"{OUT}/GATE_R7_LIST_ARMS_R25.txt", "w", encoding="utf-8", newline=chr(10)).write(
    io.open(f"{G}/ord0417r25list_arms.txt", encoding="utf-8").read())
print(json.dumps({"files": sorted(os.listdir(OUT)), "run_lines": len(lines_out)}, indent=1))
