"""Leg six summary: flatten the figures this lane cites, each one appearing exactly once.

Why this file exists: a published receipt must never be rewritten, so the block cannot point at a line
for a value that occurs several times in it (`body_chars`, `h1_count`, `cmdr_shape_hits` each repeat per
case). Here every cited figure is derived from the receipts, written once, and the block anchors to the
line in THIS file. Nothing is measured in here -- it only re-reads `trash_reach_*.json` and
`trash_existence_readout_r2.json` and does arithmetic on their fields.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

READOUTS = pathlib.Path("D:/moodle/_qoder_newlane_ord0496/review/ord0556/readouts")
REACH = READOUTS / "trash_reach_20261005T174830Z.json"
EXIST = READOUTS / "trash_existence_readout_r2.json"
OUT = READOUTS / "trash_leg6_figures_r1.json"

d = json.loads(REACH.read_text(encoding="utf-8"))
x = json.loads(EXIST.read_text(encoding="utf-8"))
cases = {f"{c['route']}|{c['locale']}": c for c in d["cases"]}
te, tz, bk = cases["/v8/trash|en"], cases["/v8/trash|zh"], cases["/v8/bookings|en"]
live, old, lane = x["tips"]["live_tip"], x["tips"]["older_sweep_base"], x["tips"]["lane_branch_tip"]
cmp_ = x["sweep_vs_live_tip"]
cnt = d["counts"]

fig = {
    "cases_attempted": cnt["cases_attempted"],
    "cases_aborted": cnt["cases_aborted"],
    "trash_reads_no_heading": cnt["trash_without_heading"],
    "trash_reads_panel_mounted": cnt["trash_panel_mounted"],
    "page_errors_total": cnt["page_errors_total"],
    "trash_en_body_chars": te["body_chars"],
    "trash_zh_body_chars": tz["body_chars"],
    "trash_en_heading_nodes": te["h1_count"] + te["h2_count"],
    "trash_zh_heading_nodes": tz["h1_count"] + tz["h2_count"],
    "bookings_h1": bk["h1_count"],
    "bookings_h2": bk["h2_count"],
    "bookings_heading_nodes": bk["h1_count"] + bk["h2_count"],
    "bookings_body_chars": bk["body_chars"],
    "trash_en_shape_hits": len(te["cmdr_shape_hits"]),
    "trash_zh_shape_hits": len(tz["cmdr_shape_hits"]),
    "bookings_shape_hits": len(bk["cmdr_shape_hits"]),
    "bookings_hits_transform_none": len([h for h in bk["cmdr_shape_hits"] if h["transform"] == "none"]),
    "bookings_kickers_transform_uppercase": len([k for k in bk["kicker_style"] if k["transformed"] == "uppercase"]),
    "trash_en_kicker_node_text": te["kicker_style"][0]["node_text"],
    "trash_zh_kicker_node_text": tz["kicker_style"][0]["node_text"],
    "backend_port": d["generation"]["backend_port"],
    "frontend_port": d["generation"]["frontend_port"],
    "canary_untouched": d["teardown"]["canary_source_untouched"],
    "live_tip_paths": live["paths_total"],
    "live_tip_trash_named_paths": live["trash_named_paths"],
    "live_tip_route_keys": live["route_keys_count"],
    "live_tip_trash_is_route": live["trash_is_a_route"],
    "sweepbase_paths": old["paths_total"],
    "sweepbase_trash_named_paths": old["trash_named_paths"],
    "sweepbase_route_keys": old["route_keys_count"],
    "sweepbase_trash_is_route": old["trash_is_a_route"],
    "lane_tree_paths": lane["paths_total"],
    "lane_tree_trash_named_paths": lane["trash_named_paths"],
    "route_keys_only_on_lane": len(x["route_key_sets"]["only_on_lane_tree"]),
    "route_keys_only_on_live_tip": len(x["route_key_sets"]["only_on_live_tip"]),
    "sweep_routes_in_file": cmp_["routes_in_sweep_file"],
    "live_tip_routes_equal_sweep": cmp_["sets_equal"],
    "blob_live_v8Routes": live["v8Routes_blob"],
    "blob_sweepbase_v8Routes": old["v8Routes_blob"],
    "reach_run": d["generation"]["run"],
    "reach_tree_head": d["generation"]["tree_head"],
}
doc = {"derived_from": {"screen_reading": REACH.name,
                        "screen_reading_sha256": hashlib.sha256(REACH.read_bytes()).hexdigest(),
                        "existence": EXIST.name,
                        "existence_sha256": hashlib.sha256(EXIST.read_bytes()).hexdigest()},
       "note": "no new measurement here: arithmetic over the two named receipts only",
       "figures": fig}
OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
for k, v in fig.items():
    print(f"{k}={v}")
