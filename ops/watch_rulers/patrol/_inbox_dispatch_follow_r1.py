# -*- coding: utf-8 -*-
"""值守 17:40 · 收件箱里每一枚派单的「车道动了没有」——按枚列，不按单号列。

为什么要这一枚：`_unclaimed_orders_r1.py` 回答的是「这张单有没有人接」（按单号、跨号令者块配对），
它 17:15 报 0 张。但用户 17:2x 的现场是「没几个窗口在跑」——那要的是**另一格**：
收件箱里挂着 13 枚块头，每一枚都点了一条车道；哪些车道在收到之后真的动了、哪些还睡着。
只有这张表能告诉号令者「发出去的话有几枚没落地」，也告诉我该往哪几扇窗送。

判据（两件事比对，都是实测）：
  枚上写的时刻  —— 块头里的 `@HH:MM+08`，没有就用文件 mtime；
  那条车道的流水 —— 该 id8 的 jsonl 最后一次写盘。
  动过 = 流水最后写盘 >= 枚上时刻；没动 = 晚于它就没再写过（说明这条派单落在那扇窗上没回声）。

用法：PYTHONIOENCODING=utf-8 python _inbox_dispatch_follow_r1.py
边界：只读账本与流水；0 次敲门、0 次写账本。块头里没点到 8 位 id 的（例如按花名写的）标「认不出收件窗」，不猜。
"""
import glob
import io
import os
import re
import sys
import time

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_inbox_dispatch_follow_latest.txt")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def lane_mtime(sid8):
    g = glob.glob(os.path.join(PROJ, sid8 + "*.jsonl"))
    if not g:
        return None
    return max(os.path.getmtime(p) for p in g)


def main():
    t = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    m = re.search(r"^## ORDERS\b.*?(?=^## )", t, re.M | re.S)
    if not m:
        print("读不到 `## ORDERS` 段")
        return 1
    seg = m.group(0)
    now = time.time()
    day0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d"))
    lines = [u"_inbox_dispatch_follow_r1.py 于 %s｜收件箱 %d 字符" % (time.strftime("%H:%M:%S", time.localtime(now)), len(seg))]
    heads = [(mm.start(), mm.group(1)) for mm in re.finditer(r"^### (.+)$", seg, re.M)]
    rows = []
    for pos, h in heads:
        sid = None
        mm = re.search(r"\b([0-9a-f]{8})\b", h)
        if mm and lane_mtime(mm.group(1)):
            sid = mm.group(1)
        mt = re.search(r"@(\d\d):(\d\d)\+0?8", h)
        if mt:
            when = day0 + int(mt.group(1)) * 3600 + int(mt.group(2)) * 60
            src = u"枚上 @%s:%s" % (mt.group(1), mt.group(2))
        else:
            when = None
            src = u"枚上没写时刻"
        rows.append((h, sid, when, src))
    n_moved = n_still = n_unknown = 0
    for h, sid, when, src in rows:
        if not sid:
            n_unknown += 1
            lines.append(u"认不出收件窗  %-96s %s" % (h[:96], src))
            continue
        lm = lane_mtime(sid)
        if when is None:
            lines.append(u"时刻不可比  %-9s 流水 %s 前动过｜%s" % (sid, int((now - lm) / 60), src))
            n_unknown += 1
            continue
        if lm >= when:
            n_moved += 1
            lines.append(u"有回声    %-9s 派单 %s｜流水在其后 %.1f 分钟动过" % (
                sid, time.strftime("%H:%M", time.localtime(when)), (lm - when) / 60.0))
        else:
            n_still += 1
            lines.append(u"没回声    %-9s 派单 %s｜那扇窗最后写盘在 %s（比派单还早 %.1f 分钟）" % (
                sid, time.strftime("%H:%M", time.localtime(when)),
                time.strftime("%H:%M:%S", time.localtime(lm)), (when - lm) / 60.0))
    lines.append(u"")
    lines.append(u"合计：收件箱块头 %d 枚｜有回声 %d｜没回声 %d｜认不出窗口或时刻 %d" % (len(rows), n_moved, n_still, n_unknown))
    lines.append(u"边界：判据只是「那条窗的流水最后写盘 晚不晚于 枚上时刻」；晚于不等于做完了，早于也不等于没收到（可能收到但还没轮到跑）。")
    out = u"\n".join(lines) + u"\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
