# -*- coding: utf-8 -*-
"""把「挂在账本与流水里、等号令者一个人裁」的问题收成一格清单——只读。

为什么要单开这一件：裁语的入口只有号令者一枝笔（LEDGER_SINGLE_WRITER_V1），车道不许自己改守卫、
不许自己定产品语义，所以一句「请裁一格」挂一小时，那条车道就整条停一小时。他一轮要亲测十几枚块，
最容易漏的就是这种**不在派单行里、埋在正文中段的问句**。这一件把它们逐枚挖出来，带上：
谁问的（块头逐字）、什么时候（块头自报时刻 + 入账文件名戳）、原文（不缩句，只截断）、等了多久。
0 写账本、0 改任何人的文件、0 判定该不该裁——那仍是他的活。
"""
import glob
import io
import os
import re
import sys
import time

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 挖问句的词面（宁窄勿宽：判据要能被别人复算，所以每条命中都打印原文）
ASK = re.compile(u"请裁|求裁|要你裁|等你裁|需要你裁|要你定|得你点头|得由你或用户点头|请裁决|二选一|该不该")
TOP_LINES = 6000          # 账本只看 ORDERS 起的前这么多行（新件都在这一带）

txt = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
try:
    start = next(i for i, l in enumerate(txt) if l.startswith(u"## ORDERS"))
except StopIteration:
    start = 0
region = txt[start:start + TOP_LINES]

# 入账时刻：文件名戳（HHMMSS，无日期）→ 用 mtime 限定今天
stamp = {}
for f in glob.glob(os.path.join(INBOX, "_processed", "*.md.inserted_*")):
    m = re.search(r"(.+)\.md\.inserted_(\d{6})$", os.path.basename(f))
    if m and time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(f))) == time.strftime("%Y-%m-%d"):
        stamp[m.group(1)] = m.group(2)

head = None
head_line = 0
rows = []
for i, l in enumerate(region):
    if l.startswith(u"### "):
        head = l[4:].strip()
        head_line = start + i + 1
    elif head and ASK.search(l):
        rows.append((head, head_line, l.strip()))

print("=== 挂在账本里的待裁问句：区域 %s 起 %d 行，命中 %d 条 ===" % (start + 1, len(region), len(rows)))
seen = set()
for head, ln, q in rows:
    key = (head[:40], q[:60])
    if key in seen:
        continue
    seen.add(key)
    hm = re.match(u"(\\d\\d:\\d\\d)", head)
    self_time = hm.group(1) if hm else "?"
    who = re.findall(r"[0-9a-f]{8}", head)
    print("- 块头（第 %s 行）：%s" % (ln, head[:150]))
    print("    自报时刻 %s｜块名里能取到的会话 id：%s" % (self_time, " ".join(who) or "没写"))
    print("    问句原文：%s" % q[:300])
    print()

# 车道流水里那种「要点头」的（不在账本里，只在她们最后一段正文）
ARCH = os.path.join(HERE, "lane_tail_full.txt")
if os.path.exists(ARCH):
    a = io.open(ARCH, encoding="utf-8", errors="replace").read()
    print("=== 只在流水尾条里、没进账本的等待（取自 12:47 的落档件 lane_tail_full.txt）===")
    for m in re.finditer(r"==== ([0-9a-f]{8}) tail_len=\d+ ====\n(.*?)(?=\n==== |\Z)", a, re.S):
        body = m.group(2).strip().replace("\n", " ")
        hit = re.search(u"[^。]{0,90}(?:得你点头|得由你或用户点头)[^。]{0,90}。", body)
        print("- `%s`：%s" % (m.group(1), (hit.group(0) if hit else body[:170]).strip()))
