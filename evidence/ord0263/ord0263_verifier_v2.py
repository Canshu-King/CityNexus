"""ORD-0263 verifier v2 - the S2 cell no longer asserts that the OLD wrong sentence exists.

Why this rewrite was owed to someone else: B found that on the authoritative tip `shell.offlineMsg` has
**no emitter left** (the ORD-0169/R14 sorting landed first), so my v1 assertion
"S2 body contains 网络不可用" is *vacuously false* on the current tree no matter whether the copy is
fixed - a judge that can never fire is not a judge.  My v1 therefore had to be re-pointed at what the
arbiter's vocabulary actually demands, and the hole B exposed gets its own permanent arm:

* `V1` now requires a conjunction: the rendered sentence must **name the service** AND **hand over the
  local snapshot** AND carry **zero network words**.  An absent sentence can no longer pass.
* `V1-vacuity` is the witness arm for exactly the bug: a capture with no network words and no
  service/snapshot words - i.e. "the old mistake simply disappeared" - must read RED.
* `V1-killer` keeps the historical shape (the sentence my own canary measured at 14:4x on
  `c0aafc94`-era code) and must still read RED, so the judge did not become lenient.
* `V4` is B's fourth state and it is right: the read never answers while `/api/v1/health` answers 500.
  Today that pair is indistinguishable from a plain network failure; the fix must classify it as
  `ORIGIN_ERROR_WITH_SNAPSHOT` with a bounded read, and `V4` fails if it collapses into either of the
  other two arms.

Judging is still driven only by measured fields; a missing field is `NOT_MEASURED`, never green.
Nothing here edits product code, and nothing here edits anyone else's gauge.
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
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())

NETWORK_WORDS = re.compile(r"网络不可用|离线 · 只读|OFFLINE|network is (?:down|unavailable)|连不上")
SERVICE_WORDS = re.compile(r"服务(暂时)?不可用|服务器(刚才|明确)?答|origin (?:answered|is unavailable)|HTTP \d{3}")
SNAPSHOT_WORDS = re.compile(r"本地快照|已保存的行程|只读的已保存|saved snapshot|read-?only snapshot")
LOADING_WORDS = re.compile(r"正在准备|锚点 · 住宿|loading|skeleton")
RETRY_DOOR = re.compile(r"重试|retry", re.I)


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


def selftest() -> int:
    rows = []

    def chk(name, expect, got, detail=None):
        rows.append({"arm": name, "expect": expect, "got": got, "match": expect == got, "detail": detail})
        print(f"  [{'OK ' if expect == got else 'BAD'}] {name} expect={expect} got={got}"
              f"{'' if not detail else '  ' + json.dumps(detail, ensure_ascii=False)[:190]}")

    old_wrong = {"origin_answer": {"status": 500, "thrown": False}, "snapshot_present": True,
                 "navigator_onLine": True, "classified_label": None,
                 "rendered_text": "离线 · 只读 你未来 24 小时已保存。 网络不可用 · 正在显示只读的已保存行程。 重试"}
    fixed_words = {"origin_answer": {"status": 500, "thrown": False}, "snapshot_present": True,
                   "navigator_onLine": True, "classified_label": "ORIGIN_ERROR_WITH_SNAPSHOT",
                   "rendered_text": "连接正常 · 这台服务器的行程服务暂时不可用（HTTP 500）。 正在显示本地快照（你上次看到的行程）。 重试"}
    silent_absence = {"origin_answer": {"status": 500, "thrown": False}, "snapshot_present": True,
                      "navigator_onLine": True, "classified_label": None, "rendered_text": "行程暂时看不到内容。",
                      "vacuity_note": "the old wrong sentence is simply gone; nothing names the cause"}
    chk("V1-true_positive:names_service_and_hands_over_snapshot", "GREEN", judge_v1(fixed_words)["verdict"],
        judge_v1(fixed_words)["measured"])
    chk("V1-killer:the_measured_old_sentence_still_reads_red", "RED", judge_v1(old_wrong)["verdict"],
        judge_v1(old_wrong)["measured"])
    chk("V1-vacuity:sentence_just_disappearing_is_not_a_pass", "RED", judge_v1(silent_absence)["verdict"],
        judge_v1(silent_absence)["measured"])
    chk("V1-vacuity-witness:the_same_capture_is_red_for_the_right_reason", "RED",
        judge_v1_vacuity(silent_absence)["verdict"], judge_v1_vacuity(silent_absence)["measured"])
    chk("V1-vacuity-witness:green_when_the_three_parts_are_present", "GREEN",
        judge_v1_vacuity(fixed_words)["verdict"], judge_v1_vacuity(fixed_words)["measured"])
    s3_fixed = {"origin_answer": {"status": None, "thrown": True}, "settled_within_deadline": True,
                "seconds_to_settle": 4.0, "snapshot_present": True, "classified_label": "NETWORK_UNREACHABLE_WITH_SNAPSHOT",
                "doors": {"retry": 1}, "rendered_text": "连不上这台服务器（请求超时）。 正在显示本地快照（你上次看到的行程）。 重试"}
    s3_today = {"origin_answer": {"status": None, "thrown": True}, "settled_within_deadline": False,
                "seconds_to_settle": None, "snapshot_present": True, "classified_label": None,
                "doors": {"retry": 0}, "rendered_text": "正在准备城市周末行程… 锚点 · 住宿 · 出行事实 · 可行性"}
    chk("V2-true_positive:no_answer_gets_its_own_class", "GREEN", judge_v2(s3_fixed)["verdict"], judge_v2(s3_fixed)["measured"])
    chk("V2-killer:remove_the_read_deadline_and_the_cell_goes_red", "RED", judge_v2(s3_today)["verdict"],
        judge_v2(s3_today)["measured"])
    chk("V2-killer:missing_deadline_field_is_not_measured_not_green", "NOT_MEASURED",
        judge_v2({"origin_answer": {"status": None, "thrown": True}, "snapshot_present": True})["verdict"])
    s4_fixed = {"read_never_answered": True, "health_answer": {"status": 500, "thrown": False},
                "settled_within_deadline": True, "seconds_to_settle": 4.0,
                "classified_label": "ORIGIN_ERROR_WITH_SNAPSHOT", "rendered_text": fixed_words["rendered_text"]}
    s4_merged_network = dict(s4_fixed, classified_label="NETWORK_UNREACHABLE_WITH_SNAPSHOT",
                             rendered_text=s3_fixed["rendered_text"])
    s4_hung = dict(s4_fixed, settled_within_deadline=False, classified_label=None, rendered_text=s3_today["rendered_text"])
    chk("V4-true_positive:silent_read_answered_health_is_origin_error", "GREEN", judge_v4(s4_fixed)["verdict"],
        judge_v4(s4_fixed)["measured"])
    chk("V4-killer:collapsing_it_into_the_network_arm_is_red", "RED", judge_v4(s4_merged_network)["verdict"],
        judge_v4(s4_merged_network)["measured"])
    chk("V4-killer:an_unbounded_read_never_reaches_the_attribution", "RED", judge_v4(s4_hung)["verdict"],
        judge_v4(s4_hung)["measured"])
    v3 = judge_v3({"S2_origin_error": fixed_words, "S3_no_answer": s3_fixed})
    chk("V3-true_positive:two_distinct_classified_arms", "GREEN", v3["verdict"], v3["measured"])
    merged = dict(s3_fixed, rendered_text=fixed_words["rendered_text"], classified_label="ORIGIN_ERROR_WITH_SNAPSHOT")
    v3b = judge_v3({"S2_origin_error": fixed_words, "S3_no_answer": merged})
    chk("V3-killer:one_sentence_for_both_arms_is_red", "RED", v3b["verdict"], v3b["measured"])
    v3c = judge_v3({"S2_origin_error": fixed_words, "S3_no_answer": s3_today})
    chk("V3-killer:skeleton_instead_of_a_classification_is_red", "RED", v3c["verdict"], v3c["measured"])
    ok = all(r["match"] for r in rows)
    out = {"at": NOW, "what": "ORD-0263 verifier v2 selftest - can each cell say RED, and is every cell sensitive to the mechanism it names",
           "why": "B found v1's S2 arm asserted the presence of a sentence that the current tree can no longer emit, "
                  "i.e. vacuously false; v2 asserts the conjunction the arbiter vocabulary actually requires",
           "arms_total": len(rows), "arms_matched": sum(1 for r in rows if r["match"]),
           "overall": "GREEN" if ok else "RED", "rows": rows}
    p = BASE / "ord0263_verifier_v2_selftest.json"
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
           "V4_silent_read_answered_health": judge_v4(cells.get("S4_read_silent_health_answered") or {})}
    out = {"at": NOW, "capture": str(path), "capture_subject": cap.get("subject"),
           "verdicts_computed_from_measured_fields": res,
           "derived_result": ("ALL_GREEN" if all(v.get("verdict") == "GREEN" for v in res.values())
                              else "RED_CELLS: " + ",".join(k for k, v in res.items() if v.get("verdict") != "GREEN")),
           "note": "I am the verifier for this order, so a derived_result is mine to write - it is derived "
                   "from the fields printed above, not asserted"}
    p = BASE / f"ord0263_verdict_{path.stem}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(json.dumps({k: (v.get("verdict"), v.get("measured") or v.get("why")) for k, v in res.items()},
                     ensure_ascii=False, indent=1)[:2600])
    print("[live] derived_result:", out["derived_result"], "->", p.name)
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("selftest", "live"))
    ap.add_argument("--capture", default="")
    a = ap.parse_args()
    return selftest() if a.mode == "selftest" else live(Path(a.capture))


if __name__ == "__main__":
    raise SystemExit(main())
