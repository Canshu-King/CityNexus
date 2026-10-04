"""Do r2's four new distinctions actually bite?  Controls first, then one damage at a time -- all against
scratch text and read-only git, nothing under the worktree is written.

Each arm names the reading it expects from the instrument, not from me; an arm that passes because the tool
answered nothing is caught by the control that requires a real prediction (`PREDICTED`) for a pair that does
share history.
"""
import json
import os
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
sys.path.insert(0, os.path.join(LANE, "tools"))
import landed_blob_rescan_r2 as R

CASES = [
    {"id": "C1_held_control", "expect_class": "HELD", "note": "a hand whose bytes really are on the line"},
    {"id": "C2_predicted_control", "expect_pred": "PREDICTED",
     "note": "merge-tree on a commit and its own parent: the arm can produce a prediction at all"},
    {"id": "M1_absent_without_receipt", "expect_class": "NOT_ON_LINE", "forbid": "LOST_LANDED_CONTENT",
     "note": "r1's mislabel: never landed must not read as lost"},
    {"id": "M2_absent_with_receipt", "expect_class": "LOST_LANDED_CONTENT",
     "note": "with a receipt the same reading does become a loss"},
    {"id": "M3_changed_not_absent", "expect_class": "SUPERSEDED_ON_LINE", "forbid": "NOT_ON_LINE",
     "note": "a path that exists with other bytes is not 'not on the line'"},
    {"id": "M4_vacuous_merge_tree", "expect_pred": "NO_PREDICTION",
     "note": "exit 128 has to answer 'no prediction', never 'zero conflicts'"},
    {"id": "M5_key_blind_spot", "expect_missed": 1, "note": "the ORD-0485 family must surface as a candidate"},
    {"id": "M6_distance_is_not_stray", "expect_own": 0,
     "note": "a tool-only hand: generation distance is large, its own product paths are zero"},
    {"id": "M7_unreadable_tree", "expect_sentinel": "UNREADABLE_ON_LINE",
     "note": "an unusable revision is not a vanished file (r1's arm, kept because r2 still classifies it)"},
]


def coord_set(path, expect):
    return {"ref": "scratch", "head": "scratch", "coords": [{"path": path, "expect": expect}],
            "own_product_paths": 0, "own_product": []}


def counts_for(tip, path, expect):
    rows = R.scan(tip, coord_set(path, expect))
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    return counts, rows


def run(case, tip, held_ref, held_head, tool_ref, tool_head, stale_head):
    out = {"id": case["id"], "note": case["note"], "expect": case.get("expect_class")
                                                          or case.get("expect_pred")
                                                          or case.get("expect_missed")
                                                          or case.get("expect_own")
                                                          or case.get("expect_sentinel")}
    if case["id"] == "C1_held_control":
        cs, why = coordinates(held_ref, held_head)
        counts = {}
        for r in R.scan(tip, cs):
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        got = R.classify(counts, True)
        out["counts"] = counts
    elif case["id"] == "C2_predicted_control":
        rc, parent, _e = R.git("rev-parse", "%s^" % held_head)
        got = R.prediction(held_head, parent.strip())
        out["prediction"] = got["prediction"]
        return {"id": case["id"], "note": case["note"], "expect": case["expect_pred"],
                "got": got["prediction"], "bit": got["prediction"] == "PREDICTED",
                "detail": {"merge_tree_exit": got["merge_tree_exit"], "conflicts": got["conflicts"]}}
    elif case["id"] == "M1_absent_without_receipt":
        counts, rows = counts_for(tip, "review/this/path/does/not/exist_r2_arm.json",
                                  "0" * 40)
        got = R.classify(counts, False)
        out["rows"] = rows
    elif case["id"] == "M2_absent_with_receipt":
        counts, rows = counts_for(tip, "review/this/path/does/not/exist_r2_arm.json",
                                  "0" * 40)
        got = R.classify(counts, True)
        out["rows"] = rows
    elif case["id"] == "M3_changed_not_absent":
        # aim at a path the line really carries: the HELD hand's own first path, read off that ref rather than
        # typed -- the first draft of this arm pointed at a side-ref-only path and came back NOT_ON_LINE,
        # which was the arm's mistake, not the classifier's
        cs, why = coordinates(held_ref, held_head)
        a_path = cs["coords"][0]["path"]
        rc, real_blob, _e = R.git("rev-parse", "%s:%s" % (tip, a_path))
        counts, rows = counts_for(tip, a_path, "f" * 40)
        got = R.classify(counts, False)
        out["real_blob_on_line"] = real_blob.strip()
        out["path"] = a_path
    elif case["id"] == "M4_vacuous_merge_tree":
        p = R.prediction(tip, stale_head)
        out["prediction"] = p
        return {"id": case["id"], "note": case["note"], "expect": case["expect_pred"],
                "got": p["prediction"], "bit": p["prediction"].startswith("NO_PREDICTION")
                                          and p["conflicts"] is None,
                "detail": {"merge_tree_exit": p["merge_tree_exit"], "conflicts": p["conflicts"],
                           "why": p["why"]}}
    elif case["id"] == "M5_key_blind_spot":
        synth = [["refs/heads/review/newlane-ord0485-phone-walkthrough-r1", "1" * 40],
                 ["refs/heads/review/" + held_ref.split("/")[-1], held_head],
                 ["refs/heads/review/1ba48dbf-ord0476-checkin-r1", "2" * 40]]
        heads, cands = R.my_refs(synth)
        out["heads"] = heads
        out["candidates"] = [c[0] for c in cands]
        return {"id": case["id"], "note": case["note"], "expect": 1, "got": len(cands),
                "bit": len(cands) == 1 and cands[0][0].endswith("walkthrough-r1")
                           and not any("walkthrough" in h for h in heads),
                "detail": {"heads_matched_by_key": heads, "candidates_missed": [c[0] for c in cands]}}
    elif case["id"] == "M6_distance_is_not_stray":
        cs, why = coordinates(tool_ref, tool_head)
        dist = R.gen_distance(tip, tool_head)
        out["own"] = cs["own_product_paths"]
        out["dist"] = dist
        return {"id": case["id"], "note": case["note"], "expect": 0, "got": cs["own_product_paths"],
                "bit": cs["own_product_paths"] == 0
                       and dist.get("gen_distance_product_paths", 0) > 0,
                "detail": {"own_product_paths": cs["own_product_paths"], "gen_distance": dist}}
    elif case["id"] == "M7_unreadable_tree":
        counts, rows = counts_for("deadbeef" + "0" * 32, "review/anything", "0" * 40)
        got = R.classify(counts, True)
        out["rows"] = rows
    if case.get("expect_class"):
        ok = got == case["expect_class"] and (case.get("forbid") is None or case["forbid"] not in got)
        return {"id": case["id"], "note": case["note"], "expect": case["expect_class"], "got": got,
                "forbid": case.get("forbid"), "bit": bool(ok), "detail": out}
    if case.get("expect_sentinel"):
        verd = out["rows"][0]["verdict"]
        return {"id": case["id"], "note": case["note"], "expect": case["expect_sentinel"], "got": verd,
                "bit": verd == case["expect_sentinel"], "detail": out["rows"]}
    raise SystemExit("ARM_HAS_NO_ASSERTION " + case["id"])


def coordinates(ref, head):
    return R.coordinates(ref, head)


def main():
    tip = R.live_tip()
    rows = R.all_review_refs()
    got = dict(rows)
    held_ref = "refs/heads/review/0afdb49b-ord0500-staging-door-r4"
    tool_ref = "refs/heads/review/0afdb49b-landed-blob-rescan-r1"
    stale_ref = "refs/heads/review/newlane-ord0500-phone-checkin-entry-r1"
    results = [run(c, tip, held_ref, got[held_ref], tool_ref, got[tool_ref], got[stale_ref]) for c in CASES]
    every = all(r["bit"] for r in results)
    out = {"schema": "CNX_LANDED_BLOB_RESCAN_ARMS_V2", "tool": "landed_blob_rescan_arms_r2",
           "live_tip": tip, "runs": results, "arm_count": len(results),
           "controls": [r["id"] for r in results if r["id"].startswith("C")],
           "mutants": [r["id"] for r in results if r["id"].startswith("M")],
           "every_arm_bit": bool(every), "worktree_written": False,
           "r1_defects_addressed": ["LOST label needs a receipt", "merge-tree exit 128 is not zero conflicts",
                                    "generation distance is not a stray write",
                                    "name key misses the ORD-0485 family"]}
    dest = os.path.join(LANE, "evidence", "landed_blob_rescan_arms_r2.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"every_arm_bit": every,
                      "rows": [(r["id"], r["got"], r["bit"]) for r in results]}, indent=1))
    print("WROTE " + dest)
    if not every:
        raise SystemExit("RESCAN_ARMS_R2_NOT_ALL_BIT")


if __name__ == "__main__":
    main()
