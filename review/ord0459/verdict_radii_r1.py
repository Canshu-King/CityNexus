"""ORD-0459 verdict table -- derive each element's outcome from the two instruments, no sentences.

Inputs, all measured on the same generation (the live tip as the before arm, this branch as the
after arm):
  radii_diff_join_r2.json  -- per element: computed radius on both arms, its own crop's cross-arm
                              pixel count and its own same-arm floor
  paint_before.json / paint_after.json -- per element: whether its corner can paint at all
                              (fill, border, shadow or background-image), measured on both arms

Verdicts are computed, never typed:
  MOVED               radius changed, corner can paint, crop moved past its own floor
  NOT_PAINTABLE       radius changed, corner measured to have no fill, no border, no shadow, no image
  NO_PIXEL_DELTA      radius changed, corner can paint, crop did not move past its own floor
  UNCHANGED           computed radius identical on both arms
Any element that cannot be matched between the two arms is reported as IDENTITY_UNMATCHED with its
rect, because a silent drop would shrink the denominator without saying so.
"""
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path("D:/moodle/_qoder_q_ord0448_20260929")
LADDER = {"0px", "4px", "8px", "12px", "16px", "20px", "24px", "50%", "999px"}

join = json.loads((ROOT / "radii_diff_join_r2.json").read_text(encoding="utf-8"))
paint = {}
for arm in ("before", "after"):
    d = json.loads((ROOT / ("paint_%s.json" % arm)).read_text(encoding="utf-8"))
    paint[arm] = d["elements"]


def key(e):
    return (e["tag"], e["cls"], tuple(e["rect"]))


pb = {key(e): e for e in paint["before"]}
pa = {key(e): e for e in paint["after"]}
print("screen on both paint runs: before %s / after %s" % (
    json.dumps(json.loads((ROOT / "paint_before.json").read_text(encoding="utf-8"))["screen"], ensure_ascii=False),
    json.dumps(json.loads((ROOT / "paint_after.json").read_text(encoding="utf-8"))["screen"], ensure_ascii=False)))
print("elements matched between the joiner and the paint instrument: before %d after %d" % (len(pb), len(pa)))

rows, counts = [], {}
for r in join["elements"]:
    k = (r["tag"], r["class"], tuple(r["rect"]))
    src = pa.get(k) or pb.get(k)
    matched = src is not None
    can = src["corner_can_paint"] if matched else None
    if not matched:
        v = "IDENTITY_UNMATCHED"
    elif not r["radius_changed"]:
        v = "UNCHANGED"
    elif r["radius_changed"] and not can:
        v = "NOT_PAINTABLE"
    elif r["painted_moved"]:
        v = "MOVED"
    else:
        v = "NO_PIXEL_DELTA"
    counts[v] = counts.get(v, 0) + 1
    rows.append({**r, "corner_can_paint": can, "background_color": (src or {}).get("background_color"),
                 "has_border": (src or {}).get("has_border"), "box_shadow": (src or {}).get("box_shadow"),
                 "off_table_before": r["radius_before"] not in LADDER,
                 "off_table_after": r["radius_after"] not in LADDER, "verdict": v})

print("=== verdict counts over the %d sampled elements ===" % len(rows))
for v in sorted(counts):
    print("   %-18s %d" % (v, counts[v]))

print("=== the affected element set, named ===")
print("   %-18s %-9s %-30s %-22s %-14s %-8s %-8s %s" % ("verdict", "tag", "class", "testid", "radius", "floor", "cross", "off-table"))
for r in sorted(rows, key=lambda x: (x["verdict"], x["rect"][1], x["rect"][0])):
    if r["verdict"] == "UNCHANGED":
        continue
    print("   %-18s %-9s %-30s %-22s %-14s %-8s %-8s before=%s after=%s" % (
        r["verdict"], r["tag"], r["class"][:30], (r["testid"] or "-")[:22],
        r["radius_before"] + "->" + r["radius_after"], r["own_floor_px"], r["cross_arm_px"],
        r["off_table_before"], r["off_table_after"]))

off_b = sum(1 for r in rows if r["off_table_before"])
off_a = sum(1 for r in rows if r["off_table_after"])
print("=== acceptance, computed ===")
print("   sampled elements: %d" % len(rows))
print("   elements whose computed radius was off the table, before arm: %d" % off_b)
print("   elements whose computed radius is off the table, after arm: %d" % off_a)
print("   cells that name the commander's two offending tiers explicitly, before arm: 9px=%d 10px=%d" % (
    sum(1 for r in rows if r["radius_before"] == "9px"), sum(1 for r in rows if r["radius_before"] == "10px")))
print("   after arm: 9px=%d 10px=%d" % (
    sum(1 for r in rows if r["radius_after"] == "9px"), sum(1 for r in rows if r["radius_after"] == "10px")))
print("   radius changed: %d ; of which MOVED=%d NOT_PAINTABLE=%d NO_PIXEL_DELTA=%d" % (
    sum(1 for r in rows if r["radius_changed"]), counts.get("MOVED", 0),
    counts.get("NOT_PAINTABLE", 0), counts.get("NO_PIXEL_DELTA", 0)))

out = {"ladder": sorted(LADDER), "verdict_counts": counts, "off_table_before": off_b,
       "off_table_after": off_a, "sampled": len(rows), "elements": rows,
       "inputs": {"join": "radii_diff_join_r2.json", "paint_before": "paint_before.json",
                  "paint_after": "paint_after.json"}}
(ROOT / "radii_verdict_r1.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                                            encoding="utf-8", newline="\n")
print("wrote radii_verdict_r1.json")
