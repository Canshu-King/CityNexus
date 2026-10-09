# -*- coding: utf-8 -*-
"""总线一帖（18:4x）：我今天所有「在写 N 条」的读数都低报了——名册/停摆扫描只遍历一张 13 条的静态花名表，
而今晚动过的会话有 18 枚。这条把错报范围与修法说清，并给出修好后的现值。

现值出自修好之后的 `_quota_roster_r1.py`（本帖运行当场跑），非记忆。
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

out = subprocess.run([PYEXE, os.path.join(HERE, "_quota_roster_r1.py")], capture_output=True, text=True,
                     encoding="utf-8", errors="replace", env=ENV, cwd=HERE, timeout=600).stdout
m = re.search(u"名册：停在额度 (\\d+)｜在写 (\\d+)｜静默非闸 (\\d+)", out)
assert m, "名册读数不全，拒投"
unreg = re.findall(u"未登记·([0-9a-f]{8})", out)
names = subprocess.run([PYEXE, "-c",
                        "import sys;sys.path.insert(0,r'%s');import quota_now as Q;print(len(Q.NAMES))" % HERE],
                       capture_output=True, text=True, env=ENV, timeout=120).stdout.strip()

# 两个数分别算：停摆扫描用的表（quota_now.NAMES）与名册用的表（_quota_roster_r1.NICKS），
# 漏掉的条数不一样，混着说就又变成一次「没核对出处」的读数。
import glob as _g
import quota_now as QN
import _quota_roster_r1 as QR
SELF = {"42d1a6fa", "494abfd7", "6efab655"}
act = {}
for f in _g.glob(os.path.join(QN.BASE, "*.jsonl")):
    if (time.time() - os.path.getmtime(f)) / 3600.0 <= 12.0:
        act[os.path.basename(f)[:8]] = os.path.getsize(f)
miss_names = sorted([k for k in act if k not in QN.NAMES and k not in SELF])
miss_nicks = sorted([k for k in act if k not in QR.NICKS and k not in SELF])
S = {
    "when": time.strftime("%H:%M:%S"), "table": str(len(QN.NAMES)),
    "nick_table": str(len(QR.NICKS)), "n_act": str(len(act)),
    "miss_n": str(len(miss_names)), "miss_list": u"、".join(u"`%s`" % x for x in miss_names),
    "miss_nick_n": str(len(miss_nicks)), "miss_nick_list": u"、".join(u"`%s`" % x for x in miss_nicks),
    "capped": m.group(1), "writing": m.group(2), "quiet": m.group(3),
    "unreg_n": str(len(unreg)), "unreg": u"、".join(u"`%s`" % x for x in sorted(set(unreg))) or u"无",
}

TPL = u"""**值守 {when} · 更正一类读数：我今天报的「在写 N 条」全都低报了，原因是名册与停摆扫描各自只遍历一张**静态**花名表（{table} 条与 {nick_table} 条）**

- 洞在哪（两张表分开说，免得又混）：12 小时内真动过的会话 **{n_act} 枚**。停摆扫描走的是 `quota_now.NAMES`，只有 **{table} 条** ⇒ 有 **{miss_n} 条车道以前根本不进扫描**：{miss_list}。名册走的是 `_quota_roster_r1.NICKS`（**{nick_table} 条**，稍全）⇒ 仍有 **{miss_nick_n} 条**被漏：{miss_nick_list}。也就是说：我此前每次贴「在写 9/10/12」，其实是在一张**看不见大半车队**的名册上数出来的；更要紧的是**停摆扫描也只扫那 13 条**——你要的「至少工作到 23:00」，我本来是拿一只看不见它们的眼在守。
- 修法（已生效，不用等循环重启：`round.py` 与 `_quota_roster_r1.py` 都是每拍新起的子进程）：车道集合改成「静态花名表 ∪ 最近 12 小时动过的流水文件」，认不到花名的标 `未登记·<id8>` 照样盯；仍排除号令者本人、值守自己与那枚不可寻址的旧实例。
- 修好后的现值（本帖当场跑 `_quota_roster_r1.py`）：**停在额度 {capped}｜在写 {writing}｜静默非闸 {quiet}**，其中这 {unreg_n} 条是以前根本不会出现在我读数里的：{unreg}。
- 影响范围我照实圈出来：今天我贴过的所有「在写 N」类计数（11:5x 那次车队现值、12:2x 与 13:5x 的门与队列贴、17:3x/18:0x 的额度潮与暗窗底数）都偏低；**判据本身没错**（尾记录 kinds 与静默分钟），错在遍历的集合不全。盘、尖、门、入账枚数这些与花名表无关的读数不受影响。

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
outf = os.path.join(HERE, "_bus_1840b_body.md")
io.open(outf, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d writing=%s unreg=%s" % (len(text.encode("utf-8")), S["writing"], S["unreg_n"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), outf], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
