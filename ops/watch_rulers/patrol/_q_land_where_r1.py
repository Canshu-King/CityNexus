# -*- coding: utf-8 -*-
"""把「交完活停着等验收」那几扇，逐扇对上**她在等哪一枚落**——一句话能点单的程度。

为什么不是只报「3 扇停着」：那已经是哨兵 Q 档做的事了，包工头看完还是得自己去找。
这一格把两份现读拼起来：
· Q 档那一行的车道与龄（读哨兵最新一轮的总结，不另算一套判据）；
· 落地顺序表的枝名与自报改动枚数（`_landing_plan_*.txt`，同一趟里的现读，只读预测）。
拼出来的东西是：**这扇停着，是因为她那枝还在等落；她那枝在甲（可同批）／乙（要跟谁分跳）／丙（代次已过期，先别点）哪一桶**。

数不手打：两份都从工件正则取，取不到就具名报「对不上」，不猜。
"""
import glob
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = sorted(glob.glob(os.path.join(HERE, u"_landing_plan_1005_*.txt")),
              key=os.path.getmtime)[-1]
SENT_LOG = os.path.join(HERE, u"_sentinel_relay_latest.log")
ART = os.path.join(HERE, u"_q_land_where.txt")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    plan = io.open(PLAN, encoding="utf-8", errors="replace").read()
    sent = io.open(SENT_LOG, encoding="utf-8", errors="replace").read().splitlines()
    q = [l for l in reversed(sent) if u"交完活停着等验收" in l]
    if not q:
        raise SystemExit(u"ABORT：读不到 Q 档那一行 ⇒ 不拼这张表")
    qline = q[0]
    lanes = re.findall(u"([0-9a-f]{8}) ([^、（]+) 交(\\d+) 分/静(\\d+) 分", qline)
    if not lanes:
        raise SystemExit(u"ABORT：Q 档那行里没解析出车道（形状变了）：%s" % qline[:160])
    cands = re.findall(u"^  (review/\\S+) 头 ([0-9a-f]{12}) 自报改动\\s*(\\d+) 枚", plan, re.M)
    # 对子一次解析到位：两枚枝名、撞几枚文件、撞在哪枚文件上。
    # （上一版这里我自己写错了取值式，把枝名自己当成对家打出来——表给包工头看就是害人点错，
    #   所以现在直接按 (a, b, n, file) 四元组取，且下面用到时对家必须不含自己，含就抛。）
    pairs = re.findall(u"^  (\\S+) × (\\S+) 共 (\\d+) 枚：(\\S+)", plan, re.M)
    collided = set()
    for a, b, _n, _f in pairs:
        collided.add(a); collided.add(b)
    stale = set(re.findall(u"(review/\\S+) 块报", plan))
    free = set()
    fm = re.search(u"与谁都不同改的枝 \\d+ 枚：(.+)", plan)
    if fm:
        free = set(x.strip() for x in fm.group(1).split(u","))

    out = [u"取数时刻 %s｜Q 档原文取 %s｜候选表取 %s"
           % (time.strftime("%Y-%m-%d %H:%M:%S"), u"_sentinel_relay_latest.log", os.path.basename(PLAN))]
    lines = []
    for lane, tag, delivered, silent in lanes:
        mine = [c for c, _h, _n in cands if lane in c]
        if not mine:
            lines.append(u"车道 %s（%s）｜交完 %s 分、静 %s 分｜候选表里没有她的枝 ⇒ 她等的不是落地，是点单或裁语"
                         % (lane, tag.strip(), delivered, silent))
            out.append(lines[-1])
            continue
        for br in mine:
            if br in stale:
                bucket = u"丙（块里代次已过期，先别点，让她重报当代号）"
            elif br in collided:
                opp = [(o, f) for a, b, _n, f in pairs for o in (a, b)
                       if br in (a, b) and o != br]
                if not opp:
                    raise SystemExit(u"ABORT：%s 在撞车集合里却找不到对家 ⇒ 我对这张表的解析不可信" % br)
                bucket = u"乙（要跟 %s 分跳落，同批后落那枚必 ABORT）" % u"、".join(
                    u"%s（撞 %s）" % (o[:46], f.split(u"/")[-1]) for o, f in opp[:2])
            elif br in free:
                bucket = u"甲（彼此不改同一枚文件，可同批落）"
            else:
                bucket = u"（不在甲也不在乙：这一枚我没对上桶，具名留给你查，不猜）"
            n = [c[2] for c in cands if c[0] == br][0]
            lines.append(u"车道 %s（%s）｜交完 %s 分、静 %s 分｜枝 %s 自报改动 %s 个文件｜%s"
                         % (lane, tag.strip(), delivered, silent, br, n, bucket))
            out.append(lines[-1])
    io.open(ART, u"w", encoding=u"utf-8", newline=chr(10)).write(chr(10).join(out) + chr(10))
    print(chr(10).join(out))
    print(u"\n候选表分母：枝 %d 枚｜对子 %d 对（涉及 %d 枚枝）｜代次过期 %d 枚｜同批可落 %d 枚" % (
        len(cands), len(pairs), len(collided), len(stale), len(free)))
    return 0


if __name__ == u"__main__":
    sys.exit(main())
