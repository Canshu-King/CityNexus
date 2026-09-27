#!/usr/bin/env python3
"""ORD-0384 -- the `stay_budget.declared` shape: a gate-condition finding, not a product defect.

The commander asked for this one separately and said it lands on the gate's list, not this order's. The
shape: the live phone chain answered `declared: null` for the Guangzhou journey, while every
authoritative e2e run answered `declared: false`. A rule written as `declared === null` therefore fires
on the chain and never fires in the gate -- which is not the product disagreeing with itself, it is the
gate's fixture not carrying the state the gate claims to judge.

This script does not restate that from memory. It counts the value actually recorded in every X1/Y1
receipt on disk and prints both sides with their coordinates, so the denominator is visible.

It also records what the re-scoping changed: `stay_budget_undeclared` is no longer an item at all,
because the field has no contract anchor (it is declared only on `JourneyCreate`, the request body). So
the divergence no longer moves the screen -- but the fixture still answers `false` where the chain
answered `null`, and any future anchored rule on that field inherits the same blind spot.
"""
import glob
import io
import json
import os
import sys

EV = r"D:/moodle/_qoder_n3_ord0357/review/evidence/ord0384"
MD = r"D:/moodle/_qoder_n3_ord0357/review/ORD0384_GATE_CONDITION_declared_shape_r1.md"


def classify(rec):
    if "declared_value" not in rec:
        return "key_absent"
    v = rec["declared_value"]
    if v is None:
        return "null"
    if v is False:
        return "false"
    if v is True:
        return "true"
    return "other:%r" % (v,)


def main():
    files = sorted(glob.glob(os.path.join(EV, "cmdr*__[XY]1.json")))
    counts = {}
    per_file = []
    for f in files:
        rec = json.load(io.open(f, encoding="utf-8"))
        c = classify(rec)
        counts[c] = counts.get(c, 0) + 1
        per_file.append({"receipt": os.path.basename(f), "declared_class": c,
                         "run_id": rec.get("run_id"), "test_status": rec.get("test_status")})
    live = json.load(io.open(os.path.join(EV, "live_derivation_r2.json"), encoding="utf-8"))
    live_rule = next(r for r in live["rules"] if r["key"] == "stay_budget_undeclared")
    two = json.load(io.open(os.path.join(EV, "two_contracts_r1.json"), encoding="utf-8"))
    stay = next(r for r in two["fields"] if r["field"] == "stay_budget")
    # A receipt that never wrote the key is not evidence about the fixture -- it is a receipt from a
    # version of the cell that stopped recording the field. Counting the two together would silently
    # inflate the denominator, so they are reported apart.
    recorded = {k: v for k, v in counts.items() if k != "key_absent"}
    out = {"generated_by": os.path.basename(__file__), "order": "ORD-0384",
           "e2e_receipts_scanned": len(files),
           "e2e_receipts_that_recorded_the_field": sum(counts.values()) - counts.get("key_absent", 0),
           "e2e_receipts_not_recording_it": counts.get("key_absent", 0),
           "e2e_declared_counts": counts, "e2e_declared_counts_recorded_only": recorded,
           "live_declared_value": live_rule["deciding_value"],
           "live_declared_coordinate": live_rule["coordinate"],
           "live_journey_id": live["journey_id"],
           "stay_budget_contract_side": {"hand_declared": stay["hand_declared"],
                                         "generated_paths": stay["generated_paths"],
                                         "generated_path_count": stay["generated_path_count"]},
           "per_receipt": per_file,
           "verdict": "GATE_CONDITION_NOT_TRUE_IN_FIXTURE",
           "why_not_a_product_defect": "the panel and the derivation agree with whatever the response "
                                       "says; the two stacks simply do not say the same thing, so the "
                                       "gate never exercises the state the screen shows in the field."}
    io.open(os.path.join(EV, "declared_shape_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    md = ["# ORD-0384 -- 门条件不真：`trip.stay_budget.declared` 在两套栈上不是同一个值",
          "",
          "结论：这是**门的条件不真**，不是产品缺陷。号令者已确认归入门的整改，不记本单账。",
          "",
          "## 两侧实测（数字都从收据里数出来，不是回忆）",
          "",
          "| 侧 | 读数 | 坐标 |",
          "| --- | --- | --- |",
          "| 手机链 :4781（广州两日，03:55 已被 demo/reset 抹掉） | `declared` = `null` | `%s` |" % live_rule["coordinate"],
          "| authoritative e2e（扫 %d 份 X1/Y1 收据，其中 %d 份真的记了这个字段） | `declared` = `false` 共 %d 份；`null` 共 %d 份；另有 %d 份是本单改写后的 Y1，它不再记这个字段，所以不计入分母 | `review/evidence/ord0384/declared_shape_r1.json` |"
          % (len(files), sum(counts.values()) - counts.get("key_absent", 0), counts.get("false", 0), counts.get("null", 0), counts.get("key_absent", 0)),
          "",
          "e2e 侧没有一份收据出现过 `null`。也就是说：写成 `declared === null` 的规则在链上会亮，在门里永远不亮。",
          "",
          "## 为什么它不是产品缺陷",
          "",
          "面板与推导模块对「响应说什么」是一致的（Y1 双向共现在两套栈上都绿）。不一致的是两套栈对同一个字段说了不同的话，",
          "所以门从未跑过屏幕上真实会出现的那个状态。",
          "",
          "## 重定范围之后的现状",
          "",
          "`stay_budget_undeclared` 已经不是条目了：`stay_budget` 在生成式契约里只出现 " + str(stay["generated_path_count"]) + " 次，"
          "位置是 `JourneyCreate/properties/stay_budget`，即**请求体那一侧**；两份契约都没有把它写在响应上。",
          "所以这个形状差异现在不再影响屏上内容。但 fixture 仍答 `false` 而链答 `null` 这件事没有修，",
          "任何将来锚在这个字段上的规则都会继承同一个盲区。",
          "",
          "补一条给门的线索：三态出口的代码在本树里是存在的（`backend/app/stay_mobility.py:1619` 会答 "
          "`STAY_BUDGET_NOT_DECLARED`），所以 `null` 不是缺能力，是 seed 与出口两条路没被同一格覆盖。",
          "",
          "## 建议给门的整改",
          "",
          "1. 让 e2e 的 seed 能造出 `declared: null` 与 `declared: false` 两种状态，并各配一格；",
          "2. 门的每条断言把「我造的是哪个状态」写进收据（本单 Y2 已按这个写法：三轮分别记 `constructed_open` / `cleared` / `constructed_open_again`）。",
          ""]
    io.open(MD, "w", encoding="utf-8", newline="\n").write("\n".join(md))
    print("e2e receipts=%d counts=%s" % (len(files), json.dumps(counts, ensure_ascii=False)))
    print("live declared=%r at %s" % (live_rule["deciding_value"], live_rule["coordinate"]))
    print("stay_budget generated paths=%d %s" % (stay["generated_path_count"], stay["generated_paths"][:1]))
    print("READING " + os.path.join(EV, "declared_shape_r1.json").replace("\\", "/"))
    print("WROTE " + MD.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
