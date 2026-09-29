"""ORD-0459 joiner v2 -- the affected element set, named, with a per-element noise floor.

v1 of this joiner diffed whole frames and was judged by a single global floor. That floor came from
the before arm's own two passes, and because the map tiles were still arriving between them it read
21,772 changed pixels -- bigger than the corner work it was supposed to expose, so only 4 of 19
changed elements could be attributed. This version fixes the attribution instead of relaxing the bar:

  * the floor is now PER ELEMENT -- the same crop of the same element, before arm against itself --
    so tile churn under one card can never out-shout that card's own corners;
  * crops come from the full-document frame, so elements below the 844 px fold are measured, not
    quietly dropped;
  * a corner counts as MOVED only when its own crop moves past its own floor;
  * the ladder membership of every on-screen radius is recomputed from the tallies, so "no off-table
    value" is a derived verdict with a denominator, not a sentence.
"""
import json
import pathlib
import sys

from PIL import Image, ImageChops

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path("D:/moodle/_qoder_q_ord0448_20260929")
PREFIX = sys.argv[1] if len(sys.argv) > 1 else "shot2"
OUTF = "radii_diff_join_r2.json" if PREFIX == "shot2" else ("radii_diff_join_%s.json" % PREFIX)
LADDER = {"0px", "4px", "8px", "12px", "16px", "20px", "24px", "50%", "999px"}
PADDING = 3


def load(arm):
    d = json.loads((ROOT / (PREFIX + "_" + arm) / "elements.json").read_text(encoding="utf-8"))
    return d, d["elements"]


def img(arm, name):
    return Image.open(ROOT / (PREFIX + "_" + arm) / (name + ".png")).convert("RGB")


def changed_px(a, b, box):
    """Count pixels above the threshold inside box (left, top, right, bottom) of two same-size images."""
    if a.size != b.size:
        return None, "size mismatch %s vs %s" % (a.size, b.size)
    if box[0] < 0 or box[1] < 0 or box[2] > a.size[0] or box[3] > a.size[1]:
        return None, "box outside frame"
    d = ImageChops.difference(a.crop(box), b.crop(box))
    n = 0
    px = d.load()
    w, h = d.size
    for y in range(h):
        for x in range(w):
            r, g, bl = px[x, y]
            if r + g + bl > 12:
                n += 1
    return n, None


def crop_box(rect, size):
    x, y, w, h = rect
    return (max(0, x - PADDING), max(0, y - PADDING),
            min(size[0], x + w + PADDING), min(size[1], y + h + PADDING))


db, eb = load("before")
da, ea = load("after")
size = img("before", "pass1_full").size
print("frames: before_full %s, after_full %s, viewport %s" % (size, img("after", "pass1_full").size, db["viewport"]))
print("tile settle: before %s / after %s" % (json.dumps(db["settle"]), json.dumps(da["settle"])))
print("console errors: before %d, after %d" % (len(db["console_errors"]), len(da["console_errors"])))

print("=== ladder membership, recomputed from the two tallies ===")
for label, d in (("before", db), ("after", da)):
    off = {k: v for k, v in d["radius_tally"].items() if k not in LADDER}
    on = sum(v for k, v in d["radius_tally"].items() if k in LADDER)
    print("   %s: sampled=%d  on-table=%d  OFF-table=%d  off-table values=%s" % (
        label, d["sampled"], on, sum(off.values()), json.dumps(off, ensure_ascii=False)))

print("=== per element: its own crop, its own floor ===")
rows = []
for b, a in zip(eb, ea):
    same = (b["tag"] == a["tag"] and b["cls"] == a["cls"] and b["rect"] == a["rect"])
    box_b, box_a = crop_box(b["rect"], size), crop_box(a["rect"], size)
    cross = floor = None
    err1 = err2 = None
    if same:
        cross, err1 = changed_px(img("before", "pass1_full"), img("after", "pass1_full"), box_a)
        floor, err2 = changed_px(img("before", "pass1_full"), img("before", "pass2_full"), box_a)
    else:
        floor, err2 = None, "identity moved between arms"
    rows.append({
        "tag": a["tag"], "class": a["cls"], "testid": a["testid"], "rect": a["rect"],
        "radius_before": b["radius"], "radius_after": a["radius"],
        "in_viewport_390x844": a["in_viewport"],
        "crop_px": (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]),
        "own_floor_px": floor, "cross_arm_px": cross,
        "radius_changed": b["radius"] != a["radius"],
        "painted_moved": (cross is not None and floor is not None and cross > floor),
        "error": err1 or err2,
    })

moved = [r for r in rows if r["painted_moved"]]
changed = [r for r in rows if r["radius_changed"]]
print("elements sampled: %d; computed radius changed: %d; painted and past their own floor: %d" % (
    len(rows), len(changed), len(moved)))
for r in rows:
    flag = "MOVED " if r["painted_moved"] else ("equal " if not r["radius_changed"] else "silent ")
    print("   %s %-9s %-30s %-9s %-22s rect=%-22s floor=%-6s cross=%-6s %s" % (
        flag, r["tag"], (r["class"] or "")[:30], r["radius_before"] + "->" + r["radius_after"],
        r["testid"] or "-", str(r["rect"]), r["own_floor_px"], r["cross_arm_px"],
        r["error"] or ("in-viewport" if r["in_viewport_390x844"] else "below-fold")))

out = {"shots_prefix": PREFIX, "frames": {"full": list(size), "viewport": db["viewport"]},
       "ladder": sorted(LADDER, key=lambda s: (s.endswith("%"), s)),
       "tally_before": db["radius_tally"], "tally_after": da["radius_tally"],
       "off_table_before": {k: v for k, v in db["radius_tally"].items() if k not in LADDER},
       "off_table_after": {k: v for k, v in da["radius_tally"].items() if k not in LADDER},
       "sampled": len(rows), "radius_changed": len(changed), "painted_moved": len(moved),
       "tile_settle": {"before": db["settle"], "after": da["settle"]},
       "console_errors": {"before": db["console_errors"], "after": da["console_errors"]},
       "elements": rows}
(ROOT / OUTF).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                                              encoding="utf-8", newline="\n")
print("wrote " + OUTF)
