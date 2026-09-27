#!/usr/bin/env python3
"""ORD-0371 follow-up: the counter-example the commander named - "delete :289-:293, keep only the spread
form, the ruler must go red again" - run through BOTH generations and written as a publishable artifact.

The counter-example file is the shipped candidate with exactly those five lines removed (the provenance
label `t("recovery.serverReason") / t("recovery.deviceReason")`), so the ONLY difference between
`Shipped.tsx` and `NoProvenanceLabel.tsx` is the label.  If r7b1 clears both, it opened the fold on the
spread alone and the double trigger is gone; that is the failure this artifact is built to catch.
"""
import hashlib
import json
import os
import subprocess
import sys

LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0371"
RULERS = {"r7b": ("ui_exposure_taint_ast_r7b.cjs", "d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2"),
          "r7b1": ("ui_exposure_taint_ast_r7b1.cjs", "b6716d9a3c67dafc72fef501bfaff101c84e918a")}
CASES = {"shipped_label_present": "r7b1_acc/Shipped.tsx",
         "label_deleted_289_293": "r7b1_acc/NoProvenanceLabel.tsx"}
CELL = "RecoveryRequiredPanel.tsx|UPSTREAM_TEXT_VIA_HELPER_TO_DOM"


def blob_of(path):
    raw = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest(), len(raw)


def run(gen, case):
    ruler = os.path.join(LIVE, RULERS[gen][0])
    computed, _ = blob_of(ruler)
    assert computed == RULERS[gen][1], (gen, computed)
    src = os.path.join(WORK, CASES[case])
    sblob, sbytes = blob_of(src)
    js = os.path.join(WORK, "ce_%s_%s.json" % (gen, case))
    r = subprocess.run(["node", ruler, "--file", src, "--out", js],
                       capture_output=True, timeout=600)
    doc = json.load(open(js, encoding="utf-8"))
    hits = [{"rule": h.get("rule"), "line": h.get("line"), "sink": h.get("sink")}
            for h in doc.get("hits", [])]
    return {"generation": gen, "ruler_blob": computed, "case": case,
            "source": CASES[case], "source_blob": sblob, "source_bytes": sbytes,
            "exit": r.returncode, "verdict": doc.get("verdict"),
            "hits": hits, "hits_n": len(hits),
            "attributed_in_fold_count": doc.get("attributed_in_fold_count"),
            "fold_without_anchor_count": doc.get("fold_without_anchor_count"),
            "fold_without_anchor": [{"line": f.get("line"), "rule": f.get("rule")}
                                    for f in doc.get("fold_without_anchor", [])]}


def main():
    rows = [run(g, c) for c in CASES for g in RULERS]
    by = {(r["generation"], r["case"]): r for r in rows}
    checks = {
        "r7b_flags_the_shipped_file": by[("r7b", "shipped_label_present")]["hits_n"] == 1,
        "r7b1_clears_the_shipped_file": by[("r7b1", "shipped_label_present")]["hits_n"] == 0
        and by[("r7b1", "shipped_label_present")]["attributed_in_fold_count"] == 1,
        "r7b1_still_red_without_the_label": by[("r7b1", "label_deleted_289_293")]["hits_n"] == 1
        and by[("r7b1", "label_deleted_289_293")]["fold_without_anchor_count"] >= 1,
        "r7b_also_red_without_the_label": by[("r7b", "label_deleted_289_293")]["hits_n"] >= 1,
        "both_generations_agree_on_the_label_deleted_case":
            by[("r7b", "label_deleted_289_293")]["hits_n"]
            == by[("r7b1", "label_deleted_289_293")]["hits_n"],
        "double_trigger_survives": by[("r7b1", "label_deleted_289_293")]["hits_n"] == 1
        and by[("r7b1", "shipped_label_present")]["hits_n"] == 0}
    out = {"subject": "counter-example for r7b1's spread anchor: recognition without the provenance "
                      "label must NOT clear the cell",
           "differ_only_by": "frontend/src/features/recovery/RecoveryRequiredPanel.tsx lines 289-293 "
                             "(the span holding t(\"recovery.serverReason\") / t(\"recovery.deviceReason\"))",
           "runs": rows, "checks": checks, "overall_pass": all(checks.values())}
    io_dump = os.path.join(WORK, "counterexample_nolabel_r7b1.json")
    open(io_dump, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out["checks"], ensure_ascii=False, indent=1))
    for r in rows:
        print(r["generation"], r["case"], "hits", r["hits_n"], "aif", r["attributed_in_fold_count"],
              "foa", r["fold_without_anchor_count"], [h["line"] for h in r["hits"]])
    print("overall_pass", out["overall_pass"])
    return 0 if out["overall_pass"] else 3


if __name__ == "__main__":
    sys.exit(main())
