# -*- coding: utf-8 -*-
"""「今天新建、且账本一次都没引用」的导出树到底占多少——一条能量化的清理线索（只读）。

号令者 18:04 那块第六节已经自己做过一半：他逐枚 `grep -ac` 了八枚**旧**导出树，八枚引用全非零，所以他没动。
他缺的是另一半：**今天**这一批（14 张单在跑）建出来的树里，哪些账本根本没提过——那些才是可以「复现回来」的那一类
（项目里跑通过的路数：`git archive <40 位>` 能原地重建）。

实现：账本只读**一遍**（10 MB 级），对 314 枚顶层 `_qoder_*` 目录一次计数；再只对本轮新建的做 10 秒硬超时抽样 du。
不删、不改名、不重启任何人的进程。
"""
import io
import os
import re
import subprocess
import sys
import time

ROOT = r"D:\moodle"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

names = [d for d in os.listdir(ROOT) if d.startswith("_qoder_") and os.path.isdir(os.path.join(ROOT, d))]
led = io.open(LEDGER, encoding="utf-8", errors="replace").read()
# 单遍计数：把账本按空白切开成 token，统计每个目录名出现的次数（避免 314 次全文件 grep）
partial = {}
pat = re.compile("|".join(re.escape(n) for n in names))
for m in pat.finditer(led):
    partial[m.group(0)] = partial.get(m.group(0), 0) + 1

now = time.time()
rows = []
for n in names:
    mt = os.path.getmtime(os.path.join(ROOT, n))
    rows.append((n, (now - mt) / 3600.0, partial.get(n, 0)))

today = [r for r in rows if r[1] <= 12.0]
uncited_today = [r for r in today if r[2] == 0]
cited_today = [r for r in today if r[2] > 0]
old_uncited = [r for r in rows if r[1] > 12.0 and r[2] == 0]

print("顶层 `_qoder_*` 目录：%d 枚（账本单遍正则现读，计数可复算）" % len(names))
print("  今天 12 小时内动过：%d 枚｜其中账本引用 0 次：%d 枚｜有引用：%d 枚" % (len(today), len(uncited_today), len(cited_today)))
print("  12 小时以上没动过、且账本 0 引用：%d 枚" % len(old_uncited))
print()
print("账本引用最多的几枚（这些不能动，他 18:04 的口径也是这个）：")
for n, h, c in sorted(rows, key=lambda x: -x[2])[:6]:
    print("  %-46s 引用 %4d 次｜%5.1f 小时前动过" % (n, c, h))
print()
print("今天动过、账本 0 引用的（**候选**，逐枚 du 硬超时 12 秒）：")
tot = 0
got = 0
for n, h, c in sorted(today, key=lambda x: x[1])[:18]:
    if c:
        continue
    p = os.path.join(ROOT, n)
    try:
        r = subprocess.run(["du", "-sk", p], capture_output=True, text=True, timeout=12,
                           encoding="utf-8", errors="replace")
        kb = int(r.stdout.split("\t")[0]) if r.stdout.strip().split("\t")[0].isdigit() else None
    except Exception:
        kb = None
    if kb is None:
        print("  %-46s %5.1f h  du 超时/读不到（说明它大）" % (n, h))
    else:
        tot += kb
        got += 1
        print("  %-46s %5.1f h  %8.1f MiB" % (n, h, kb / 1024.0))
print("  抽样 %d 枚合计 %.1f MiB（其余没走完的先不算，不外推）" % (got, tot / 1024.0))
print()
df = subprocess.run(["df", "-k", "/d"], capture_output=True, text=True).stdout
m = re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%", df)
print("盘现值：余 %.1f MiB @ %s" % (int(m.group(3)) / 1024.0, time.strftime("%H:%M:%S")))
print("边界：账本引用 0 次 ≠ 可以删——证据可能入枝、被别的名字引用、或车道还在用；这句话只给「去哪找量」，删不删由号令者或用户点名。")
