"""ORD-0500 r6 协助 -- fold the counts the earlier run printed to stdout into the receipt itself.

The byte-carry reading was computed once and its numbers only ever lived in a terminal. A block that
quotes "70 of 72" while the artifact it cites stores no such figure is a citation to nothing, so the
summary is derived here from the rows that *are* stored and written back into the same file.
"""
import io
import json

PATH = ("D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/ord0500-r6-rebase-preview/"
        "receipts/o500_r6_byte_carry_r1.json")

with io.open(PATH, encoding="utf-8") as handle:
    data = json.load(handle)

rows = data["rows"]
carried = [r["path"] for r in rows if r["merged_equals_cand"]]
differ = [r["path"] for r in rows if not r["merged_equals_cand"]]
data["summary"] = {
    "write_set": len(rows),
    "merged_carries_the_lane_blob": len(carried),
    "merged_does_not_carry_the_lane_blob": len(differ),
    "paths_not_carried": sorted(differ),
    "how_counted": "per path: git rev-parse <predicted_tree>:<path> vs <candidate>:<path>, both read out "
    "of the same merge-tree run; the write set is measured against the merge base (the fork point), not "
    "against the tip, because the tip's own new files are not this branch's writes",
}
with io.open(PATH, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(data, handle, indent=1, ensure_ascii=False)

print("SUMMARY_ADDED write_set=%d carried=%d not_carried=%s"
      % (len(rows), len(carried), sorted(differ)))
