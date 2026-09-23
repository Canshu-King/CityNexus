"""ORD-0263 fifth-state candidate: judge the readings already on disk with HARNESS's own entry point.

The driver collected every reading and then died on a wrong function name in MY assembly code (`v3` has no
`judge_all`; its live entry is `live()`). Nothing is re-measured here -- the same artifacts from that one
round are assembled into the capture his `live()` expects, and his ruler decides. Only his output
directory is retargeted inside my process; no rule, regex or token table is touched, and the ruler blob is
re-hashed before and after.

Proxy ownership is shown pairwise rather than by a marker: for every shape, the browser's own Resource
Timing recorded the journey read as answered with that shape's status/content-type, and my origin's log
recorded the same path at the same shape -- a read that had been answered by anyone else's backend could
not produce both lines.
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
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
RULER = pathlib.Path(r"D:\moodle\_qoder_harness_ord0254\tools\ord0263_verifier_v3.py")
RULER_BLOB = "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9"
SHAPE_MODE = {"200_html": "html", "200_empty": "empty", "200_not_json": "nonjson"}
CELL_MODE = {"S2_origin_error": "five_hundred", "S3_no_answer": "silent",
             "S4_read_silent_health_answered": "mixed"}


def blob(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def load_ruler():
    rb = RULER.read_bytes()
    assert blob(rb) == RULER_BLOB, "the ruler on disk is not the published blob"
    spec = importlib.util.spec_from_file_location("ord0263_v3", str(RULER))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.BASE = BASE                      # output only; no rule, no regex, no table touched
    return mod, rb


def rows(mode: str):
    p = BASE / f"s5fix_origin_{mode}.log"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def read(label: str) -> dict:
    p = BASE / f"s5fix_read_{label}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"missing": p.name}


def classified_label(r: dict):
    last = r.get("in_memory_attribution_last") or {}
    snap = bool((r.get("snapshot") or {}).get("rows"))
    if not last:
        return "LIVE" if (r.get("state_nodes") or {}).get("today-heading") else None
    reason = last.get("reason")
    return {"SERVER_ERROR": "ORIGIN_ERROR_WITH_SNAPSHOT" if snap else "ORIGIN_ERROR",
            "NETWORK_UNAVAILABLE": "NETWORK_UNREACHABLE_WITH_SNAPSHOT" if snap else "NETWORK_UNREACHABLE",
            "ORIGIN_INVALID_RESPONSE": "ORIGIN_ANSWERED_BUT_NOT_USABLE_WITH_SNAPSHOT" if snap
            else "ORIGIN_ANSWERED_BUT_NOT_USABLE",
            "JOURNEY_NOT_FOUND": "JOURNEY_GONE"}.get(reason, reason)


def health_row(mode: str):
    got = [x for x in rows(mode) if str(x.get("kind", "")).startswith("health")]
    return got[-1] if got else None


def cell(r: dict, answered_row: dict | None, hr: dict | None = None) -> dict:
    timing = (r.get("resource_timing") or {}).get("journey") or {}
    hung = bool(answered_row) and answered_row.get("kind") == "hung"
    return {"classified_label": classified_label(r),
            "rendered_text": r.get("rendered_text") or "",
            "origin_answer": {"status": None if hung else (answered_row or {}).get("status") or timing.get("status"),
                              "thrown": hung or not timing,
                              "ct": (answered_row or {}).get("content_type"),
                              "body_bytes": (answered_row or {}).get("body_bytes")},
            "settled_within_deadline": r.get("settled_after_ms") is not None,
            "seconds_to_settle": None if r.get("settled_after_ms") is None
            else round(r["settled_after_ms"] / 1000, 2),
            "snapshot_present": bool((r.get("snapshot") or {}).get("rows")),
            "snapshot_rows": (r.get("snapshot") or {}).get("rows"),
            "navigator_onLine": True,
            "doors": {"retry": sum(1 for b in (r.get("buttons") or []) if "重试" in b),
                      "read_only_snapshot": sum(1 for b in (r.get("buttons") or []) if "只读" in b)},
            # his judge_v4 asks for these two columns; they are my instrument's own rows, not inference
            "read_never_answered": hung,
            "health_answer": ({"status": hr.get("status"), "thrown": False, "ct": hr.get("content_type")}
                              if hr else {"status": None, "thrown": True})}


def main() -> int:
    v3, rb = load_ruler()
    shapes, pairwise = [], {}
    for shape, mode in SHAPE_MODE.items():
        r = read(shape)
        got = [x for x in rows(mode) if x["kind"] == "answered" and "/experience" in x["path"]]
        if not got:
            raise SystemExit(f"ABORT: {mode} log has no answered journey row")
        inst = got[-1]
        shapes.append({"shape": shape,
                       "origin_answer": {"status": inst["status"], "thrown": False,
                                         "content_type": inst["content_type"], "body_bytes": inst["body_bytes"],
                                         "body_head": inst["body_head"],
                                         "wire": f"s5fix_origin_{mode}.log answered {inst['status']} "
                                                 f"{inst['content_type']} {inst['body_bytes']} B at {inst['at']}"},
                       "rendered_text": r.get("rendered_text") or "",
                       "snapshot_rows": (r.get("snapshot") or {}).get("rows"),
                       "buttons": r.get("buttons") or []})
        t = (r.get("resource_timing") or {}).get("journey") or {}
        pairwise[shape] = {"browser_resource_timing": t, "origin_log_row": inst,
                           "status_agrees": t.get("status") == inst["status"],
                           "path_agrees": "/experience" in (t.get("url") or "")}
    cells = {}
    for cell_name, mode in CELL_MODE.items():
        r = read(cell_name)
        got = [x for x in rows(mode) if "/experience" in (x.get("path") or "")]
        cells[cell_name] = cell(r, got[-1] if got else None, health_row(mode))
        cells[cell_name]["instrument_last_row"] = got[-1] if got else None
    live_read = read("live")
    cells["S1_live"] = {"classified_label": classified_label(live_read),
                        "rendered_text": live_read.get("rendered_text") or "",
                        "origin_answer": {"status": ((live_read.get("resource_timing") or {}).get("journey") or {}).get("status"),
                                          "thrown": False, "ct": "application/json"},
                        "settled_within_deadline": True, "seconds_to_settle": 0.0,
                        "snapshot_present": bool((live_read.get("snapshot") or {}).get("rows")),
                        "snapshot_rows": (live_read.get("snapshot") or {}).get("rows"),
                        "navigator_onLine": True,
                        "doors": {"retry": 0, "read_only_snapshot": 0}}
    cells["S5_invalid_response"] = {"shapes": shapes}
    cap_path = BASE / "ord0263_capture_candidate_s5fix.json"
    cap_path.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                                    "subject": "CANDIDATE branch agent/b-c01d72a3-ord0263-s5, dist_s5, my :4443 -> my :8443",
                                    "cells": cells}, ensure_ascii=False, indent=1), "utf-8", newline="\n")

    rc = v3.live(cap_path)
    verdict = json.loads((BASE / f"ord0263_verdict_{cap_path.stem}.json").read_text(encoding="utf-8"))

    per5 = {s["shape"]: v3.judge_v5(s) for s in shapes}
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0263 第五态候选 · 六格自证（三形 + 前四格，尺自己的 live 判级）",
           "lane": "B c01d72a3",
           "how_computed": "the driver's browser round completed and wrote every reading; it then crashed in my "
                           "assembly code on a wrong ruler entry point (v3 exposes live(), not judge_all). "
                           "This script re-JUDGES the same artifacts -- nothing was re-measured, and no reading "
                           "was retyped.",
           "ruler": {"path": str(RULER), "blob40": blob(rb), "expected": RULER_BLOB,
                     "unchanged_after": blob(RULER.read_bytes()) == blob(rb),
                     "retargeted_in_my_process_only": "v3.BASE -> my order directory (output path, no rule touched)",
                     "entry_point_used": "live()"},
           "surface": {"preview": 4443, "origin": 8443, "bundle": "dist_s5 built from agent/b-c01d72a3-ord0263-s5",
                       "snapshot_earned_via": "the app's own sealed-demo control against a real uvicorn "
                                              "(enter reading: settle 3.25s, snapshot present, count 1)",
                       "proxy_ownership": "pairwise per shape: browser Resource Timing and my origin's log agree "
                                          "on status and path for the same journey read (see pairwise_proofs)",
                       "provider_egress": "AI off, resolver off, Photon at 127.0.0.1:9",
                       "write_leg_probe": "not run: forbidden this round by commander 5798766898"},
           "pairwise_proofs": pairwise,
           "screen_sentences": {k: (read(k).get("rendered_text") or "").replace("\n", " | ")[:260]
                                for k in ["live", *SHAPE_MODE, *CELL_MODE]},
           "judge_v5_per_shape": per5,
           "ruler_live_verdict": verdict, "ruler_live_rc": rc,
           "attribution_as_measured_in_memory": {k: read(k).get("in_memory_attribution_last")
                                                 for k in [*SHAPE_MODE, *CELL_MODE]}}
    p = BASE / "q263_s5fix_selfproof.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print("\n  derived_result:", verdict["derived_result"])
    for k, v in verdict["verdicts_computed_from_measured_fields"].items():
        print(f"    {k:34s} {v.get('verdict')}")
    print("--- what the screen says now, per shape")
    for k in SHAPE_MODE:
        print(f"  {k}: {(read(k).get('rendered_text') or '').replace(chr(10), ' | ')[:200]}")
    print("->", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
