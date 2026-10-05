"""Delta between two generations of the same roster, computed instead of described.

The r2 re-scan ruler was built to answer one question -- did content that landed fall out of the line -- and
it can only be answered by comparing two runs taken on two named tips.  This tool reads two scan JSONs and
prints the transitions per ref, the prediction-leg split (which answers nothing and which now answers), and
the denominator of refs on the line.

It also settles the near-miss this window: while reading the new tip I found `review/ord0500-staging-door/tools/
r24_chain.sh` absent and almost reported it as landed content dropping out again.  The question that settles it
is whose path that is, so the tool asks it per path rather than trusting my memory of the hand.
"""
import json
import os
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
sys.path.insert(0, os.path.join(LANE, "tools"))
import landed_blob_rescan_r2 as R

OLD = "evidence/landed_blob_rescan_r2_extended.json"
NEW = "evidence/landed_blob_rescan_r2_gen_d107131c.json"
DISPUTED = "review/ord0500-staging-door/tools/r24_chain.sh"


def own_paths(head):
    rc, out, _e = R.git("diff", "--name-only", "%s^..%s" % (head, head))
    return [l.strip() for l in out.splitlines() if l.strip()]


def main():
    old = json.load(open(os.path.join(LANE, OLD), encoding="utf-8"))
    new = json.load(open(os.path.join(LANE, NEW), encoding="utf-8"))
    o = {r["ref"].split("/")[-1]: r for r in old["refs"]}
    n = {r["ref"].split("/")[-1]: r for r in new["refs"]}
    moved = [{"ref": k, "was": o[k]["verdict"], "now": n[k]["verdict"]} for k in sorted(set(o) & set(n))
             if o[k]["verdict"] != n[k]["verdict"]]
    added = sorted(set(n) - set(o))
    preds = {}
    for r in n.values():
        key = str((r.get("prediction") or {}).get("prediction", "none"))
        preds[key] = preds.get(key, 0) + 1
    # whose path is the disputed one: the hand that declares it, and whether any hand whose paths are all on
    # the line claims it
    owners, held_owners = [], []
    for r in n.values():
        paths = own_paths(r["head"])
        if DISPUTED in paths:
            owners.append({"ref": r["ref"].split("/")[-1], "verdict": r["verdict"]})
            if r["verdict"] == "HELD":
                held_owners.append(r["ref"].split("/")[-1])
    out = {"schema": "CNX_RESCAN_GENERATION_DELTA_V1", "tool": "rescan_generation_delta_r1",
           "old_tip": old["live_tip"], "new_tip": new["live_tip"], "refs_old": len(o), "refs_new": len(n),
           "added_this_window": added, "moved_count": len(moved), "moved": moved,
           "prediction_split": preds, "path_tally_new": new["path_tally"],
           "review_refs_on_line_new": new["review_refs_on_line"],
           "disputed_path": DISPUTED, "disputed_path_declared_by": owners,
           "disputed_path_held_by_a_landed_hand": held_owners,
           "near_miss_verdict": ("NOT_A_ROLLBACK" if not held_owners and owners else "CHECK_BY_HAND"),
           "receipted_refs_new": [x.split("/")[-1] for x in new.get("receipted_refs", [])],
           "lost_today_new": sum(1 for r in n.values() if "LOST_LANDED_CONTENT" in r["verdict"])}
    dest = os.path.join(LANE, "evidence", "rescan_generation_delta_r1.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("old_tip", "new_tip", "refs_old", "refs_new", "moved_count",
                                          "prediction_split", "disputed_path_declared_by",
                                          "near_miss_verdict", "lost_today_new")},
                     ensure_ascii=False, indent=1))
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
