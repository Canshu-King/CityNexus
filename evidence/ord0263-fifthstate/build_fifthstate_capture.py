"""ORD-0263 fifth state: append the three junk-body readings to the already-measured four cells.

Two rules shape this builder:

* the four old cells are **read out of `ord0263_capture_landedgen.json`** (the file whose blob is already
  published), not retyped - so adding a fifth cell cannot silently edit one of the first four;
* everything I claim about what the origin answered comes from the instrument's own side log
  (`ord0263_junk_<shape>.log`), and everything I claim about the screen is the rendered text, including the
  `归因详情` line the product itself prints. `screen_declared_reason` etc. are therefore the product's own words,
  not labels I pasted on.

The point of the file is one RED reading on the generation currently on disk: the origin answers 200 in single
milliseconds and the traveller is told the request never went out.
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

FOUR_CELLS = BASE / "ord0263_capture_landedgen.json"

# rendered text, verbatim from the page (归因详情 expanded by clicking, read as innerText)
SCREEN = ("连接 | 网络不可用 | 这一发请求没能出去，也没有收到任何回答，所以这是网络问题。你的行程数据没有丢失，"
          "已保存的只读副本还能看。请检查网络后重试。 | 看已保存的只读副本 | 重试 | 归因详情 | "
          "attribution_reason=NETWORK_UNAVAILABLE evidence_kind=TRANSPORT http_status=none "
          "source_layer=TRANSPORT retryable=true recovery_action=read-only-cached cached_copy_present=true")

SHAPES = [
    {"shape": "200_html", "log": "ord0263_junk_html.log",
     "page_read": {"name": "/api/v1/journeys/22222222-2222-4222-8222-222222222222/experience",
                   "rel_start_ms": 414, "rel_end_ms": 420, "duration_ms": 6, "status": 200},
     "served_by_instrument": "the served index.html, i.e. exactly what an SPA fallback hands back",
     "snapshot_rows": 1, "buttons": ["看已保存的只读副本", "重试"]},
    {"shape": "200_empty", "log": "ord0263_junk_empty.log",
     "page_read": {"name": "/api/v1/journeys/22222222-2222-4222-8222-222222222222/experience",
                   "rel_start_ms": 263, "rel_end_ms": 267, "duration_ms": 4, "status": 200},
     "health_page_read": {"name": "/api/v1/health", "rel_start_ms": 269, "rel_end_ms": 273,
                          "duration_ms": 4, "status": 200},
     "served_by_instrument": "200 with Content-Length: 0",
     "snapshot_rows": 1, "buttons": ["看已保存的只读副本", "重试"]},
    {"shape": "200_not_json", "log": "ord0263_junk_nonjson.log",
     "page_read": {"name": "/api/v1/journeys/22222222-2222-4222-8222-222222222222/experience",
                   "rel_start_ms": 132, "rel_end_ms": 137, "duration_ms": 4, "status": 200},
     "served_by_instrument": "200 text/plain, a sentence that is not JSON",
     "snapshot_rows": 1, "buttons": ["看已保存的只读副本", "重试"]},
]


def answered_row(log_name: str) -> dict:
    """The instrument's own record of the reply it sent for the journey read."""
    p = BASE / log_name
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    hit = [r for r in rows if r.get("kind") == "answered" and "/experience" in (r.get("path") or "")]
    if not hit:
        raise SystemExit(f"ABORT: {log_name} has no answered row for the journey read - "
                         f"kinds present: {sorted({r.get('kind') for r in rows})}")
    return hit[-1]


def parse_att(text: str) -> dict:
    keys = ("attribution_reason", "evidence_kind", "http_status", "source_layer", "retryable",
            "recovery_action", "cached_copy_present")
    out = {}
    for k in keys:
        m = re.search(rf"\b{k}=([^\s|]+)", text)
        if m:
            out[k] = m.group(1)
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    four = json.loads(FOUR_CELLS.read_text(encoding="utf-8"))
    shapes = []
    for s in SHAPES:
        inst = answered_row(s["log"])
        shapes.append({
            "shape": s["shape"],
            "origin_answer": {"status": inst["status"], "thrown": False,
                              "content_type": inst["content_type"], "body_bytes": inst["body_bytes"],
                              "body_head": inst["body_head"],
                              "wire": f"{s['log']}: the instrument answered {inst['status']} "
                                      f"{inst['content_type']} with {inst['body_bytes']} B at "
                                      f"{inst['at']} - {s['served_by_instrument']}"},
            "rendered_text": SCREEN,
            "screen_declared": parse_att(SCREEN),
            "page_resource_timing": {"journey_read": s["page_read"],
                                     "health_read": s.get("health_page_read")},
            "snapshot_rows": s["snapshot_rows"], "buttons": s["buttons"],
            "settled_within_deadline": True, "seconds_to_settle": 0.0,
            "note": "no deadline was needed - the origin replied in single-digit milliseconds"})

    cap = {"at": NOW,
           "subject": four["subject"] + " - plus the fifth state (answered 2xx with an unparseable body)",
           "why_fifth": "red team 5796920909 raised A1 to a runtime reading and it CONFIRMED; arbiter "
                        "5796901133 §问三 pre-ruled that a reproduction reopens ORD-0263 with a fifth cell "
                        "in the same table rather than a new order. This capture is that cell, measured on "
                        "the bundle currently on disk.",
           "generation_fingerprint": four["generation_fingerprint"],
           "surface": four["surface"],
           "four_old_cells_provenance": {
               "read_from": FOUR_CELLS.name, "retyped": False,
               "file_sha256": hashlib.sha256(FOUR_CELLS.read_bytes()).hexdigest(),
               "cells_carried": list(four["cells"].keys())},
           "fifth_state_acceptance_used": "the arbiter's minimum, not my vocabulary: keep the HTTP-response "
                                          "fact in evidence_kind, keep http_status=200, do not land on "
                                          "NETWORK_UNAVAILABLE/NO_REPLY, and let the cached-copy column "
                                          "follow the measurement. The label string itself is NOT pinned "
                                          "(arbiter wrote 名字可再定).",
           "cells": dict(four["cells"], S5_invalid_response={"shapes": shapes}),
           "headline_reading": {
               "what_the_origin_did": "answered 200 in 4-6 ms, three shapes: HTML / empty / not-JSON",
               "what_the_screen_said": "「这一发请求没能出去，也没有收到任何回答，所以这是网络问题」",
               "what_the_products_own_attribution_column_says": parse_att(SCREEN),
               "contradiction": "a 200 is an answer; the client reports the transport never carried one "
                                "(http_status=none, evidence_kind=TRANSPORT) while the page really did "
                                "receive 1200 / 0 / 33 bytes"}}
    p = BASE / "ord0263_capture_landedgen_fifth.json"
    p.write_text(json.dumps(cap, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    b = p.read_bytes()
    for s in shapes:
        print(f"{s['shape']:14s} answered {s['origin_answer']['status']} "
              f"{s['origin_answer']['body_bytes']:>5} B {s['origin_answer']['content_type']:26s}"
              f" -> screen says reason={s['screen_declared']['attribution_reason']} "
              f"kind={s['screen_declared']['evidence_kind']} http_status={s['screen_declared']['http_status']}")
    print(f"[write] {p.name} {len(b):,} B  blob {hashlib.sha1(b'blob %d\x00' % len(b) + b).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
