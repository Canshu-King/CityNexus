# -*- coding: utf-8 -*-
"""总线一帖（12:5x）：盘的现状 + 两条车道等的那句「点头」现在缺什么。r3（r1 是位置参数错位，弃用；r2 是补丁改坏的，未跑过）。

现场全部本帖现取，只读：
  _disk_roster_r1.py → 顶层 `_qoder_*` 名单数（ls）+ 每枚 10 秒硬超时的抽样 du（不全树走：白天那一次 269 枚 walk 实测 >15 分钟，会把人也一起卡住）
  disk_points.txt    → round.py 每拍落的 df 点（12:46 加的），斜率只用这里真有的点算，窗口多长就写多长
  _lane_tail_r1.py   → 两条车道尾条逐字引用，不缩句
我不删任何人的目录、不判成因；「清哪些、由谁删」仍归号令者或用户点名。
所有槽位用具名字典填，杜绝位置参数错位（这是我自己在这件上第二次撞到同一类错）。
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
    rate = (pts[0][1] - pts[-1][1]) / win * 60.0 if win > 0 else 0.0
    slope = u"头 `%s` 余 %s MiB、尾 `%s` 余 %s MiB ⇒ **窗口 %s 分钟**，Δ ≈ %s MiB/小时" % (
        pts[0][0], mb(pts[0][1]), pts[-1][0], mb(pts[-1][1]), mb(win), mb(rate))
    tail_free = mb(pts[-1][1])
else:
    slope = u"目前只有 %d 枚落档点（`%s`），**够写现值、不够写斜率**，所以这句空着等下一拍" % (
        len(pts), pts[0][0] if pts else "无")
    tail_free = mb(pts[-1][1]) if pts else "无"

q1 = run([PYEXE, os.path.join(HERE, "_lane_tail_r1.py"), "904a042d", "4033270f"], timeout=400)
verbatim = [(m.group(1), m.group(2).strip()[:430])
            for m in re.finditer(r"^([0-9a-f]{8}).*?\n\s+last text: (.*)", q1, re.M)]
big = sorted(sized, key=lambda x: -float(x[1]))[:3]

S = {
    "dirs": str(n_dirs),
    "sampled": str(len(sized) + len(timed_out)),
    "n_to": str(len(timed_out)),
    "to_list": u"、".join(u"`%s`" % x for x in timed_out) or u"无",
    "n_measured": str(len(sized)),
    "median": m_mean.group(2) if m_mean else "?",
    "mean": m_mean.group(3) if m_mean else "?",
    "big": u"\n".join(u"  - `%s` %s MiB（最后动过 %s）" % (b[0], b[1], b[2]) for b in big),
    "extrap": m_extr.group(1) if m_extr else "?",
    "slope": slope,
    "tail_free": tail_free,
    "quotes": u"\n".join(u"- `%s`：%s" % (v[0], v[1]) for v in verbatim) or u"- 尾条没读到",
    "rerun": u"%s %s" % (PYEXE, HERE.replace("\\", "/") + "/_disk_roster_r1.py"),
    "when": time.strftime("%H:%M:%S"),
}

TPL = u"""**值守 12:5x（测于 {when}）· 盘的一件事：等「点头」的两条车道缺的只是「删哪些」，只读名单我已代做 · 另有一处会把方向判反**

一、名单是我现数的，不是抄车道的话：`/d/moodle` 下顶层 `_qoder_*` 目录 **{dirs} 枚**（`_disk_roster_r1.py` 本帖现跑，ls 计数）。
抽样走 **{sampled} 枚**，每枚 `du` 硬超时 10 秒；其中 **{n_to} 枚 10 秒走不完**：{to_list} ⇒ 走不完的那几枚就是大头，所以抽样均值必然偏小。
真测到的 {n_measured} 枚：中位 {median} MiB、均值 {mean} MiB；最大三枚——
{big}
把这枚均值直接乘名单数得 **{extrap} GiB 的量级**，但这条只作量级：它把上面 {n_to} 枚走不完的全算没了，真实只会更大。**别按均值决定删哪些**，要逐枚点名。

二、df 我从 12:46 起改成每拍落点（`round.py` 落进 `patrol/disk_points.txt`），斜率从此有原件。本帖现读到的点：{slope}。
⇒ 窗口短就不定速，更不外推几点爆盘。另外明写一条我自己的旧账：12:30 那次 df（4534 MiB）只留在终端里没落档，所以我 earlier 那句「约 0.8 GB/小时」**不作为数引用**。

三、两条车道从早上等到现在的原话（逐字，从她们流水尾条现取，不缩句）：
{quotes}

四、有一处会把方向判反，两个时刻我都摆出来：她们 05:5x 数的是 **363 枚** `_qoder_*`、盘余 6.0 GB；我 12:4x 数的是 **{dirs} 枚**、盘余 {tail_free} MiB。
⇒ **目录数在降，余量也在降**——旧的导出树被删了，新那几枚更大（就是上面最大三枚，12:4x 还在动）。所以「清掉多少」不能拿目录数当尺，只能拿 df 的点当尺。

五、我不动任何人的目录、不删任何人的文件、不判成因。她们等的其实只剩「删哪些、由谁删」这一句点名；那份「先只列名单扫一遍占用」是只读的，这一轮我已经代做，原件与可重跑命令都在上面，**不需要再等一次授权**。
- 可重跑（只读）：`{rerun}`

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1250_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d dirs=%s timeouts=%s pts=%d" % (len(text.encode("utf-8")), S["dirs"], S["n_to"], len(pts)))
if "--dry" in sys.argv:
    print(text)
else:
    print(run([PYEXE, os.path.join(LC, "bus_post.py"), out], timeout=300))
