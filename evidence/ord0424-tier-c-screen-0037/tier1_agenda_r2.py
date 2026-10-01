# -*- coding: utf-8 -*-
"""ORD-0424 follow-up r2 - the complete tier-1 population, taken out of the ruler itself.

Why a second pass: `--list-fallbacks` only prints the A and B bands, so the agenda I built from its
transcript was 86 rows and missed every tier-C hit - and tier C is exactly the band this order is about.
Reading a list the tool filtered for display is not the same as asking the tool for its own set, so this
driver imports the shipped ruler module and calls `scan_tree` + the same tier predicate
`render_tiers_finding` uses (`h[0] in A/B/C`, `h[6] == 1`), then groups the result by file.

The output is an agenda for a screen instrument: one row per proven render slot, with the literal the
ruler believes reaches the eye, so each one can be checked against what a real browser paints.
"""
import collections
import importlib.util
import io
import json
import os
import sys

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0424"
RULER = os.path.join(WORK, "cnx_copy_tiers_r2_extract.py")
TIP = "0c061d9eb74b21f0b0b297a068778479b08658b4"


def load_module():
    spec = importlib.util.spec_from_file_location("cnx_copy_tiers_r2", RULER)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    src = os.path.join(WORK, "exp_c2", "frontend", "src")
    data = os.path.join(WORK, "exp_c2", "data", "mock")
    mod = load_module()
    hits, pairs, files = mod.scan_tree(src, data)
    live = [h for h in hits if h[0] in ("A", "B", "C")]
    by_tier = collections.Counter(h[6] for h in live)
    t1 = [h for h in live if h[6] == 1]
    # (band, file, line, literal, why, shape, render_tier, slot)
    rows = [{"band": h[0], "file": os.path.relpath(h[1], os.path.join(WORK, "exp_c2")).replace(os.sep, "/"),
             "line": h[2], "literal": h[3], "why": h[4], "shape": h[5], "slot": h[7]} for h in t1]
    by_file = collections.Counter(r["file"] for r in rows)
    faces = []
    for f, n in sorted(by_file.items(), key=lambda kv: (-kv[1], kv[0])):
        faces.append({"file": f, "name": f.split("/")[-1], "tier1_rows": n,
                      "rows": [r for r in rows if r["file"] == f]})
    finding = mod.render_tiers_finding(src, data)
    out = {"tip": TIP,
           "ruler_bytes": os.path.getsize(RULER),
           "cmd": "import the shipped ruler module, call scan_tree(exp_c2/frontend/src, exp_c2/data/mock) "
                  "and keep the same predicate render_tiers_finding uses (band in A/B/C, h[6]==1)",
           "files_scanned": files, "live_hits": len(live),
           "render_tier_counts": {str(k): by_tier.get(k, 0) for k in (1, 2, 3)},
           "ruler_own_finding": finding[1],
           "previous_agenda_rows": 86,
           "why_the_previous_agenda_was_short": "`--list-fallbacks` iterates only bands A and B; the tier-C "
                                                "band is where the 403 rows live and some of them are "
                                                "render-tier 1, so the displayed list is not the set",
           "tier1_rows": len(rows), "tier1_files": len(faces), "faces": faces}
    io.open(os.path.join(WORK, "tier1_agenda_r2.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print("live %d | T1 %d | T2 %d | T3 %d | files %d" % (
        len(live), by_tier.get(1, 0), by_tier.get(2, 0), by_tier.get(3, 0), files))
    print("ruler says:", finding[1][:170])
    for f in faces[:16]:
        print("   %4d  %s" % (f["tier1_rows"], f["name"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
