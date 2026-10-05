"""Delta between the two aggregate-label generations of the fleet re-scan.

r1's per-path counts stand; only the labels over them changed, and "only labels changed" is a
claim that has to name which hands were relabelled or it is worth nothing.  This reads both
artefacts from disk, pairs them by ref, and writes the changed pairs plus one row per class.

It also records what the batch bug cost: the two hands that r1 reported as "published nothing"
because git dropped the lexically largest head from the batch -- one of them is a real empty
commit, the other two are hands whose paths ARE on the line.
"""
import collections
import json
import os
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
R1 = os.path.join(LANE, "evidence", "fleet_rescan_r1", "fleet_rescan_r1.json")
R2 = os.path.join(LANE, "evidence", "fleet_rescan_r2", "fleet_rescan_r2.json")
OUT = os.path.join(LANE, "evidence", "fleet_rescan_r2", "label_delta_r2.json")

# r1's word for a class, r2's word for the same reading; pairs that are NOT aliases are the
# findings of this generation.
ALIAS = {"ALL_ABSENT": "ALL_NOT_ON_LINE", "ALL_CHANGED": "ALL_DIFFERENT_ON_LINE",
         "OTHER": "NONE_HELD_SPLIT", "NO_PATHS_REPORTED": "NO_PATHS_REPORTED",
         "HELD": "HELD", "MIXED": "MIXED", "NOT_REACHED": "NOT_REACHED"}


def r1_counts(row):
    """r1 printed flat per-class numbers instead of a counts dict; normalise so the two
    generations can be compared field by field."""
    return {k: row[k] for k in ("same", "absent", "changed") if row.get(k)}


def main():
    for path in (R1, R2):
        if not os.path.exists(path):
            raise SystemExit("ABORT_ARTIFACT_MISSING " + path)
    old = json.load(open(R1, encoding="utf-8"))
    new = json.load(open(R2, encoding="utf-8"))
    om = {r["ref"]: r for r in old["rows"]}
    nm = {r["ref"]: r for r in new["rows"]}
    if set(om) != set(nm):
        raise SystemExit("ABORT_ROSTER_DIFFERS only_old=%d only_new=%d"
                         % (len(set(om) - set(nm)), len(set(nm) - set(om))))

    changed = []
    head_moves = []
    for ref in sorted(nm):
        o, n = om[ref], nm[ref]
        if o["head"] != n["head"]:
            # another lane advanced its own branch between the two passes: that is a different
            # reading at a different coordinate, not a relabelling by this generation.
            head_moves.append({"ref": ref, "r1_head": o["head"], "r2_head": n["head"],
                               "r1_label": o["class"], "r2_label": n["class"],
                               "r1_paths": o["paths"], "r2_paths": n["paths"]})
            continue
        exp = ALIAS.get(o["class"], o["class"])
        if exp != n["class"]:
            changed.append({"ref": ref, "head": n["head"], "r1_label": o["class"],
                            "r2_label": n["class"], "r1_paths": o["paths"], "r2_paths": n["paths"],
                            "r1_counts": r1_counts(o),
                            "r2_counts": {k: v for k, v in n["counts"].items() if v},
                            "why": n.get("why")})
    if not changed:
        raise SystemExit("ABORT_NO_LABEL_CHANGE -- this generation found nothing to relabel and "
                         "should not be published as if it did")
    pairs = collections.Counter((c["r1_label"], c["r2_label"]) for c in changed)

    # per-path counts are supposed to be untouched: prove it, or attribute every move to a named
    # cause.  Two causes exist in this generation -- deletions that r1 folded into CHANGED, and
    # paths r1's per-head pass saw against one parent while the fleet pass (-m) sees both.
    count_moves = []
    for ref in sorted(nm):
        o, n = om[ref], nm[ref]
        if o["head"] != n["head"]:
            continue
        oc = r1_counts(o)
        pair = (oc.get("same", 0), oc.get("absent", 0), oc.get("changed", 0))
        new_triple = (n["counts"]["SAME"], n["counts"]["ABSENT"], n["counts"]["CHANGED"])
        if pair != new_triple:
            dh, du = n["counts"]["DELETION_HELD"], n["counts"]["DELETION_UNDONE"]
            same_paths = o["paths"] == n["paths"]
            explained = (pair[0] - new_triple[0] == dh and pair[2] - new_triple[2] == du
                         and pair[1] == new_triple[1])
            if o["class"] == "NO_PATHS_REPORTED":
                cause = "recovered_from_batch_drop"
            elif explained and same_paths:
                cause = "deletion_class_split"
            elif explained:
                cause = "path_roster_grew_at_same_head"
            else:
                cause = "UNATTRIBUTED"
            count_moves.append({"ref": ref, "r1": list(pair), "r2": list(new_triple),
                                "r1_paths": o["paths"], "r2_paths": n["paths"],
                                "deletion_held": dh, "deletion_undone": du,
                                "n_parents": n.get("n_parents"), "cause": cause})
    unattr = [c for c in count_moves if c["cause"] == "UNATTRIBUTED"]
    if unattr:
        raise SystemExit("ABORT_UNATTRIBUTED_COUNT_MOVES %s -- every number that moved between the "
                         "two passes has to name why" % json.dumps(unattr[:2], ensure_ascii=False)[:400])

    doc = {
        "tool": "label_delta_r2",
        "refs_compared": len(nm),
        "refs_whose_own_head_moved_between_passes": len(head_moves),
        "head_moves": head_moves,
        "labels_changed": len(changed),
        "changed_pairs": [{"from": a, "to": b, "refs": c} for (a, b), c in pairs.most_common()],
        "rows_with_per_path_counts_moved": len(count_moves),
        "count_move_causes": {k: v for k, v in collections.Counter(c["cause"] for c in count_moves).items()},
        "unattributed_count_moves": len(unattr),
        "count_moves": count_moves,
        "recovered_from_batch_bug": [c for c in changed if c["r1_label"] == "NO_PATHS_REPORTED"],
        "changed_rows": changed,
        "r1_tip": old["tip"], "r2_tip": new["tip"],
        "same_tip": old["tip"] == new["tip"],
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print("refs_compared=%d labels_changed=%d same_tip=%s (r1=%s r2=%s)"
          % (len(nm), len(changed), doc["same_tip"], old["tip"][:10], new["tip"][:10]))
    for p in doc["changed_pairs"]:
        print("  %-20s -> %-24s %d refs" % (p["from"], p["to"], p["refs"]))
    print("rows_with_per_path_counts_moved=%d" % doc["rows_with_per_path_counts_moved"])
    for c in count_moves[:6]:
        print("   %-46s r1=%s r2=%s" % (c["ref"].split("/")[-1][:46], c["r1"], c["r2"]))
    print("recovered_from_batch_bug=%d" % len(doc["recovered_from_batch_bug"]))
    for c in doc["recovered_from_batch_bug"]:
        print("   %-46s -> %s paths=%d" % (c["ref"].split("/")[-1][:46], c["r2_label"], c["r2_paths"]))
    print("bytes=%d" % os.path.getsize(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
