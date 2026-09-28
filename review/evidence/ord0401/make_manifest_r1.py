"""ORD-0401 -- manifest of the evidence set, computed from the files, never typed."""
import hashlib
import json
from pathlib import Path

OUT = Path("D:/moodle/_qoder_q_ord0401_evidence")
DEST = Path("D:/moodle/_qoder_q_ord0401/wt/review/evidence/ord0401")

PRODUCED_BY = {
    "hub_reachability_tip-e7286dfd.json": "review/evidence/ord0401/probe_0401_r1.mjs, ORD0401_BASE=http://127.0.0.1:4781 (the generation the commander deployed at 18:15)",
    "hub_reachability_candidate-8b0ea597.json": "review/evidence/ord0401/probe_0401_r1.mjs, ORD0401_BASE=http://127.0.0.1:4301 (this lane's own server over the git-archive snap build)",
    "hub_reachability_390x844.json": "first single-width run of the same instrument, kept because it is the arm that reproduced the commander's 351 px reading",
    "first_screen_rect_r1.json": "review/evidence/ord0401/measure_first_screen_r1.mjs -- fixed overlays and the hit-test grid that put the usable first screen at y<768",
    "first_screen_budget_r1.json": "review/evidence/ord0401/measure_budget_r1.mjs -- per-width overlay and anchor scan",
    "shape_budget_r1.json": "review/evidence/ord0401/measure_shapes_r1.mjs -- roads 1 and 2 priced in the live flow at four widths",
    "shape_budget_r2.json": "review/evidence/ord0401/measure_shapes_r2.mjs -- the title-keeping quiet rows (D/E/F/G) that chose the shipped shape",
    "placement_options_r1.json": "review/evidence/ord0401/measure_placements_r1.mjs -- P1..P5, each with what it pushes behind the tab bar",
    "items_open_counterarm_r1.json": "review/evidence/ord0401/probe_items_arm_r1.mjs -- labeled fixture arm proving the note still renders when a check is open",
    "copy_pair_tip-e7286dfd.json": "review/ord0401/copy_pair_check_r1.py against the tip generation (control)",
    "copy_pair_candidate-8b0ea597.json": "review/ord0401/copy_pair_check_r1.py against this lane's build (arm)",
}

files = []
for p in sorted(OUT.iterdir()):
    if p.name == "MANIFEST.json" or not p.is_file():
        continue
    b = p.read_bytes()
    entry = {
        "path": f"review/evidence/ord0401/{p.name}",
        "bytes": len(b),
        "sha256": hashlib.sha256(b).hexdigest(),
    }
    if p.name in PRODUCED_BY:
        entry["produced_by"] = PRODUCED_BY[p.name]
    files.append(entry)

manifest = {
    "order": "ORD-0401",
    "lane": "Q (session 904a042d)",
    "candidate_commit": "8b0ea597197dd3885525340bb408180026205b06",
    "base_tip_measured": "e7286dfd47db2dd9a1420867dd534b906b2d032a",
    "generations_compared": {
        "tip": "index-Doj2alof.js served by http://127.0.0.1:4781",
        "candidate": "index-DJhaPS9z.js served by this lane's http://127.0.0.1:4301 from the git-archive snap",
    },
    "files": files,
    "file_count": len(files),
    "total_bytes": sum(f["bytes"] for f in files),
}
text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
(OUT / "MANIFEST.json").write_text(text, encoding="utf-8", newline="\n")
DEST.mkdir(parents=True, exist_ok=True)
(DEST / "MANIFEST.json").write_text(text, encoding="utf-8", newline="\n")
print("files", manifest["file_count"], "bytes", manifest["total_bytes"])
