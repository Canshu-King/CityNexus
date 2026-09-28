"""ORD-0417 snap census: fold the two generations' receipts into one A/B pair, derived from rows.

Publishing this instead of a hand-written summary: the pair a reader needs is
  tip bundle   -- the cell exists, one client rect, name painted  (8/8 shape x arm runs)
  control      -- only the cell was cut, same dictionary value, cell absent, name not painted (0/8)
and both halves must come out of the same artifact set so no arm borrows another's witness.

What the control was, exactly: `frontend/src/components/v8/MapPanel.tsx` re-archived from the tip, the
five lines of the `{selectedPoint && (<span className="v8-map-selected-stop">…)}` block deleted, the
rest of the file untouched (`git hash-object` of the restored file equals the tip blob after the run).
Nothing else in the snap differed, which is why `idle` band and caption heights match to the pixel --
that equality is asserted below rather than claimed.
"""
import json
import sys

DIR = sys.argv[1]
out = {"generated_from": [f"{DIR}/SNAP_{l}_{a}.census.json" for l in ("TIP", "CTRL") for a in ("zh", "en")]}

rows = {}
for label in ("TIP", "CTRL"):
    for arm in ("zh", "en"):
        d = json.load(open(f"{DIR}/SNAP_{label}_{arm}.census.json", encoding="utf-8"))
        for r in d["results"]:
            rows[(label, arm, r["shape"])] = r

shapes = sorted({k[2] for k in rows})
pair = []
for shape in shapes:
    for arm in ("zh", "en"):
        t, c = rows[("TIP", arm, shape)], rows[("CTRL", arm, shape)]
        pair.append({
            "shape": shape,
            "arm": arm,
            "tip_cell_present": t["cell_box_px"] is not None,
            "ctrl_cell_present": c["cell_box_px"] is not None,
            "tip_name_painted_on_glass": t["name_painted_on_glass"],
            "ctrl_name_painted_on_glass": c["name_painted_on_glass"],
            "tip_cell_text": t["cell_text"],
            "ctrl_cell_text": c["cell_text"],
            "tip_cell_box_px": t["cell_box_px"],
            "tip_cell_client_rect_count": len(t["cell_client_rects"] or []),
            "tip_cell_client_rects": t["cell_client_rects"],
            "caption_height_idle_px_both": [t["caption_height_idle_px"], c["caption_height_idle_px"]],
            "band_height_idle_px_both": [t["band_height_idle_px"], c["band_height_idle_px"]],
            "tip_band_growth_px": t["band_growth_px"],
            "ctrl_band_growth_px": c["band_growth_px"],
            "tip_controls": [t["controls_idle"], t["controls_with_selection"]],
            "ctrl_controls": [c["controls_idle"], c["controls_with_selection"]],
            "tip_lost_reachable": t["lost_reachable"],
            "ctrl_lost_reachable": c["lost_reachable"],
            "tip_covered_px2": sum(p["px2"] for p in t["newly_covered_pins"]),
            "ctrl_covered_px2": sum(p["px2"] for p in c["newly_covered_pins"]),
        })

out["pair"] = pair
idle_tip = {(p["shape"], p["arm"]): p["band_height_idle_px_both"][0] for p in pair}
idle_ctrl = {(p["shape"], p["arm"]): p["band_height_idle_px_both"][1] for p in pair}
out["derived"] = {
    "shape_arm_runs": len(pair),
    "tip_cell_present": f'{sum(1 for p in pair if p["tip_cell_present"])}/{len(pair)}',
    "ctrl_cell_present": f'{sum(1 for p in pair if p["ctrl_cell_present"])}/{len(pair)}',
    "tip_name_painted": f'{sum(1 for p in pair if p["tip_name_painted_on_glass"])}/{len(pair)}',
    "ctrl_name_painted": f'{sum(1 for p in pair if p["ctrl_name_painted_on_glass"])}/{len(pair)}',
    "idle_geometry_identical_between_generations": idle_tip == idle_ctrl,
    "caption_idle_identical": all(p["caption_height_idle_px_both"][0] == p["caption_height_idle_px_both"][1]
                                  for p in pair),
    "arms_where_tip_grew_band": [f'{p["arm"]} {p["shape"]} {p["tip_band_growth_px"]} px'
                                 for p in pair if (p["tip_band_growth_px"] or 0) > 0],
    "arms_where_control_grew_band": [f'{p["arm"]} {p["shape"]} {p["ctrl_band_growth_px"]} px'
                                     for p in pair if (p["ctrl_band_growth_px"] or 0) > 0],
    "reachable_lost_any_generation": sum(len(p["tip_lost_reachable"]) + len(p["ctrl_lost_reachable"])
                                         for p in pair),
    "control_added_no_control": all(p["tip_controls"][0] == p["ctrl_controls"][0] for p in pair),
    "max_tip_cell_client_rect_count": max(p["tip_cell_client_rect_count"] for p in pair),
    "coverage_delta_px2": {f'{p["arm"]} {p["shape"]}': p["tip_covered_px2"] - p["ctrl_covered_px2"]
                           for p in pair},
}
# CJK in `cell_text` must not cross a Windows console pipe (GBK eats it), so this writes its own file.
payload = json.dumps(out, indent=1, ensure_ascii=False)
dst = sys.argv[2] if len(sys.argv) > 2 else ""
if dst:
    open(dst, "w", encoding="utf-8", newline=chr(10)).write(payload)
    print(f"wrote {dst}")
else:
    print(payload)
