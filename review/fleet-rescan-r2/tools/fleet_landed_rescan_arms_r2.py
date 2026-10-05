"""Counter-examples for tools/fleet_landed_rescan_r2.py.

A ruler that never says "wrong" is not a ruler.  Each arm below feeds the real functions a shape
that has a named correct answer, and the arm is only MET when the ruler gives it -- including the
two aggregate defects this generation exists to fix, which are re-measured here rather than
described:

  * r1 folded whole-tree snapshot hands into CHANGED, which read as "thousands of artefacts were
    overwritten on the line".  C4 asks for that shape and refuses the old label.
  * r1 had no class for a hand that only deletes, so it fell into the catch-all.  C5 asks for it.

Nothing here writes to the line: the shapes are built in memory, and the only git calls are reads.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(r"D:/moodle/_qoder_phone_ord0485_20260930", "tools"))
import fleet_landed_rescan_r2 as R

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
OUT = os.path.join(LANE, "evidence", "fleet_rescan_r2")
HEX = "0" * 39 + "1"


def arm(name, ok, detail):
    return {"arm": name, "bit": bool(ok), "detail": detail}


def main():
    os.makedirs(OUT, exist_ok=True)
    tip_rows = [r for r in R.lsremote("refs/heads/*") if r[0] == R.TIP_REF]
    tip = tip_rows[0][1]
    tree = R.tip_tree(tip)
    doc = json.load(open(os.path.join(OUT, "fleet_rescan_r2.json"), encoding="utf-8"))
    held = [r for r in doc["rows"] if r["class"] == "HELD"]
    snap = [r for r in doc["rows"] if r["class"] == "SNAPSHOT_SHAPED"]

    arms = []

    rows = doc["rows"]

    # C1 -- control: a hand the ruler calls HELD really is byte-equal on the live tip.
    h = held[0]
    coords = R.published_paths([h["head"]]).get(h["head"], {})
    counts, _ = R.counts_for(tree, coords, present=set(tree.values()))
    cls, _ = R.aggregate(counts, len(coords), len(tree))
    arms.append(arm("C1_control_held_not_accused",
                    cls == "HELD" and counts["ABSENT"] == 0 and counts["CHANGED"] == 0 and counts["SAME"] > 0,
                    {"ref": h["ref"], "class": cls, "same": counts["SAME"], "absent": counts["ABSENT"],
                     "changed": counts["CHANGED"]}))

    # C2 -- a differing blob on a real path must be CHANGED, never SAME: the ruler is not
    # laundering a byte difference into a pass.
    path = sorted(p for p, s in tree.items() if p.lower().endswith(".py"))[0]
    counts, samples = R.counts_for(tree, {path: {"deleted": False, "expect": HEX}}, present=set(tree.values()))
    arms.append(arm("C2_different_bytes_cannot_read_same",
                    counts["CHANGED"] == 1 and counts["SAME"] == 0,
                    {"path": path, "counts": counts, "sample": samples["changed"][0] if samples["changed"] else {}}))

    # C3 -- a path the line does not carry must be ABSENT and must NOT be called CHANGED
    # (r1's real bug class: a fatal line whose revision was scraped as a blob).
    counts, samples = R.counts_for(tree, {"nope/not/a/path_qoder_r2_probe.py": {"deleted": False, "expect": HEX}},
                                   present=set(tree.values()))
    cls, _ = R.aggregate(counts, 1, len(tree))
    arms.append(arm("C3_missing_path_is_absent_not_changed",
                    counts["ABSENT"] == 1 and counts["CHANGED"] == 0 and cls == "ALL_NOT_ON_LINE",
                    {"class": cls, "counts": counts}))

    # C4 -- the r1 aggregate defect: a snapshot-shaped hand must get NO landed/lost verdict even
    # when every one of its paths differs on the line.
    counts_all_changed = {"SAME": 0, "ABSENT": 0, "CHANGED": len(tree), "UNREADABLE_ON_LINE": 0,
                          "DELETION_HELD": 0, "DELETION_UNDONE": 0}
    cls, why = R.aggregate(counts_all_changed, len(tree), len(tree))
    arms.append(arm("C4_snapshot_hand_gets_no_verdict",
                    cls == "SNAPSHOT_SHAPED" and bool(why),
                    {"shape": "%d paths, every one different" % len(tree), "class": cls,
                     "old_r1_label_would_be": "ALL_SUPERSEDED_ON_LINE",
                     "snapshot_refs_observed": len(snap),
                     "snapshot_paths_observed": doc["snapshot_shaped_paths_total"]}))

    # C5 -- a hand that only deletes, and whose deletions are still in force, is its own class
    # instead of the catch-all.
    cls, _ = R.aggregate({"SAME": 0, "ABSENT": 0, "CHANGED": 0, "UNREADABLE_ON_LINE": 0,
                          "DELETION_HELD": 4, "DELETION_UNDONE": 0}, 4, len(tree))
    arms.append(arm("C5_pure_deletion_hand_named", cls == "ALL_DELETIONS_HELD",
                    {"class": cls, "refs_observed": sum(1 for r in doc["rows"]
                                                        if r["class"] == "ALL_DELETIONS_HELD")}))

    # C6 -- a deletion the line has undone must never be folded into HELD, and gets its own class.
    counts, _ = R.counts_for(tree, {path: {"deleted": True, "expect": HEX}}, present=set(tree.values()))
    cls, _ = R.aggregate(counts, 1, len(tree))
    arms.append(arm("C6_undone_deletion_not_a_pass",
                    counts["DELETION_UNDONE"] == 1 and counts["SAME"] == 0
                    and cls == "ALL_DELETIONS_UNDONE",
                    {"class": cls, "counts": counts,
                     "refs_observed": sum(1 for r in rows if r["class"] == "ALL_DELETIONS_UNDONE")}))

    # C7 -- a tip blob that cannot be read locally is UNREADABLE_ON_LINE, not CHANGED: the ruler
    # must not turn its own blind spot into an accusation.
    counts, samples = R.counts_for(tree, {path: {"deleted": False, "expect": HEX}}, present=set())
    arms.append(arm("C7_unreadable_blob_is_not_changed",
                    counts["UNREADABLE_ON_LINE"] == 1 and counts["CHANGED"] == 0,
                    {"counts": counts, "sample": samples["unreadable"][0] if samples["unreadable"] else {}}))

    # C8 -- the vacuous-leg guard: diff-tree over heads that are not objects has to abort instead
    # of returning an empty roster that would then read as "nothing published anywhere".
    try:
        R.published_paths(["deadbeef" + "0" * 32])
        arms.append(arm("C8_empty_roster_aborts", False, {"note": "published_paths accepted a non-object"}))
    except SystemExit as exc:
        arms.append(arm("C8_empty_roster_aborts", "ABORT" in str(exc), {"abort": str(exc)[:90]}))

    # C9 -- the fleet denominator has to be the remote's own answer: refs are counted, heads are
    # de-duplicated, and a shared head is reported rather than collapsed.
    rows = doc["rows"]
    arms.append(arm("C9_denominator_is_the_remote",
                    len(rows) == doc["review_refs"] and doc["distinct_review_heads"] <= doc["review_refs"]
                    and doc["review_refs"] > 0,
                    {"refs": doc["review_refs"], "distinct_heads": doc["distinct_review_heads"],
                     "refs_sharing_a_head": doc["refs_sharing_a_head"],
                     "unresolvable_locally": doc["heads_unresolvable_locally"]}))

    # C10 -- the scan is a read: no ref moved over the whole run.
    rc, out, err = R.git("ls-remote", "--refs", "origin", "refs/heads/review/*")
    now_rows = [l.split("\t") for l in out.splitlines() if l.strip()]
    same_now = {n: s for s, n in now_rows}
    moved = [r["ref"] for r in rows if same_now.get(r["ref"]) != r["head"]]
    arms.append(arm("C10_no_ref_moved", not moved and len(now_rows) == doc["review_refs"],
                    {"moved": moved[:4], "refs_now": len(now_rows), "refs_at_scan": doc["review_refs"]}))

    # C11 -- the batch pass must equal the per-head pass, including for the lexically largest head.
    # Without the trailing newline git --stdin dropped that one, and its hand then reported
    # "published nothing"; this is the arm that keeps the fix from silently rotting.
    heads_all = sorted({r["head"] for r in rows if r["class"] != "NOT_REACHED"})
    batch = R.published_paths(heads_all)
    with_paths = [h for h in heads_all if h in batch]
    largest = with_paths[-1]
    sample = [largest, with_paths[0], held[0]["head"], snap[0]["head"] if snap else with_paths[1]]
    mismatches, empty_largest = [], []
    for head in sorted(set(sample)):
        solo = R.published_paths([head]).get(head, {})
        if solo != batch.get(head, {}):
            mismatches.append({"head": head[:12], "solo_paths": len(solo),
                               "batch_paths": len(batch.get(head, {}))})
        if head == largest and not solo:
            empty_largest.append(head[:12])
    arms.append(arm("C11_batch_equals_per_head",
                    not mismatches and largest in batch and not empty_largest,
                    {"sampled": len(set(sample)), "mismatches": mismatches,
                     "largest_head": largest[:12], "largest_in_batch": largest in batch,
                     "largest_paths": len(batch.get(largest, {})),
                     "heads_in_batch": len(batch), "heads_asked": len(heads_all),
                     "heads_quiet": len(heads_all) - len(with_paths)}))

    ok = all(a["bit"] for a in arms)
    doc_out = {"arms": arms, "every_arm_bit": ok, "tip": tip,
               "ruler_blob_source": "tools/fleet_landed_rescan_r2.py"}
    with open(os.path.join(OUT, "fleet_rescan_arms_r2.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc_out, indent=1, ensure_ascii=False) + "\n")
    for a in arms:
        print("%-38s bit=%s %s" % (a["arm"], a["bit"], json.dumps(a["detail"], ensure_ascii=False)[:190]))
    print("every_arm_bit=%s" % ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
