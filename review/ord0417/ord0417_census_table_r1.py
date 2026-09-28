"""ORD-0417: fold the four r2 census receipts into one table, and derive the verdict FROM the rows.

The duty order asks for two dimensions per shape -- the element box and `Range.getClientRects()` --
because wrapping is only observable in the second one.  This script does not restate any number by
hand: every cell is read out of the census JSONs, and the conclusion is computed from them
(`verdict` is derived, not authored).
"""
import json
import sys

DIR = sys.argv[1] if len(sys.argv) > 1 else "."
ARMS = ["zh", "en"]
LABELS = ["SNAP_TIP", "SNAP_CTRL"]
SAFETY_GAP_PX = 16

rows = []
for label in LABELS:
    for arm in ARMS:
        d = json.load(open(f"{DIR}/{label}_{arm}.census.json", encoding="utf-8"))
        for r in d["results"]:
            rows.append({
                "label": label, "arm": arm, "shape": r["shape"],
                "pins": r["entry"]["pins"],
                "name_on_glass": r["name_painted_on_glass"],
                "band_px": [r["band_height_idle_px"], r["band_height_with_selection_px"]],
                "grew_px": r["band_growth_px"],
                "caption_px": [r["caption_height_idle_px"], r["caption_height_with_selection_px"]],
                "cell_box_px": r["cell_box_px"],
                "cell_client_rects": r["cell_client_rects"],
                "cell_lines": r["cell_line_count"],
                "controls": [r["controls_idle"], r["controls_with_selection"]],
                "reach": [r["reachable_idle"], r["reachable_with_selection"]],
                "lost": r["lost_reachable"],
                "unhittable": r["newly_unhittable_pins"],
                "below_floor": r["pins_below_floor"],
                "covered_px2_total": sum(p["px2"] for p in r["newly_covered_pins"]),
                "covered_pins": [f'{p["painted"]}:{p["px2"]} px2' for p in r["newly_covered_pins"]],
                "cell_text": r["cell_text"],
                "fatal": r.get("fatal"),
            })

hdr = ("label", "arm", "shape", "name", "band_px", "grew_px", "caption_px", "cell_box_px",
       "cell_rects", "cell_lines", "ctl", "reach", "lost", "unhitt", "below", "covered_px2_total")
print("| " + " | ".join(hdr) + " |")
print("|" + "|".join(["---"] * len(hdr)) + "|")
for r in rows:
    print("| " + " | ".join(str(v) for v in (
        r["label"], r["arm"], r["shape"], str(r["name_on_glass"]), f'{r["band_px"][0]}->{r["band_px"][1]}',
        r["grew_px"], f'{r["caption_px"][0]}->{r["caption_px"][1]}', r["cell_box_px"],
        len(r["cell_client_rects"] or []), r["cell_lines"], f'{r["controls"][0]}->{r["controls"][1]}',
        f'{r["reach"][0]}->{r["reach"][1]}', len(r["lost"]), len(r["unhittable"]),
        len(r["below_floor"]), r["covered_px2_total"])) + " |")

tip = [r for r in rows if r["label"] == "SNAP_TIP"]
ctrl = [r for r in rows if r["label"] == "SNAP_CTRL"]
verdict = {
    "rows_read": len(rows),
    "fatal_rows": [r["shape"] for r in rows if r["fatal"]],
    "tip_name_painted": f"{sum(1 for r in tip if r['name_on_glass'])}/{len(tip)}",
    "ctrl_name_painted": f"{sum(1 for r in ctrl if r['name_on_glass'])}/{len(ctrl)}",
    "tip_grew_over_gap": [f'{r["arm"]} {r["shape"]} {r["grew_px"]} px'
                          for r in tip if (r["grew_px"] or 0) > SAFETY_GAP_PX],
    "tip_grew_within_gap": [f'{r["arm"]} {r["shape"]} {r["grew_px"]} px'
                            for r in tip if 0 < (r["grew_px"] or 0) <= SAFETY_GAP_PX],
    "tip_grew_zero": sum(1 for r in tip if (r["grew_px"] or 0) == 0),
    "ctrl_grew_zero": sum(1 for r in ctrl if (r["grew_px"] or 0) == 0),
    "tip_lost_any": sum(len(r["lost"]) for r in tip),
    "ctrl_lost_any": sum(len(r["lost"]) for r in ctrl),
    "tip_unhittable_any": sum(len(r["unhittable"]) for r in tip),
    "tip_below_floor_any": sum(len(r["below_floor"]) for r in tip),
    "tip_cell_lines_max": max((r["cell_lines"] or 0) for r in tip),
    "tip_cell_rects_gt_1": [f'{r["arm"]} {r["shape"]}' for r in tip
                            if len(r["cell_client_rects"] or []) > 1],
    "caption_grew_only_where_cell_present": all(
        (r["caption_px"][0] == r["caption_px"][1]) for r in ctrl),
    "coverage_delta_px2": {
        f'{t["arm"]} {t["shape"]}': t["covered_px2_total"] - c["covered_px2_total"]
        for t in tip for c in ctrl if (t["arm"], t["shape"]) == (c["arm"], c["shape"])},
    "per_row_covered_pins_tip": {f'{t["arm"]} {t["shape"]}': t["covered_pins"] for t in tip},
    "per_row_covered_pins_control": {f'{c["arm"]} {c["shape"]}': c["covered_pins"] for c in ctrl},
    "control_band_and_caption_identical_to_tip_idle": sorted(
        (r["arm"], r["shape"], tuple(r["band_px"][:1]), tuple(r["caption_px"][:1])) for r in ctrl
    ) == sorted((r["arm"], r["shape"], tuple(r["band_px"][:1]), tuple(r["caption_px"][:1])) for r in tip),
}
print(json.dumps(verdict, indent=1, ensure_ascii=False))
