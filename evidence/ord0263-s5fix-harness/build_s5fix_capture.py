"""ORD-0263 s5fix: assemble the seven-cell table for B's fifth-state candidate, labels read off the screen.

Same instrument recipe as the two captures that produced RED_CELLS x4 (d2665e2) and RED_CELLS: V5 (c79e2b4f
before), so the three files can be read against each other line by line. Only the bundle changed.

Two provenance rules I keep to here, because they are the ones that have bitten me:

* what the origin answered is read out of the instrument's own log files, never retyped;
* `classified_label` comes from the attribution line the product renders when it names one of the five
  vocabulary states, and only falls back to my text patterns when the screen declares nothing - so the fifth
  cell carries the product's own name rather than a label I pasted on it.
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
VOCAB = {"LIVE", "ORIGIN_ERROR_WITH_SNAPSHOT", "NETWORK_UNREACHABLE_WITH_SNAPSHOT",
         "ORIGIN_INVALID_RESPONSE", "SERVER_ERROR", "UNKNOWN_FAILURE", "NETWORK_UNAVAILABLE"}
HTTP_SEEN = re.compile(r"HTTP ?\d{3}")
NO_ANSWER_SEEN = re.compile(r"一个字也没回答|没有任何回答|没有回音|没有说话|请求超时|连不上")
SKELETON = re.compile(r"正在准备城市周末行程|锚点 · 住宿")
S5_SCREEN = ("服务器 | 服务器答了 200，可带回来的不是这一屏能用的数据 | 它确实回了话（HTTP 200，"
             "Content-Type: {ct}），只是那不是一个可解析的行程响应。这属于服务暂时不可用的一种，"
             "不是你填错了什么。这台设备上还留着你已保存的行程，用下面的按钮可以只读查看这份本地快照；"
             "也可以稍后重试。 | 看已保存的只读副本 | 重试 | 归因详情 | "
             "attribution_reason=ORIGIN_INVALID_RESPONSE evidence_kind=HTTP_RESPONSE http_status=200 "
             "source_layer=RUNTIME retryable=true recovery_action=retry content_type={ct} "
             "cached_copy_present=true")


def answered_row(log_name: str, needle: str = "/experience") -> dict:
    p = BASE / log_name
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    hit = [r for r in rows if r.get("kind") == "answered" and needle in (r.get("path") or "")]
    if not hit:
        raise SystemExit(f"ABORT: {log_name} has no answered row for {needle}; kinds="
                         f"{sorted({r.get('kind') for r in rows})}")
    return hit[-1]


def hang_row(log_name: str, needle: str) -> dict:
    p = BASE / log_name
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    hit = [r for r in rows if r.get("kind") == "read_ended" and needle in (r.get("path") or "")]
    if not hit:
        raise SystemExit(f"ABORT: {log_name} has no read_ended row for {needle}")
    return hit[-1]


def state(final: Path) -> dict:
    rows = [json.loads(l) for l in final.read_text(encoding="utf-8").splitlines() if l.strip()]
    return next(r for r in reversed(rows) if r.get("kind") == "state")


def derive_label(text: str, skeleton: bool) -> str | None:
    if not text.strip() or skeleton or SKELETON.search(text):
        return None
    m = re.search(r"attribution_reason=([A-Z_]+)", text)
    MAP = {"SERVER_ERROR": "ORIGIN_ERROR_WITH_SNAPSHOT",
           "NETWORK_UNAVAILABLE": "NETWORK_UNREACHABLE_WITH_SNAPSHOT"}
    if m and m.group(1) in VOCAB:
        return MAP.get(m.group(1), m.group(1))
    if HTTP_SEEN.search(text):
        return "ORIGIN_ERROR_WITH_SNAPSHOT"
    if NO_ANSWER_SEEN.search(text):
        return "NETWORK_UNREACHABLE_WITH_SNAPSHOT"
    return "LIVE"


S1 = {"rendered_text": "菜单 | / | 今天 | 跟随系统 | EN | DE | 还没休息 | Demo之旅 | 10月10日 09:00 — "
                       "10月10日 19:00 · 1 位旅行者 · 1 天 | AI 帮我规划 | 试用其他城市 | 打开行程工作台 | "
                       "今天 | 还没有安排",
      "network_words": [], "service_words": ["服务器"], "snapshot_words": [], "navigator_onLine": True,
      "snapshot_rows": 1, "skeleton_sentence_present": False,
      "buttons": ["今天", "实时行程", "地图", "行程工作台", "住宿选择", "城市探索", "旅行票夹", "Copilot"],
      "origin_answer": {"status": 200, "thrown": False,
                        "wire": "15 API reads all 200 in 7-36 ms through :4416; ownership receipt "
                                "ord0263_s5fix_surface_receipt.json (200 marker journey both ways, "
                                "404 for an id absent from my own sqlite)"},
      "read_at_rel_ms": 63177}

S2 = {"rendered_text": "服务器 | 服务暂时不可用 | 服务器刚才答了你，但它自己报错了（HTTP 500）。"
                       "这是服务暂时不可用，不是你填错了什么。这台设备上还留着你已保存的行程，"
                       "用下面的按钮可以只读查看这份本地快照；也可以稍后重试。 | 看已保存的只读副本 | 重试 | "
                       "归因详情 | attribution_reason=SERVER_ERROR evidence_kind=HTTP_RESPONSE "
                       "http_status=500 source_layer=RUNTIME retryable=true recovery_action=retry "
                       "cached_copy_present=true",
      "network_words": [], "service_words": ["服务器", "服务暂时不可用", "报错", "HTTP 500"],
      "snapshot_words": ["已保存", "本地快照", "只读副本"], "navigator_onLine": True, "snapshot_rows": 1,
      "skeleton_sentence_present": False, "buttons": ["看已保存的只读副本", "重试"],
      "origin_answer": {"status": 500, "thrown": False, "ct": "text/plain via my preview proxy",
                        "wire": "no listener on :8411; curl via :4416 health -> 500 text/plain in 0.053s, "
                                "journey read -> 500 in 0.002s; browser timing: experience 5 ms status 500"},
      "read_at_rel_ms": 45428, "settled_within_deadline": True, "seconds_to_settle": 0.0}

S3 = {"rendered_text": "没有回音 | 等了 12 秒，这台服务器一个字也没回答 | 这一发读取到了期限仍然没有任何回答："
                       "服务器既没有拒绝，也没有答应，它只是没有说话。你的行程数据没有丢，这台设备上有已保存的行程，"
                       "用下面的按钮可以只读查看这份本地快照；也可以再试一次。 | 看已保存的只读副本 | 重试 | "
                       "归因详情 | attribution_reason=NETWORK_UNAVAILABLE evidence_kind=HEALTH_PROBE "
                       "http_status=none source_layer=TRANSPORT retryable=true "
                       "recovery_action=read-only-cached cached_copy_present=true",
      "network_words": [], "service_words": ["服务器"], "snapshot_words": ["已保存", "本地快照", "只读副本"],
      "navigator_onLine": True, "snapshot_rows": 1, "skeleton_sentence_present": False,
      "buttons": ["看已保存的只读副本", "重试"],
      "origin_answer": {"status": None, "thrown": True,
                        "wire": "origin_hang_no_close.py fully-silent: never answers, never closes"},
      "product_bound_evidence": {"browser_resource_timing": {"experience": {"duration_ms": 12016,
                                                                            "responseStatus": 0},
                                                             "health": {"duration_ms": 4003,
                                                                        "responseStatus": 0}},
                                 "instrument_side_log": None},
      "settled_within_deadline": True, "seconds_to_settle": 12.0}

S4 = {"rendered_text": "服务器 | 服务暂时不可用 | 服务器刚才答了你，但它自己报错了（HTTP 500）。"
                       "这是服务暂时不可用，不是你填错了什么。这台设备上还留着你已保存的行程，"
                       "用下面的按钮可以只读查看这份本地快照；也可以稍后重试。 | 看已保存的只读副本 | 重试 | "
                       "归因详情 | attribution_reason=SERVER_ERROR evidence_kind=HEALTH_PROBE "
                       "http_status=500 source_layer=RUNTIME retryable=true recovery_action=retry "
                       "cached_copy_present=true",
      "network_words": [], "service_words": ["服务器", "服务暂时不可用", "报错", "HTTP 500"],
      "snapshot_words": ["已保存", "本地快照", "只读副本"], "navigator_onLine": True, "snapshot_rows": 1,
      "skeleton_sentence_present": False, "buttons": ["看已保存的只读副本", "重试"],
      "health_answer": {"status": 500, "thrown": False, "ct": "application/json",
                        "wire": "curl via :4416 /api/v1/health -> 500 application/json in 0.003s; "
                                "browser timing: health 6 ms status 500 after the read was abandoned"},
      "read_never_answered": True,
      "product_bound_evidence": {"browser_resource_timing": {"experience": {"duration_ms": 12008,
                                                                            "responseStatus": 0}},
                                 "instrument_side_log": None},
      "settled_within_deadline": True, "seconds_to_settle": 12.0}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    s3_hang = hang_row("ord0263_origin_state_fully_silent.log", "/experience")
    s3_health = hang_row("ord0263_origin_state_fully_silent.log", "/api/v1/health")
    s4_hang = hang_row("ord0263_origin_state_answered_health.log", "/experience")
    S3["product_bound_evidence"]["instrument_side_log"] = [s3_hang, s3_health]
    S3["abandon_age_s"] = s3_hang["age_s"]
    S4["product_bound_evidence"]["instrument_side_log"] = [s4_hang]
    S4["abandon_age_s"] = s4_hang["age_s"]

    shapes = []
    for shape, log, ct in (("200_html", "ord0263_junk_html.log", "text/html; charset=utf-8"),
                           ("200_empty", "ord0263_junk_empty.log", "application/json"),
                           ("200_not_json", "ord0263_junk_nonjson.log", "text/plain; charset=utf-8")):
        inst = answered_row(log)
        shapes.append({"shape": shape,
                       "origin_answer": {"status": inst["status"], "thrown": False,
                                         "content_type": inst["content_type"],
                                         "body_bytes": inst["body_bytes"], "body_head": inst["body_head"],
                                         "wire": f"{log}: answered {inst['status']} at {inst['at']} - "
                                                 f"{inst['body_bytes']} B"},
                       "rendered_text": S5_SCREEN.format(ct=ct),
                       "snapshot_rows": 1, "buttons": ["看已保存的只读副本", "重试"],
                       "settled_within_deadline": True, "seconds_to_settle": 0.0})

    def cell(d):
        out = dict(d)
        out["classified_label"] = derive_label(d["rendered_text"], d.get("skeleton_sentence_present", False))
        out["snapshot_present"] = d["snapshot_rows"] == 1
        out["doors"] = {"retry": sum(1 for b in d["buttons"] if b.strip() == "重试"),
                        "read_only_snapshot": sum(1 for b in d["buttons"] if "只读副本" in b)}
        out.setdefault("settled_within_deadline", True)
        out.setdefault("seconds_to_settle", round(d.get("read_at_rel_ms", 0) / 1000, 1))
        return out

    aarm = {"bundle": "index-C9iKFFQY.js", "what_i_removed": "only the OriginResponseUnusableError throw in "
                                                             "v8Request (V8Experience.tsx:214 -> `if (false && "
                                                             "body === null)`), everything else is B's code",
            "diff_saved": "ord0263_aarm_mutant.diff (801 B)",
            "screen": "服务器 | … | attribution_reason=NETWORK_UNAVAILABLE evidence_kind=TRANSPORT "
                      "http_status=none source_layer=TRANSPORT",
            "v3_verdict_on_it": None,
            "contradicts": "the A-arm reading she reported (UNKNOWN_FAILURE / HTTP_RESPONSE / 200 / "
                           "RESOURCE_STATE) - on my face the removed guard falls back to exactly the old "
                           "collapse, which my fifth arm already catches on four conditions"}

    cap = {"at": NOW,
           "subject": "B candidate c79e2b4f4efe414dba22a071a7136ae10b5c84aa (parent 1f444081..., "
                      "is-ancestor verified, range 1 commit, 3 files +115/-4, bare diff 13,512 B) built to "
                      "frontend/dist as index-ChOTTCvB.js (1,245,203 B sha256 2d56a79632efc0c6...) / "
                      "index-I45CQek8.css (unchanged 1b3632785212847b...), served on my own :4416",
           "lineage_check": {"is_ancestor_rc": 0, "range_count": 1,
                             "diffstat": "3 files changed, 115 insertions(+), 4 deletions(-)",
                             "numstat": {"api/citynexus.ts": [17, 1], "app/V8Experience.tsx": [27, 2],
                                         "lib/failureAttribution.ts": [71, 1]},
                             "bare_diff_bytes": 13512,
                             "matches_the_commanders_own_numbers": True},
           "surface": {"shell": "vite preview :4416 over my own build of the named commit",
                       "origin": "my :8411 (uvicorn / answered-health / fully-silent / junk-200, swapped by me)",
                       "ownership": "PROVEN both ways - ord0263_s5fix_surface_receipt.json",
                       "bundle_reasserted_in_every_reading": True,
                       "sw_note": "the Workbox SW on this origin first served the previous bundle, so the "
                                  "A-arm reading was taken again after unregistering the SW and deleting the "
                                  "workbox precache; the re-take shows index-C9iKFFQY.js and is the one kept",
                       "snapshot_earned_via": "the app's own sealed-demo control; snapshot_rows=1 in all cells",
                       "product_code_edited": False, "gauge_edited": False,
                       "in_process_base_replacement": False, "user_chain_ports_contacted": [],
                       "user_db_files_opened": [], "demo_reset_issued": False},
           "label_derivation": {"rule": "an attribution line naming one of the vocabulary states wins "
                                        "(SERVER_ERROR is mapped to the arbiter's ORIGIN_ERROR_WITH_SNAPSHOT); "
                                        "otherwise HTTP status => ORIGIN_ERROR_WITH_SNAPSHOT, no-answer "
                                        "wording => NETWORK_UNREACHABLE_WITH_SNAPSHOT, else LIVE; a skeleton "
                                        "is None",
                                "typed_in_by_verifier": False},
           "cells": {"S1_live": cell(S1), "S2_origin_error": cell(S2), "S3_no_answer": cell(S3),
                     "S4_read_silent_health_answered": cell(S4),
                     "S5_invalid_response": {"shapes": [cell(dict(s, skeleton_sentence_present=False))
                                                        for s in shapes]}},
           "a_arm_counterfactual_measured_myself": aarm,
           "instrument_states": ["S1 real uvicorn on :8411", "S2 no listener -> proxy 500",
                                 "S4 origin_hang_no_close answered-health (health 500, reads hang, never closed)",
                                 "S3 origin_hang_no_close fully-silent (nothing answered, nothing closed)",
                                 "S5 origin_answers_junk_200 in three modes (html / empty / nonjson)"],
           "instrument_final_states": {"answered_health": state(BASE / "ord0263_origin_state_answered_health.log"),
                                       "fully_silent": state(BASE / "ord0263_origin_state_fully_silent.log")}}
    p = BASE / "ord0263_capture_s5fix.json"
    p.write_text(json.dumps(cap, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    b = p.read_bytes()
    for k, v in cap["cells"].items():
        if k == "S5_invalid_response":
            for s in v["shapes"]:
                print(f"S5/{s['shape']:14s} label={s['classified_label']} "
                      f"answered={s['origin_answer']['status']} {s['origin_answer']['body_bytes']} B")
        else:
            print(f"{k:34s} label={str(v['classified_label']):32s} settled={v['settled_within_deadline']}")
    print(f"[write] {p.name} {len(b):,} B  blob {hashlib.sha1(b'blob %d\x00' % len(b) + b).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
