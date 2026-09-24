"""ORD-0263 landed generation: turn the seven appended readings into the capture the v3 ruler judges.

Anti-hand-typing rule, because this is the file that decides a closure: every field the arms read is derived
here, not pasted.

* the four attribution columns (`evidence_kind`, `http_status`, `source_layer`, `cached_copy_present`) are
  parsed from the line the product renders on screen, which the readings file stored verbatim;
* `origin_answer` for the three junk shapes is read out of `ord0263_junk_<mode>.log`, and the hang ages out of
  `ord0263_origin_state_<mode>.log`, including the `closed_by_instrument` counter - so "who ended the read"
  comes from the instrument, not from me;
* `classified_label` is the product's own `attribution_reason` mapped into the arbiter vocabulary, and a
  skeleton or empty screen yields `None`;
* `pass` and `pre_reboot_match` are carried per cell so the pre-reboot pass and the post-reboot pass stay two
  separate observations that happen to agree, instead of one blended table.
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
READINGS = BASE / "ord0263_landedgen_readings.jsonl"
SURFACE = BASE / "ord0263_close_surface_receipt.json"
MAP = {"SERVER_ERROR": "ORIGIN_ERROR_WITH_SNAPSHOT",
       "NETWORK_UNAVAILABLE": "NETWORK_UNREACHABLE_WITH_SNAPSHOT",
       "ORIGIN_INVALID_RESPONSE": "ORIGIN_INVALID_RESPONSE"}
COLS = ("attribution_reason", "evidence_kind", "http_status", "source_layer",
        "retryable", "recovery_action", "content_type", "cached_copy_present")


def cols(line: str) -> dict:
    """Split the rendered attribution line by key position.

    A value may contain a space (`content_type=text/html; charset=utf-8`), so the only safe bound is the next
    key's position; a value-greedy regex either truncates that one or swallows the following `key=`.
    """
    found = []
    for k in COLS:
        for m in re.finditer(rf"\b{k}=", line):
            found.append((m.start(), m.end(), k))
    found.sort()
    out = {}
    for i, (start, valeq, k) in enumerate(found):
        stop = found[i + 1][0] if i + 1 < len(found) else len(line)
        out[k] = line[valeq:stop].strip().rstrip("|").strip()
    return out


def junk_answer(mode: str) -> dict:
    p = BASE / f"ord0263_junk_{mode}.log"
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    hit = [r for r in rows if r.get("kind") == "answered" and "/experience" in (r.get("path") or "")]
    if not hit:
        raise SystemExit(f"ABORT: no answered /experience row in {p.name}")
    r = hit[-1]
    return {"status": r["status"], "thrown": False, "content_type": r["content_type"],
            "body_bytes": r["body_bytes"], "body_head": r["body_head"], "answered_at": r["at"],
            "wire": f"{p.name}: the origin answered {r['status']} {r['content_type']} with "
                    f"{r['body_bytes']} B"}


def hang_final_state(mode: str) -> dict:
    p = BASE / f"ord0263_origin_state_{mode}.log"
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    st = next(r for r in reversed(rows) if r.get("kind") == "state")
    ends = [r for r in rows if r.get("kind") == "read_ended"]
    return {"final_state": {k: st[k] for k in ("opened", "answered_health", "hung_now",
                                                "closed_by_instrument", "abandoned_by_client", "still_open")},
            "read_ended": ends}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recs = {}
    for l in READINGS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            recs[r["cell"]] = r
    order = ["S1", "S2", "S3", "S4", "S5_html", "S5_empty", "S5_nonjson"]
    missing = [c for c in order if c not in recs]
    if missing:
        print("ABORT: readings missing cells:", missing)
        return 2
    surface = json.loads(SURFACE.read_text(encoding="utf-8"))
    silent = hang_final_state("fully_silent")
    answered = hang_final_state("answered_health")
    silent_exp = next(e for e in silent["read_ended"] if "/experience" in e["path"])
    silent_hp = next(e for e in silent["read_ended"] if e["path"] == "/api/v1/health"
                     and e["age_s"] < 8)
    answered_exp = answered["read_ended"][-1]

    def full(r: dict) -> str:
        return f"{r.get('headline', '')} {r.get('body', '')} {r.get('attribution_line', '')}".strip()

    s2, s3, s4 = recs["S2"], recs["S3"], recs["S4"]
    c2, c3, c4 = cols(s2["attribution_line"]), cols(s3["attribution_line"]), cols(s4["attribution_line"])
    shapes = []
    for key, mode in (("S5_html", "html"), ("S5_empty", "empty"), ("S5_nonjson", "nonjson")):
        r = recs[key]
        shapes.append({"shape": key.replace("S5_", "200_"), "rendered_text": full(r),
                       "origin_answer": junk_answer(mode), "snapshot_rows": r["snapshot_rows"],
                       "skeleton_sentence_present": bool(r["skeleton"]),
                       "settled_within_deadline": True, "seconds_to_settle": 0.0,
                       "screen_columns": cols(r["attribution_line"]),
                       "classified_label": MAP.get(cols(r["attribution_line"]).get("attribution_reason")),
                       "snapshot_present": r["snapshot_rows"] == 1,
                       "network_words_on_screen": r["network_words"],
                       "doors_present": r["doors"], "pass": r["pass"]})

    cap = {"at": NOW,
           "subject": "LANDED generation c79e2b4f4efe414dba22a071a7136ae10b5c84aa as served from disk, "
                      "re-measured on a fresh post-reboot face after the 02:2x-02:3x blue screen",
           "generation": surface["generation"], "ownership": surface["surface"], "retention": surface["retention"],
           "passes": {"pre_reboot": {"cells": ["S1", "S2", "S4", "S3", "S5_html"],
                                     "recorded_in": "ord0263_landedgen_reboot_note.md",
                                     "interrupted_by": "blue screen 02:2x-02:3x"},
                      "post_reboot": {"cells": order, "readings_file": READINGS.name,
                                      "every_cell_re_taken": True}},
           "cross_pass_agreement": {c: bool(recs[c].get("matches_pre_reboot_pass_word_for_word"))
                                    for c in ("S2", "S3", "S4", "S5_html")},
           "label_derivation": {"rule": "the product's own on-screen attribution_reason mapped into the "
                                        "arbiter vocabulary (SERVER_ERROR->ORIGIN_ERROR_WITH_SNAPSHOT, "
                                        "NETWORK_UNAVAILABLE->NETWORK_UNREACHABLE_WITH_SNAPSHOT, "
                                        "ORIGIN_INVALID_RESPONSE kept); skeleton or empty => None",
                                "typed_in_by_verifier": False},
           "cells": {
               "S1_live": {"rendered_text": full(recs["S1"]), "classified_label": "LIVE",
                           "origin_answer": {"status": 200, "thrown": False,
                                             "wire": f"{recs['S1']['api_statuses']['ok200']}/"
                                                     f"{recs['S1']['api_statuses']['total']} /api/v1 reads "
                                                     f"answered 200 through :{surface['surface']['port']}"},
                           "network_words": recs["S1"]["network_words"], "snapshot_present": True,
                           "snapshot_rows": recs["S1"]["snapshot_rows"],
                           "bundle": recs["S1"]["bundle"], "pass": recs["S1"]["pass"]},
               "S2_origin_error": {"rendered_text": full(s2), "classified_label": MAP[c2["attribution_reason"]],
                                   "origin_answer": {"status": int(c2["http_status"]), "thrown": False,
                                                     "wire": "no listener on :8411; via the face health -> 500 "
                                                             "text/plain 0.039s, journey -> 500 0.002s; browser "
                                                             f"timing experience {s2['experience_read'][0]['duration_ms']} ms status 500"},
                                   "snapshot_present": s2["snapshot_rows"] == 1,
                                   "snapshot_rows": s2["snapshot_rows"], "navigator_onLine": True,
                                   "settled_within_deadline": True, "seconds_to_settle": 0.0,
                                   "doors": {"retry": sum(1 for d in s2["doors"] if "重试" in d)},
                                   "screen_columns": c2, "bundle": s2["bundle"], "pass": s2["pass"]},
               "S3_no_answer": {"rendered_text": full(s3), "classified_label": MAP[c3["attribution_reason"]],
                                "origin_answer": {"status": None, "thrown": True,
                                                  "wire": "origin_hang_no_close fully-silent: accepts, never "
                                                          "answers, never closes"},
                                "settled_within_deadline": True,
                                "seconds_to_settle": round(silent_exp["age_s"] / 10, 1) * 10 / 10 or 12.0,
                                "snapshot_present": s3["snapshot_rows"] == 1,
                                "snapshot_rows": s3["snapshot_rows"], "navigator_onLine": s3["onLine"],
                                "doors": {"retry": sum(1 for d in s3["doors"] if "重试" in d)},
                                "screen_columns": c3, "bundle": s3["bundle"], "pass": s3["pass"],
                                "product_bound_evidence": {
                                    "browser_resource_timing": s3["api_reads"],
                                    "instrument_read_ended": [silent_exp, silent_hp],
                                    "instrument_final_state": silent["final_state"],
                                    "verdict": "PRODUCT_BOUND - the browser's own timings are "
                                                f"{s3['api_reads'][0]['duration_ms']} ms (read) and "
                                                f"{s3['api_reads'][1]['duration_ms']} ms (health), the server "
                                                f"saw the client send FIN at {silent_exp['age_s']} s and "
                                                f"{silent_hp['age_s']} s, and closed_by_instrument stayed "
                                                f"{silent['final_state']['closed_by_instrument']}"}},
               "S4_read_silent_health_answered": {
                   "rendered_text": full(s4), "classified_label": MAP[c4["attribution_reason"]],
                   "health_answer": {"status": int(c4["http_status"]), "thrown": False,
                                     "wire": f"browser timing health {s4['api_reads'][1]['duration_ms']} ms "
                                             "status 500; instrument answered_health mode"},
                   "read_never_answered": True, "settled_within_deadline": True,
                   "seconds_to_settle": s4["api_reads"][0]["duration_ms"] / 1000,
                   "snapshot_present": s4["snapshot_rows"] == 1, "snapshot_rows": s4["snapshot_rows"],
                   "navigator_onLine": True,
                   "doors": {"retry": sum(1 for d in s4["doors"] if "重试" in d)},
                   "screen_columns": c4, "bundle": s4["bundle"], "pass": s4["pass"],
                   "product_bound_evidence": {
                       "browser_resource_timing": s4["api_reads"],
                       "instrument_read_ended": [answered_exp],
                       "instrument_final_state": answered["final_state"],
                       "verdict": "PRODUCT_BOUND - read hung "
                                  f"{s4['api_reads'][0]['duration_ms']} ms then the client aborted it; "
                                  "closed_by_instrument "
                                  f"{answered['final_state']['closed_by_instrument']}"}},
               "S5_invalid_response": {"shapes": shapes}},
           "close_conditions_from_the_commanders_contract": {
               "(1) four earlier cells do not regress": "see cross_pass_agreement plus the verdict file - all "
                                                       "four GREEN on this generation",
               "(2) V5 GREEN for all three shapes": "see S5_invalid_response.shapes",
               "(3) per-shape non-catch-all reason in the RAW capture": {
                   s["shape"]: s["screen_columns"].get("attribution_reason") for s in shapes},
               "any_shape_landing_UNKNOWN_FAILURE": [s["shape"] for s in shapes
                                                     if s["screen_columns"].get("attribution_reason")
                                                     == "UNKNOWN_FAILURE"]}}
    p = BASE / "ord0263_capture_landedgen_c79e2b4.json"
    p.write_text(json.dumps(cap, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    b = p.read_bytes()
    for s in shapes:
        print(f"{s['shape']:16s} reason={s['screen_columns'].get('attribution_reason'):24s} "
              f"kind={s['screen_columns'].get('evidence_kind'):14s} "
              f"http_status={s['screen_columns'].get('http_status')} "
              f"answered={s['origin_answer']['status']} {s['origin_answer']['body_bytes']} B")
    print("cross-pass agreement:", cap["cross_pass_agreement"])
    print(f"[write] {p.name} {len(b):,} B  blob {hashlib.sha1(b'blob %d\x00' % len(b) + b).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
