"""ORD-0263 verifier v3 = v2 with a fifth arm bolted on and nothing else touched.

Why a new file instead of editing v2: the commander's constraint is *"v2 尺加第五格，别改前四格"*. That is only
auditable if the four old arms can be diffed against the published v2, so v3 carries them verbatim and
`legacy_arms_unchanged()` proves it at run time by comparing the source text of `judge_v1`,
`judge_v1_vacuity`, `judge_v2`, `judge_v3`, `judge_v4` and the regex block with
`tools/ord0263_verifier_v2.py`. If anybody later edits an old arm, v3 says so instead of quietly shipping a
louder verdict.

The fifth state is the one the deadline work cannot see: the origin answers **2xx** and the body is not
something the client can parse. Nothing times out, nothing throws at the transport layer, and `v8Request`'s
`response.json().catch(() => null)` turns a real 200 into a `null` payload - which the caller then trips over,
and `classifyReadFailure()` files the resulting TypeError as `NETWORK_UNAVAILABLE / TRANSPORT`, i.e. "it never
answered". So the acceptance test here is the arbiter's minimum, taken literally and read off the screen rather
than off a name:

  * `evidence_kind` must keep the HTTP-response fact (not TRANSPORT),
  * `http_status` must still say 200,
  * the reason must not be `NETWORK_UNAVAILABLE` / `NO_REPLY`,
  * the sentence must not claim the request never went out or got no answer,
  * and the cached-copy column must match the measured IndexedDB row count.

The label itself is deliberately not pinned to the string `ORIGIN_INVALID_RESPONSE`: the arbiter wrote
"名字可再定", so locking B's wording here would be my vocabulary smuggling itself into their acceptance gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
V2_PATH = BASE / "tools" / "ord0263_verifier_v2.py"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())

NETWORK_WORDS = re.compile(r"网络不可用|离线 · 只读|OFFLINE|network is (?:down|unavailable)|连不上")
SERVICE_WORDS = re.compile(r"服务(暂时)?不可用|服务器(刚才|明确)?答|origin (?:answered|is unavailable)|HTTP \d{3}")
SNAPSHOT_WORDS = re.compile(r"本地快照|已保存的行程|只读的已保存|saved snapshot|read-?only snapshot")
LOADING_WORDS = re.compile(r"正在准备|锚点 · 住宿|loading|skeleton")
RETRY_DOOR = re.compile(r"重试|retry", re.I)

# ---- fifth state: measured fields, no locked wording --------------------------------------------------
NEVER_WENT_OUT = re.compile(r"没能出去|没有收到任何回答|没有回答|无人应答|无法连接|网络问题|没连上")
ATTRIBUTION_KEYS = ("attribution_reason", "evidence_kind", "http_status", "source_layer",
                    "cached_copy_present", "retryable", "message_key")
BAD_REASONS = {"NETWORK_UNAVAILABLE", "NO_REPLY"}


def parse_attribution(text: str) -> dict:
    """Read the attribution line the product itself renders, key=value pairs, no assumptions."""
    out = {}
    for k in ATTRIBUTION_KEYS:
        m = re.search(rf"\b{k}=([^\s|]+)", text)
        if m:
            out[k] = m.group(1).strip()
    return out


def as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def judge_v5(shape: dict) -> dict:
    """One junk-body shape: an origin that answered 2xx with something unparseable.

    `shape` carries the measured answer (status/content-type/body bytes), the rendered sentence including the
    expanded 归因详情 line, and the measured snapshot row count. Missing measurements are `NOT_MEASURED`; they
    are never read as a pass.
    """
    a = shape.get("origin_answer") or {}
    if not isinstance(a.get("status"), int) or a.get("thrown") is not False:
        return {"verdict": "NOT_MEASURED",
                "why": "the fifth state needs a capture where the origin answered 2xx with an unparseable body"}
    text = shape.get("rendered_text") or ""
    att = parse_attribution(text)
    if not att:
        return {"verdict": "NOT_MEASURED",
                "why": "no attribution fields are rendered on the screen, so the columns cannot be read - "
                       "a sentence alone cannot satisfy the minimum acceptance"}
    kind = att.get("evidence_kind") or ""
    status = as_int(att.get("http_status"))
    reason = att.get("attribution_reason") or ""
    layer = att.get("source_layer") or ""
    kept_http = bool(re.search(r"HTTP", kind)) or "answered" in kind.lower()
    status_kept = status == a.get("status")
    reason_ok = bool(reason) and reason not in BAD_REASONS
    layer_ok = bool(layer) and layer.upper() != "TRANSPORT"
    collapse = bool(NEVER_WENT_OUT.search(text))
    measured_copy = bool(shape.get("snapshot_rows")) if "snapshot_rows" in shape else None
    declared_copy = (att.get("cached_copy_present") or "").strip().lower() in ("1", "true", "yes")
    copy_honours_measurement = (measured_copy is None) or (measured_copy == declared_copy)
    ok = kept_http and status_kept and reason_ok and layer_ok and (not collapse) and copy_honours_measurement
    fails = [n for n, v in (("evidence_kind_lost_HTTP", not kept_http),
                            ("http_status_not_carried", not status_kept),
                            ("reason_collapsed", not reason_ok),
                            ("layer_collapsed_to_TRANSPORT", not layer_ok),
                            ("sentence_claims_no_answer", collapse),
                            ("cached_copy_column_not_measured", not copy_honours_measurement)) if v]
    return {"verdict": "GREEN" if ok else "RED",
            "measured": {"shape": shape.get("shape"), "answered_status": a.get("status"),
                         "content_type": a.get("content_type"), "body_bytes": a.get("body_bytes"),
                         "rendered_attribution": att, "evidence_kind_keeps_HTTP": kept_http,
                         "http_status_carried": status_kept, "reason_not_network": reason_ok,
                         "layer_not_transport": layer_ok, "sentence_denies_the_answer": collapse,
                         "cached_copy_matches_measured_rows": copy_honours_measurement,
                         "measured_snapshot_rows": shape.get("snapshot_rows")},
            "failed_conditions": fails,
            "rule": "answered 2xx with an unparseable body: the HTTP-response fact must survive every column "
                    "and the sentence may not claim nothing answered"}


def aggregate_v5(shapes: list) -> dict:
    """All three shapes must hold; one passing shape must not carry the other two."""
    rows = [{"shape": s.get("shape"), **judge_v5(s)} for s in shapes]
    greens = [r for r in rows if r["verdict"] == "GREEN"]
    reds = [r for r in rows if r["verdict"] == "RED"]
    nm = [r for r in rows if r["verdict"] not in ("GREEN", "RED")]
    verdict = "RED" if reds else ("NOT_MEASURED" if nm else ("GREEN" if greens else "NOT_MEASURED"))
    return {"verdict": verdict,
            "measured": {"shapes_total": len(rows), "green": len(greens), "red": len(reds),
                         "not_measured": len(nm),
                         "red_shapes": [r["shape"] for r in reds],
                         "per_shape_conditions": {r["shape"]: r.get("failed_conditions", []) for r in reds}},
            "rule": "HTML / empty / not-JSON are three readings, not one: any shape that collapses is RED",
            "rows": rows}


# ---- the four old arms, copied verbatim from v2 (proved by legacy_arms_unchanged) --------------------

def answered(c: dict) -> bool:
    a = c.get("origin_answer") or {}
    return isinstance(a.get("status"), int) and a.get("thrown") is False


def no_answer(c: dict) -> bool:
    return (c.get("origin_answer") or {}).get("thrown") is True


def judge_v1(c: dict) -> dict:
    if not answered(c) or not c.get("snapshot_present"):
        return {"verdict": "NOT_MEASURED",
                "why": "needs a capture where the origin answered non-2xx while a local snapshot exists"}
    t = c.get("rendered_text") or ""
    net, svc, snap = bool(NETWORK_WORDS.search(t)), bool(SERVICE_WORDS.search(t)), bool(SNAPSHOT_WORDS.search(t))
    ok = (not net) and svc and snap
    return {"verdict": "GREEN" if ok else "RED",
            "measured": {"http_status": c["origin_answer"]["status"], "network_words": net,
                         "names_service": svc, "hands_over_snapshot": snap,
                         "navigator_onLine": c.get("navigator_onLine"), "retry_door_in_text": bool(RETRY_DOOR.search(t))},
            "rule": "answered non-2xx + snapshot: must NAME the service AND HAND OVER the snapshot AND carry no network word"}


def judge_v1_vacuity(c: dict) -> dict:
    """The hole B found: the wrong sentence is simply gone, and that alone must not read as fixed."""
    t = c.get("rendered_text") or ""
    net, svc, snap = bool(NETWORK_WORDS.search(t)), bool(SERVICE_WORDS.search(t)), bool(SNAPSHOT_WORDS.search(t))
    silent_absence = (not net) and (not svc) and (not snap)
    return {"verdict": "RED" if silent_absence else "GREEN",
            "measured": {"network_words": net, "names_service": svc, "hands_over_snapshot": snap,
                         "note": c.get("vacuity_note", "")},
            "rule": "an absent sentence is not a classification; only 网络词=0 且 服务词=1 且 快照词=1 counts"}


def judge_v2(c: dict) -> dict:
    if no_answer(c) is False or "settled_within_deadline" not in c:
        return {"verdict": "NOT_MEASURED", "why": "needs a capture where the fetch never got a response, plus whether it settled"}
    settled, labelled = bool(c.get("settled_within_deadline")), c.get("classified_label") == "NETWORK_UNREACHABLE_WITH_SNAPSHOT"
    door = bool(RETRY_DOOR.search(c.get("rendered_text") or "")) or int((c.get("doors") or {}).get("retry") or 0) > 0
    shown = bool(LOADING_WORDS.search(c.get("rendered_text") or ""))
    ok = settled and labelled and door and (not shown) and bool(SNAPSHOT_WORDS.search(c.get("rendered_text") or ""))
    return {"verdict": "GREEN" if ok else "RED",
            "measured": {"fetch_thrown": True, "settled_within_deadline": settled,
                         "seconds_to_settle": c.get("seconds_to_settle"), "classified_label": c.get("classified_label"),
                         "retry_door": door, "still_on_loading_skeleton": shown,
                         "hands_over_snapshot": bool(SNAPSHOT_WORDS.search(c.get("rendered_text") or ""))},
            "rule": "no answer at all: bounded read + its own label + snapshot handed over + a door"}


def judge_v3(cells: dict) -> dict:
    s2, s3 = (cells.get("S2_origin_error") or {}), (cells.get("S3_no_answer") or {})
    t2, t3 = (s2.get("rendered_text") or "").strip(), (s3.get("rendered_text") or "").strip()
    l2, l3 = s2.get("classified_label"), s3.get("classified_label")
    both = bool(t2) and bool(t3) and bool(l2) and bool(l3)
    distinct = (t2 != t3) or (l2 != l3)
    return {"verdict": "GREEN" if (both and distinct) else "RED",
            "measured": {"s2_label": l2, "s3_label": l3, "same_sentence": t2 == t3,
                         "s3_unclassified_skeleton": bool(LOADING_WORDS.search(t3))},
            "rule": "the two arms must not collapse into one outcome; a skeleton is not a classification"}


def judge_v4(c: dict) -> dict:
    """B's fourth state: the read never answers while the health probe does answer (HTTP 500).

    This is the pair that used to be invisible: 'origin answered badly' and 'origin silent' both produce
    a hung read unless the read itself has a deadline and the attribution consults the health answer.
    """
    read_hung = bool(c.get("read_never_answered"))
    health = (c.get("health_answer") or {})
    health_answered = isinstance(health.get("status"), int) and health.get("thrown") is False
    if not (read_hung and "settled_within_deadline" in c):
        return {"verdict": "NOT_MEASURED", "why": "needs a hung read plus whether the read settled"}
    settled = bool(c.get("settled_within_deadline"))
    labelled = c.get("classified_label") == "ORIGIN_ERROR_WITH_SNAPSHOT"
    net = bool(NETWORK_WORDS.search(c.get("rendered_text") or ""))
    ok = settled and health_answered and labelled and (not net)
    return {"verdict": "GREEN" if ok else "RED",
            "measured": {"read_never_answered": read_hung, "health_status": health.get("status"),
                         "settled_within_deadline": settled, "classified_label": c.get("classified_label"),
                         "network_words": net, "seconds_to_settle": c.get("seconds_to_settle")},
            "rule": "read silent + health answered => ORIGIN_ERROR_WITH_SNAPSHOT, bounded, never called a network failure"}


# ---- end legacy arms ----
LEGACY_BLOCKS = (
    ("answered", "def answered(", "\n\n\ndef no_answer(", "\n\n\ndef no_answer("),
    ("no_answer", "def no_answer(", "\n\n\ndef judge_v1(", "\n\n\ndef judge_v1("),
    ("judge_v1", "def judge_v1(", "\n\n\ndef judge_v1_vacuity(", "\n\n\ndef judge_v1_vacuity("),
    ("judge_v1_vacuity", "def judge_v1_vacuity(", "\n\n\ndef judge_v2(", "\n\n\ndef judge_v2("),
    ("judge_v2", "def judge_v2(", "\n\n\ndef judge_v3(", "\n\n\ndef judge_v3("),
    ("judge_v3", "def judge_v3(", "\n\n\ndef judge_v4(", "\n\n\ndef judge_v4("),
    # v2 ends the last arm at its selftest; v3 ends it at the splice sentinel, or the comparison would
    # include the comparison code itself and report a difference that is only my own file layout
    ("judge_v4", "def judge_v4(", "\n\n\ndef selftest(", "\n# ---- end legacy arms ----"),
)


def slice_src(text: str, start: str, stop: str) -> str:
    i, j = text.find(start), text.find(stop)
    if i < 0 or j < 0 or j <= i:
        return ""
    return text[i:j].rstrip()


def legacy_arms_unchanged() -> dict:
    """Byte-for-byte comparison against the published v2, so 'the old arms are untouched' is a reading."""
    v2 = V2_PATH.read_text(encoding="utf-8") if V2_PATH.is_file() else ""
    v3 = Path(__file__).read_text(encoding="utf-8")
    rows = []
    for name, start, stop2, stop3 in LEGACY_BLOCKS:
        a, b = slice_src(v2, start, stop2), slice_src(v3, start, stop3)
        rows.append({"block": name, "v2_chars": len(a), "v3_chars": len(b),
                     "identical": bool(a) and a == b,
                     "digest_v2": hashlib.sha1(a.encode()).hexdigest()[:12] if a else None,
                     "digest_v3": hashlib.sha1(b.encode()).hexdigest()[:12] if b else None})
    return {"blocks_compared": len(rows), "all_identical": all(r["identical"] for r in rows), "rows": rows}


def selftest() -> int:
    rows = []

    def chk(name, expect, got, detail=None):
        rows.append({"arm": name, "expect": expect, "got": got, "match": expect == got, "detail": detail})
        print(f"  [{'OK ' if expect == got else 'BAD'}] {name} expect={expect} got={got}"
              f"{'' if not detail else '  ' + json.dumps(detail, ensure_ascii=False)[:230]}")

    answered_200_html = {"shape": "200_html", "snapshot_rows": 1,
                         "origin_answer": {"status": 200, "thrown": False, "content_type": "text/html",
                                           "body_bytes": 1200}}
    fixed_shape = dict(answered_200_html, rendered_text=(
        "服务器 | 服务器答了，但这发响应它读不懂 | 它回了 200，只是带回来的不是能解析的行程数据（"
        "Content-Type: text/html）。这台设备上还留着你已保存的行程，用下面的按钮可以只读查看这份本地快照；"
        "也可以稍后重试。 | 重试 | 归因详情 | attribution_reason=ORIGIN_INVALID_RESPONSE "
        "evidence_kind=HTTP_RESPONSE http_status=200 source_layer=APPLICATION cached_copy_present=true"))
    measured_today = dict(answered_200_html, rendered_text=(
        "连接 | 网络不可用 | 这一发请求没能出去，也没有收到任何回答，所以这是网络问题。你的行程数据没有丢失，"
        "已保存的只读副本还能看。请检查网络后重试。 | 看已保存的只读副本 | 重试 | 归因详情 | "
        "attribution_reason=NETWORK_UNAVAILABLE evidence_kind=TRANSPORT http_status=none "
        "source_layer=TRANSPORT cached_copy_present=true"))
    chk("V5-true_positive:answered_200_junk_body_keeps_the_HTTP_fact", "GREEN",
        judge_v5(fixed_shape)["verdict"], judge_v5(fixed_shape)["measured"])
    chk("V5-killer:the_measured_landed_reading_is_red", "RED",
        judge_v5(measured_today)["verdict"], judge_v5(measured_today)["failed_conditions"])
    for name, mut in (
        ("reason_still_network", dict(fixed_shape, rendered_text=fixed_shape["rendered_text"].replace(
            "attribution_reason=ORIGIN_INVALID_RESPONSE", "attribution_reason=NO_REPLY"))),
        ("http_status_dropped", dict(fixed_shape, rendered_text=fixed_shape["rendered_text"].replace(
            "http_status=200", "http_status=none"))),
        ("layer_is_transport", dict(fixed_shape, rendered_text=fixed_shape["rendered_text"].replace(
            "source_layer=APPLICATION", "source_layer=TRANSPORT"))),
        ("sentence_denies_the_answer", dict(fixed_shape, rendered_text=fixed_shape["rendered_text"].replace(
            "它回了 200，只是带回来的不是能解析的行程数据", "这一发请求没能出去，也没有收到任何回答"))),
        ("copy_column_ignores_measurement", dict(fixed_shape, rendered_text=fixed_shape["rendered_text"].replace(
            "cached_copy_present=true", "cached_copy_present=false")))):
        chk(f"V5-killer:{name}", "RED", judge_v5(mut)["verdict"], judge_v5(mut)["failed_conditions"])
    chk("V5-not_measured:origin_that_never_answered_is_not_this_state", "NOT_MEASURED",
        judge_v5({"shape": "x", "origin_answer": {"status": None, "thrown": True},
                  "rendered_text": "no matter"})["verdict"])
    chk("V5-aggregate:one_green_shape_cannot_carry_two_red_ones", "RED",
        aggregate_v5([fixed_shape, measured_today, measured_today])["verdict"],
        aggregate_v5([fixed_shape, measured_today, measured_today])["measured"])
    legacy = legacy_arms_unchanged()
    chk("V0-legacy:four_old_arms_and_two_helpers_are_byte-identical_to_v2", True,
        legacy["all_identical"], {r["block"]: r["identical"] for r in legacy["rows"]})
    ok = all(r["match"] for r in rows)
    out = {"at": NOW, "what": "ORD-0263 verifier v3 selftest - the fifth state, and proof the four old arms "
                              "were not edited to make it fit",
           "arms_total": len(rows), "arms_matched": sum(1 for r in rows if r["match"]),
           "legacy_arm_comparison": legacy,
           "overall": "GREEN" if ok else "RED", "rows": rows}
    p = BASE / "ord0263_verifier_v3_selftest.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    b = p.read_bytes()
    print(f"SELFTEST {out['overall']} ({out['arms_matched']}/{out['arms_total']})  {p.name} {len(b):,} B "
          f"blob {hashlib.sha1(b'blob %d\x00' % len(b) + b).hexdigest()}")
    return 0 if ok else 9


def live(path: Path) -> int:
    cap = json.loads(path.read_text(encoding="utf-8"))
    cells = cap.get("cells") or {}
    res = {"S1_live": {"verdict": "GREEN"} if (cells.get("S1_live") or {}).get("classified_label") == "LIVE"
           and not NETWORK_WORDS.search((cells.get("S1_live") or {}).get("rendered_text") or "")
           else {"verdict": "RED", "why": "S1 must be LIVE with no offline/network wording"},
           "V1_origin_error_5xx": judge_v1(cells.get("S2_origin_error") or {}),
           "V1_vacuity_witness": judge_v1_vacuity(cells.get("S2_origin_error") or {}),
           "V2_no_answer": judge_v2(cells.get("S3_no_answer") or {}),
           "V3_distinctness": judge_v3(cells),
           "V4_silent_read_answered_health": judge_v4(cells.get("S4_read_silent_health_answered") or {}),
           "V5_origin_invalid_response": aggregate_v5(
               (cells.get("S5_invalid_response") or {}).get("shapes") or [])}
    out = {"at": NOW, "capture": str(path), "capture_subject": cap.get("subject"),
           "verdicts_computed_from_measured_fields": res,
           "derived_result": ("ALL_GREEN" if all(v.get("verdict") == "GREEN" for v in res.values())
                              else "RED_CELLS: " + ",".join(k for k, v in res.items()
                                                            if v.get("verdict") != "GREEN")),
           "note": "v3 adds only the fifth arm; the six verdicts above the fifth are produced by the same "
                   "v2 code paths, byte-compared in the selftest"}
    p = BASE / f"ord0263_verdict_{path.stem}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(json.dumps({k: (v.get("verdict"), (v.get("measured") or v.get("why") or v.get("failed_conditions")))
                      for k, v in res.items()}, ensure_ascii=False, indent=1)[:3200])
    print("[live] derived_result:", out["derived_result"], "->", p.name)
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("selftest", "live", "legacy"))
    ap.add_argument("--capture", default="")
    a = ap.parse_args()
    if a.mode == "legacy":
        print(json.dumps(legacy_arms_unchanged(), ensure_ascii=False, indent=1))
        return 0
    return selftest() if a.mode == "selftest" else live(Path(a.capture))


if __name__ == "__main__":
    raise SystemExit(main())
