"""ORD-0263 livegen: assemble what the CURRENT release generation actually shows, and derive every label.

Same shape as the B-candidate capture on purpose - one instrument, one judge, two front ends - so the only
variable between the two verdicts is the bundle. Readings are verbatim returns of one evaluate/sampler body
against my own face `http://127.0.0.1:4414`, whose `/api` proxy is pinned to my backend `:8411`
(`ord0263_livegen_surface_receipt.json`: byte-identical copy of the served dist + 200-on-marker-journey and
404-on-an-absent-id, both ways).

One correction I owe the judge rather than the product: my label derivation is text-based, and a traveller
still sitting on 「正在准备城市周末行程…」 matches neither the HTTP pattern nor the no-answer pattern, so the
first version of `derive_label` would have called that LIVE. A skeleton is not a state - so the skeleton
condition is now checked FIRST and yields `None`. That makes the derivation stricter, and the two-sided
self-check at the bottom of this file proves both directions.
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
HTTP_SEEN = re.compile(r"HTTP ?\d{3}")
NO_ANSWER_SEEN = re.compile(r"一个字也没回答|没有任何回答|没有回音|没有说话|请求超时|连不上")
SKELETON = re.compile(r"正在准备城市周末行程|锚点 · 住宿")


def derive_label(text: str, skeleton: bool) -> str | None:
    if not text.strip() or skeleton:
        return None                      # never reached a classification at all
    if HTTP_SEEN.search(text):
        return "ORIGIN_ERROR_WITH_SNAPSHOT"
    if NO_ANSWER_SEEN.search(text):
        return "NETWORK_UNREACHABLE_WITH_SNAPSHOT"
    return "LIVE"


S1 = {"rendered_text": "菜单 | / | 今天 | 跟随系统 | EN | DE | 晚上好 | Demo之旅 | 10月10日 09:00 — 10月10日 19:00 · 1 位旅行者 · 1 天 | AI 帮我规划 | 试用其他城市 | 打开行程工作台 | 今天 | 还没有安排",
      "network_words": [], "service_words": ["服务器"], "snapshot_words": [],
      "navigator_onLine": True, "snapshot_rows": 1, "skeleton_sentence_present": False,
      "buttons": ["今天", "实时行程", "地图", "行程工作台", "住宿选择", "城市探索", "旅行票夹",
                  "Copilot", "恢复与执行", "智能守护", "旅行者画像", "菜单", "AI 帮我规划"],
      "origin_answer": {"status": 200, "thrown": False,
                        "wire": "curl via :4414 /api/v1/health -> 200; journeys/<marker id> -> 200; "
                                "the same id via :8411 direct -> 200"},
      "read_at_rel_ms": 49465,
      "extra_note": "the release generation already carries the honest cursor sentence: 服务器没有给出这一分钟"
                    "的执行游标，这一屏的时间按行程的时间窗来读 (that is 0261/0264 territory, not 0263)"}

S2 = {"rendered_text": "服务器 | 服务器这次没能把行程读出来 | 服务器自己报错了（HTTP 500）。这是它那边的问题，"
                       "不是你填错了什么。可以重试；如果一直这样，稍后再来。 | 重试 | 归因详情",
      "network_words": [], "service_words": ["服务器", "报错", "HTTP 500"], "snapshot_words": [],
      "navigator_onLine": True, "snapshot_rows": 1, "skeleton_sentence_present": False,
      "buttons": ["重试"],
      "origin_answer": {"status": 500, "thrown": False, "ct": "text/plain via my preview proxy",
                        "wire": "no listener on :8411; curl via :4414 /api/v1/health -> 500 text/plain in "
                                "0.039s, /api/v1/journeys/<id> -> 500 in 0.002s, /v8/hub -> 200 in 0.003s"},
      "read_at_rel_ms": 51285,
      "timeline": {"sample_ms": 400, "samples": 109, "first_sample_ms": 8077, "last_sample_ms": 51285,
                   "skeleton_samples": 0, "labelled_samples": 109},
      "extra_note": "half-fixed on this generation: it no longer blames the traveller's network AND it names "
                    "the HTTP status, but a saved snapshot that really is in IndexedDB (1 row) is neither "
                    "named nor offered - there is no 看已保存的只读副本 door"}

S3 = {"rendered_text": "CN | 正在准备城市周末行程… | 锚点 · 住宿 · 出行事实 · 可行性",
      "network_words": [], "service_words": [], "snapshot_words": [],
      "navigator_onLine": True, "snapshot_rows": 1, "skeleton_sentence_present": True,
      "buttons": [],
      "origin_answer": {"status": None, "thrown": True,
                        "wire": "silent listener on :8411 accepts TCP and never answers nor closes; "
                                "curl via :4414 /api/v1/health -> 000 after 8.0s, /v8/hub -> 200 in 0.003s"},
      "timeline": {"sample_ms": 400, "samples": 186, "first_sample_ms": 10605, "last_sample_ms": 84610,
                   "skeleton_samples": 186, "labelled_samples": 0},
      "seconds_to_settle": None, "settled_within_deadline": False,
      "extra_note": "84.0 s of observation, every sample the same skeleton, zero buttons: the read never "
                    "settles because nothing in this generation bounds it"}

S4 = {"rendered_text": "服务器 | 服务器这次没能把行程读出来 | 服务器自己报错了（HTTP 500）。这是它那边的问题，"
                       "不是你填错了什么。可以重试；如果一直这样，稍后再来。 | 重试 | 归因详情",
      "network_words": [], "service_words": ["服务器", "报错", "HTTP 500"], "snapshot_words": [],
      "navigator_onLine": True, "snapshot_rows": 1, "skeleton_sentence_present": False,
      "buttons": ["重试"],
      "health_answer": {"status": 500, "thrown": False, "ct": "application/json",
                        "wire": "curl via :4414 /api/v1/health -> 500 application/json in 0.003s"},
      "read_never_answered": True,
      "read_wire": "curl via :4414 /api/v1/journeys/<id> -> 000 after 14.0s (instrument hangs 40 s then "
                   "closes the socket)",
      "timeline": {"sample_ms": 400, "samples": 131, "first_sample_ms": 12735, "last_sample_ms": 64720,
                   "skeleton_samples": 69, "labelled_samples": 62,
                   "last_skeleton_ms": 39910, "first_labelled_ms": 40311},
      "seconds_to_settle": 40.3, "settled_within_deadline": False,
      "extra_note": "IMPORTANT validity limit: the sentence only appeared at 40.311 s, which is my own "
                   "instrument closing the socket after HANG_SECONDS=40 - not a bound inside the product. "
                   "Had the origin held the connection open, this cell would still be a skeleton, exactly "
                   "like S3. So this generation does not classify the state; my instrument ended the read "
                   "for it, and the classification it then produced is the same S2 sentence, which also "
                   "never mentions the local snapshot"}


def cell(d: dict) -> dict:
    out = dict(d)
    out["classified_label"] = derive_label(d["rendered_text"], d["skeleton_sentence_present"])
    out["snapshot_present"] = d["snapshot_rows"] == 1
    out["doors"] = {"retry": sum(1 for b in d["buttons"] if b.strip() == "重试"),
                    "read_only_snapshot": sum(1 for b in d["buttons"] if "只读副本" in b)}
    out.setdefault("settled_within_deadline", True)
    if "seconds_to_settle" not in out:
        out["seconds_to_settle"] = round(out.get("read_at_rel_ms", 0) / 1000, 1)
    return out


def selfcheck_derivation() -> list:
    """Both directions, so the stricter rule is not just a convenient excuse."""
    rows = [
        {"case": "skeleton text with no HTTP and no no-answer word", "text": S3["rendered_text"],
         "skeleton": True, "expect": None, "got": derive_label(S3["rendered_text"], True)},
        {"case": "answered 500 sentence", "text": S2["rendered_text"], "skeleton": False,
         "expect": "ORIGIN_ERROR_WITH_SNAPSHOT", "got": derive_label(S2["rendered_text"], False)},
        {"case": "healthy today screen must not become a classification", "text": S1["rendered_text"],
         "skeleton": False, "expect": "LIVE", "got": derive_label(S1["rendered_text"], False)},
        {"case": "B's own no-answer sentence (cross-check against the shipped fix)",
         "text": "没有回音 | 等了 12 秒，这台服务器一个字也没回答", "skeleton": False,
         "expect": "NETWORK_UNREACHABLE_WITH_SNAPSHOT",
         "got": derive_label("没有回音 | 等了 12 秒，这台服务器一个字也没回答", False)},
    ]
    for r in rows:
        r["match"] = r["expect"] == r["got"]
    return rows


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = selfcheck_derivation()
    for r in rows:
        print(f"  [{'OK ' if r['match'] else 'BAD'}] {r['case']:60s} {r['got']}")
    if not all(r["match"] for r in rows):
        print("ABORT: my own label derivation does not pass its two-sided check")
        return 2
    cap = {"at": NOW,
           "subject": "RELEASE GENERATION served to the user's phone: index-D76m_cky.js / "
                      "index-I45CQek8.css, built from landed tip d2665e2 (0261/0264 wizard fixes), "
                      "does NOT contain ORD-0263 - B's candidate is not landed",
           "generation_fingerprint": {"disk_root_read_only": r"D:\moodle\_qoder_preview_20260920\dist",
                                      "files": 29, "bytes": 14518104,
                                      "tree_sha256": "54d2da94b4aa00dc23c615e1a7f3677f1bddf742a50991e2a263bf990e287538",
                                      "index_html_mtime": "2026-09-23T20:05",
                                      "rebuilt": False,
                                      "my_byte_identical_copy": str(BASE / "livegen" / "dist")},
           "surface": {"shell": "vite preview :4414 (my port, my copy of the bundle)",
                       "origin": "my :8411",
                       "chrome_context": "one context; snapshot earned through the app's own "
                                         "「使用封存的演示行程」 control before the states were swapped; "
                                         "snapshot_rows=1 in every reading",
                       "product_code_edited": False, "gauge_edited": False,
                       "user_chain_ports_contacted": [], "user_db_files_opened": [],
                       "demo_reset_issued": False},
           "label_derivation": {"rule": "skeleton-present or empty text => None (no classification); "
                                        "otherwise HTTP status => ORIGIN_ERROR_WITH_SNAPSHOT; "
                                        "no-answer wording => NETWORK_UNREACHABLE_WITH_SNAPSHOT; "
                                        "otherwise LIVE",
                                "checked_against": rows, "typed_in_by_verifier": False},
           "cells": {"S1_live": cell(S1), "S2_origin_error": cell(S2), "S3_no_answer": cell(S3),
                     "S4_read_silent_health_answered": cell(S4)},
           "state_instrumentation": [
               "S1: real uvicorn on :8411 over db/canary_8411.db (marker row + journey 200 both ways)",
               "S2: no listener on :8411 -> my preview proxy answers 500",
               "S4: tools/mixed_origin_port.py -> /api/v1/health 500 json, every other path hangs 40 s",
               "S3: tools/silent_api_port.py -> accepts TCP, never answers, never closes"],
           "decisive_datum": "on this generation S3 spends 84.0 s (186/186 samples) on 「正在准备城市周末行程…」 "
                             "with ZERO buttons and a real saved snapshot (1 row) in IndexedDB; and S4 only "
                             "leaves the skeleton because MY instrument closed the socket at 40 s"}
    p = BASE / "ord0263_capture_releasegen.json"
    p.write_text(json.dumps(cap, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    b = p.read_bytes()
    for k, v in cap["cells"].items():
        print(f"{k:34s} label={str(v['classified_label']):32s} snapshot_words="
              f"{'yes' if re.search('本地快照|已保存的行程|只读的已保存', v['rendered_text']) else 'NO'}")
    print(f"[write] {p.name} {len(b):,} B  blob {hashlib.sha1(b'blob %d\x00' % len(b) + b).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
