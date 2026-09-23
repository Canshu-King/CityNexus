"""ORD-0263 V5: run the proposed criteria against the UNFIXED tree, mechanically.

A criterion handed over without its current reading is just prose. So each V5 judgement below is
derived from measured fields of my own two generations -- the frozen word tables are imported from
HARNESS's ruler (not copied, not edited, blob re-hashed before and after), and the four earlier cells
are re-judged with his own judge_all so "S1..S4 stay green before the fix" is a reading too, not a
promise.

Nothing here claims GREEN for V5: this is the control round, which must be red.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = pathlib.Path(r"D:\moodle\_qoder_b_ord0263_20260923")
RULER = pathlib.Path(r"D:\moodle\_qoder_harness_ord0254\tools\ord0263_verifier.py")
PUBLISHED_BLOB40 = "ed8a61dc79d87cc2acf18ef93ecca7caf89b4b83"


def blob40(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def load_ruler():
    rb = RULER.read_bytes()
    if blob40(rb) != PUBLISHED_BLOB40:
        raise SystemExit("ABORT: the ruler on disk is not the published blob I signed")
    spec = importlib.util.spec_from_file_location("ord0263_verifier", str(RULER))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, rb


def cell_from_read(read: dict, origin_read: dict) -> dict:
    """Shape the fifth capture cell exactly like S2/S3 so HARNESS's existing helpers apply to it."""
    last = (read.get("app_attribution") or {}).get("last") or {}
    probe = read.get("origin_probe") or {}
    return {
        "classified_label": None,  # derived below by my printed rule, same function capture uses
        "rendered_text": read.get("rendered_text") or "",
        "origin_answer": {"status": probe.get("status"), "ct": probe.get("ct"),
                          "thrown": probe.get("thrown"), "probe_ms": probe.get("ms")},
        "read_answer": {"status": origin_read.get("status"), "content_type": origin_read.get("content_type"),
                        "body_head": origin_read.get("body_head")},
        "settled_within_deadline": read.get("seconds_to_settle") is not None,
        "seconds_to_settle": read.get("seconds_to_settle"),
        "navigator_onLine": (read.get("service_worker") or {}).get("onLine"),
        "snapshot_present": bool((read.get("snapshot") or {}).get("present")),
        "doors": {"retry": (read.get("classification_nodes") or {}).get("failure-retry", 0),
                  "read_cached": (read.get("classification_nodes") or {}).get("failure-read-cached", 0)},
        "attribution": last,
    }


def main() -> int:
    mod, rb = load_ruler()
    repro = json.loads((BASE / "q263_s5_reproduction.json").read_text(encoding="utf-8"))
    repro2 = json.loads((BASE / "q263_a3_reproduction.json").read_text(encoding="utf-8"))
    gen1 = json.loads((BASE / "s5_state.json").read_text(encoding="utf-8"))
    gen2 = json.loads((BASE / "s5_second.json").read_text(encoding="utf-8"))
    origin_read = repro["origin_probe_measured"]["direct_read"]

    c1 = cell_from_read(gen1, origin_read)
    c2 = cell_from_read(gen2, {"status": 200, "content_type": "text/html",
                               "body_head": "<!doctype html><html><head><meta c"})
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0263 第五格判据在未修树上的机械派生（控制轮）",
           "ruler": {"path": str(RULER), "blob40": blob40(rb), "expected": PUBLISHED_BLOB40,
                     "unchanged_after": blob40(RULER.read_bytes()) == blob40(rb),
                     "word_tables_imported_not_copied": True},
           "tree": "landed tip 2b49e3ca + ORD-0268 一行（src 与 2b49e3ca 相同）；第五态尚未修"}

    # the printed label rule from my capture instrument, applied to the fifth cell
    for c in (c1, c2):
        r = (c["attribution"] or {}).get("reason")
        snap = c["snapshot_present"]
        if r == "SERVER_ERROR":
            c["classified_label"] = "ORIGIN_ERROR_WITH_SNAPSHOT" if snap else "ORIGIN_ERROR"
        elif r == "NETWORK_UNAVAILABLE":
            c["classified_label"] = "NETWORK_UNREACHABLE_WITH_SNAPSHOT" if snap else "NETWORK_UNREACHABLE"
        elif r == "JOURNEY_NOT_FOUND":
            c["classified_label"] = "JOURNEY_GONE"
        elif r:
            c["classified_label"] = r

    def judge_v5(c: dict) -> dict:
        a = c["attribution"] or {}
        t = c["rendered_text"]
        net = bool(mod.NETWORK_WORDS.search(t))
        svc = bool(mod.SERVICE_WORDS.search(t))
        snap_w = bool(mod.SNAPSHOT_WORDS.search(t))
        answered = mod.answered(c)
        body_says_facts = ("200" in t) and ("text/html" in t or "文档" in t)
        return {
            "V5a_fact_kept": {"verdict": "GREEN" if a.get("evidence_kind") == "HTTP_RESPONSE"
                                     and a.get("http_status") == c["read_answer"]["status"] else "RED",
                              "measured": {"evidence_kind": a.get("evidence_kind"),
                                           "http_status": a.get("http_status"),
                                           "read_status_measured": c["read_answer"]["status"]},
                              "rule": "the answered fact and its status must survive into the attribution"},
            "V5b_not_a_network_or_no_reply_class": {
                "verdict": "RED" if (a.get("reason") == "NETWORK_UNAVAILABLE"
                                     or a.get("message_key") == "failure.noAnswer"
                                     or str(c["classified_label"]).startswith("NETWORK_UNREACHABLE")) else "GREEN",
                "measured": {"reason": a.get("reason"), "message_key": a.get("message_key"),
                             "classified_label": c["classified_label"]},
                "rule": "the mechanical fingerprint: answered==True with a NETWORK_UNREACHABLE-family label"},
            "V5c_screen_says_a_true_sentence": {
                "verdict": "GREEN" if ((not net) and svc and (snap_w or not c["snapshot_present"])
                                       and body_says_facts) else "RED",
                "measured": {"network_words": net, "service_words": svc, "snapshot_words": snap_w,
                             "names_http_200_and_html": body_says_facts},
                "rule": "must name the origin and the unusable answer, never the network"},
            "V5d_both_read_channels": {
                "verdict": "NOT_MEASURED",
                "why": "the requestJson leg has only its source shape (citynexus.ts:652-668) so far; "
                       "no on-screen reading of a 200+HTML answer reaching that channel yet"},
            "V5e_probe_may_not_cover_it": {
                "verdict": "GREEN" if (a.get("evidence_kind") == "HTTP_RESPONSE"
                                       and c["doors"]["retry"] > 0 and c["doors"]["read_cached"] > 0) else "RED",
                "measured": {"evidence_kind": a.get("evidence_kind"),
                             "probe_status": c["origin_answer"]["status"],
                             "retry_door": c["doors"]["retry"], "snapshot_door": c["doors"]["read_cached"]},
                "rule": "a 200 probe must not be used to launder the attribution, and both doors stay"},
        }

    out["V5_control_round"] = {"generation_1": judge_v5(c1), "generation_2": judge_v5(c2)}
    out["V5_cells"] = {"generation_1": c1, "generation_2": c2}

    # ---- the four earlier cells, judged by HARNESS's own unmodified judge_all on the pre-fix capture
    cap_post = json.loads((BASE / "capture_post.json").read_text(encoding="utf-8"))
    cap_post = {**cap_post, "cells": dict(cap_post.get("cells") or {})}
    cap_post["cells"]["S5_origin_answered_html"] = c1
    out["S1_to_S4_before_any_fix"] = mod.judge_all(cap_post)
    s3 = cap_post["cells"].get("S3_no_answer") or {}
    out["reverse_sentinel_s3_must_stay"] = {
        "measured": {"S3_classified_label": s3.get("classified_label"),
                     "S3_origin_answer_thrown": (s3.get("origin_answer") or {}).get("thrown")},
        "must_remain": "NETWORK_UNREACHABLE_WITH_SNAPSHOT with thrown==True",
        "meaning": "if the fifth state later swallows 'never answered', this reading flips and I have "
                   "over-reached -- that is what keeps V5 inside ORD-0263's scope"}
    counts = json.loads((BASE / "s5_counts.json").read_text(encoding="utf-8")) if (BASE / "s5_counts.json").exists() else None
    out["A3"] = {"verdict": "NOT_THE_SAME_LIE_NOT_MERGED",
                 "measured": {"writes": repro2["A3"].get("writes_seen"),
                              "write_responses_settled": repro2["A3"].get("write_responses_settled"),
                              "samples": repro2["A3"].get("sample_count"),
                              "ever_blamed_network_or_origin": repro2["A3"].get("ever_blamed_network_or_origin"),
                              "attribution_records": len(repro2["A3"].get("attribution_samples") or []),
                              "stop_door_clicked_at_s": (repro2["A3"].get("stop_waiting_used") or {}).get("clicked_at_s"),
                              "after_stop_rendered": (repro2["A3"].get("stop_waiting_used") or {}).get("after_wait_outcome"),
                              "origin_counters": counts},
                 "instrument_self_report": "hit_test==NONE on the stop button (no scrollIntoView first); the door's "
                                           "usability is proven by the rendered sentence after the click, not by that field",
                 "cause_line": "readDeadline.ts:43-44 returns a bare fetch() for non-GET/HEAD, so a hung write has no "
                               "deadline -- a deadline question, not an attribution one (ORD-0262 family)"}

    p = BASE / "q263_s5_criteria_control.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")

    def summarise(tag, j):
        print(f"  {tag}: " + " ".join(f"{k}={v['verdict']}" for k, v in j.items()))
    for g, j in out["V5_control_round"].items():
        summarise(g, j)
    summarise("S1..S4 (pre-fix capture, ruler's own judge_all)", out["S1_to_S4_before_any_fix"])
    print("  S3 sentinel:", json.dumps(out["reverse_sentinel_s3_must_stay"]["measured"], ensure_ascii=False))
    print("  A3 blames network:", out["A3"]["measured"]["ever_blamed_network_or_origin"])
    print("ruler unchanged after:", out["ruler"]["unchanged_after"], "->", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
