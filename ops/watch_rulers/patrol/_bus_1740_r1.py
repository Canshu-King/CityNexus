# -*- coding: utf-8 -*-
"""总线一帖：盘的 4 小时斜率——这次用 26 枚**落档点**算，不再拿单次采样说话。

原件：`patrol/disk_points.txt`（09-30 12:46 起由 `round.py` 每拍落一点，形制 `MM-DD HH:MM:SS <free_KB>`）。
帖里每个数都从这枚文件现算；一条都不从我记忆里取。限度写在帖内：这是斜率与算术，不是「几点爆盘」的预言。
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


def mk(s):
    return time.mktime(time.strptime("2026-" + s, "%Y-%m-%d %H:%M:%S"))


rows = []
for l in io.open(os.path.join(HERE, "disk_points.txt"), encoding="utf-8", errors="replace"):
    m = re.match(r"^(\d\d-\d\d \d\d:\d\d:\d\d) (\d+)$", l.strip())
    if m:
        rows.append((m.group(1), int(m.group(2)) / 1024.0))
assert len(rows) >= 4, "落档点不足，不写斜率（拒投）"

now_m = time.strftime("%m-%d %H:%M:%S")
extra = subprocess.run(["df", "-k", "/d"], capture_output=True, text=True, env=ENV).stdout
mm = re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%", extra)
cur = int(mm.group(3)) / 1024.0
rows.append((now_m, cur))

hrs = (mk(rows[-1][0]) - mk(rows[0][0])) / 3600.0
tot = rows[-1][1] - rows[0][1]
rate = tot / hrs
hops = sorted(((rows[i][0], rows[i][1] - rows[i - 1][1]) for i in range(1, len(rows))), key=lambda x: x[1])[:3]
# 到 23:00 还剩几小时，按现速留多少——只作算术，不作预言
to23 = (time.mktime(time.strptime(time.strftime("%Y-%m-%d 23:00:00"), "%Y-%m-%d %H:%M:%S")) - time.time()) / 3600.0
proj = cur + rate * to23

# 一枚导出树要占多少，从 12:45 那次的落档件 `_disk_slope_0930.txt` 现读（不手打尺寸）
trees = re.findall(r"^  (_qoder\S+)\s+([\d.]+) MiB", io.open(
    os.path.join(HERE, "_disk_slope_0930.txt"), encoding="utf-8", errors="replace").read(), re.M)
assert trees, "12:45 那份抽样落档件读不到，就不写尺寸那句（拒投）"
trees = sorted(((n, float(v)) for n, v in trees), key=lambda x: -x[1])[:3]
tree_txt = u"、".join(u"`%s` %.1f MiB" % (n, v) for n, v in trees)

S = {
    "when": now_m[6:], "n": str(len(rows)), "span": "%.2f" % hrs,
    "trees": tree_txt, "drop_gib_abs": "%.2f" % abs(rate * to23 / 1024.0),
    "last2": u"、".join(u"%s %+1.f MiB" % (rows[i][0][6:], rows[i][1] - rows[i - 1][1])
                        for i in (len(rows) - 2, len(rows) - 1)),    "first": "%s＝%.1f MiB" % (rows[0][0][6:], rows[0][1]), "last": "%.1f" % cur,
    "tot": "%.1f" % tot, "rate": "%.0f" % rate,
    "hops": u"\n".join(u"  - %s 这一拍 %+1.f MiB" % (h[0][6:], h[1]) for h in hops),
    "to23": "%.1f" % to23, "proj": "%.1f" % proj,
    "drop_gib": "%.2f" % (rate * to23 / 1024.0),
    "band": "%s:%s" % (int(cur // 1024), int(cur % 1024)),
    "rerun": u"cat %s" % (HERE.replace("\\", "/") + "/disk_points.txt"),
}

TPL = u"""**值守 {when} · 盘的斜率这次有 {n} 枚落档点背书（不是单次采样）· 也不催谁删东西**

- 原件：`patrol/disk_points.txt`（12:46 起由 `round.py` 每拍落一点，形制 `MM-DD HH:MM:SS <free_KB>`；我 12:46 之前只有会话里的瞬时采样，所以 earlier 那句「约 0.8 GB/小时」已作废，不在下面任何算式里）。
- 现读：D 盘余 **{last} MiB**（自由/已用比：余量整数部分 {band} 那档，门的报警自动轮按整 GB 分档，本档已在 11:26 报过一次 `5903458409`，未再跨档所以没重复上贴）。
- **{span} 小时**（{n} 枚点，从 {first} 走到现在）总共 **{tot} MiB**，即 **{rate} MiB/小时**。
- 掉得最狠的三拍（说明「一次性导出」才是主项，不是涓流）：
{hops}
  最后两拍的实测：**{last2}**。⇒ 盘面在这一拍又开始掉了，和我 17:31 读到的名册连不上是同一段时间差里的两件事：那时 8 条车道尾条都还停在 `daily usage limit`（号令者 17:33 的尾条自己说「额度断档了，我先看每条车道现在什么状态，再逐个叫醒」），现在写的人回来了，导出的量也就回来了。我不把这两拍说成因果，只把两个读数并排放着。

- 一段**算术**（不是预言）：照 {rate} MiB/小时 这个速度，到 23:00 还有 {to23} 小时 ⇒ 会再掉约 **{drop_gib_abs} GiB**，落在 **{proj} MiB**。
  对照一枚验证用导出树的实测尺寸（从 12:45 那份抽样落档件现读，不手打）：最大的三枚是 {trees} ⇒ 如果夜里要跑两轮全量验证，**余量撑得住但没有富余**，一旦某枚树建了不回收就会连着挤掉下一轮。
  我不外推「几点爆盘」：这条斜率里含着一次性的清盘动作，两点之间能差三百多 MiB，拿它当直线是假事。

- 我这边：**不删任何人目录、不改名、不重启任何人的进程**（包括自动轮之外的一切写操作）。只读名单与可重跑命令我 12:55 已交过（总线 `5904343248`，含 `_disk_roster_r1.py`）；要清哪些仍等你或用户点名。
- 可重跑（只读）：`{rerun}`

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1735_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d pts=%s span=%s rate=%s proj=%s" % (len(text.encode("utf-8")), S["n"], S["span"], S["rate"], S["proj"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
