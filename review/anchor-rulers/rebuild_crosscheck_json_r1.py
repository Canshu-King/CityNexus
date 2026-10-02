"""把 cross-check 那一趟的读数从它自己的 stdout 里重建为机读件（不重跑、不补数）。

为什么会走到这一步：跑完后 JSON 落盘前崩在 `"interpreter": A.PY`（WindowsPath 不可序列化），
15 手的读数只在 `xc_landed_r2.log` 里活着。本件把那 15 行逐行解析回来，与我那一代的期望逐手配对；
任何一手解析不出来、或案例名与 `anchor_ruler_counterexamples_r1.json` 对不上，就拒绝出件。
原始 stdout 一起进证据枝，谁都能拿它复核这份重建。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

WT = Path("D:/moodle/_qoder_anchor_crosscheck_20261002/wt")
LOG = Path("D:/moodle/_qoder_newlane_ord0444_20260929/scratch/xc_landed_r2.log")
MINE = Path("D:/moodle/_qoder_newlane_ord0444_20260929/scratch/anchor_ruler_counterexamples_r1.json")
OUT = Path("D:/moodle/_qoder_anchor_rulers_20261002/crosscheck_landed_rulers_r1.json")
BAD: list[str] = []

lines = [l.strip() for l in LOG.read_text(encoding="utf-8", errors="replace").splitlines()
         if l.strip().startswith("{") and '"case"' in l]
rows = []
for l in lines:
    try:
        rows.append(json.loads(l))
    except json.JSONDecodeError as exc:
        BAD.append("PARSE %s %s" % (exc.__class__.__name__, l[:60]))
mine = json.loads(MINE.read_text(encoding="utf-8"))
by_name = {c["case"]: c for c in mine["cases"]}
merged = []
for r in rows:
    m = by_name.get(r["case"])
    if m is None:
        BAD.append("UNKNOWN_CASE %r" % r["case"][:40])
        continue
    merged.append({"case": r["case"], "expectation_in_my_generation": m["expect"],
                   "verdict_in_my_generation": m["verdict"],
                   "assert_line_in_my_generation": (m.get("actual_assert_line") or [""])[0],
                   "mutated_path": m["mutated_path"], "mutation_landed": m["mutation_landed"],
                   "verdict_on_landed_rulers": r["verdict_on_landed_rulers"],
                   "assert_line_on_landed_rulers": r["assert_line_on_landed_rulers"]})
missing = sorted(set(by_name) - {r["case"] for r in merged})
if len(merged) != 15 or missing:
    BAD.append("CASES %d/15 missing=%s" % (len(merged), missing))
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(WT), capture_output=True,
                      text=True).stdout.strip()
clean = subprocess.run(["git", "status", "--porcelain"], cwd=str(WT),
                       capture_output=True, text=True).stdout.strip()
differ = [r["case"] for r in merged if r["verdict_on_landed_rulers"] != r["verdict_in_my_generation"]]
if BAD:
    print("REFUSED:", *BAD, sep="\n  ")
    sys.exit(1)
OUT.write_text(json.dumps({
    "landed_tip": head, "my_branch": mine["form"]["worktree_head"],
    "interpreter": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
    "python": mine["form"]["python"],
    "rebuilt_from": "xc_landed_r2.log (that run's own stdout; the JSON dump crashed on a Path field)",
    "rebuilt_at": time.strftime("%m-%d %H:%M:%S"),
    "crosscheck_worktree_clean_after_restore": clean,
    "cases": merged,
    "counts": {"total": len(merged),
               "red_on_landed": sum(1 for r in merged if r["verdict_on_landed_rulers"] == "RED"),
               "green_on_landed": sum(1 for r in merged if r["verdict_on_landed_rulers"] == "GREEN"),
               "landed_before_mine": len(differ)},
    "where_the_two_versions_differ": differ}, ensure_ascii=False, indent=1), encoding="utf-8")
print("WROTE", OUT, "| red_on_landed", sum(1 for r in merged if r["verdict_on_landed_rulers"] == "RED"),
      "| differ", differ, "| clean", repr(clean))
