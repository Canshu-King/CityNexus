# -*- coding: utf-8 -*-
"""账本里最近的块头（按**块头自称的时间**排，不按文件顺序——账本按作者分块插入，位置不代表新旧）。

04:52 修的一处判据缺陷：上一版用 `\\b(\\d\\d)[:：]?(\\d\\d)` 抓时间，结果 `2026-09-29` 里的
"20"+"26" 先命中，一堆块被排成 20:26；`02:21` 那形也会和 `+08` 打架。现在只在**日期之后**的片段里
抓 `HH:MM` 或 `HHMM(+08)`，并要求小时在 00-23、分钟在 00-59。
"""
import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")

DATE = re.compile(r"(2026-(\d\d)-(\d\d))|(\(\d\d)(\d\d)\)")  # 2026-09-29 或 0929
HM = re.compile(r"\b([01]?\d|2[0-3])[:：]?([0-5]\d)\b")

rows = []
for i, l in enumerate(lines):
    if not l.startswith("### "):
        continue
    d = DATE.search(l)
    if not d:
        continue
    mm, dd = (d.group(2), d.group(3)) if d.group(2) else (d.group(4), d.group(5))
    rest = l[d.end():]
    t = HM.search(rest)
    if not t:
        continue
    hh, mi = t.group(1), t.group(2)
    rows.append(("%s-%s %02d:%s" % (mm, dd, int(hh), mi), i + 1, l.strip()[:170]))

rows.sort(reverse=True)
since = sys.argv[1] if len(sys.argv) > 1 else "09-29 03:30"
sel = [r for r in rows if r[0] >= since]
print("块头总数=%d，时间 >= %s 的有 %d 枚（新→旧）" % (len(rows), since, len(sel)))
for k, ln, h in sel[:28]:
    print("  [%s] :%d %s" % (k, ln, h))
