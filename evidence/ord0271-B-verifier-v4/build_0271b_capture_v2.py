"""ORD-0271-B: assemble one round's fifth-state capture from what the instruments wrote, not from what I saw.

Usage: python build_0271b_capture.py [round-number]   ->   ord0271b_capture_round<N>.json

Three sources, each read from its own file:

* `ord0271b_readings.jsonl` - the screen text, the attribution line and the measured IndexedDB row count, each
  line written by my collector as the page posted it, with the page's own sha256 over those exact bytes. A line
  whose stored bytes no longer hash to the sha the page computed is dropped and reported, so a transcription or a
  later edit cannot pass as a reading.
* `ord0263_junk_<mode>.log` - what the origin answered, taken from the origin's side of the wire.
* `ord0271B_face_<gen>.json` - which build was behind the face, with the per-asset sha256 re-hashed from the bytes
  the face answered over HTTP, plus the Q8(b) fingerprints the page itself reported.

A reading is only admitted when the generation it claims to be about is the generation that was actually
executing: `asset_matches_expected` and `sha_matches_local_build` both true. That rule is not decoration - the
first control reading of this round failed it, because the page was one load behind after a generation switch and
still ran the mutant bundle while the face already served the control bytes. It is in the output as
`rejected_readings` with the reason, not quietly discarded.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())

# pass label -> (generation, fifth-state shape name), derived per round so round 2 is the same instrument
def passes_for(round_no: int) -> dict:
    c, m = f"control{round_no}", f"mutant{round_no}"
    return {
        f"{c}_html": (c, "200_html"),        # taken one load behind after the generation switch: must be
        f"{c}_html_rerun": (c, "200_html"),  # rejected by Q8(b); only the re-run can be admitted
        f"{c}_empty": (c, "200_empty"),
        f"{c}_nonjson": (c, "200_not_json"),
        f"{m}_html": (m, "200_html"),
        f"{m}_empty": (m, "200_empty"),
        f"{m}_nonjson": (m, "200_not_json"),
        f"{m}_html_rerun": (m, "200_html_rerun"),
    }
MODE_OF_SHAPE = {"200_html": "html", "200_empty": "empty", "200_not_json": "nonjson",
                 "200_html_rerun": "html"}


def blob40(d: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(d) + d).hexdigest()


def readings(PASSES: dict) -> list[dict]:
    p = BASE / "ord0271b_readings.jsonl"
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    kept, rejected, skipped = [], [], []
    for r in rows:
        label = r.get("label")
        if label not in PASSES:
            # the sanity LIVE readings prove the bundle runs normally; they are not fifth-state shapes, and
            # naming them here is what keeps "not in the table" from reading as "not measured"
            skipped.append(label)
            continue
        claimed = r.get("sha256")
        actual = hashlib.sha256(r["payload"].encode("utf-8")).hexdigest()
        if claimed != actual:
            rejected.append({"label": label, "why": "payload no longer hashes to the sha the page computed",
                             "page_sha256": claimed, "disk_sha256": actual})
            continue
        o = json.loads(r["payload"])
        f = o.get("q8b_fingerprints") or {}
        if not (f.get("asset_matches_expected") and f.get("sha_matches_local_build")):
            rejected.append({"label": label,
                             "why": "the bundle the page executed is not the generation this pass claims "
                                    "(stale shell / one load behind after a generation switch)",
                             "asset_matches_expected": f.get("asset_matches_expected"),
                             "sha_matches_local_build": f.get("sha_matches_local_build"),
                             "executed": [e.get("url") for e in
                                          f.get("executed_bundle_rehashed_from_its_own_url") or []]})
            continue
        kept.append({"label": label, "o": o, "f": f, "disk_sha256": actual, "bytes": r["bytes"],
                     "received_at": r.get("received_at")})
    return kept, rejected, skipped


def answered_row(mode: str, at: str) -> dict:
    """The origin's own log, nearest the reading time, for the journey read."""
    p = BASE / f"ord0263_junk_{mode}.log"
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("kind") == "answered" and "/experience" in (r.get("path") or "")]
    if not rows:
        raise SystemExit(f"ABORT: {p.name} has no answered /experience row at all")
    def secs(t):
        h, m, s = (t or "0:0:0").split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    target = secs(at)
    best = min(rows, key=lambda r: abs(secs(r.get("at", "0:0:0")) - target))
    drift = abs(secs(best.get("at", "0:0:0")) - target)
    return {"row": best, "drift_seconds": drift, "log": p.name,
            "log_blob40": blob40(p.read_bytes()), "answered_rows_in_log": len(rows)}


def face(gen: str) -> dict:
    p = BASE / f"ord0271B_face_{gen}.json"
    if not p.is_file():
        raise SystemExit(f"ABORT: no face receipt for generation {gen}: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    round_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    PASSES = passes_for(round_no)
    kept, rejected, skipped = readings(PASSES)
    shapes = {f"control{round_no}": [], f"mutant{round_no}": []}
    for item in kept:
        gen, shape_name = PASSES[item["label"]]
        o, f = item["o"], item["f"]
        mode = MODE_OF_SHAPE[shape_name]
        a = answered_row(mode, item.get("received_at") or "0:0:0")
        rendered = " | ".join(x for x in [o.get("headline", ""), o.get("body", ""), "归因详情",
                                          o.get("attribution_line", "")] if x)
        asset = (f.get("script_urls_executed") or [""])[0].split("/")[-1]
        fr = face(gen)
        wire = (fr.get("shell") or {}).get("answered_over_http") or {}
        asset_rel = "assets/" + asset
        shapes[gen].append({
            "shape": shape_name,
            "pass_label": item["label"],
            "snapshot_rows": o.get("snapshot_rows"),
            "origin_answer": {"status": a["row"]["status"], "thrown": False,
                              "content_type": a["row"]["content_type"],
                              "body_bytes": a["row"]["body_bytes"],
                              "body_head": a["row"]["body_head"],
                              "answered_at": a["row"]["at"], "path": a["row"]["path"],
                              "wire": f"{a['log']}: answered {a['row']['status']} "
                                      f"{a['row']['content_type']} {a['row']['body_bytes']} B "
                                      f"(drift {a['drift_seconds']} s)",
                              "log_blob40": a["log_blob40"]},
            "rendered_text": rendered,
            "doors_on_screen": o.get("doors"),
            "snapshot_words_on_screen": o.get("snapshot_words"),
            "network_words_on_screen": o.get("network_words"),
            "q8b_fingerprints": {
                "executed_script_urls": f.get("script_urls_executed"),
                "rehashed_from_own_url": f.get("executed_bundle_rehashed_from_its_own_url"),
                "asset_matches_expected": f.get("asset_matches_expected"),
                "sha_matches_local_build": f.get("sha_matches_local_build"),
                "sw_controls_page": f.get("sw_controls_page"),
                "shell_same_generation": f.get("shell_same_generation"),
                "cached_shell_same_generation": f.get("cached_shell_same_generation"),
                "expected_asset": (f.get("expected_asset")), "expected_sha256": (f.get("expected_sha256"))},
            "generation_evidence": {
                "face_receipt": f"ord0271B_face_{gen}.json",
                "face_served_asset": asset_rel,
                "face_answered_over_http": wire.get(asset_rel),
                "face_tree_sha256": (fr.get("served_root") or {}).get("tree_sha256"),
                "face_ownership": (fr.get("surface") or {}).get("ownership_verdict")},
            "reading_provenance": {"collector_sha256": item["disk_sha256"], "bytes": item["bytes"],
                                   "readings_file": "ord0271b_readings.jsonl",
                                   "readings_file_blob40": blob40(
                                       (BASE / "ord0271b_readings.jsonl").read_bytes())},
        })
    for gen in shapes:
        shapes[gen].sort(key=lambda s: s["shape"])
    cgen, mgen = f"control{round_no}", f"mutant{round_no}"
    out = {"at": NOW, "order": "ORD-0271-B", "lane": "HARNESS d291c9dc",
           "round": round_no,
           "subject": "runtime readings for the fifth state on candidate c79e2b4f: control build and the "
                      "single-variable UNKNOWN_FAILURE mutant of the same build, same face, same instrument",
           "commit_under_test": "c79e2b4f4efe414dba22a071a7136ae10b5c84aa",
           "mutant": {"source_file": "frontend/src/lib/failureAttribution.ts",
                      "line": 159, "change": 'make("ORIGIN_INVALID_RESPONSE", ...) -> make("UNKNOWN_FAILURE", ...)',
                      "diff_file": "ord0271B_mutant_diff.patch",
                      "diff_blob40": blob40((BASE / "ord0271B_mutant_diff.patch").read_bytes()),
                      "control_asset": "assets/index-ChOTTCvB.js",
                      "control_sha256": "2d56a79632efc0c6b30396ebbddcd54bd84c0d2fa6a30d3f20d09f4655d419de",
                      "mutant_asset": "assets/index-BlYkFxF7.js",
                      "mutant_sha256": "a919a53f7a91ab79fbc669056f146270bba00b8f63d4ef0f1dd4244e7b94ab4a"},
           "cells": {"S5_invalid_response": {"shapes": shapes[cgen]},
                     "S5_invalid_response_mutant": {"shapes": shapes[mgen]}},
           "rejected_readings": rejected,
           "counts": {"readings_admitted": sum(len(v) for v in shapes.values()),
                      "control_shapes": len(shapes[cgen]), "mutant_shapes": len(shapes[mgen]),
                      "readings_rejected": len(rejected),
                      "readings_not_fifth_state": skipped}}
    p = BASE / f"ord0271b_capture_round{round_no}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(json.dumps({"control_shapes": [(s["shape"], s["origin_answer"]["content_type"],
                                          s["origin_answer"]["body_bytes"], s["snapshot_rows"],
                                          (s["rendered_text"].split("attribution_reason=")[1].split()[0]
                                           if "attribution_reason=" in s["rendered_text"] else None))
                                         for s in shapes[cgen]],
                      "mutant_shapes": [(s["shape"], s["origin_answer"]["content_type"],
                                         s["origin_answer"]["body_bytes"], s["snapshot_rows"],
                                         (s["rendered_text"].split("attribution_reason=")[1].split()[0]
                                          if "attribution_reason=" in s["rendered_text"] else None))
                                        for s in shapes[mgen]],
                      "rejected": [(r["label"], r["why"][:70]) for r in rejected],
                      "not_fifth_state": sorted(set(skipped))},
                     ensure_ascii=False, indent=1))
    print("->", p.name, f"{p.stat().st_size:,} B blob {blob40(p.read_bytes())[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
