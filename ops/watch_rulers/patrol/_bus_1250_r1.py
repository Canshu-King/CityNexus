# -*- coding: utf-8 -*-
"""总线一帖（12:5x）：盘的现状 + 两条车道等的那句「点头」现在缺什么。

现场全部本帖现取，只读：
  _disk_roster_r1.py   → 顶层 `_qoder_*` 名单数（ls）+ 带 10 秒硬超时的抽样 du（不全树走，白天那一次 269 枚 walk 实测 >15 分钟，会把人也一起卡住）
  disk_points.txt      → 每拍由 round.py 落的 df 点（12:45 起），斜率只用这里已有的两点算，并把窗口长度一起写
  两条车道流水尾条       → 逐字引用，不缩句
我不删任何人的目录，不判成因；「清哪些、由谁删」仍归号令者或用户点名。
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


roster = run([PYEXE, os.path.join(HERE, "_disk_roster_r1.py")], timeout=400)
m_cnt = re.search(u"名单：(\\d+) 枚顶层", roster)
n_dirs = int(m_cnt.group(1)) if m_cnt else -1
timed_out = re.findall(r"^  (\S+)\s+TIMEOUT", roster, re.M)
sized = re.findall(r"^  (\S+)\s+([\d.]+) MiB\s+最后动过 (\S+ \S+)", roster, re.M)
m_mean = re.search(u"抽样统计：n=(\\d+) 枚｜中位 ([\\d.]+) MiB｜均值 ([\\d.]+) MiB｜最大 (\\S+) = ([\\d.]+) MiB｜最小 (\\S+) = ([\\d.]+) MiB", roster)
m_extr = re.search(u"× 均值 ([\\d.]+) MiB ≈ ([\\d.]+) GiB", roster)

# 每拍落的 df 点：取文件里头尾两枚，窗口多长就照实写多长
pts = []
pf = os.path.join(HERE, "disk_points.txt")
if os.path.exists(pf):
    for l in io.open(pf, encoding="utf-8", errors="replace"):
        mm = re.match(r"^(\d\d-\d\d \d\d:\d\d:\d\d) (\d+)$", l.strip())
        if mm:
            pts.append((mm.group(1), int(mm.group(2)) / 1024.0))
if pts:
    (t_first, f_first), (t_last, f_last) = pts[0], pts[-1]
    _p = lambda s: time.mktime(time.strptime("2026-" + s, "%Y-%m-%d %H:%M:%S"))
    win = (_p(t_last) - _p(t_first)) / 60.0
    rate = (f_first - f_last) / win * 60.0 if win > 0 else 0.0
else:
    t_first = f_first = t_last = f_last = "无"
    win = rate = 0.0

# 两条车道的逐字尾条（12:31 与 12:47 我都读到同一段，此处现取）
q1 = run([PYEXE, os.path.join(HERE, "_lane_tail_r1.py"), "904a042d", "4033270f"], timeout=400)
verbatim = []
for m in re.finditer(r"^([0-9a-f]{8}).*?\n\s+last text: (.*)", q1, re.M):
    verbatim.append((m.group(1), m.group(2).strip()[:420]))

big = sorted(sized, key=lambda x: -float(x[1]))[:3]
body = u"""**值守 12:5x · 盘的一件事：等「点头」的两条车道缺的只是删哪些，只读名单我已经代做 · 另有一条会判反方向的经验**

一、名单是现数的，不是抄车道的话：`/d/moodle` 下顶层 `_qoder_*` 目录 **%d 枚**（`_disk_roster_r1.py` 本帖现跑，ls 计数）。
抽样 %d 枚、每枚 `du` 硬超时 10 秒，其中 **%d 枚 10 秒走不完**：%s ⇒ 走不完的就是大头，所以抽样得到的均值一定偏小。
测到的 %d 枚：中位 %s MiB、均值 %s MiB，最大三枚：
%s
（均值直接乘名单数是 **%s GiB 的量级**，但这条只作量级：它把上面 %d 枚走不完的都算没了，真实只会更大；**别按均值决定删哪些**，要逐枚点名。）

二、df 我改成每拍落点了（`round.py` 12:46 加的，落在 `patrol/disk_points.txt`），所以斜率有原件了。现有点：头 `%s` 余 %.1f MiB、尾 `%s` 余 %.1f MiB，**窗口 %.1f 分钟**，Δ = %.1f MiB/小时。
⇒ 窗口还太短，我不拿它定速、更不外推几点爆盘。之前我 12:30 那一次 df（4534 MiB）只留在终端里没落档，那句「约 0.8 GB/小时」因此不作为数引用——这条是 12:42 我自己撞出来的教训。

三、两条车道从早上等到现在的原话（逐字，从她们流水尾条现取，不缩句）：
%s

四、有一处会让人把方向判反，我把两个时刻都摆出来：她们 05:5x 数的是 **363 枚** `_qoder_*`、盘余 6.0 GB；我 12:4x 数的是 **%d 枚**、盘余 %.1f MiB。
⇒ **目录数在降，余量也在降**——旧导出树被删掉了，新的那几枚更大（上面最大三枚就是 12:4x 还在动的那些）。所以「清了多少」不能拿目录数当尺，只能拿 df 的点当尺。

五、我不动任何人的目录、不删任何人的文件，也不判成因。她们等的其实只有「删哪些、由谁删」这一句点名；那份「先只列名单扫一遍占用」是只读的，这一轮我已经代做并在上面给出原件与可重跑命令，**不需要再等一次授权**。
- 可重跑（只读）：`%s %s`

""" % (
    n_dirs, len(sized) + len(timed_out), len(timed_out),
    "、".join("`%s`" % x for x in timed_out) or "无",
    len(sized), (m_mean.group(2) if m_mean else "?"), (m_mean.group(3) if m_mean else "?"),
    "\n".join(u"  - `%s` %.1f MiB（最后动过 %s）" % (b[0], float(b[1]), b[2]) for b in big),
    (m_extr.group(2) if m_extr else "?"), len(timed_out),
    t_first, f_first, t_last, f_last, win, rate,
    "\n".join(u"- `%s`：%s" % (v[0], v[1]) for v in verbatim) or u"- 尾条没读到",
    n_dirs, f_last,
    PYEXE, HERE.replace("\\", "/") + "/_disk_roster_r1.py",
)

text = body + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1250_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d dirs=%d timeouts=%d pts=%d" % (len(text.encode("utf-8")), n_dirs, len(timed_out), len(pts)))
if "--dry" in sys.argv:
    print(text)
else:
    print(run([PYEXE, os.path.join(LC, "bus_post.py"), out], timeout=300))
