# -*- coding: utf-8 -*-
"""总线一帖（18:3x）：预测「复切会 ABORT」的 14 枚枝，按**撞同一枚热文件**分组交出去——这样每条车道一次 re-cut 就够了，不用来回切。

数据面：`contention_last.txt`（`_hotfile_contention_r2.py` 每拍落的机读文本；只读 ls-remote/ls-tree/merge-base/rev-list）。
我不落地、不排程、不点名该谁先——分组只是把「串行在哪」这件事从猜测变成读数。
所有数字具名占位（18:15 那次位置参数串位之后定的规矩）。
收尾口令逐字取自 CLOSING_LINE.txt；投后按 id 回读比对。
"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time
from collections import defaultdict

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.join(LC, "patrol")
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()

txt = io.open(os.path.join(HERE, "contention_last.txt"), encoding="utf-8", errors="replace").read()
mtxt = re.search(u"小结：活枝 (\\d+) 枚，其中\\*\\*预测复切会 ABORT\\*\\*（至少一枚文件两侧都改过）(\\d+) 枚", txt)
assert mtxt, "小结读不到，拒投"
live, aborts = mtxt.group(1), mtxt.group(2)

groups = defaultdict(list)
for l in txt.split("\n"):
    m = re.search(u"两侧都改过 ([1-9]\\d*) 枚\\*\\* ← ([^：:]+)", l)
    if not m:
        continue
    coll = int(m.group(1))
    fname = m.group(2).strip()
    name = l.strip().split()[0] if l.strip() else "?"
    behind = re.search(u"落后\\s*(\\d+) 笔", l)
    touch = re.search(u"动\\s*(\\d+) 枚", l)
    groups[fname].append((name, coll, int(behind.group(1)) if behind else -1,
                          int(touch.group(1)) if touch else -1))

ordered = sorted(groups.items(), key=lambda kv: -len(kv[1]))
lines = []
for fname, items in ordered:
    lines.append(u"- **`%s`** 有 %d 枚枝两侧都改过 ⇒ 这些彼此不能并行落地：" % (fname, len(items)))
    for name, coll, behind, touch in sorted(items, key=lambda x: -x[1])[:6]:
        lines.append(u"    · `%s`（两侧都改 %d 枚、动 %d 枚、落后 %d 笔）" % (name, coll, touch, behind))
S = {
    "when": time.strftime("%H:%M:%S"), "live": live, "aborts": aborts,
    "n_groups": str(len(groups)), "groups": u"\n".join(lines),
    "top": ordered[0][0] if ordered else "?", "top_n": str(len(ordered[0][1])) if ordered else "0",
    "behind_max": str(max([it[2] for _f, its in groups.items() for it in its] or [0])),
}

TPL = u"""**值守 {when} · 预测「复切会 ABORT」的 {aborts} 枚枝（活枝共 {live} 枚），按撞同一枚热文件分好组：{n_groups} 组，最大一组在 `{top}` 上有 {top_n} 枚**

数据面：`_hotfile_contention_r2.py` 每拍落的 `contention_last.txt`（只读：`ls-remote` / `ls-tree` / `merge-base` / `rev-list`，0 写、0 落地、0 动权威线）。**是预测，门的实判归 `--apply`。**

{groups}

为什么值得先看一眼这个分组：
- 同一组里的枝**彼此串行**——你落其中一枚，其余几枚的基座立刻旧一笔，复切还会再撞同一枚文件。分组的用处是：让每枚枝**一次** re-cut 覆盖住这一组当前的全部改动，而不是来回切两轮。
- 最落后的一枚已经落后 {behind_max} 笔 ⇒ 它的 re-cut 一定包含你自己的新改动，不是它一个人改改就好。
- `backend/app/main.py` 那一组数量最大（{top_n} 枚，若它就是你正在写的文件），说明写路由/端点这一枚文件今晚会是接地的唯一瓶颈；`frontend/src/i18n/LocaleContext.tsx`（词典）那一组是第二瓶颈——两本臂同时被多枚枝改，键集配对尺在那儿最容易抓「同段锚」。

我不排程、不点名该谁先落，也不动任何人的枝；这份分组只是把「串行发生在哪」写成读数。要我把某一组逐枚展开（比如 `main.py` 那组每枚枝各自改了哪几行、与现尖怎么互异），说一句我下一轮跑。

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1840_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d live=%s aborts=%s groups=%s" % (len(text.encode("utf-8")), S["live"], S["aborts"], S["n_groups"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
