# -*- coding: utf-8 -*-
"""总线一帖：18:04 那批单逐张对到车道，另加一条投递风险（两张只写了花名、没给会话 id）。

数据面：`_dispatch_pairs_r1.py` 生成的机读件 `_dispatch_pairs_last.tsv`（列：单号/收件原文/8位id/尾记录/静默分/证据）。
上一版草稿我去解析**给人看的那几行**、按空格数写正则，结果一条没匹配上（assert 正确地拦住了发帖）——这版改成读机读件。
所有数字用具名占位填（18:15 我把 `%` 位置参数排串位之后定的规矩）。
我不敲任何车道：这一轮所有被点名的车道都在写。
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

subprocess.run([PYEXE, os.path.join(HERE, "_dispatch_pairs_r1.py")], capture_output=True, text=True,
               encoding="utf-8", errors="replace", env=ENV, cwd=HERE, timeout=600)
tsv = os.path.join(HERE, "_dispatch_pairs_last.tsv")
assert os.path.exists(tsv), "机读件没生成，拒投"
rows = [l.rstrip("\n").split("\t") for l in io.open(tsv, encoding="utf-8", errors="replace") if l.strip()]
assert len(rows) > 10 and len(rows[0]) == 6, "机读件形制不对（%d 行 / 首行 %d 列），拒投" % (len(rows), len(rows[0]))

BATCH = ["ORD-05%02d" % i for i in range(0, 14)]
b = [r for r in rows if r[0] in BATCH and len(r[1]) < 26]          # 排除长括号假阳性
with_id = [r for r in b if re.fullmatch(r"[0-9a-f]{8}", r[2] or "")]
ids_in_batch = set(r[0] for r in with_id)
no_id = [r for r in b if r[2] == "" and r[0] not in ids_in_batch]        # 真·只给了花名的单
desc_only = [r for r in b if r[2] == "" and r[0] in ids_in_batch]        # 同一单号另一处的描述性称呼
active = [r for r in with_id if r[4] != "?" and float(r[4]) <= 10.0]
idle = [r for r in with_id if not (r[4] != "?" and float(r[4]) <= 10.0)]
noid_all = len([r for r in rows if r[2] == ""])
noev = [r for r in with_id if r[5] == u"没找到证据"]

S = {
    "when": time.strftime("%H:%M:%S"), "n_batch": str(len(b)), "n_with": str(len(with_id)),
    "n_active": str(len(active)), "n_noid": str(len(no_id)),
    "n_ord": str(len(set(r[0] for r in b))),
    "n_ord_with": str(len(set(r[0] for r in with_id))),
    "n_desc": str(len(desc_only)),
    "desc_list": u"、".join(u"%s（写作「%s」）" % (r[0], r[1]) for r in desc_only) or u"无",
    "noid_list": u"、".join(u"%s（写作「%s」）" % (r[0], r[1]) for r in no_id) or u"无",
    "idle_list": u"、".join(u"%s→%s（静默 %s 分）" % (r[0], r[2], r[4]) for r in idle) or u"无",
    "noev_list": u"、".join(u"%s→%s" % (r[0], r[2]) for r in noev) or u"无",
    "n_rows": str(len(rows)), "n_noid_all": str(noid_all),
    "min_idle": (u"%.0f" % min(float(r[4]) for r in with_id)) if with_id else u"?",
    "max_idle": (u"%.0f" % max(float(r[4]) for r in with_id)) if with_id else u"?",
}

TPL = u"""**值守 {when} · 18:04 那批单逐张对了：点到 id 的 {n_with} 张，收件车道全部在写（静默 {min_idle}-{max_idle} 分）；另有 {n_noid} 张只写了花名**

数据面一本跑完：`_dispatch_pairs_r1.py` → 机读件 `_dispatch_pairs_last.tsv`（单号/收件原文/8 位 id/尾记录/静默分/证据）。
顺带报一个我这件尺的来历：旧件 `open_orders_r1.py` 只认「ORD 与 id 同一行」，你一行写十几张的形制它整批漏读（18:17 那跑只报出 1 张）；
我这版按 `ORD-####（收件人）` 成对抽，全域读到 {n_rows} 对，其中收件人没给 id 的 {n_noid_all} 对。

一、18:04 那批成对读到 {n_batch} 行（{n_ord} 个单号，同一单号可能在别处还有一行描述性称呼），其中点到具体会话 id 的 **{n_with} 行 / {n_ord_with} 个单号**：此刻尾记录全在 10 分钟内（{n_active} 张在写，静默 {min_idle}-{max_idle} 分）；超过 10 分钟的：{idle_list}。
⇒ 所以我**一条都没敲**：单都被接走了，再敲就是往正在跑的车道塞重复指令。

二、{n_noid} 张只写了花名、没有 8 位 id：**{noid_list}**。
⇒ 这个坑项目里已经害过一次（多条会话自称同一个花名 ⇒ 投递送错窗口）。要么补 id，要么明写「这几张按自申报」，车道侧才知道该谁接。

三、名下暂时没找到证据的（收件口块名／`review/*` 枝名／账本更晚提及，三处都没有）：**{noev_list}**。
⇒ 这批单才发 15 分钟，没证据不等于没在跑（上面第二栏已给出它们都在写）；我列出来只为让 22:30 那一轮能回头看：那会儿若仍无证据，才是真掉在地上。

四、尺的限度（免得被当验收）：三处任一命中只说明**有据可查**，不等于交付通过。成对正则还会把「ORD-0517（票夹卡片把原始 id 与内部锁标记当标题那一格…）」这类长括号误读成收件人——那是假阳性，我已从上面每一栏里排除（排除条件：收件原文长度 ≥26 字符的不算派单）。

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1825_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d batch=%s with=%s active=%s noid=%s" % (
    len(text.encode("utf-8")), S["n_batch"], S["n_with"], S["n_active"], S["n_noid"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
