"""ORD-0515: turn the exported posters into a size reading that stands on its own.

The gate says the arms passed; this says what the pictures actually measure. It walks the evidence
directory, asks the pixel instrument what is inside each PNG, and compares it against the named
bound read out of the product source -- not a copy of the number typed in here, because a bound the
instrument restates by hand can drift away from the bound the product enforces and both stay green.
"""
import glob
import json
import os
import re
import subprocess
import sys

LANE = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend"
AUDIT = LANE + "/review/ord0515/png_seam_audit_r1.py"
SOURCE = LANE + "/src/features/poster/posterCanvas.ts"
EVIDENCE = sys.argv[1] if len(sys.argv) > 1 else LANE + "/review/ord0515/run"
OUT = os.path.join(EVIDENCE, "size_readings_r1.json")
PY = sys.executable


def named_bound():
    source = open(SOURCE, encoding="utf-8").read()
    match = re.search(r"POSTER_MAX_RASTER_HEIGHT_PX\s*=\s*(\d+)", source)
    if not match:
        raise SystemExit("ABORT: the bound is no longer a named literal in the source")
    scale = re.search(r"^const DEVICE_SCALE = (\d+);", source, re.M)
    return int(match.group(1)), int(scale.group(1)) if scale else 1


def blocks_from_hairlines(groups):
    if not groups:
        return None
    if (groups + 1) % 3 == 0:
        return (groups + 1) // 3, "seams_drawn"
    if groups % 2 == 0:
        return groups // 2, "no_seams"
    return None, "underivable"


def ihdr(path):
    with open(path, "rb") as handle:
        head = handle.read(24)
    return {
        "bytes": os.path.getsize(path),
        "width": int.from_bytes(head[16:20], "big"),
        "height": int.from_bytes(head[20:24], "big"),
        "signature_ok": head[:4] == b"\x89PNG",
    }


def main():
    limit_raster, device_scale = named_bound()
    rows = []
    for path in sorted(glob.glob(os.path.join(EVIDENCE, "*.png"))):
        out = subprocess.run(
            [PY, AUDIT, path], capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        pixels = json.loads(out.stdout.strip().splitlines()[0]) if out.returncode == 0 else {"error": out.stderr[:200]}
        geometry = ihdr(path)
        name = os.path.basename(path)
        rows.append({
            "file": name,
            **geometry,
            # n blocks with drawn day seams give 3n-1 hairline rows; a build that draws none gives
            # 2n. Which one applies is decided by which formula divides exactly, not by the file
            # name -- the 0501 build draws seams but has no bound, and naming it the seamless way
            # read ten blocks for a seven-day trip.
            "day_blocks_from_hairlines": blocks_from_hairlines(pixels.get("hairline_groups")),
            "hairline_groups": pixels.get("hairline_groups"),
            "bottom_padding_rows": pixels.get("bottom_padding_rows"),
            "widest_seam_px": pixels.get("widest_seam_px"),
            "within_named_bound": geometry["height"] <= limit_raster,
        })
    readings = {
        "bound_name": "POSTER_MAX_RASTER_HEIGHT_PX",
        "bound_raster_px": limit_raster,
        "device_scale": device_scale,
        "bound_css_px": limit_raster / device_scale,
        "files": len(rows),
        "over_bound": [r["file"] for r in rows if not r["within_named_bound"]],
        "rows": rows,
    }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(readings, handle, ensure_ascii=False, indent=1)
    print("bound=%s css=%s files=%d over_bound=%d"
          % (limit_raster, readings["bound_css_px"], len(rows), len(readings["over_bound"])))
    for row in rows:
        print("  %-46s %s B  %sx%s  blocks=%s  within_bound=%s"
              % (row["file"], row["bytes"], row["width"], row["height"],
                 row["day_blocks_from_hairlines"], row["within_named_bound"]))
    print("readings %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
