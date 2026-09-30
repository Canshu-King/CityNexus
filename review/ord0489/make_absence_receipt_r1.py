"""ORD-0489 · compute the screen-absence receipt from the walk evidence, not from a sentence.

The claim "the footprint screen and the long-image screen are not on this base generation" needs a
denominator: which routes were asked, and what came back.  This reads the walk JSON the browser
driver wrote and counts the fields; it does not re-open a browser and cannot change what it reports.
"""

import json
import os
import sys

WT = "D:/moodle/_qoder_seed_ord0489/wt"
SRC = os.path.join(WT, "review/ord0489/screens/walk_r2_20260930T0439.json")
CAND = os.path.join(WT, "review/ord0489/screens/walk_candidate_r3_20260930T0439.json")
OUT = os.path.join(WT, "review/ord0489/line_generation_screen_absence.json")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    walk = json.load(open(SRC, encoding="utf-8"))
    cand = json.load(open(CAND, encoding="utf-8"))
    shapes = {}
    for shape in ("phone", "desktop"):
        sweep = walk["screens"][shape]["footprint_and_poster_sweep"]
        shapes[shape] = {
            "routes_swept": len(sweep),
            "route_names": sorted(sweep),
            "footprint_or_checkin_id_hits": sum(len(v["footprint_or_checkin_ids"]) for v in sweep.values()),
            "poster_or_longimage_id_hits": sum(len(v["poster_or_longimage_ids"]) for v in sweep.values()),
            "word_hits": {
                word: sum(v["words"].get(word, 0) for v in sweep.values())
                for word in ("足迹", "长图", "打卡", "导出")
            },
            "mounted_testids_total": sum(v["mounted_count"] for v in sweep.values()),
        }
    candidate = cand["screens"]
    receipt = {
        "order": "ORD-0489",
        "line_generation": {
            "frontend_sha": "dcb90cccc68b81f2317b28db19051dedb9f06c80",
            "preview_port": 8791,
            "evidence": os.path.basename(SRC),
            **shapes,
        },
        "candidate_generation": {
            "frontend_sha": "15d65d7f289c628b810cf5ab4a097d858a128821",
            "preview_port": 8792,
            "footprint_panel_present_rows": len(candidate["footprint_before_new_stamp"]["row_texts"]),
            "poster_stop_blocks": candidate["poster_sheet"]["stop_blocks"],
            "poster_download_bytes": candidate["poster_download"]["saved_bytes"],
            "empty_trip_poster_bar_present": candidate["empty_trip_poster_gate"]["ids"]["trip-poster-bar"]["present"],
            "empty_trip_footprint_empty_present": candidate["empty_trip_footprint"]["ids"]["footprint-empty"]["present"],
        },
        "how": "counts computed here from the browser driver's own JSON; no browser was opened by this file",
    }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=1)
    print(json.dumps(receipt["line_generation"], ensure_ascii=False)[:600])
    print("WROTE", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
