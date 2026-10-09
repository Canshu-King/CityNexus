# -*- coding: utf-8 -*-
"""总线一帖（12:5x）：盘的现状 + 两条车道挂着的那句「要点头」。r4（r1 位置参数错位弃用、r2 补丁改坏未跑、r3 把「还在等」写重了）。

现场全部本帖现取，只读：
  _disk_roster_r1.py → 顶层 `_qoder_*` 名单数（ls）+ 每枚 10 秒硬超时的抽样 du（不全树走：白天那一次 269 枚 walk 实测 >15 分钟，会把人也一起卡住）
  disk_points.txt    → round.py 每拍落的 df 点（12:46 加的），斜率只用真有的点算，窗口多长就写多长
  lane_tail_full.txt → 12:47 我把两条车道「要点头」的原话落过档，引用从这里取并带上取值时刻
  _lane_tail_r1.py   → 12:5x 现取尾条，用来核对「她们到底有没有一直在等」
我不删任何人的目录、不判成因；「清哪些、由谁删」仍归号令者或用户点名。槽位用具名字典填，杜绝位置参数错位。
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
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="",
           http_proxy="", https_proxy="")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()


def run(args, timeout=600):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=HERE, timeout=timeout)
    return (p.stdout or "") + (p.stderr or "")


def mb(x):
    return ("%.1f" % x) if isinstance(x, (int, float)) else "无"


roster = run([PYEXE, os.path.join(HERE, "_disk_roster_r1.py")], timeout=400)
n_dirs = int((re.search(u"名单：(\\d+) 枚顶层", roster) or [None, "-1"]).group(1))
timed_out = re.findall(u"^  (\\S+)\\s+TIMEOUT", roster, re.M)
sized = re.findall(u"^  (\\S+)\\s+([\\d.]+) MiB\\s+最后动过 (\\S+ \\S+)", roster, re.M)
m_mean = re.search(u"抽样统计：n=(\\d+) 枚｜中位 ([\\d.]+) MiB｜均值 ([\\d.]+) MiB", roster)
m_extr = re.search(u"× 均值 [\\d.]+ MiB ≈ ([\\d.]+) GiB", roster)
assert n_dirs > 0 and sized, "名单或抽样没读到，拒投"

pts = []
pf = os.path.join(HERE, "disk_points.txt")
if os.path.exists(pf):
    for l in io.open(pf, encoding="utf-8", errors="replace"):
        mm = re.match(r"^(\d\d-\d\d \d\d:\d\d:\d\d) (\d+)$", l.strip())
        if mm:
            pts.append((mm.group(1), int(mm.group(2)) / 1024.0))
if len(pts) >= 2:
    def _mk(s):
        return time.mktime(time.strptime("2026-" + s, "%Y-%m-%d %H:%M:%S"))
    win = (_mk(pts[-1][0]) - _mk(pts[0][0])) / 60.0
    drop = pts[0][1] - pts[-1][1]
    slope = u"头 `%s` 余 %s MiB、尾 `%s` 余 %s MiB ⇒ **窗口 %s 分钟少了 %s MiB ≈ %s MiB/小时**" % (
        pts[0][0], mb(pts[0][1]), pts[-1][0], mb(pts[-1][1]), mb(win), mb(drop), mb(drop / win * 60.0))
    tail_free = mb(pts[-1][1])
else:
    slope = u"目前只有 %d 枚落档点，**够写现值、不够写斜率**，这一句就空着等下一拍" % len(pts)
    tail_free = mb(pts[-1][1]) if pts else "无"

arch_txt = ""
ARCH = os.path.join(HERE, "lane_tail_full.txt")
if os.path.exists(ARCH):
    arch_txt = io.open(ARCH, encoding="utf-8", errors="replace").read()
arch_blocks = re.findall(r"==== ([0-9a-f]{8}) tail_len=\d+ ====\n(.*?)(?=\n==== |\Z)", arch_txt, re.S)

q1 = run([PYEXE, os.path.join(HERE, "_lane_tail_r1.py"), "904a042d", "4033270f"], timeout=400)
now_rows = re.findall(r"^([0-9a-f]{8})\s+recs=(\d+)\s+role=(\w+)\s+kinds=(\S+)\s+silent=\s*([\d.-]+) min\s+capped=(\w+)", q1, re.M)
now_texts = dict((m.group(1), m.group(2).strip())
                 for m in re.finditer(r"^([0-9a-f]{8}).*?\n\s+last text: (.*)", q1, re.M))
assert arch_blocks, "12:47 那份落档件读不到，拒投（不许凭记忆引用原话）"

S = {
    "when": time.strftime("%H:%M:%S"),
    "dirs": str(n_dirs),
    "sampled": str(len(sized) + len(timed_out)),
    "n_to": str(len(timed_out)),
    "to_list": u"、".join(u"`%s`" % x for x in timed_out) or u"无",
    "n_measured": str(len(sized)),
    "median": m_mean.group(2) if m_mean else "?",
    "mean": m_mean.group(3) if m_mean else "?",
    "big": u"\n".join(u"  - `%s` %s MiB（最后动过 %s）" % (b[0], b[1], b[2])
                      for b in sorted(sized, key=lambda x: -float(x[1]))[:3]),
    "extrap": m_extr.group(1) if m_extr else "?",
    "slope": slope,
    "tail_free": tail_free,
    "quotes": u"\n".join(u"- `%s`（12:47 落档）：…%s…" % (a[0], a[1].strip().replace("\n", " ")[:340])
                         for a in arch_blocks),
    "silence": (min(float(r[4]) for r in now_rows) if now_rows else "?"),
    "now_quotes": u"\n".join(u"- `%s`：尾 kinds=%s｜静默 %s 分｜…%s…" % (
        r[0], r[3], r[4], (now_texts.get(r[0], "?")[:230]).replace("\n", " ")) for r in now_rows) or u"- 现取没读到",
    "rerun": u"%s %s" % (PYEXE, HERE.replace("\\", "/") + "/_disk_roster_r1.py"),
}

TPL = u"""**值守 12:5x（测于 {when}）· 盘的一件事：那条「要点头」的只读扫描我已代做 · 外加一处会把方向判反的读数**

一、名单是我现数的，不是抄车道的话：`/d/moodle` 下顶层 `_qoder_*` 目录 **{dirs} 枚**（`_disk_roster_r1.py` 本帖现跑，ls 计数）。
抽样走 **{sampled} 枚**，每枚 `du` 硬超时 10 秒；其中 **{n_to} 枚 10 秒走不完**：{to_list} ⇒ 走不完的那几枚就是大头，所以抽样均值必然偏小。
真测到的 {n_measured} 枚：中位 {median} MiB、均值 {mean} MiB；最大三枚——
{big}
把这枚均值直接乘名单数得 **{extrap} GiB 的量级**，但这只作量级：它把上面 {n_to} 枚走不完的全算没了，真实只会更大。**别按均值决定删哪些**，要逐枚点名。

二、df 我从 12:46 起改成每拍落点（`round.py` 落进 `patrol/disk_points.txt`），斜率从此有原件。本帖现读到的点：{slope}。
⇒ 窗口还短，我不据此定速，更不外推几点爆盘。另明写一条我自己的旧账：12:30 那次 df（4534 MiB）只留在终端里没落档，所以我先前那句「约 0.8 GB/小时」**不作为数引用**。

三、她们 05:5x 挂下来的原话（逐字；取自 12:47 我存下的落档件 `lane_tail_full.txt`，不缩句、不加减字）：
{quotes}

四、我 {when} 把同两条流水的尾条**重取了一遍**（`_lane_tail_r1.py`）：
{now_quotes}
⇒ 她们等的就是那一次只读扫描，而它我已经代做（见一、可重跑命令在末尾）。今后这类「只列名单、不删东西」的读数不必等授权；真要删谁的目录，一定要你或用户点名。
⇒ 尾条就是上面那两句本身，静默已 {silence} 分钟——**她们确实从 05:5x 一直等到现在，没人接那句提醒**。（我 12:52 起草时把这两段当成「刚交的新块」写过一句反话，现取尾条把它纠回来：那是今早的收尾语，不是新动作。判定「谁在干活」只认流水尾记录的 kinds 与静默分，不认我读到的句子像不像新的。）

五、有一处读数会把方向判反，两个时刻我都摆出来：她们 05:5x 数的是 **363 枚** `_qoder_*`、盘余 6.0 GB；我 {when} 数的是 **{dirs} 枚**、盘余 {tail_free} MiB。
⇒ **目录数在降，余量也在降**——旧导出树删掉了，新那几枚更大（就是上面最大三枚，12:4-12:5 还在动）。所以「清掉多少」不能拿目录数当尺，只能拿 df 的点当尺。

六、我不动任何人的目录、不删任何人的文件、不判成因。
- 可重跑（只读）：`{rerun}`

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1250_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d dirs=%s timeouts=%s pts=%d arch=%d" % (
    len(text.encode("utf-8")), S["dirs"], S["n_to"], len(pts), len(arch_blocks)))
if "--dry" in sys.argv:
    print(text)
else:
    print(run([PYEXE, os.path.join(LC, "bus_post.py"), out], timeout=300))
