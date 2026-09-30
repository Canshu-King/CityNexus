# -*- coding: utf-8 -*-
"""ORD-0536 r1 - generation reconciliation for the exposure ruler family.

Three rulers read ONE tree and this prints where their numbers agree:

  r7b   = the name the pre-landing door pins (preflight_and_land_r7.py:49), blob d3f66ce...
  r7b4  = the newest published name, blob cefcb38...
  r8    = ORD-0536's structured-exemption revision (this lane's new file)

Why the third column exists: the door's Q64 arm compares an ABSOLUTE cell count
(preflight_and_land_r7.py:384 builds `growth` from `exposure_counts`, which is a count per
(file, rule)).  A ruler generation that moves a cell from `hits` into `attributed_in_fold`
changes that count without printing a basis, so a candidate can be refused for a number that
shifted under it.  r8's `cells_total` is the pre-exemption denominator, which is the number that
must be stable for the comparison to mean anything.  This script measures the claim instead of
asserting it.

Read-only: every tree here is a `git archive` export the caller already cut.  Nothing is written
outside this work dir, the authoritative line is not touched, and no port is opened.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

LC = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
HERE = os.path.dirname(os.path.abspath(__file__))
NODE = "node"
ENV = dict(os.environ)
ENV.pop("HTTP_PROXY", None)
ENV.pop("HTTPS_PROXY", None)

RULERS = {
    "r7b": os.path.join(LC, "ui_exposure_taint_ast_r7b.cjs"),
    "r7b4": os.path.join(LC, "ui_exposure_taint_ast_r7b4.cjs"),
    "r8": os.path.join(HERE, "ui_exposure_taint_ast_r8.cjs"),
}


def blob_of(path):
    raw = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest(), len(raw)


def run(ruler_path, tree_src, out_path):
    p = subprocess.run([NODE, ruler_path, "--tree", tree_src, "--out", out_path],
                       capture_output=True, env=ENV, timeout=1800)
    if not os.path.isfile(out_path):
        raise RuntimeError("%s wrote no output (rc %s): %s" % (
            os.path.basename(ruler_path), p.returncode,
            p.stderr.decode("utf-8", "replace")[:300]))
    return json.load(io.open(out_path, encoding="utf-8"))


def partition(doc):
    """The four buckets a cell can land in, in the shape each generation reports them."""
    hits = doc.get("hits") or []
    folded = doc.get("attributed_in_fold") or []
    cex = doc.get("contract_exempted") or []
    foldless = doc.get("fold_without_anchor") or []
    red = [h for h in hits if h.get("rule") != "RULER_ERROR"]
    # r8 reports the whole set up front; the older generations only report what survived.
    cells_total = doc.get("cells_total")
    pre = cells_total if doc.get("cells") and cells_total else len(red) + len(folded) + len(cex)
    return {"red": len(red), "folded": len(folded), "contract_exempted": len(cex),
            "fold_without_anchor": len(foldless), "pre_exemption_cells": pre,
            "cells_total_field": cells_total,
            "red_keys": sorted({"%s|%s|%s" % (h.get("file", "").split("/")[-1], h.get("line"), h.get("rule"))
                                for h in red}),
            "exempt_keys": sorted({"%s|%s|%s" % (f.get("file", "").split("/")[-1],
                                                 f.get("file_line") or f.get("line"),
                                                 f.get("rule"))
                                   for f in list(folded) + list(cex)})}


def main():
    trees = json.load(io.open(sys.argv[1], encoding="utf-8"))
    out = {"rulers": {}, "trees": {}, "method": "each ruler runs `--tree` over the same export dir once"}
    for name, path in RULERS.items():
        blob, size = blob_of(path)
        out["rulers"][name] = {"path": path, "blob": blob, "bytes": size}
    for entry in trees:
        label, src, rev = entry["label"], entry["tree"], entry.get("rev", "")
        row = {"export_tree": src, "rev": rev, "note": entry.get("note", "")}
        for name, path in RULERS.items():
            doc = run(path, src, os.path.join(HERE, "rec_%s_%s.json" % (name, label)))
            row[name] = partition(doc)
            if name == "r8":
                row["r8_verdict"] = doc.get("verdict")
                row["r8_ledger"] = [{"rule": e["rule"], "file": e["file"], "line": e["line"],
                                     "exemption_id": e["exemption_id"], "evidence": e["evidence"],
                                     "basis": e["basis"],
                                     "measured_on_tree": e["measured_on_tree"]}
                                    for e in doc.get("exemption_ledger") or []]
                row["r8_table"] = doc.get("exemption_table")
                row["r8_red_detail"] = [{"cell": "%s:%s" % (c["file"].split("/")[-1], c["line"]),
                                         "rule": c["rule"], "red_because": c["red_because"]}
                                        for c in doc.get("cells") or [] if c["verdict"] == "RED"]
        stable = set(row[n]["pre_exemption_cells"] for n in RULERS)
        row["pre_exemption_denominator_stable_across_generations"] = (len(stable) == 1)
        row["red_set_identical_r7b_vs_r8"] = (row["r7b"]["red_keys"] == row["r8"]["red_keys"])
        row["red_diff_r7b_minus_r8"] = sorted(set(row["r7b"]["red_keys"]) - set(row["r8"]["red_keys"]))
        row["red_diff_r8_minus_r7b"] = sorted(set(row["r8"]["red_keys"]) - set(row["r7b"]["red_keys"]))
        out["trees"][label] = row
        sys.stderr.write("%s: r7b red %s / r7b4 red %s / r8 red %s, pre-exemption %s (stable=%s)\n" % (
            label, row["r7b"]["red"], row["r7b4"]["red"], row["r8"]["red"],
            sorted(stable), row["pre_exemption_denominator_stable_across_generations"]))
    io.open(os.path.join(HERE, "generation_reconciliation_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
