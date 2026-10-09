# -*- coding: utf-8 -*-
"""叫醒那条要我「在 `## ORDERS` 里找自己的单号」——这一枚尺把结果算出来并落档，不靠我印象。

为什么单独建：`open_orders_r1.py` 那版认的是「同一行里既有 ORD 又有 id」，号令者 09-30 18:04 那批
一行十四张的写法它漏了 13 张（详见 `_dispatch_pairs_r1.py:1` 的配对正则改造）。这里沿用配对形制，
并把「本会话名下几枚」这个问题单独回答：**枚数只从扫到的行里算，不从全文 grep 倒推**。

边界：账本只读；扫段 = `## ORDERS` 起、到下一个 `^## ` 标题或 +6000 行为止。取不到段就印读数不全。
"""
import io
import re
import sys

LEDGER = r"D:\moodle\CITYNexus_Agent_Control_ledger"  # 不用；真路径在下一行
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ME = sys.argv[1] if len(sys.argv) > 1 else "42d1a6fa"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

lines = io.open(LEDGER, encoding="utf-8", errors="replace", newline="").read().splitlines()
start = None
for i, l in enumerate(lines):
    if l.strip().startswith("## ORDERS"):
        start = i
        break
out = []
if start is None:
    out.append(u"读数不全：这一份里没有 `## ORDERS` 标题行（共 %d 行）" % len(lines))
else:
    end = start + 1
    while end < len(lines) and not (lines[end].startswith("## ") and not lines[end].startswith("## ORDERS")):
        end += 1
        if end - start > 6000:
            break
    seg = lines[start:end]
    pairs = []
    for off, l in enumerate(seg):
        for m in re.finditer(u"ORD-(0\\d{3})（([^）]{2,40})）", l):
            pairs.append((start + off + 1, m.group(1), m.group(2)))
        for m in re.finditer(u"ORD-(0\\d{3})\\s*[\\(\\[]([^\\)\\]]{2,40})[\\)\\]]", l):
            pairs.append((start + off + 1, m.group(1), m.group(2)))
    mine = [p for p in pairs if ME in p[2]]
    out.append(u"段：`## ORDERS` 在行 %d，段尾行 %d，段内 %d 行" % (start + 1, end, len(seg)))
    out.append(u"配对扫到的派单行（ORD+收件）共 %d 条" % len(pairs))
    out.append(u"收件串里含 `%s` 的：%d 条" % (ME, len(mine)))
    for ln, oid, rec in mine[:20]:
        out.append(u"   行 %d：ORD-%s ← %s" % (ln, oid, rec))
    uniq = sorted(set(p[1] for p in pairs))
    out.append(u"段内出现过的单号去重 %d 枚：%s" % (len(uniq), u",".join(uniq)))
    out.append(u"收件串去重（前 40 条，看清形制：有的写会话 id、有的写花名）：%s"
               % u" | ".join(sorted(set(p[2] for p in pairs))[:40]))
    hits = [(i + 1, l.strip()[:70]) for i, l in enumerate(lines) if ME in l]
    out.append(u"全文 grep `%s` 命中 %d 处（行号：前 70 字）：" % (ME, len(hits)))
    for ln, txt in hits:
        out.append(u"   %d: %s" % (ln, txt))
for o in out:
    print(o)
