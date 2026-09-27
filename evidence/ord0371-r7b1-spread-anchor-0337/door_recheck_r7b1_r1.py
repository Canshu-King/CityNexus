#!/usr/bin/env python3
"""ORD-0371 follow-up (taint ruler): re-run the COMMANDER'S OWN door comparison with both generations.

The door (`preflight_and_land_r3.py:118-151` + `:320-357`) refuses a candidate that GROWS the Q64 cell
set over the tip.  Its acceptance for my ruler fix is written in that door's units ("that handle gone,
cand_cells still <= 10"), so this tool reproduces the door's arithmetic verbatim - `git archive` of
frontend/src into its own scratch dir, `--tree`, cell key (basename, line, rule), count-per-(file,rule)
growth, `pair_added` - and only swaps the ruler file.  Nothing here edits a ruler, a product file or the
door; the door's own constants are re-implemented line-for-line and then compared against its receipt.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0371"
RULERS = {"r7b": ("ui_exposure_taint_ast_r7b.cjs", "d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2"),
          "r7b1": ("ui_exposure_taint_ast_r7b1.cjs", "b6716d9a3c67dafc72fef501bfaff101c84e918a")}
REVS = [("tip_before_landing", "04071b8258ebcdcf1e9e4c9714fb516283d1e1ad"),
        ("candidate_25396236063f", "25396236063f13827312c33960be0b9510845fc3"),
        ("landed_090c048f", "090c048f220a3089506f565929ceda1511315a09")]
CAND_FILES = ["v12Authoritative.ts", "PlanWithAiSheet.tsx", "RecoveryRequiredPanel.tsx",
              "simulationAdapter.ts", "SortableActivityList.tsx", "V12TripStudioPanel.tsx",
              "LocaleContext.tsx", "styles.css"]
NAMED = "RecoveryRequiredPanel.tsx:298|UPSTREAM_TEXT_VIA_HELPER_TO_DOM"
CELL = "RecoveryRequiredPanel.tsx|UPSTREAM_TEXT_VIA_HELPER_TO_DOM"


def cell_key(cell):
    """door :85-88 verbatim - takes an already-built "File.tsx:104|RULE" key and strips the line."""
    m = re.match(r"^(.+):(\d+)\|(.+)$", cell)
    return "%s|%s" % (m.group(1), m.group(3)) if m else cell


def exposure_counts(cells):
    """door :107-115 verbatim."""
    out = {}
    for key in cells:
        m = re.match(r"^(.+):(\d+)\|(.+)$", key)
        k = "%s|%s" % (m.group(1), m.group(3)) if m else key
        out[k] = out.get(k, 0) + 1
    return out


def pair_added(added, removed):
    """door :91-104 verbatim."""
    pool = {}
    for c in removed:
        pool.setdefault(cell_key(c), []).append(c)
    out = []
    for c in sorted(added, key=cell_key):
        if pool.get(cell_key(c)):
            pool[cell_key(c)].pop()
        else:
            out.append(c)
    return out


def run_ruler(gen, rev, sub):
    out = os.path.join(WORK, sub)
    if os.path.isdir(out):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", out.replace("/", "\\")], timeout=600)
    os.makedirs(out, exist_ok=True)
    p = subprocess.run("git -C %s archive %s frontend/src | tar -x -C %s" % (REPO, rev, out),
                       shell=True, capture_output=True, timeout=900)
    assert not p.returncode, p.stderr.decode("utf-8", "replace")[:300]
    fname, declared = RULERS[gen]
    ruler = os.path.join(LIVE, fname)
    raw = open(ruler, "rb").read()
    computed = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
    assert computed == declared, ("ruler identity drift", gen, computed, declared)
    js = os.path.join(out, "ruler.json")
    r = subprocess.run(["node", ruler, "--tree", os.path.join(out, "frontend", "src"), "--out", js],
                       capture_output=True, timeout=1800)
    assert r.returncode == 0 or os.path.isfile(js), r.stderr.decode("utf-8", "replace")[:300]
    doc = json.load(io.open(js, encoding="utf-8"))
    cells = {"%s:%s|%s" % (h["file"].split("/")[-1], h["line"], h.get("rule"))
             for h in doc.get("hits", [])}
    res = {"generation": gen, "ruler_blob": computed, "rev": rev,
           "files_found": doc.get("files_found"), "modules_in_graph": doc.get("modules_in_graph"),
           "parse_diagnostics_total": doc.get("parse_diagnostics_total"),
           "resolution_truncated_total": doc.get("resolution_truncated_total"),
           "unresolved_import_count": doc.get("unresolved_import_count"),
           "cells_total": len(cells), "cells": sorted(cells),
           "attributed_in_fold_count": doc.get("attributed_in_fold_count"),
           "fold_without_anchor_count": doc.get("fold_without_anchor_count"),
           "named_cell_counts": exposure_counts(cells).get(CELL, 0),
           "candidate_files_with_cells": sorted({c.split(":")[0] for c in cells
                                                 if c.split(":")[0] in CAND_FILES})}
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", out.replace("/", "\\")], timeout=600)
    return res


def main():
    runs, door_view = {}, {}
    for gen in RULERS:
        for name, rev in REVS:
            runs["%s|%s" % (gen, name)] = run_ruler(gen, rev, "door_%s_%s" % (gen, name))
    for gen in RULERS:
        tip = set(runs["%s|tip_before_landing" % gen]["cells"])
        cand = set(runs["%s|candidate_25396236063f" % gen]["cells"])
        added, removed = sorted(cand - tip), sorted(tip - cand)
        ct, cc = exposure_counts(tip), exposure_counts(cand)
        growth = {k: cc[k] - ct.get(k, 0) for k in cc if cc[k] > ct.get(k, 0)}
        unpaired = pair_added(added, removed)
        door_view[gen] = {"tip_cells": len(tip), "cand_cells": len(cand),
                          "growth_by_file_and_rule": growth, "unpaired_added": unpaired,
                          "added_line_exact": added, "removed_count": len(removed),
                          "named_handle_present": NAMED in cand,
                          "gate_would": "REFUSE" if (growth or unpaired) else "PASS",
                          "landed_090c048f_cells": runs["%s|landed_090c048f" % gen]["cells_total"]}
    # Self-check: my re-implementation of the door's arithmetic is only usable as a like-for-like
    # reading if it reproduces the door's OWN published receipt field for field.  The receipt under test
    # is the REFUSED preflight this whole order came out of, so r7b's numbers are on the record.
    ref = json.load(open(os.path.join(LIVE, "land_ord0369r3.json"), encoding="utf-8"))["gate_run"]["exposure"]
    mine = door_view["r7b"]
    agree = {}
    for k in ("tip_cells", "cand_cells", "removed_count"):
        agree[k] = {"mine": mine[k], "door_receipt": ref[k], "equal": mine[k] == ref[k]}
    agree["growth_by_file_and_rule"] = {"mine": mine["growth_by_file_and_rule"],
                                        "door_receipt": ref["growth_by_file_and_rule"],
                                        "equal": mine["growth_by_file_and_rule"]
                                        == ref["growth_by_file_and_rule"]}
    agree["unpaired_added"] = {"mine": mine["unpaired_added"], "door_receipt": ref["unpaired_added"],
                               "equal": mine["unpaired_added"] == ref["unpaired_added"]}
    agree["ruler_blob"] = {"mine": RULERS["r7b"][1], "door_receipt": ref["ruler_blob"],
                           "equal": RULERS["r7b"][1] == ref["ruler_blob"]}
    report = {"rulers": {g: {"file": RULERS[g][0], "blob": RULERS[g][1],
                             "bytes": os.path.getsize(os.path.join(LIVE, RULERS[g][0]))}
                         for g in RULERS},
              "candidate_files_in_view": len(CAND_FILES), "door_view": door_view, "runs": runs,
              "door_arithmetic_reproduces_receipt": agree,
              "all_fields_agree": all(v["equal"] for v in agree.values()),
              "r7b_receipt_under_test": "evidence/cmdr-landing-ORD-0369r3-0300/"
                                        "preflight_REFUSED_exposure_r1.json "
                                        "7d81a39bc11a101333e664b7e737d23fbc7d4cfa"}
    io.open(os.path.join(WORK, "door_recheck_r7b1_r1.json"), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(door_view, ensure_ascii=False, indent=1))
    for k, v in runs.items():
        print(k, "cells", v["cells_total"], "aif", v["attributed_in_fold_count"],
              "foa", v["fold_without_anchor_count"], "trunc", v["resolution_truncated_total"],
              "named", v["named_cell_counts"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
