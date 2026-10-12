"""Aggregate the denominator run into one receipt: which files the two invocation modes disagree on.

Duplicates are resolved last-wins (a file re-measured with the fixed predicate overwrites the earlier
line), and every count is derived from the rows rather than typed.
"""

from __future__ import annotations

import json
import pathlib
import sys

LANE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930")
TREE = LANE / "wt2"
LOG = LANE / "tmp/GUARD_DENOMINATOR_r1.jsonl"
AB = LANE / "tmp/GUARD_CONTROL_AB_r1.json"
OUT = LANE / "tmp/GUARD_DENOMINATOR_r1.json"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    by_file: dict[str, dict] = {}
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        key = rec["file"]
        if rec.get("plain") is None and key in by_file and by_file[key].get("plain"):
            continue  # keep the richer (control-bearing) row
        by_file[key] = rec

    ab = json.loads(AB.read_text(encoding="utf-8"))
    whole = next(c for c in ab["cases"] if c["case"] == "whole_file")
    pending = {"file": "tests/test_qoder_pending_destination_identity.py",
               "stamped": {"summary": whole["stamped"]["summary"],
                           "red_set": whole["stamped"]["red_set"],
                           "errors": []},
               "plain": {"summary": whole["plain"]["summary"],
                         "red_set": whole["plain"]["red_set"], "errors": []},
               "differs": whole["red_set_differs"]}
    by_file.setdefault(pending["file"], pending)

    differing = {f: r for f, r in by_file.items() if r["differs"]}
    rows = []
    for f, r in sorted(by_file.items()):
        rows.append({"file": f,
                     "stamped_summary": r["stamped"]["summary"],
                     "stamped_red": r["stamped"]["red_set"],
                     "stamped_errors": (r["stamped"].get("errors") or [])[:2],
                     "control_ran": r.get("plain") is not None,
                     "plain_summary": (r.get("plain") or {}).get("summary", "(not needed)"),
                     "differs": r["differs"]})
    receipt = {
        "generated_by": "89f2e2d6",
        "order": "denominator for the fresh-database guard, measured in both invocation modes",
        "tree_head": next(iter(by_file.values()))["tree_head"],
        "files_compared": len(rows),
        "files_where_the_two_modes_disagree": len(differing),
        "files_where_they_agree": len(rows) - len(differing),
        "disagreement_list": sorted(f for f in differing),
        "arms_lost_only_under_the_stamp": {f: differing[f]["stamped"]["red_set"] or differing[f]["stamped"].get("errors")
                                           for f in sorted(differing)},
        "rows": rows,
        "not_measured": "population of files that open their own sqlite was counted by the same "
                        "predicate the sampler uses; the other backend test files (which share one "
                        "process database) were not compared in either mode",
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("files_compared %d disagree %d agree %d"
          % (receipt["files_compared"], receipt["files_where_the_two_modes_disagree"],
             receipt["files_where_they_agree"]))
    for f in receipt["disagreement_list"]:
        print("   %s  %s" % (f.split("/")[-1], receipt["arms_lost_only_under_the_stamp"][f][:2]))
    mine = [f for f in receipt["disagreement_list"] if "0520" in f]
    print("files of my own order in that list: %d -> %s" % (len(mine), [f.split('/')[-1] for f in mine]))
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
