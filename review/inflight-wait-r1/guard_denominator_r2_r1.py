"""Fold the earlier two-mode sweep into the denominator receipt as r2.

r1 was published inside this hand and counted only its own 32 files; the three files measured in the
first sweep that also match the seeding predicate are real readings for the same question, so the
honest denominator is 33 -- 9 disagree, 24 agree.  r1 is left untouched.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

TREE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930/wt2")
R1 = TREE / "review/inflight-wait-r1/GUARD_DENOMINATOR_r1.json"
BLAST = TREE / "review/inflight-wait-r1/GUARD_BLAST_RADIUS_r1.json"
OUT = TREE / "review/inflight-wait-r1/GUARD_DENOMINATOR_r2.json"
SEED = re.compile(r'tmp_path / "\S+\.db"|sqlite3\.connect\(|create_engine\(f?"sqlite|make_engine\(')

sys.stdout.reconfigure(encoding="utf-8")
r1 = json.loads(R1.read_text(encoding="utf-8"))
blast = json.loads(BLAST.read_text(encoding="utf-8"))
rows = {r["file"]: r for r in r1["rows"]}
added = []
for pair in blast["pairs"]:
    name = pair["file"] if pair["file"].startswith("tests/") else "tests/" + pair["file"]
    if name in rows:
        continue
    rows[name] = {"file": name,
                  "stamped_summary": pair["authoritative"]["summary"],
                  "stamped_red": pair["authoritative"]["red_set"],
                  "stamped_errors": pair["authoritative"].get("errors", []),
                  "control_ran": True,
                  "plain_summary": pair["plain"]["summary"],
                  "differs": pair["red_set_differs"]}
    added.append(name)

seeded = sorted("tests/" + p.name for p in (TREE / "backend/tests").glob("test_*.py")
                if SEED.search(p.read_text(encoding="utf-8", errors="replace")))
compared = sorted(set(rows) & set(seeded))
disagree = sorted(f for f in compared if rows[f]["differs"])
unmeasured = sorted(set(seeded) - set(compared))

out = {"generated_by": "89f2e2d6", "supersedes_for_this_count": "review/inflight-wait-r1/GUARD_DENOMINATOR_r1.json",
       "why_r2": "r1 counted only its own sweep (%d files); %d seeded files were already measured in "
                 "the earlier two-mode sweep and belong in the same denominator"
                 % (len(r1["rows"]), len([a for a in added if a in seeded])),
       "tree_head": r1["tree_head"],
       "seeded_population": len(seeded),
       "files_compared": len(compared),
       "files_where_the_two_modes_disagree": len(disagree),
       "files_where_they_agree": len(compared) - len(disagree),
       "unmeasured_candidates": unmeasured,
       "rows_merged_from_the_first_sweep": [a for a in added if a in seeded],
       "disagreement_list": disagree,
       "arms_lost_only_under_the_stamp": {f: (rows[f]["stamped_red"] or rows[f]["stamped_errors"])
                                          for f in disagree},
       "rows": [rows[f] for f in compared]}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("seeded=%d compared=%d disagree=%d agree=%d unmeasured=%d merged_in=%s"
      % (len(seeded), len(compared), len(disagree), len(compared) - len(disagree),
         len(unmeasured), [m.split("/")[-1] for m in out["rows_merged_from_the_first_sweep"]]))
print("out %s" % OUT)
