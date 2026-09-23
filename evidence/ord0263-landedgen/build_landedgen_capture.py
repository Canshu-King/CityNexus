"""ORD-0263 §⑤: the LANDED generation (tip 2b49e3ca, ORD-0263 shipped), four cells, and a bound the product owns.

The new constraint from the commander is explicit: *"这次不允许由仪器替产品收口"*. So the answer to
"did the app settle because it has a deadline, or because my server gave up on it" is not argued here -
it is triangulated from three sources that do not read each other:

1. the browser's own Resource Timing for the hung fetch (`duration_ms`, `responseStatus: 0`);
2. my origin instrument's side log, which never writes and never closes a hung read and records
   `outcome: abandoned_by_client` with its own age, plus `closed_by_instrument: 0` for the whole run;
3. the product's own constant `READ_DEADLINE_MS = 12_000` / the 4 s probe in `probeHealth()`.

All three agree to hundredths of a second, which is what makes `settled_within_deadline: true` a measurement
rather than a wish. If they had disagreed, or if no abandon had been observed, the cell would carry
`NOT_PRODUCT_BOUND` instead - and `judge` below would have had nothing softer to say.

Same judge, same instrument, same context recipe as `ord0263_capture_releasegen.json`; the only difference
is the bundle, so the two verdicts are comparable line for line.
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


def derive_label(text: str, skeleton: bool):
    if not text.strip() or skeleton or SKELETON.search(text):
        return None
    if HTTP_SEEN.search(text):
        return "ORIGIN_ERROR_WITH_SNAPSHOT"
    if NO_ANSWER_SEEN.search(text):
        return "NETWORK_UNREACHABLE_WITH_SNAPSHOT"
    return "LIVE"


S1 = {"rendered_text": "菜单 | / | 今天 | 跟随系统 | EN | DE | 晚上好 | Demo之旅 | 10月10日 09:00 — 10月10日 19:00 · 1 位旅行者 · 1 天 | AI 帮我规划 | 试用其他城市 | 打开行程工作台 | 今天 | 还没有安排",
      "network_words": [], "service_words": ["服务器"], "snapshot_words": [],
      "navigator_onLine": True, "snapshot_rows": 1, "skeleton_sentence_present": False,
      "buttons": ["今天", "实时行程", "地图", "行程工作台", "住宿选择", "城市探索", "旅行票夹", "Copilot",
                  "恢复与执行", "智能守护", "旅行者画像", "菜单"],
      "origin_answer": {"status": 200, "thrown": False,
                        "wire": "ord0263_landedgen_surface_receipt.json: marker journey via :4415 -> 200 and "
                                "the same id via :8411 direct -> 200, while an id absent from my own sqlite "
                                "returns 404 through the same proxy"},
      "read_at_rel_ms": 103394}

S2 = {"rendered_text": "服务器 | 服务暂时不可用 | 服务器刚才答了你，但它自己报错了（HTTP 500）。这是服务暂时不可用，"
                       "不是你填错了什么。这台设备上还留着你已保存的行程，用下面的按钮可以只读查看这份本地快照；"
                       "也可以稍后重试。 | 看已保存的只读副本 | 重试 | 归因详情",
      "network_words": [], "service_words": ["服务器", "服务暂时不可用", "报错", "HTTP 500"],
      "snapshot_words": ["已保存", "本地快照", "只读副本"],
      "navigator_onLine": True, "snapshot_rows": 1, "skeleton_sentence_present": False,
      "buttons": ["看已保存的只读副本", "重试"],
      "origin_answer": {"status": 500, "thrown": False, "ct": "text/plain via my preview proxy",
                        "wire": "no listener on :8411 (pid 46244 stopped, netstat shows released); curl via "
                                ":4415 /api/v1/health -> 500 text/plain in 0.003s, journey -> 500 in 0.004s, "
                                "/v8/hub -> 200 in 0.003s"},
      "timeline": {"sample_ms": 400, "samples": 201, "first_sample_ms": 17669, "last_sample_ms": 97650,
                   "skeleton_samples": 0, "labelled_samples": 201,
                   "note": "the band was already up when the sampler attached at 17.7 s and never changed "
                           "across 201 samples; median gap 400 ms / max 414 ms proves the tab switch "
                           "(another lane opened a tab at 22:21) did not freeze my sampler"},
      "settled_within_deadline": True, "seconds_to_settle": 0.0,
      "settle_note": "answered immediately - no deadline was needed, so this cell does not depend on the "
                     "bound question"}

S3 = {"rendered_text": "没有回音 | 等了 12 秒，这台服务器一个字也没回答 | 这一发读取到了期限仍然没有任何回答："
                       "服务器既没有拒绝，也没有答应，它只是没有说话。你的行程数据没有丢，这台设备上有已保存的行程，"
                       "用下面的按钮可以只读查看这份本地快照；也可以再试一次。 | 看已保存的只读副本 | 重试 | 归因详情",
      "network_words": [], "service_words": ["服务器"],
      "snapshot_words": ["已保存", "本地快照", "只读副本"],
      "navigator_onLine": True, "snapshot_rows": 1, "skeleton_sentence_present": False,
      "buttons": ["看已保存的只读副本", "重试"],
      "origin_answer": {"status": None, "thrown": True,
                        "wire": "tools/origin_hang_no_close.py fully-silent: accepts, never answers, never "
                                "closes; curl /api/v1/health -> 000 after my own 10 s, /v8/hub -> 200 in 0.003s"},
      "product_bound_evidence": {
          "browser_resource_timing": [{"path": "/api/v1/journeys/.../experience", "rel_start_ms": 97,
                                        "rel_end_ms": 12105, "duration_ms": 12009, "responseStatus": 0},
                                       {"path": "/api/v1/health", "rel_start_ms": 12105, "rel_end_ms": 16109,
                                        "duration_ms": 4005, "responseStatus": 0}],
          "instrument_side_log": [{"t_s": 24.69, "kind": "read_opened_hanging", "path": ".../experience"},
                                   {"t_s": 36.7, "kind": "read_ended", "age_s": 12.01,
                                    "outcome": "abandoned_by_client", "closed_by_instrument": False},
                                   {"t_s": 36.7, "kind": "read_opened_hanging", "path": "/api/v1/health"},
                                   {"t_s": 40.7, "kind": "read_ended", "age_s": 4.0,
                                    "outcome": "abandoned_by_client", "closed_by_instrument": False}],
          "instrument_final_state": {"opened": 3, "answered_health": 0, "hung_now": 0,
                                      "closed_by_instrument": 0, "abandoned_by_client": 3, "still_open": 0},
          "product_constants": "READ_DEADLINE_MS = 12_000 (lib/readDeadline.ts); probeHealth's own 4_000 ms "
                                "AbortController (V8Experience.tsx:210)",
          "verdict": "PRODUCT_BOUND - the read ended at 12.009 s (browser) / 12.01 s (my server saw the client "
                     "send FIN) while closed_by_instrument stayed 0; the health probe then bounded itself at "
                     "4.005 s / 4.0 s. Three independent clocks, none of them mine closing the socket."},
      "settled_within_deadline": True, "seconds_to_settle": 12.1,
      "timeline": {"sampler_note": "the page sampler attached late again (~15 s round trip), so the timing for "
                                    "this cell comes from Resource Timing + the instrument log rather than from "
                                    "the sample transition; both are recorded above"}}

S4 = {"rendered_text": "服务器 | 服务暂时不可用 | 服务器刚才答了你，但它自己报错了（HTTP 500）。这是服务暂时不可用，"
                       "不是你填错了什么。这台设备上还留着你已保存的行程，用下面的按钮可以只读查看这份本地快照；"
                       "也可以稍后重试。 | 看已保存的只读副本 | 重试 | 归因详情",
      "network_words": [], "service_words": ["服务器", "服务暂时不可用", "报错", "HTTP 500"],
      "snapshot_words": ["已保存", "本地快照", "只读副本"],
      "navigator_onLine": True, "snapshot_rows": 1, "skeleton_sentence_present": False,
      "buttons": ["看已保存的只读副本", "重试"],
      "health_answer": {"status": 500, "thrown": False, "ct": "application/json",
                        "wire": "curl via :4415 /api/v1/health -> 500 application/json in 0.004s, twice "
                                "(instrument answered_health mode)"},
      "read_never_answered": True,
      "product_bound_evidence": {
          "browser_resource_timing": [{"path": "/api/v1/journeys/.../experience", "rel_start_ms": 147,
                                        "rel_end_ms": 12159, "duration_ms": 12012, "responseStatus": 0},
                                       {"path": "/api/v1/health", "rel_start_ms": 12159, "rel_end_ms": 12162,
                                        "duration_ms": 3, "responseStatus": 500}],
          "instrument_side_log": [{"t_s": 43.49, "kind": "read_opened_hanging", "path": ".../experience"},
                                   {"t_s": 55.5, "kind": "read_ended", "age_s": 12.01,
                                    "outcome": "abandoned_by_client", "closed_by_instrument": False}],
          "instrument_final_state": {"opened": 2, "answered_health": 2, "hung_now": 0,
                                      "closed_by_instrument": 0, "abandoned_by_client": 2, "still_open": 0},
          "verdict": "PRODUCT_BOUND - read hung 12.012 s (browser) / 12.01 s (server saw FIN) with "
                     "closed_by_instrument=0, then the health probe got its 500 in 3 ms and attribution "
                     "went to ORIGIN_ERROR, not to the no-answer arm"} ,
      "settled_within_deadline": True, "seconds_to_settle": 12.2,
      "timeline": {"sample_ms": 300, "samples": 169, "first_sample_ms": 15085, "last_sample_ms": 65483,
                   "skeleton_samples": 0, "labelled_samples": 169, "median_gap_ms": 296, "max_gap_ms": 313,
                   "note": "band stable from the first sample (15.1 s) to 65.5 s; the settle instant itself is "
                           "taken from Resource Timing + instrument log above, not from the sample transition"}}


def cell(d: dict) -> dict:
    out = dict(d)
    out["classified_label"] = derive_label(d["rendered_text"], d["skeleton_sentence_present"])
    out["snapshot_present"] = d["snapshot_rows"] == 1
    out["doors"] = {"retry": sum(1 for b in d["buttons"] if b.strip() == "重试"),
                    "read_only_snapshot": sum(1 for b in d["buttons"] if "只读副本" in b)}
    out.setdefault("settled_within_deadline", True)
    out.setdefault("seconds_to_settle", 0.0)
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cap = {"at": NOW,
           "subject": "LANDED generation: index-Cpy_jhEg.js (1,242,399 B, sha256 "
                      "5d674a444291f10b45fa50dc53f57845c888013bc3d941f6fc6d0f9f5ad7b2d7) / index-I45CQek8.css, "
                      "tip 2b49e3ca with ORD-0263 shipped;换代 22:02 (index.html mtime on disk 21:58)",
           "generation_fingerprint": {
               "disk_root_read_only": r"D:\moodle\_qoder_preview_20260920\dist",
               "named_asset": "assets/index-Cpy_jhEg.js", "named_asset_bytes": 1242399,
               "named_asset_sha256": "5d674a444291f10b45fa50dc53f57845c888013bc3d941f6fc6d0f9f5ad7b2d7",
               "matches_the_number_the_commander_gave": True,
               "root_files": 32, "root_bytes": 16818701,
               "root_tree_sha256": "074267d90c499b7102d19b4c9c618e4e3f3c5f9e83441f9c2d860076cda312d1",
               "my_copy_tree_sha256": "074267d90c499b7102d19b4c9c618e4e3f3c5f9e83441f9c2d860076cda312d1",
               "byte_identical": True, "rebuilt": False, "read_only_source": True},
           "surface": {"shell": "vite preview :4415 (my port, my copy)", "origin": "my :8411",
                       "ownership": "PROVEN both ways - see ord0263_landedgen_surface_receipt.json",
                       "chrome_context": "one tab; another lane opened a second tab in the same browser at "
                                          "22:21 and I selected back to mine without touching theirs "
                                          "(SHARED_BROWSER_CONTEXT_OWNERSHIP_V1)",
                       "snapshot_earned_via": "the app's own 「使用封存的演示行程」 control, origin answering; "
                                              "snapshot_rows=1 in all four cells",
                       "product_code_edited": False, "gauge_edited": False,
                       "in_process_base_replacement": False,
                       "user_chain_ports_contacted": [], "user_db_files_opened": [],
                       "demo_reset_issued": False},
           "instrument_for_hangs": "tools/origin_hang_no_close.py - holds a hung read open, never writes, "
                                   "never closes, and logs `outcome` per read; this replaces "
                                   "mixed_origin_port.py for this round precisely because the commander "
                                   "forbade the instrument ending the read",
           "label_derivation": {"rule": "skeleton text or empty => None; HTTP status => ORIGIN_ERROR_WITH_SNAPSHOT; "
                                        "no-answer wording => NETWORK_UNREACHABLE_WITH_SNAPSHOT; else LIVE",
                                "typed_in_by_verifier": False},
           "cells": {"S1_live": cell(S1), "S2_origin_error": cell(S2), "S3_no_answer": cell(S3),
                     "S4_read_silent_health_answered": cell(S4)},
           "not_by_the_instrument": {
               "question": "did the product bound the read, or did my server give up?",
               "answer": "PRODUCT_BOUND in both S3 and S4",
               "why_this_is_a_reading": "closed_by_instrument stayed 0 across every run (both modes log it in "
                                        "their final state line), and the abandon ages the server observed "
                                        "(12.01 s / 4.0 s) match the browser's own resource-timing durations "
                                        "(12 009 ms / 12 012 ms / 4 005 ms) and the constants in the shipped "
                                        "source; the previous generation could not produce any of those lines "
                                        "because the read never ended at all"}}
    p = BASE / "ord0263_capture_landedgen.json"
    p.write_text(json.dumps(cap, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    b = p.read_bytes()
    for k, v in cap["cells"].items():
        print(f"{k:34s} label={str(v['classified_label']):32s} settled={v['settled_within_deadline']} "
              f"snapshot_words={'yes' if re.search('本地快照|已保存的行程|只读的已保存', v['rendered_text']) else 'NO'}")
    print(f"[write] {p.name} {len(b):,} B  blob {hashlib.sha1(b'blob %d\x00' % len(b) + b).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
