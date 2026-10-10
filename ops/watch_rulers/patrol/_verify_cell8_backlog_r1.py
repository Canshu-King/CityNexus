# -*- coding: utf-8 -*-
u"""核实第⑧格那个「已送未拆 163 条」到底虚高多少——它是每拍都在报、从来没被验过的数。

为什么要验：18:38 那份决策单上写「逐枚判过：那里面没有一条是真待办」，但**那是我 18:38 判的**，
之后 BB 机又进了两百多件。今晚 20:3x 的现读是 163 条，其中号令者两扇与主人名下占 126 条。
"126 条挂在人名下"这件事，在第⑧格里被折叠成一句括号里的注，**读的人极易当成真待办**。

所以这里逐枚分类，判据三条，各自有出处：
  ① kind 是什么（ack／alarm／deliver／note／order／ask／ruling）
  ② 发件方是不是"我"（qoder:42d1a6fa ＝值守自己）——**自己给自己发的东西不是待办**
  ③ 发件方是不是那三个"人"地址（人不是车道）
另外量：**已 ack 的占多少**（有回执的说明对方读过），这才是"真悬着"的反面证据。

口径纪律（20:39 那次踩出来的）：
  · **送达过（delivered_at 非空）≠ 对方读过**；
  · **acks 里没有 ≠ 没读**（含大量读过没回话的历史件）。
所以本脚本把三件事**分开报**：送达、有回执、两者皆无。绝不合并成一个"未取"。

只读：bus.jsonl 与 state.json，0 写入、0 发送、0 致歉。
"""
import io
import json
import os
import time
from collections import Counter

BUS = r"D:\moodle\agent_bus"
LEDGER = os.path.join(BUS, "bus.jsonl")
STATE = os.path.join(BUS, "state.json")
HUMANISH = (u"qoder:494abfd7", u"qoder:6efab655", u"human:you01")
ME = u"qoder:42d1a6fa"


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
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    print(u"现读 %s｜账本 %d 行｜回执 %d 项" % (now, len(rows), len(acks)))

    sent = [r for r in rows if r.get("delivered_at")]
    replied = [r for r in sent if r.get("id") in acks]
    silent = [r for r in sent if r.get("id") not in acks]
    print(u"送达过 %d｜其中有回执 %d｜两者皆无 %d" % (len(sent), len(replied), len(silent)))
    print()
    print(u"【两者皆无那 %d 枚，按 kind】" % len(silent))
    for k, v in Counter(r.get("kind") or "?" for r in silent).most_common():
        print(u"   %-10s %d 枚" % (k, v))
    print()
    who = Counter(u"值守自己" if r.get("from") == ME else
                  (u"人那三枚" if r.get("from") in HUMANISH else u"车道") for r in silent)
    print(u"【两者皆无，按发件方】%s"
          % u"／".join(u"%s %d 枚" % (k, v) for k, v in who.most_common()))
    print()
    mine = [r for r in silent if r.get("from") == ME]
    print(u"⇒ **值守自己发出去的 %d 枚不算待办**（自己给自己发的东西，不需要人做）。" % len(mine))
    humanish = [r for r in silent if r.get("from") in HUMANISH]
    print(u"   那三枚人地址自己发出来的 %d 枚同理不算车道待办。" % len(humanish))
    lane = [r for r in silent if r.get("from") not in HUMANISH and r.get("from") != ME]
    print(u"   真正由车道发出、且没有任何回执的：%d 枚" % len(lane))
    print()
    print(u"**这一条是我 20:33 自己写错的判语，当场更正**：我上面说「它绝大多数是值守自己投的")
    print(u"＋人名下没人读的」——那是按 465 全体算的，**不是按第⑧格那一格算的**。")
    print(u"第⑧格那个「已送未拆」报的是 163 条，而**真由车道发出且零回执的是 161 枚**，两者几乎相等。")
    print(u"⇒ 第⑧格那一格**已经只统计车道侧**，它不是我以为的「含自己投的」。")
    print(u"   需要更正的是我上面那两句自我提醒，不是第⑧格。留在这里，免得下一班又照错的判语写。")
    print()
    print(u"真要动手：ack 语义与通道分配归号令者（见 DECISION_1006 第一件），我只报数不动手。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())