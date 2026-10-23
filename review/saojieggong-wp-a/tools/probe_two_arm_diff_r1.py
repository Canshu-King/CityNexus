# -*- coding: utf-8 -*-
"""两臂逐格对表（票夹取景器版）。

格子身份取 (场景, 选择器, 文本前 24 字) —— 故意不含比值：号令者那把尺把 sel|ratio|text 当身份，
同一格从 1.09 变成 6.47 会同时记成「修好一格 + 新开一格」。这里把比值挪到判据里分三类：
  消除   = 对照红、实臂不红
  位移   = 两臂都红但比值变了（再分变好/变坏）
  新开   = 对照不红、实臂红  ← 判据要这一类为零
"""
import io
import json
import os
import sys

HERE = r"D:/moodle/_cmdr_saojieggong_1016"


def load(arm):
    p = os.path.join(HERE, "probe_%s" % arm, "report.json")
    if not os.path.isfile(p):
        return None
    return json.load(io.open(p, encoding="utf-8"))


def cells(rep):
    out = {}
    for s in rep["scenes"]:
        sc = "%s/%s" % (s["vp"], s["theme"])
        for r in s["fail_rows"]:
            out[(sc, r["sel"], r["text"][:24])] = r
        # 不红的格也收，才能判「新开」
        for r in s.get("on_booking", []):
            pass
    return out


def good_cells(rep):
    out = {}
    for s in rep["scenes"]:
        sc = "%s/%s" % (s["vp"], s["theme"])
        for r in s.get("on_booking", []):
            if r.get("pass"):
                out[(sc, r["sel"], r["text"][:24])] = r
    return out


def main():
    a = load(sys.argv[1] if len(sys.argv) > 1 else "control")
    b = load(sys.argv[2] if len(sys.argv) > 2 else "armA")
    if not a or not b:
        print("两臂快照不全（probe_control / probe_armA 至少要有一份），拒绝下结论")
        return 2
    ca, cb = cells(a), cells(b)
    ga = good_cells(a)
    cleared = [k for k in ca if k not in cb]
    opened = [k for k in cb if k not in ca]
    moved = [k for k in ca if k in cb]
    better = [k for k in moved if cb[k]["ratio"] > ca[k]["ratio"]]
    worse = [k for k in moved if cb[k]["ratio"] < ca[k]["ratio"]]
    print("对照臂 红格 %d 枚 / 实臂 红格 %d 枚" % (len(ca), len(cb)))
    print("节点：对照 %d 枚 / 实臂 %d 枚；卡片：对照 %d / 实臂 %d；收件栏：对照 %d / 实臂 %d" % (
        a["totals"]["nodes"], b["totals"]["nodes"], a["totals"]["booking_cards"], b["totals"]["booking_cards"],
        a["totals"]["inbox_aside"], b["totals"]["inbox_aside"]))
    print()
    for k in sorted(cleared):
        print("  消除 → %s %-34s %-24s %s" % (k[0], k[1][:34], k[2][:24], ca[k]["ratio"]))
    for k in sorted(better):
        print("  位移变好 → %s %-30s %-20s %s → %s（门槛 %s，两臂都还没过）" % (
            k[0], k[1][:30], k[2][:20], ca[k]["ratio"], cb[k]["ratio"], cb[k]["need"]))
    for k in sorted(worse):
        print("  位移变坏 → %s %-30s %-20s %s → %s" % (
            k[0], k[1][:30], k[2][:20], ca[k]["ratio"], cb[k]["ratio"]))
    for k in sorted(opened):
        print("  新开 → %s %-34s %-24s %s（门槛 %s，对照臂这格原本 %s）" % (
            k[0], k[1][:34], k[2][:24], cb[k]["ratio"], cb[k]["need"],
            "不在量到的面上" if k not in ga else "过"))
    print()
    print("合计：消除 %d 枚，位移变好 %d 枚，位移变坏 %d 枚，新开 %d 枚" % (
        len(cleared), len(better), len(worse), len(opened)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
