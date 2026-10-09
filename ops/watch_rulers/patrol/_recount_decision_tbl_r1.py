# -*- coding: utf-8 -*-
u"""重算 DECISION_1006 那三行，并把**三种"读过没有"的口径分开列**。

为什么要分口径（19:39 实测踩出来的）：18:38 那份单写「号令者未取 79」，
我第一版照着"acks 里没有就是未取"算，得 369 —— 差 4.7 倍，方向都会裁反。
现读三口径的关系是：
  · `delivered_at` 非空 ⇒ **送达过**（投递腿走过），290/384
  · `acks[id]` 有值 ⇒ **对方回过回执**，15/384，且全部 15 条都是号令者自己写的
  · `seen_topics` ⇒ 值守侧记录的话题游标，与收件人无关（743 条，命中号令者收件 0）
⇒ 真正的病根形状：**290 件送达、只有 15 件有回执**，即"通道到得了、收件端不读"。
这与 18:38 单上的判断（alarm 27 未取、样本 0）方向一致，但数字必须按现读给。

**不许拿"未取"这个词**去指 acks 的空——那是"没回执"，含大量已被对方读过但没回话的历史件。
所以本脚本打印的分母/分子逐项都写清是哪一种口径。
"""
import io
import json
import os
import time
from collections import Counter

BUS = r"D:\moodle\agent_bus"
LEDGER = os.path.join(BUS, "bus.jsonl")
STATE = os.path.join(BUS, "state.json")

TARGETS = [(u"qoder:494abfd7", u"号令者"),
           (u"qoder:6efab655", u"副号令者·夜班"),
           (u"human:you01", u"主人")]
KINDS_OF_INTEREST = ("deliver", "order", "ask", "ruling")


def main():
    if not os.path.exists(LEDGER):
        print(u"REFUSE：账本不在 %s，不报数" % LEDGER)
        return 1
    rows = []
    for line in io.open(LEDGER, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    st = json.load(io.open(STATE, encoding="utf-8"))
    acks = st.get("acks") or {}
    forgotten = set(st.get("forgotten") or [])
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    print(u"现读时刻 %s｜账本 %d 行｜acks %d 项｜forgotten %d 枚"
          % (now, len(rows), len(acks), len(forgotten)))
    print()
    print(u"| 收件人 | 总收件 | 送达过(delivered_at) | 有回执(acks) | 送达但零回执 |")
    print(u"|---|---|---|---|---|")
    for addr, name in TARGETS:
        mine = [r for r in rows if r.get("to") == addr]
        alive = [r for r in mine if r.get("id") not in forgotten]
        got = [r for r in alive if r.get("delivered_at")]
        ack = [r for r in alive if r.get("id") in acks]
        zero = [r for r in got if r.get("id") not in acks]
        print(u"| `%s` %s | %d | %d | %d | %d |"
              % (addr, name, len(mine), len(got), len(ack), len(zero)))
        print(u"|　└ 零回执按 kind | | | | %s |"
              % (u"／".join(u"%s %d" % (k, v) for k, v in
                           Counter(r.get("kind") or "?" for r in zero).most_common(6)) or u"—"))
        pend = [r for r in alive if r.get("kind") in KINDS_OF_INTEREST]
        pac = [r for r in pend if r.get("id") in acks]
        print(u"|　└ 待验收类 %s 共 %d 枚，其中已回执 %d 枚 | | | | |"
              % (u"／".join(KINDS_OF_INTEREST), len(pend), len(pac)))
    print()
    print(u"⇒ 读法：**送达但零回执**才是病根那一格；「acks 为空」不等于「没读」。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())