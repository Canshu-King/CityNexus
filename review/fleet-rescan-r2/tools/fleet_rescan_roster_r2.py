"""Compact publication set for the fleet re-scan.

fleet_rescan_r2.json carries a per-hand sample list as well as the counts, which makes it ~1 MB;
the same reading in one line per ref (ref, head, class, paths, six counts) plus the aggregate
block is what anyone landing needs, and costs a fraction of the shared disk.  Numbers are copied
out of the JSON, never retyped, so the published set and the full artefact cannot drift by hand;
the tool aborts if a row is missing or if the line count disagrees.
"""
import json
import os
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
SRC = os.path.join(LANE, "evidence", "fleet_rescan_r2", "fleet_rescan_r2.json")
OUT = os.path.join(LANE, "evidence", "fleet_rescan_r2_roster_r2.tsv")
SUM = os.path.join(LANE, "evidence", "fleet_rescan_r2_summary_r2.json")
COLS = ["SAME", "ABSENT", "CHANGED", "UNREADABLE_ON_LINE", "DELETION_HELD", "DELETION_UNDONE"]
DROP = {"rows"}


def main():
    if not os.path.exists(SRC):
        raise SystemExit("ABORT_SOURCE_MISSING " + SRC)
    doc = json.load(open(SRC, encoding="utf-8"))
    rows = doc["rows"]
    if len(rows) != doc["review_refs"]:
        raise SystemExit("ABORT_ROSTER_SHORT %d rows vs %d refs" % (len(rows), doc["review_refs"]))
    head = "# fleet_landed_rescan_r2 roster  tip=%s  tip_tree_paths=%d  refs=%d  distinct_heads=%d" % (
        doc["tip"], doc["tip_tree_paths"], doc["review_refs"], doc["distinct_review_heads"])
    lines = [head, "# columns: ref<TAB>head<TAB>class<TAB>own_paths<TAB>" + "\t".join(COLS)]
    for r in sorted(rows, key=lambda x: x["ref"]):
        c = r.get("counts") or {}
        lines.append("\t".join([r["ref"], r["head"], r["class"], str(r["paths"])]
                               + [str(c.get(k, 0)) for k in COLS]))
    body = "\n".join(lines) + "\n"
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    if body.count("\n") - 2 != len(rows):
        raise SystemExit("ABORT_ROSTER_LINE_COUNT %d vs %d" % (body.count("\n") - 2, len(rows)))

    summary = {k: v for k, v in doc.items() if k not in DROP}
    summary["roster_tsv_rows"] = len(rows)
    summary["per_ref_rows_live_at"] = "evidence/fleet_rescan_r2/fleet_rescan_r2.json (lane-local, %d B)" % (
        os.path.getsize(SRC))
    with open(SUM, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    reload = json.load(open(SUM, encoding="utf-8"))
    if reload["class_tally"] != doc["class_tally"]:
        raise SystemExit("ABORT_SUMMARY_TALLY_DRIFT")
    print("roster_rows=%d roster_bytes=%d summary_bytes=%d src_json_bytes=%d ratio=%.1fx"
          % (len(rows), os.path.getsize(OUT), os.path.getsize(SUM), os.path.getsize(SRC),
             os.path.getsize(SRC) / os.path.getsize(OUT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
