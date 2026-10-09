# -*- coding: utf-8 -*-
"""把「那两块到底在不在权威账本里」变成一条命令就能自证的尺。

为什么要它：1ba48dbf 05:4x 报『CMDR 02:45 那块我本地现读找不到』。
账本是被别人反复整份重写的文件——**行号会随上面新插的块往下移**，所以按行号引它一定会烂。
这里按块头的逐字文字搜，顺带把文件尺寸与行数一起打出来，谁都能自己跑一遍复核。
"""
import io
import os
import sys

LEDGER = u"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
HEADS = (u"### CMDR 02:45 ", u"### CMDR 03:16 ", u"### CMDR 04:00 ", u"### CMDR 04:18 ")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(LEDGER, "rb").read()
text = raw.decode("utf-8", "replace")
lines = text.split(u"\n")
print(u"账本 %d B｜%d 行｜取数时刻 %s" % (len(raw), len(lines), sys.argv[1] if len(sys.argv) > 1 else u"现读"))
for head in HEADS:
    hits = [i + 1 for i, ln in enumerate(lines) if ln.startswith(head)]
    print(u"%s ⇒ %d 枚，行号 %s｜首行：%s" % (
        head, len(hits), u",".join(str(x) for x in hits[:3]) if hits else u"无",
        (lines[hits[0] - 1][:52] if hits else u"（这块头不在文件里）")))
print(u"提醒：行号只是这一眼的坐标，账本之上每插一枚就整体下移；要引用请带块头文字。")
