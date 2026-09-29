"""ORD-0448 joiner -- pixel difference on the glass, and the element set that owns it.

Three comparisons, deliberately: within the SAME arm twice (that is the noise floor: pulsing dot,
tile loading, caret), and then before-arm against after-arm. A region only counts when it moves by
more than the floor. Each surviving region is then attributed to the sampled elements whose painted
box overlaps it, with the radius that element had before and after -- so the reading names elements,
not just pixels.
"""
import json
import pathlib
import sys

from PIL import Image, ImageChops

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path("D:/moodle/_qoder_q_ord0448_20260929")
CELL = 8
THRESH = 12


def img(p):
    return Image.open(p).convert("RGB")


def diff_mask(a, b):
    d = ImageChops.difference(a, b)
    w, h = d.size
    px = d.load()
    cells = set()
    changed = 0
    for y in range(0, h):
        for x in range(0, w):
            r, g, bl = px[x, y]
            if r + g + bl > THRESH:
                changed += 1
                cells.add((x // CELL, y // CELL))
    return changed, cells, (w, h)


def boxes(cells):
    """Merge flagged cells into rectangles: greedy growth over the cell set."""
    todo = set(cells)
    out = []
    while todo:
        x0, y0 = min(todo, key=lambda c: (c[1], c[0]))
        x1 = x0
        while (x1 + 1, y0) in todo:
            x1 += 1
        y1 = y0
        while all((x, y1 + 1) in todo for x in range(x0, x1 + 1)):
            y1 += 1
        block = {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}
        todo -= block
        out.append((x0 * CELL, y0 * CELL, (x1 + 1) * CELL, (y1 + 1) * CELL))
    return out


def load(arm):
    return json.loads((ROOT / ("shot_" + arm) / "elements.json").read_text(encoding="utf-8"))["elements"]


before, after = load("before"), load("after")
noise_b, noise_a = None, None
cb, cells_b, size = diff_mask(img(ROOT / "shot_before/pass1.png"), img(ROOT / "shot_before/pass2.png"))
ca, cells_a, _ = diff_mask(img(ROOT / "shot_after/pass1.png"), img(ROOT / "shot_after/pass2.png"))
rb, cells_x, _ = diff_mask(img(ROOT / "shot_before/pass1.png"), img(ROOT / "shot_after/pass1.png"))
floor = max(cb, ca)
print("image %dx%d px" % size)
print("same-arm noise: before-arm %d changed px, after-arm %d changed px -> floor %d" % (cb, ca, floor))
print("before-arm vs after-arm: %d changed px (%s the floor)" % (rb, "above" if rb > floor else "at or below"))

regions = [b for b in boxes(cells_x) if (b[2] - b[0]) * (b[3] - b[1]) * CELL * CELL > 0]
print("changed regions after the merge: %d" % len(regions))

moved = []
for el_b, el_a in zip(before, after):
    if el_b["radius"] != el_a["radius"]:
        x, y, w, h = el_a["rect"]
        overlapping = [r for r in regions if not (r[2] < x or r[0] > x + w or r[3] < y or r[1] > y + h)]
        moved.append({
            "tag": el_a["tag"], "class": el_a["cls"], "testid": el_a["testid"],
            "radius_before": el_b["radius"], "radius_after": el_a["radius"],
            "rect": el_a["rect"], "regions_overlapping": len(overlapping),
            "identity_matches": el_b["tag"] == el_a["tag"] and el_b["cls"] == el_a["cls"],
        })
hit = [m for m in moved if m["regions_overlapping"] > 0]
print("elements whose computed radius changed: %d of %d sampled; of those, painted inside a changed region: %d" % (
    len(moved), len(before), len(hit)))
for m in moved:
    print("   %-9s %-34s %s -> %s  rect=%s  regions=%d" % (
        m["tag"], m["class"][:34], m["radius_before"], m["radius_after"], m["rect"], m["regions_overlapping"]))
for r in regions[:14]:
    print("   region px x=%d y=%d w=%d h=%d" % (r[0], r[1], r[2] - r[0], r[3] - r[1]))

(ROOT / "radii_diff_join_r1.json").write_text(json.dumps({
    "image_size": list(size), "noise_px_same_arm_before": cb, "noise_px_same_arm_after": ca, "floor_px": floor,
    "cross_arm_changed_px": rb, "regions": [{"x": r[0], "y": r[1], "w": r[2] - r[0], "h": r[3] - r[1]} for r in regions],
    "sampled": len(before), "radius_changed_elements": moved,
    "radius_changed_and_inside_a_region": len(hit)}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("wrote radii_diff_join_r1.json")
