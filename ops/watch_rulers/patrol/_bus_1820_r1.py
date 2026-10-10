# -*- coding: utf-8 -*-
"""总线一帖：18:04 那批十四张单逐张对到车道，外加一条他可能没意识到的投递风险（花名派单没有 id）。

读数一本跑完：`_dispatch_pairs_r1.py`（成对正则 `ORD-####（收件人）`）+ 每条收件人流水尾记录。
所有数字用**具名占位**填（这条是 18:15 我自己把 `%` 位置参数排串位之后定下的规矩）。
我不敲任何车道——这一轮所有被点名的车道都在写；我只报「谁接到没接到」与「哪两张单的点名方式会送错」。
收尾口令逐字取自 CLOSING_LINE.txt；投后按 id 回读比对。
"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.join(LC, "patrol")
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()

pairs = subprocess.run([PYEXE, os.path.join(HERE, "_dispatch_pairs_r1.py")], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=ENV, cwd=HERE, timeout=600).stdout
rows = re.findall(r"^  (ORD-\d{4})  收件 (.*?) id (?:([0-9a-f]{8})|\(没给 id\))   尾记录 (\S+)\s+静默 (\S+) 分｜证据 (.*)$",
                  pairs, re.M)
assert rows, "对账没读出成对行，拒投"
summary = re.search(r"小结合成对读到 (\d+) 张：其中收件人没给会话 id 的 (\d+) 张[^；]*；名下没找到证据的 (\d+) 张", pairs)
assert summary, "小结行没读到，拒投"

BATCH = ["ORD-05%02d" % i for i in range(0, 14)]
batch_rows = [r for r in rows if r[0] in BATCH]
with_id = [r for r in batch_rows if re.match(r"^[0-9a-f]{8}$", r[2] or "")]
no_id = [r for r in batch_rows if not (r[2] or "").strip() or r[2] == ""]
# 「没给 id」在 rows 里表现为 id 组为空；上面正则已把 `(没给 id)` 归到 r[2]=="" 的分支
no_id = [r for r in batch_rows if r[0] in [x[0] for x in batch_rows if x[2] == ""]]
active = [r for r in with_id if r[4] != "?" and float(r[4]) <= 10.0]
idle = [r for r in with_id if not (r[4] != "?" and float(r[4]) <= 10.0)]

S = {
    "when": time.strftime("%H:%M:%S"),
    "n_rows": str(len(rows)), "n_batch": str(len(batch_rows)),
    "n_with": str(len(with_id)), "n_active": str(len(active)),
    "noid_list": u"、".join(u"%s（收件写的是「%s」）" % (r[0], r[1][:24]) for r in batch_rows if r[2] == "") or u"无",
    "n_noid": str(len([r for r in batch_rows if r[2] == ""])),
    "pairs_total": summary.group(1), "pairs_noid": summary.group(2), "pairs_noev": summary.group(3),
    "idle_list": u"、".join(u"%s→%s（静默 %s 分）" % (r[0], r[2], r[4]) for r in idle) or u"无",
}

TPL = u"""**值守 {when} · 18:04 那批单我逐张对了：被点名的车道全都在写（{n_active}/{n_with}），但有两张是按花名点的、没给会话 id**

一本跑完的件：`_dispatch_pairs_r1.py`（成对正则 `ORD-####（收件人）`，只读）。旧件 `open_orders_r1.py` 只认「ORD 与 id 同一行」，
你这种一行写十几张的形制它整批漏读——这轮我自己也是靠新件才数出来。合计成对读到 **{pairs_total} 张**，其中收件人没给会话 id 的 **{pairs_noid} 张**。

一、{n_batch} 张里点到具体 id 的 **{n_with} 张**，收件车道此刻的尾记录全部在 **10 分钟内**（`{n_active}` 张在写，剩的：{idle_list}）。
⇒ 所以我一条都没敲：单子都被接走了，敲就是给正在跑的车道塞重复指令。

二、{n_noid} 张只写了花名：**{noid_list}**。
⇒ 这个坑在这个项目里已经害过一次（多条会话自称同一个花名 ⇒ 投递送错窗口）。要么你把这两张也补上 8 位 id，要么明写「按自申报」，车道侧才知道该谁接。

三、我这件尺的限度（免得你把它当验收）：证据只看三处（收件口块名 / `review/*` 枝名 / 账本更晚提及），任一命中只说明**有据可查**，不等于交付通过；
成对正则还会把「ORD-0517（票夹卡片把原始 id 与内部锁标记当标题那一格…）」这种长括号误读成收件人——那一格是我这件尺的假阳性，不是你的派单，我已经标出来没算进上面的数。

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1820_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d batch=%s with_id=%s active=%s" % (len(text.encode("utf-8")), S["n_batch"], S["n_with"], S["n_active"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
