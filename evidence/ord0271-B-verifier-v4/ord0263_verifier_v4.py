"""ORD-0271-B verifier v4 = v3 with exactly one new clause in the fifth arm, and nothing else touched.

Why a new file: the commander's constraint is *"v3 原路径原 blob 不覆盖，v4 另名"*. v3 stays at
`tools/ord0263_verifier_v3.py`, 21,703 B, git-blob `e9a4188f63e27bbbf8bfed35adfd554b9e8641d9`, and arm
`V0c-v3-blob-unchanged` below re-hashes that file from disk on every run so the claim is a reading rather than
a sentence I wrote once.

What changed, and only that: the fifth state's reason column may no longer be a catch-all. v3 forbade
`NETWORK_UNAVAILABLE` and `NO_REPLY` because those *rename an answer into "nobody answered"*. The runtime
counter-proof this order measured says the same defect survives that ban: rename the fifth state to the
generic `UNKNOWN_FAILURE` and every other column stays honest -- `evidence_kind=HTTP_RESPONSE`,
`http_status=200`, `source_layer=RUNTIME`, the sentence still says 「服务器答了 200」 -- so v3 reads it GREEN
while the traveller is told the failure has no name. So v4's `reason_ok` forbids the catch-all too.

The label is still deliberately not pinned: `ORIGIN_INVALID_RESPONSE` is not required anywhere, because the
arbiter wrote "名字可再定" and locking B's vocabulary into an acceptance gate would be my naming taste
masquerading as a measurement. What v4 requires is that the reason is *not one of the three names that
describe some other state*.

Everything else is inherited verbatim and proved twice over:
* `legacy_arms_unchanged()` byte-compares the four old arms, the two helpers and the regex block against the
  published v2 -- eight blocks -- and that comparison is itself a selftest arm;
* `fifth_arm_delta()` compares this file's fifth-arm region against v3's and prints the added and removed
  source lines, so "I only added the one clause" is something a reader can check line by line.

The killer for the new clause is a *dedicated single-variable* one, per arbiter Q8(a): take a real control
reading -- all six columns as measured on a real screen -- and rewrite exactly one token, the reason, to
`UNKNOWN_FAILURE`, leaving `evidence_kind`, `http_status`, `message_key`, the sentence and the snapshot column
as measured. The same three shapes must then go RED *only* on the new clause, and v3 must still read them
GREEN. The runtime mutant build's readings (a real single-line source mutation, Q8(b)-fingerprinted) are judged
alongside, and where their RED is compound the receipt says so and names which extra conditions the product
itself broke -- it does not quietly claim a cleaner carrier than it measured.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
V2_PATH = BASE / "tools" / "ord0263_verifier_v2.py"
V3_PATH = BASE / "tools" / "ord0263_verifier_v3.py"
V3_PUBLISHED_BLOB = "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9"
V3_PUBLISHED_BYTES = 21703
CAPTURE = BASE / "ord0271b_capture_round1.json"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())

# ---- v2's shared regex vocabulary, copied verbatim (proved byte-for-byte by legacy_arms_unchanged) ------
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
# v4's one addition. A catch-all name is not a classification either: `UNKNOWN_FAILURE` is
# what the product falls back to when it has decided nothing, so a fifth state filed there has
# lost the one fact it was meant to carry even when every other column of the line is honest.
BAD_REASONS_V4 = BAD_REASONS | {"UNKNOWN_FAILURE"}


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
    reason_ok = bool(reason) and reason not in BAD_REASONS_V4
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
                         "only_reason_clause_failed": fails == ["reason_collapsed"],
                         "measured_snapshot_rows": shape.get("snapshot_rows")},
            "failed_conditions": fails,
            "rule": "answered 2xx with an unparseable body: the HTTP-response fact must survive every column "
                    "and the sentence may not claim nothing answered; and the reason may not "
                    "be a catch-all either (v4): UNKNOWN_FAILURE names no state at all"}


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



# ---- end legacy arms ------------------------------------------------------------------------------------

# v3's seven compared blocks, plus the regex block v2 shares with it, so "the old arms are untouched" reads
# across everything the old verdicts are made of. Each block names its own stop marker in v2 and in this file:
# the two files end those regions differently (v2 goes straight into its selftest, this one into a sentinel),
# and comparing a block that swallowed the comparison code itself once reported a difference that was only my
# own file layout.
LEGACY_BLOCKS = (
    ("regex_block", "NETWORK_WORDS = re.compile", "\n\n\ndef answered(",
     "\n\n# ---- fifth state: measured fields"),
    ("answered", "def answered(", "\n\n\ndef no_answer(", "\n\n\ndef no_answer("),
    ("no_answer", "def no_answer(", "\n\n\ndef judge_v1(", "\n\n\ndef judge_v1("),
    ("judge_v1", "def judge_v1(", "\n\n\ndef judge_v1_vacuity(", "\n\n\ndef judge_v1_vacuity("),
    ("judge_v1_vacuity", "def judge_v1_vacuity(", "\n\n\ndef judge_v2(", "\n\n\ndef judge_v2("),
    ("judge_v2", "def judge_v2(", "\n\n\ndef judge_v3(", "\n\n\ndef judge_v3("),
    ("judge_v3", "def judge_v3(", "\n\n\ndef judge_v4(", "\n\n\ndef judge_v4("),
    ("judge_v4", "def judge_v4(", "\n\n\ndef selftest(", "\n# ---- end legacy arms ----"),
)


def slice_src(text: str, start: str, stop: str) -> str:
    i, j = text.find(start), text.find(stop)
    if i < 0 or j < 0 or j <= i:
        return ""
    return text[i:j].rstrip()


def load_ruler(path: Path, name: str):
    """Load another version of my own ruler so a cross-ruler claim is computed, not asserted.

    Both files are inert at import time (constants and function definitions only), and each keeps its own
    `BAD_REASONS`, so `v3 says GREEN / v4 says RED` becomes a pair of calls on the same object."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_capture(path: Path = CAPTURE) -> dict:
    if not path.is_file():
        return {"missing": True, "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def shapes_of(cap: dict, which: str) -> list:
    cells = (cap.get("cells") or {})
    return (cells.get(which) or {}).get("shapes") or []


def one_token_reason_rewrite(shape: dict, to: str = "UNKNOWN_FAILURE") -> tuple:
    """The dedicated single-variable carrier: one token of one column, everything else as measured.

    Returns (new_shape, how_many_tokens_changed). It refuses to produce a carrier whose rendered text does not
    contain the reason it is supposed to be replacing, because a substitution that hits nothing is exactly the
    empty-running killer this order is not allowed to ship.
    """
    t = shape.get("rendered_text") or ""
    hits = re.findall(r"attribution_reason=\S+", t)
    if len(hits) != 1:
        return dict(shape), 0
    new_t = t.replace(hits[0], f"attribution_reason={to}")
    return dict(shape, rendered_text=new_t), 1


def fifth_arm_delta() -> dict:
    """Line-by-line difference between v3's fifth-arm region and this file's, so the scope of the change reads."""
    v3 = V3_PATH.read_text(encoding="utf-8") if V3_PATH.is_file() else ""
    v4 = Path(__file__).read_text(encoding="utf-8")

    def region(text: str) -> list:
        i, j = text.find("# ---- fifth state: measured fields"), text.find("# ---- the four old arms")
        if i < 0 or j < 0 or j <= i:
            i, j = text.find("NEVER_WENT_OUT"), text.find("# ---- the four old arms")
        if i < 0 or j < 0 or j <= i:
            return []
        return [l.rstrip() for l in text[i:j].rstrip().splitlines()]

    a, b = region(v3), region(v4)
    added = [l for l in b if l not in a]
    removed = [l for l in a if l not in b]
    return {"v3_lines": len(a), "v4_lines": len(b), "added": added, "removed": removed,
            "changed_line_count": len(added) + len(removed)}


def legacy_arms_unchanged() -> dict:
    """Byte-for-byte comparison against the published v2, so 'the old arms are untouched' is a reading."""
    v2 = V2_PATH.read_text(encoding="utf-8") if V2_PATH.is_file() else ""
    v4 = Path(__file__).read_text(encoding="utf-8")
    rows = []
    for name, start, stop2, stop4 in LEGACY_BLOCKS:
        a, b = slice_src(v2, start, stop2), slice_src(v4, start, stop4)
        rows.append({"block": name, "v2_chars": len(a), "v4_chars": len(b),
                     "identical": bool(a) and a == b,
                     "digest_v2": hashlib.sha1(a.encode()).hexdigest()[:12] if a else None,
                     "digest_v4": hashlib.sha1(b.encode()).hexdigest()[:12] if b else None})
    return {"blocks_compared": len(rows), "all_identical": all(r["identical"] for r in rows), "rows": rows}


def v3_blob_unchanged() -> dict:
    b = V3_PATH.read_bytes() if V3_PATH.is_file() else b""
    digest = hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest() if b else None
    return {"path": V3_PATH.name, "bytes": len(b), "blob40": digest, "expected_blob40": V3_PUBLISHED_BLOB,
            "expected_bytes": V3_PUBLISHED_BYTES,
            "unchanged": digest == V3_PUBLISHED_BLOB and len(b) == V3_PUBLISHED_BYTES}


def selftest() -> int:
    rows = []

    def chk(name, expect, got, detail=None):
        rows.append({"arm": name, "expect": expect, "got": got, "match": expect == got, "detail": detail})
        print(f"  [{'OK ' if expect == got else 'BAD'}] {name} expect={expect} got={got}"
              f"{'' if not detail else '  ' + json.dumps(detail, ensure_ascii=False)[:260]}")

    cap = load_capture()
    ctl = shapes_of(cap, "S5_invalid_response")
    mut = shapes_of(cap, "S5_invalid_response_mutant")
    v3 = load_ruler(V3_PATH, "ord0263_v3_for_cross_read") if V3_PATH.is_file() else None

    # --- the fifth arm's own literals, kept from v3 so an old killer cannot be quietly weakened ----------
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
    for name, mut_lit in (
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
        chk(f"V5-killer:{name}", "RED", judge_v5(mut_lit)["verdict"], judge_v5(mut_lit)["failed_conditions"])
    chk("V5-not_measured:origin_that_never_answered_is_not_this_state", "NOT_MEASURED",
        judge_v5({"shape": "x", "origin_answer": {"status": None, "thrown": True},
                  "rendered_text": "no matter"})["verdict"])
    chk("V5-aggregate:one_green_shape_cannot_carry_two_red_ones", "RED",
        aggregate_v5([fixed_shape, measured_today, measured_today])["verdict"],
        aggregate_v5([fixed_shape, measured_today, measured_today])["measured"])

    # --- arm A: the new clause must not over-fire on the real, unmutated readings -------------------------
    chk("V5-positive_control:three_real_control_readings_are_green", 3, len(ctl),
        {"capture": CAPTURE.name, "capture_missing": cap.get("missing"),
         "shapes": [(s["shape"], judge_v5(s)["verdict"]) for s in ctl]})
    chk("V5-positive_control:aggregate_of_the_real_control_readings", "GREEN",
        aggregate_v5(ctl)["verdict"] if ctl else "NOT_MEASURED",
        aggregate_v5(ctl)["measured"] if ctl else None)
    chk("V5-positive_control:no_control_shape_fails_the_new_reason_clause", [],
        [s["shape"] for s in ctl if "reason_collapsed" in (judge_v5(s).get("failed_conditions") or [])],
        {"why": "the new clause must fire on the catch-all, not on every fifth-state reading"})

    # --- arm B: the dedicated single-variable carrier, one token of one column of a real reading ----------
    carriers, v3_checks, only_new = [], [], []
    for s in ctl:
        c, changed = one_token_reason_rewrite(s)
        v4j, v3j = judge_v5(c), (v3.judge_v5(c) if v3 else {})
        carriers.append({"shape": s["shape"], "tokens_changed": changed, "v4": v4j["verdict"],
                         "v4_failed_conditions": v4j.get("failed_conditions"),
                         "v3": v3j.get("verdict"), "v3_failed_conditions": v3j.get("failed_conditions"),
                         "reason_column_now": (c["rendered_text"].split("attribution_reason=")[1].split(" ")[0]),
                         "evidence_kind_untouched": "evidence_kind=HTTP_RESPONSE" in c["rendered_text"],
                         "http_status_untouched": "http_status=200" in c["rendered_text"],
                         "snapshot_column_untouched": "cached_copy_present=true" in c["rendered_text"]})
        v3_checks.append(v3j.get("verdict"))
        only_new.append(v4j.get("failed_conditions") == ["reason_collapsed"] and changed == 1)
    chk("V5-killer:dedicated_single_variable_carrier_is_red_only_on_the_new_clause", [True] * 3, only_new,
        carriers)
    chk("V5-killer:the_same_three_carriers_read_GREEN_under_v3", ["GREEN"] * 3, v3_checks,
        {"why": "proof the new clause is the only thing that fires here, and that v3 could not see it"})

    # --- arm C: the real runtime mutant build's readings, judged by both rulers ---------------------------
    runtime = []
    for s in mut:
        v4j, v3j = judge_v5(s), (v3.judge_v5(s) if v3 else {})
        f4, f3 = set(v4j.get("failed_conditions") or []), set(v3j.get("failed_conditions") or [])
        runtime.append({"shape": s["shape"], "pass": s.get("pass_label"), "v4": v4j["verdict"],
                        "v3": v3j.get("verdict"), "v4_only": sorted(f4 - f3), "v3_only": sorted(f3 - f4),
                        "v4_failed_conditions": sorted(f4), "v3_failed_conditions": sorted(f3),
                        "reason_column": (s["rendered_text"].split("attribution_reason=")[1].split(" ")[0]
                                          if "attribution_reason=" in s["rendered_text"] else None)})
    chk("V5-real_mutant_runtime_readings_are_red_under_v4", ["RED"] * len(mut),
        [r["v4"] for r in runtime] if mut else ["NOT_MEASURED"], runtime)
    chk("V5-real_mutant_runtime_readings:the_condition_v4_adds_is_exactly_the_new_clause", [],
        sorted({c for r in runtime for c in r["v4_only"] if c != "reason_collapsed"}), runtime)
    chk("V5-real_mutant_runtime_readings:v4_loses_nothing_v3_had", [],
        sorted({c for r in runtime for c in r["v3_only"]}), runtime)

    legacy = legacy_arms_unchanged()
    chk("V0-legacy:four_old_arms_two_helpers_and_the_regex_block_are_byte-identical_to_v2", True,
        legacy["all_identical"], {r["block"]: r["identical"] for r in legacy["rows"]})
    delta = fifth_arm_delta()
    chk("V0b-fifth-arm:v4_forbids_exactly_one_more_reason_than_v3", ["UNKNOWN_FAILURE"],
        sorted(set(BAD_REASONS_V4) - set(v3.BAD_REASONS)) if v3 else ["NO_V3"],
        {"v3_forbids": sorted(v3.BAD_REASONS) if v3 else None, "v4_forbids": sorted(BAD_REASONS_V4),
         "source_lines_added": delta["added"], "source_lines_removed": delta["removed"],
         "changed_line_count": delta["changed_line_count"]})
    chk("V0b-fifth-arm:the_fifth_state_label_is_still_not_pinned_to_a_string", True,
        "ORIGIN_INVALID_RESPONSE" not in json.dumps(sorted(BAD_REASONS_V4)),
        {"rule": "v4 forbids names that describe another state; it does not require any particular name"})
    blob = v3_blob_unchanged()
    chk("V0c-v3-blob-unchanged:the_old_ruler_was_not_edited_to_make_the_new_one_fit", True,
        blob["unchanged"], blob)

    ok = all(r["match"] for r in rows)
    out = {"at": NOW, "what": "ORD-0271-B verifier v4 selftest - the catch-all reason clause, its dedicated "
                              "single-variable carrier, and proof the four old arms and v3 itself are untouched",
           "arms_total": len(rows), "arms_matched": sum(1 for r in rows if r["match"]),
           "capture": {"path": CAPTURE.name, "missing": cap.get("missing", False),
                       "control_shapes": len(ctl), "mutant_shapes": len(mut),
                       "blob40": hashlib.sha1(CAPTURE.read_bytes()).hexdigest() if CAPTURE.is_file() else None},
           "cross_ruler": {"v3_path": V3_PATH.name, "v3_loaded": bool(v3), "runtime_rows": runtime,
                           "single_variable_carriers": carriers},
           "legacy_arm_comparison": legacy, "fifth_arm_delta": delta, "v3_blob": blob,
           "overall": "GREEN" if ok else "RED", "rows": rows}
    p = BASE / "ord0263_verifier_v4_selftest.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    b = p.read_bytes()
    receipt_blob = hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()
    print(f"SELFTEST {out['overall']} ({out['arms_matched']}/{out['arms_total']})  {p.name} {len(b):,} B "
          f"blob {receipt_blob}")
    return 0 if ok else 9


def live(path: Path) -> int:
    cap = json.loads(path.read_text(encoding="utf-8"))
    cells = cap.get("cells") or {}
    v3 = load_ruler(V3_PATH, "ord0263_v3_for_live_read") if V3_PATH.is_file() else None
    fifth_shapes = (cells.get("S5_invalid_response") or {}).get("shapes") or []
    res = {"S1_live": {"verdict": "GREEN"} if (cells.get("S1_live") or {}).get("classified_label") == "LIVE"
           and not NETWORK_WORDS.search((cells.get("S1_live") or {}).get("rendered_text") or "")
           else {"verdict": "RED", "why": "S1 must be LIVE with no offline/network wording"},
           "V1_origin_error_5xx": judge_v1(cells.get("S2_origin_error") or {}),
           "V1_vacuity_witness": judge_v1_vacuity(cells.get("S2_origin_error") or {}),
           "V2_no_answer": judge_v2(cells.get("S3_no_answer") or {}),
           "V3_distinctness": judge_v3(cells),
           "V4_silent_read_answered_health": judge_v4(cells.get("S4_read_silent_health_answered") or {}),
           "V5_origin_invalid_response": aggregate_v5(fifth_shapes)}
    under_v3 = v3.aggregate_v5(fifth_shapes)["verdict"] if v3 else "NO_V3"
    out = {"at": NOW, "ruler": "v4", "capture": str(path), "capture_subject": cap.get("subject"),
           "verdicts_computed_from_measured_fields": res,
           "fifth_arm_under_both_rulers": {"v3": under_v3, "v4": res["V5_origin_invalid_response"]["verdict"],
                                           "per_shape": [
                                               {"shape": s.get("shape"),
                                                "v3": (v3.judge_v5(s)["verdict"] if v3 else None),
                                                "v3_failed": (v3.judge_v5(s).get("failed_conditions")
                                                              if v3 else None),
                                                "v4": judge_v5(s)["verdict"],
                                                "v4_failed": judge_v5(s).get("failed_conditions")}
                                               for s in fifth_shapes]},
           "derived_result": ("ALL_GREEN" if all(v.get("verdict") == "GREEN" for v in res.values())
                              else "RED_CELLS: " + ",".join(k for k, v in res.items()
                                                            if v.get("verdict") != "GREEN")),
           "note": "v4 adds only the catch-all clause to the fifth arm; the six verdicts above it come from the "
                   "same v2 code paths, byte-compared in the selftest"}
    p = BASE / f"ord0263v4_verdict_{path.stem}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(json.dumps({k: (v.get("verdict"), (v.get("measured") or v.get("why") or v.get("failed_conditions")))
                      for k, v in res.items()}, ensure_ascii=False, indent=1)[:3200])
    print("[live] fifth arm:", json.dumps(out["fifth_arm_under_both_rulers"]["per_shape"], ensure_ascii=False))
    print("[live] derived_result:", out["derived_result"], "->", p.name)
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("selftest", "live", "legacy", "delta"))
    ap.add_argument("--capture", default="")
    a = ap.parse_args()
    if a.mode == "legacy":
        print(json.dumps(legacy_arms_unchanged(), ensure_ascii=False, indent=1))
        return 0
    if a.mode == "delta":
        print(json.dumps(fifth_arm_delta(), ensure_ascii=False, indent=1))
        return 0
    return selftest() if a.mode == "selftest" else live(Path(a.capture))


if __name__ == "__main__":
    raise SystemExit(main())
