"""ORD-0263 - the three-cell verifier, written so it cannot turn green by itself.

Scope as narrowed by the commander @CMDR@: the **404 arm is already correct on the released build** (his own
read-only pass over :4781 proves it: 「这台服务器上没有这一趟行程了 … 这不是网络问题：服务器刚才答得出来」).
That reading is *reference*, never my baseline - it is the release, not my fixture. The two arms that must
be pinned are (1) `HTTP 5xx + local snapshot`, which today says 网络不可用, and (2)
`timeout / DNS / connect failure`, which today cannot be classified at all because
`api/citynexus.ts:642 requestJson()` has no deadline, so `V8Experience.tsx:601` never rejects and
`:198 return response.ok` has nothing to distinguish.

Design rules, each of which exists because I have been burned by its absence:

* **Every verdict is derived from measured fields** in a capture file (`origin_answer`,
  `settled_within_deadline`, `snapshot_present`, `rendered_text`, `classified_label`, `doors`).  No
  verdict is a string literal I typed, and no cell passes because a field is missing - a missing field is
  `NOT_MEASURED`, which is not green (A-3).
* **Three killers, both directions**, so that each cell is shown to be capable of saying RED and to be
  *sensitive to the very mechanism under test*:
  - `V1` is fed the correct S2 wording (PASS) and today's measured S2 wording (RED).
  - `V2` is fed a capture where the timeout classification exists (PASS) and the same capture with the
    deadline removed - i.e. what `:198` produces today (RED).  This is the commander's "删掉超时分类 ⇒
    那一格必须红".
  - `V3` is fed two distinct classified sentences (PASS) and one shared sentence (RED).
* `--live <capture.json>` re-judges a real capture; `--selftest` runs the killers.  A green selftest does
  not mean the product is fixed: it means the judge can tell the difference.
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
NETWORK_WORDS = re.compile(r"网络不可用|离线 · 只读|OFFLINE|network is (?:down|unavailable)")
SERVICE_WORDS = re.compile(r"服务(暂时)?不可用|服务器(暂时)?无法|origin|server is (?:unavailable|answering)")
SNAPSHOT_WORDS = re.compile(r"本地快照|已保存的行程|saved snapshot|read-?only snapshot")
LOADING_WORDS = re.compile(r"正在准备|loading|skeleton|锚点 · 住宿")

ARBS = ("LIVE", "ORIGIN_ERROR_WITH_SNAPSHOT", "NETWORK_UNREACHABLE_WITH_SNAPSHOT")


def answered(c: dict) -> bool:
    """The origin produced an HTTP response - any status.  This is the fact `:198` throws away."""
    a = c.get("origin_answer") or {}
    return isinstance(a.get("status"), int) and a.get("thrown") is False


def judge_v1_origin_error_cell(c: dict) -> dict:
    if not answered(c) or not c.get("snapshot_present"):
        return {"verdict": "NOT_MEASURED", "why": "needs a capture where the origin answered 4xx/5xx and a snapshot exists"}
    t = c.get("rendered_text") or ""
    wrong = bool(NETWORK_WORDS.search(t))
    says_service = bool(SERVICE_WORDS.search(t))
    says_snapshot = bool(SNAPSHOT_WORDS.search(t))
    ok = (not wrong) and says_service and says_snapshot
    return {"verdict": "GREEN" if ok else "RED",
            "measured": {"http_status": c["origin_answer"]["status"], "says_network_words": wrong,
                         "says_service_words": says_service, "says_snapshot_words": says_snapshot,
                         "navigator_onLine": c.get("navigator_onLine")},
            "rule": "answered non-2xx + snapshot: must name the service and the snapshot, and must not claim the network"}


def judge_v2_no_answer_cell(c: dict) -> dict:
    a = c.get("origin_answer") or {}
    if a.get("thrown") is not True or "settled_within_deadline" not in c:
        return {"verdict": "NOT_MEASURED", "why": "needs a capture where the fetch never got a response, plus whether the read settled"}
    settled = bool(c.get("settled_within_deadline"))
    labelled = c.get("classified_label") == "NETWORK_UNREACHABLE_WITH_SNAPSHOT"
    door = int((c.get("doors") or {}).get("retry") or 0) > 0
    shown = bool(LOADING_WORDS.search(c.get("rendered_text") or ""))
    ok = settled and labelled and door and (not shown)
    return {"verdict": "GREEN" if ok else "RED",
            "measured": {"fetch_thrown": True, "settled_within_deadline": settled,
                         "classified_label": c.get("classified_label"), "retry_door_present": door,
                         "still_on_loading_skeleton": shown, "snapshot_present": c.get("snapshot_present"),
                         "seconds_to_settle": c.get("seconds_to_settle")},
            "rule": "no answer at all: the read must settle inside a deadline, be labelled as its own class, show the snapshot and leave a door"}


def judge_v3_distinctness(cells: dict) -> dict:
    s2 = (cells.get("S2_origin_error") or {}).get("rendered_text") or ""
    s3 = (cells.get("S3_no_answer") or {}).get("rendered_text") or ""
    l2 = (cells.get("S2_origin_error") or {}).get("classified_label")
    l3 = (cells.get("S3_no_answer") or {}).get("classified_label")
    both_classified = bool(s2.strip()) and bool(s3.strip()) and bool(l2) and bool(l3)
    distinct = s2.strip() != s3.strip() or l2 != l3
    ok = both_classified and distinct
    return {"verdict": "GREEN" if ok else "RED",
            "measured": {"s2_label": l2, "s3_label": l3, "same_sentence": s2.strip() == s3.strip(),
                         "s3_is_unclassified_skeleton": bool(LOADING_WORDS.search(s3))},
            "rule": "the two arms must not collapse into one classified outcome; a skeleton is not a classification"}


def judge_all(cap: dict) -> dict:
    cells = cap.get("cells") or {}
    out = {
        "S1_live": ({"verdict": "GREEN"} if cells.get("S1_live", {}).get("classified_label") == "LIVE"
                    and not NETWORK_WORDS.search(cells.get("S1_live", {}).get("rendered_text") or "")
                    else {"verdict": "RED", "why": "S1 must be LIVE with no offline wording"}),
        "V1_origin_error_5xx": judge_v1_origin_error_cell(cells.get("S2_origin_error") or {}),
        "V2_no_answer": judge_v2_no_answer_cell(cells.get("S3_no_answer") or {}),
        "V3_distinctness": judge_v3_distinctness(cells),
    }
    for k, v in out.items():
        if "verdict" in v and v["verdict"] not in ("GREEN", "RED"):
            v.setdefault("why", "field missing")
    return out


# ---------------------------------------------------------------- fixtures for the killers
def fixture_s2_correct() -> dict:
    return {"origin_answer": {"status": 500, "thrown": False}, "snapshot_present": True,
            "navigator_onLine": True, "classified_label": "ORIGIN_ERROR_WITH_SNAPSHOT",
            "rendered_text": "服务暂时不可用 · 正在显示本地快照（你上次看到的行程）。 重试"}


def fixture_s2_measured_today() -> dict:
    return {"origin_answer": {"status": 500, "thrown": False}, "snapshot_present": True,
            "navigator_onLine": True, "classified_label": "ORIGIN_ERROR_WITH_SNAPSHOT",
            "rendered_text": "离线 · 只读 你未来 24 小时已保存。 网络不可用 · 正在显示只读的已保存行程。 重试"}


def fixture_s3_with_deadline() -> dict:
    return {"origin_answer": {"status": None, "thrown": True}, "settled_within_deadline": True,
            "seconds_to_settle": 4.0, "snapshot_present": True,
            "classified_label": "NETWORK_UNREACHABLE_WITH_SNAPSHOT",
            "doors": {"retry": 1}, "rendered_text": "连不上这台服务器 · 正在显示本地快照。 重试"}


def fixture_s3_without_deadline() -> dict:
    """Same surface, but the per-read deadline is removed - which is what :198/:642 do today:
    nothing settles, so no classification ever happens and the merged boolean cannot tell the classes."""
    c = fixture_s3_with_deadline()
    c.update({"settled_within_deadline": False, "seconds_to_settle": None,
              "classified_label": "ORIGIN_ERROR_WITH_SNAPSHOT", "doors": {"retry": 0},
              "rendered_text": "正在准备城市周末行程… 锚点 · 住宿 · 出行事实 · 可行性"})
    return c


def selftest() -> int:
    rows = []

    def check(name: str, expect: str, got: str, detail=None) -> None:
        rows.append({"arm": name, "expect": expect, "got": got, "match": expect == got, "detail": detail})
        print(f"  [{'OK ' if expect == got else 'BAD'}] {name}: expect={expect} got={got}"
              f"{'' if not detail else '  ' + json.dumps(detail, ensure_ascii=False)[:200]}")

    v = judge_v1_origin_error_cell(fixture_s2_correct())
    check("V1-true_positive:correct_service_and_snapshot_words", "GREEN", v["verdict"], v.get("measured"))
    v = judge_v1_origin_error_cell(fixture_s2_measured_today())
    check("V1-killer:today_s_network_words_must_be_red", "RED", v["verdict"], v.get("measured"))
    v = judge_v2_no_answer_cell(fixture_s3_with_deadline())
    check("V2-true_positive:no_answer_with_a_real_deadline", "GREEN", v["verdict"], v.get("measured"))
    v = judge_v2_no_answer_cell(fixture_s3_without_deadline())
    check("V2-killer:remove_the_read_deadline_and_the_cell_goes_red", "RED", v["verdict"], v.get("measured"))
    v = judge_v3_distinctness({"S2_origin_error": fixture_s2_correct(), "S3_no_answer": fixture_s3_with_deadline()})
    check("V3-true_positive:two_distinct_classified_arms", "GREEN", v["verdict"], v.get("measured"))
    shared = fixture_s3_with_deadline() | {"rendered_text": fixture_s2_correct()["rendered_text"],
                                           "classified_label": "ORIGIN_ERROR_WITH_SNAPSHOT"}
    v = judge_v3_distinctness({"S2_origin_error": fixture_s2_correct(), "S3_no_answer": shared})
    check("V3-killer:one_sentence_for_both_arms_is_red", "RED", v["verdict"], v.get("measured"))
    # A-3 witness: an absent field must never read as a pass.
    v = judge_v2_no_answer_cell({"origin_answer": {"status": None, "thrown": True}, "snapshot_present": True})
    check("V2-killer:missing_deadline_field_is_not_measured_not_green", "NOT_MEASURED", v["verdict"])
    ok = all(r["match"] for r in rows)
    out = {"at": NOW, "what": "ORD-0263 verifier selftest - can every cell say RED, and is V2 sensitive to the deadline mechanism",
           "rule": "a judge that has never been seen to fail is not a judge; these arms assert nothing about the product",
           "scope_from_commander": "404 arm already correct on the release (reference, not baseline); "
                                   "the two arms under test are 5xx+snapshot and no-answer",
           "arms_total": len(rows), "arms_matched": sum(1 for r in rows if r["match"]),
           "overall": "GREEN" if ok else "RED", "rows": rows}
    p = BASE / "ord0263_verifier_selftest.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    b = p.read_bytes()
    print(f"SELFTEST {out['overall']} ({out['arms_matched']}/{out['arms_total']})  {p.name} {len(b):,} B "
          f"blob {hashlib.sha1(b'blob %d\x00' % len(b) + b).hexdigest()}")
    return 0 if ok else 9


def live(path: Path) -> int:
    cap = json.loads(path.read_text(encoding="utf-8"))
    res = judge_all(cap)
    out = {"at": NOW, "capture": str(path), "verdicts_computed_from_measured_fields": res,
           "commander_release_reference": "evidence/release/commander_release_walk_0923_1723.json blob "
                                          "34c6aaab1584132e (404 arm honest on the release; it is the release, not my fixture)",
           "meaning": "RED here is the defect standing; GREEN would be the fix landing"}
    p = BASE / "ord0263_verdict_on_live_capture.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    greens = sum(1 for v in res.values() if v.get("verdict") == "GREEN")
    print(f"[live] {greens}/{len(res)} cells green -> {p.name}")
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("selftest", "live"))
    ap.add_argument("--capture", default=str(BASE / "ord0263_state_matrix.json"))
    a = ap.parse_args()
    return selftest() if a.mode == "selftest" else live(Path(a.capture))


if __name__ == "__main__":
    raise SystemExit(main())
