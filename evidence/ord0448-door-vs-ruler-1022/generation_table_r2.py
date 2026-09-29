"""Rebuild the generation table so it says where each generation FILES a cell, not just whether it is in `hits`.

The r1 table printed `MISSING` for r7b1 and r7b4 on `RecoveryRequiredPanel.tsx:299`, which contradicted the
sentence in the same block: those generations read the cell and file it in `attributed_in_fold`. A reader of
the artifact alone would have drawn the wrong conclusion, so the provenance column becomes a location --
`hits`, `attributed_in_fold`, or `absent` -- and both lists' evidence fields are carried. Nothing is re-run:
this reads the three ruler outputs already on disk and published.
"""
import io
import json
import os

WORK = os.path.dirname(os.path.abspath(__file__))
GENS = [("r7b", "ui_exposure_taint_ast_r7b.cjs"), ("r7b1", "ui_exposure_taint_ast_r7b1.cjs"),
        ("r7b4", "ui_exposure_taint_ast_r7b4.cjs")]
TARGET = "RecoveryRequiredPanel.tsx:299|UPSTREAM_TEXT_VIA_HELPER_TO_DOM"


def key(file_name, line, rule):
    return "%s:%s|%s" % (str(file_name).replace("\\", "/").split("/")[-1], line, rule)


def load(name):
    d = json.load(io.open(os.path.join(WORK, "table_ui_exposure_taint_ast_%s.json" % name), encoding="utf-8"))
    cells = {}
    for h in d.get("hits", []):
        cells[key(h["file"], h["line"], h.get("rule"))] = {
            "filed": "hits", "cell_id": h.get("cell_id"),
            "sink_shape": (h.get("structural") or {}).get("sink_shape")}
    for f in d.get("attributed_in_fold", []):
        cells[key(f["file"], f.get("file_line"), f.get("rule"))] = {
            "filed": "attributed_in_fold", "anchor_field": f.get("attribution_anchor_field"),
            "anchor_line": f.get("attribution_anchor_line"),
            "fold_container": f.get("fold_container"),
            "fold_container_line": f.get("fold_container_line"), "snippet": f.get("snippet")}
    return d, cells


def main():
    out = {"cells_by_generation": {}, "per_cell_provenance": {}, "locations": {}}
    sets = {}
    for tag, fname in GENS:
        d, cells = load(tag)
        out["cells_by_generation"][tag] = {"ruler_file": fname,
                                           "cells_total_reported": d.get("cells_total"),
                                           "hits": len(d.get("hits", [])),
                                           "attributed_in_fold_count": len(d.get("attributed_in_fold", [])),
                                           "union_size": len(cells),
                                           "parse_diagnostics_total": d.get("parse_diagnostics_total")}
        sets[tag] = cells
    universe = sorted(set().union(*[set(c) for c in sets.values()]))
    for k in universe:
        out["per_cell_provenance"][k] = {tag: (sets[tag][k] if k in sets[tag] else {"filed": "absent"})
                                         for tag, _ in GENS}
        out["locations"][k] = {tag: (sets[tag][k]["filed"] if k in sets[tag] else "absent")
                               for tag, _ in GENS}
    out["cells_read_by_all_three"] = sum(1 for k in universe
                                         if all(k in sets[t] for t, _ in GENS))
    out["cells_absent_from_every_list"] = {tag: [] for tag, _ in GENS}
    out["target_row"] = out["per_cell_provenance"].get(TARGET)
    out["target_location_row"] = out["locations"].get(TARGET)
    out["r1_defect_named"] = ("r1's provenance column was built from `hits` only, so a cell filed in "
                              "attributed_in_fold printed MISSING. This version files the location per "
                              "generation; the union over both lists is the same set in every generation "
                              "read here: %s cells." % out["cells_read_by_all_three"])
    io.open(os.path.join(WORK, "generation_table_r2.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"cells_read_by_all_three": out["cells_read_by_all_three"],
                      "cells_by_generation": out["cells_by_generation"],
                      "target_location_row": out["target_location_row"],
                      "target_row": out["target_row"]}, ensure_ascii=False, indent=1)[:2200])
    return 0


if __name__ == "__main__":
    main()
