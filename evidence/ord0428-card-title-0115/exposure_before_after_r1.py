"""ORD-0428: what the exposure ruler sees before and after the card-title join.

Why this is in the delivery at all: ORD-0448 measured that the door compares a *count* of cells, and that a
candidate can lower that count by re-filing a cell into an attribute instead of removing the exposure. So
"the number went down" is not by itself evidence of a fix. This prints, per ruler generation, the cell sets
on both trees and splits the difference into what disappeared from `hits` and what appeared anywhere -
`hits` or `attributed_in_fold`. A real fix removes the cell from the union; a re-file moves it into
`attributed_in_fold` and leaves the union alone.
"""
import hashlib
import io
import json
import os
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
NUL = chr(0).encode()
TREES = {
    "before_tip4037": os.path.join(WORK, "tip4037", "frontend"),
    "after_ord0428r1": r"D:\moodle\_qoder_lane_S4_0926\wt0428\frontend",
}
GENS = [("r7b", "ui_exposure_taint_ast_r7b.cjs"), ("r7b4", "ui_exposure_taint_ast_r7b4.cjs")]


def blob_of(path):
    raw = io.open(path, "rb").read()
    return hashlib_sha1_blob(raw), len(raw)


def hashlib_sha1_blob(raw):
    return hashlib.sha1(b"blob %d" % len(raw) + NUL + raw).hexdigest()


def cells(doc, key):
    """`hits` records carry `file` + `line`; `attributed_in_fold` records carry `file` + `file_line`.

    r1 of this script read `file_line or file`, which keyed every hit by file alone (three
    PlanWithAiSheet.tsx hits collapsed into one label) and every fold cell by line alone (the file name
    dropped). Both counts were therefore set sizes of the wrong labels. Fixed here; the r1 bug is
    reported in the delivery block rather than quietly rewritten.
    """
    out = set()
    for rec in doc.get(key, []):
        line = rec.get("line")
        if line is None:
            line = rec.get("file_line")
        out.add("%s:%s|%s" % (rec.get("file"), line, rec.get("rule")))
    return out


def main():
    import hashlib
    out = {"rulers": {}, "trees": TREES, "per_generation": {}, "v8experience": {}}
    for tag, name in GENS:
        p = os.path.join(REF, name)
        b, n = blob_of(p)
        out["rulers"][tag] = {"file": name, "blob": b, "bytes": n,
                              "local_bytes_sha1": hashlib.sha1(io.open(p, "rb").read()).hexdigest()}
    for tag, name in GENS:
        side = {}
        for label, tree in TREES.items():
            js = os.path.join(WORK, "exp_%s_%s.json" % (label.split("_")[0], tag))
            doc = json.load(io.open(js, encoding="utf-8"))
            hits = cells(doc, "hits")
            fold = cells(doc, "attributed_in_fold")
            side[label] = {
                "receipt": os.path.basename(js),
                "cells_total_reported": doc.get("cells_total"),
                "hits": len(hits),
                "attributed_in_fold": len(fold),
                "union": len(hits | fold),
                "parse_diagnostics_total": doc.get("parse_diagnostics_total"),
                "_hits": hits,
                "_fold": fold,
            }
        a, b = side["before_tip4037"], side["after_ord0428r1"]
        gone_hits = sorted(a["_hits"] - b["_hits"])
        new_hits = sorted(b["_hits"] - a["_hits"])
        gone_union = sorted((a["_hits"] | a["_fold"]) - (b["_hits"] | b["_fold"]))
        new_union = sorted((b["_hits"] | b["_fold"]) - (a["_hits"] | a["_fold"]))
        moved_to_fold = sorted((a["_hits"] - b["_hits"]) & (b["_fold"] - a["_fold"]))
        # A cell whose line moved because the edit added lines above it is the same exposure, not a new
        # one. Compare by (file, rule) multiset so a shift cannot masquerade as growth or as a removal.
        def by_file_rule(s):
            out = {}
            for label in s:
                path, _, rest = label.partition("|")
                f, _, _ln = path.rpartition(":")
                out[(f, rest)] = out.get((f, rest), 0) + 1
            return out
        ua, ub = a["_hits"] | a["_fold"], b["_hits"] | b["_fold"]
        ca, cb = by_file_rule(ua), by_file_rule(ub)
        out["per_generation"][tag] = {
            "before": {k: v for k, v in a.items() if not k.startswith("_")},
            "after": {k: v for k, v in b.items() if not k.startswith("_")},
            "hits_disappeared": gone_hits,
            "hits_appeared": new_hits,
            "union_disappeared": gone_union,
            "union_appeared": new_union,
            "re_filed_into_fold_not_removed": moved_to_fold,
            "union_by_file_and_rule_before": {"%s|%s" % k: v for k, v in sorted(ca.items())},
            "union_by_file_and_rule_after": {"%s|%s" % k: v for k, v in sorted(cb.items())},
            "union_by_file_and_rule_equal": ca == cb,
            "verdict": ("REMOVED_FROM_UNION" if gone_hits and not new_union and not moved_to_fold
                        else ("REFILED" if moved_to_fold
                              else ("NO_CHANGE_LINE_SHIFT_ONLY"
                                    if not gone_hits and not new_hits and ca == cb
                                    else "NO_CHANGE" if not gone_hits and not new_hits and not new_union
                                    else "MIXED_SEE_LISTS"))),
        }
        out["v8experience"][tag] = {
            "before_v8_cells": sorted(x for x in (a["_hits"] | a["_fold"]) if "V8Experience" in x),
            "after_v8_cells": sorted(x for x in (b["_hits"] | b["_fold"]) if "V8Experience" in x),
        }
    io.open(os.path.join(WORK, "exposure_before_after_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
