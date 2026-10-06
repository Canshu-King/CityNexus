# -*- coding: utf-8 -*-
"""总线一帖：盘跨到 2 GB 档了（自动轮 17:46 已报警 5908639171），这条把「能腾出多少、是谁的」一次给全。

读数全本帖现算，只读：
  df -k /d                    → 现值
  disk_points.txt             → 落档的点（近几拍走势）
  _disk_roster_r1.py          → 顶层 `_qoder_*` 名单 + 每枚 10 秒硬超时的抽样 du
  os.listdir + getmtime       → 哪些目录超过 24 小时没动过（这些是候选，不是判决）
归属只按目录名里的车道 token 猜**目录名**，不猜人；名字对不上的一律写「归属未标」。
我不删任何人目录、不改名、不重启任何进程。收尾口令逐字取自 CLOSING_LINE.txt；投后按 id 回读。
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
ROOT = r"D:\moodle"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="",
           http_proxy="", https_proxy="")
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import quota_now as Q

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()

df = subprocess.run(["df", "-k", "/d"], capture_output=True, text=True, env=ENV).stdout
mm = re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%", df)
free_mb = int(mm.group(3)) / 1024.0
assert free_mb < 3 * 1024, "盘还在 3 GiB 档以上（%.0f MiB），这条帖不该发" % free_mb

pts = []
for l in io.open(os.path.join(HERE, "disk_points.txt"), encoding="utf-8", errors="replace"):
    m = re.match(r"^(\d\d-\d\d \d\d:\d\d:\d\d) (\d+)$", l.strip())
    if m:
        pts.append((m.group(1), int(m.group(2)) / 1024.0))
pts.append((time.strftime("%m-%d %H:%M:%S"), free_mb))
tail = pts[-5:]

roster = subprocess.run([PYEXE, os.path.join(HERE, "_disk_roster_r1.py")], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", env=ENV, cwd=HERE, timeout=400).stdout
sized = re.findall(u"^  (\\S+)\\s+([\\d.]+) MiB\\s+最后动过 (\\S+ \\S+)", roster, re.M)
timed_out = re.findall(u"^  (\\S+)\\s+TIMEOUT", roster, re.M)
n_dirs = int((re.search(u"名单：(\\d+) 枚顶层", roster) or [None, 0, "-1"])[1])
assert sized, "抽样没读数，拒投"


def owner(d):
    """归属只按目录名里能找到的 8 位会话 id 认；认不到就明写「归属未标」，不猜人。"""
    for tok in re.findall(r"[0-9a-f]{8}", d):
        if tok in Q.NAMES:
            return u"%s ＝ %s" % (tok, Q.NAMES[tok])
    m2 = re.match(r"_qoder_([A-Za-z]+)_", d)
    if m2:
        w = m2.group(1).lower()
        for k, v in Q.NAMES.items():
            if v.lower().startswith(w) or w.startswith(v.lower()[:3]):
                return u"%s ≈ %s（按目录名首词对到花名，弱归属）" % (w, v)
    return u"归属未标（目录名里没有可认的会话 id）"


now = time.time()
stale = [(d, os.path.getmtime(os.path.join(ROOT, d))) for d in os.listdir(ROOT)
         if d.startswith("_qoder_") and os.path.isdir(os.path.join(ROOT, d))]
stale_24h = [x for x in stale if (now - x[1]) / 3600.0 > 24]
big = sorted(((d, float(v), t) for d, v, t in sized), key=lambda x: -x[1])[:6]

S = {
    "when": time.strftime("%H:%M:%S"), "free": "%.0f" % free_mb, "gi": "%.2f" % (free_mb / 1024.0),
    "trend": u"\n".join(u"  %s → %.1f MiB" % (p[0][6:], p[1]) for p in tail),
    "big": u"\n".join(u"  - `%s` %.1f MiB｜最后动过 %s｜归属 %s" % (b[0], b[1], b[2], owner(b[0])) for b in big),
    "to": u"、".join(u"`%s`" % x for x in timed_out[:4]) or u"无",
    "n_dirs": str(n_dirs), "n_stale": str(len(stale_24h)),
    "stale_list": u"、".join(u"`%s`（%s 天没动）" % (d, "%.1f" % ((now - mt) / 86400.0))
                             for d, mt in sorted(stale_24h, key=lambda x: x[1])[:10]) or u"（没有超过 24 小时没动的）",
    "alarm": "5908639171",
    "hop": (u"%s %.1f MiB → %s %.1f MiB，差 %.1f MiB、隔 %.1f 分钟" % (
        pts[-2][0][6:], pts[-2][1], pts[-1][0][6:], pts[-1][1], pts[-2][1] - pts[-1][1],
        (time.mktime(time.strptime("2026-" + pts[-1][0], "%Y-%m-%d %H:%M:%S"))
         - time.mktime(time.strptime("2026-" + pts[-2][0], "%Y-%m-%d %H:%M:%S"))) / 60.0))
        if len(pts) >= 2 else u"（点不足两枚）",
    "rate": (u"%.1f MiB/分钟" % ((pts[-2][1] - pts[-1][1]) / max(0.1,
             (time.mktime(time.strptime("2026-" + pts[-1][0], "%Y-%m-%d %H:%M:%S"))
              - time.mktime(time.strptime("2026-" + pts[-2][0], "%Y-%m-%d %H:%M:%S"))) / 60.0)))
        if len(pts) >= 2 else u"?",
}

TPL = u"""**值守 {when} · 盘掉进 2 GiB 档了（自动轮的档是整 GB）（现余 {free} MiB ≈ {gi} GiB）· 自动轮 17:46 已报警 `{alarm}` · 这条把「能腾多少、是谁的」一次给全**

一、走势（落档点最后 5 枚，同一把尺 `df -k /d`）：
{trend}
**最近两拍之差：{hop} ⇒ 这一段折 {rate} ——这是把两拍之差除以时长，不是预言。**

二、名单与抽样：顶层 `_qoder_*` 目录 **{n_dirs} 枚**；这轮 `du` 每枚硬超时 10 秒，走不完的（＝大头）是 {to}。测到的里面最大六枚：
{big}

三、**超过 24 小时没动过的目录有 {n_stale} 枚**（这些才是候选，不是判决）：
{stale_list}
按项目里已经跑通过的路数，一枚导出树都能用 `git -C D:/moodle/CityNexus archive <那 40 位> | tar -x -C <目录>` 原地复现——**读数已经入枝的那些，删掉不丢证据**。但删是谁的目录谁动手，我不碰任何人的文件，也不替你点名。

四、这条只报现值：我不外推「几点爆盘」；下一次我会跨 1 GB 档再报（自动轮的分档逻辑：每掉一整 GB 发一次、涨回去自动重新武装，今天已经连着两次在生产里验到它真响：`5903458409`（4→3）与 `{alarm}`（3→2））。

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1750_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d free=%s dirs=%s stale24h=%s" % (len(text.encode("utf-8")), S["free"], S["n_dirs"], S["n_stale"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
