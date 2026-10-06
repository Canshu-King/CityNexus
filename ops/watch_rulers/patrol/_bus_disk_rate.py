# -*- coding: utf-8 -*-
"""值守贴：盘在按小时掉，我把**谁在占**与**掉速**量出来（不删任何东西）。"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()


def free(drive):
    o = subprocess.run(["df", "-h", drive], capture_output=True, text=True, timeout=60).stdout
    cols = o.splitlines()[-1].split()          # Filesystem Size Used Avail Use% Mounted
    avail = cols[3]
    m = re.match(r"([\d.]+)([GMK])", avail)
    v, u = float(m.group(1)), m.group(2)
    return v if u == "G" else (v / 1024.0 if u == "M" else v / 1048576.0)


d_now, c_now = free("/d"), free("/c")
top = io.open(os.path.join(HERE, "disk_top_0613.txt"), encoding="utf-8").read().strip().split("\n")
rows = [l for l in top if re.match(r"^\d+", l)]
sum_miB = sum(int(re.match(r"^(\d+)", l).group(1)) for l in rows)

# 掉速的两个点都从仪表日志里取（不手写数字）：`round_watch.log` 每轮先打 `[HH:MM:SS] 轮 N`，
# 随后几行打 `磁盘 C:\ free=… GB`/`磁盘 D:\ free=…`——磁盘行**不带时间戳**，所以要把最近一次时间戳挂上去。
hist = []
cur = None
for l in io.open(os.path.join(HERE, "round_watch.log"), encoding="utf-8", errors="replace"):
    ts = re.match(r"^\[(\d\d):(\d\d):(\d\d)\]", l)
    if ts:
        cur = int(ts.group(1)) * 60 + int(ts.group(2))
    m = re.search(r"磁盘 D:\\?\s*free=([\d.]+) GB", l)
    if m and cur is not None:
        hist.append((cur, float(m.group(1))))
rate = hours = None
base_gb, base_min, span = "?", None, "?"
if len(hist) >= 2:
    now_min, now_gb = hist[-1]
    older = [h for h in hist if now_min - h[0] >= 45]
    if older:
        base_min, base_gb = older[-1]
        span = now_min - base_min
        rate = round((base_gb - now_gb) * 60.0 / span, 2)
        hours = round((now_gb - 8.0) / rate, 1) if rate > 0 else "?"
        d_now = now_gb
    else:
        rate = hours = "样本不足（磁盘行跨度 <45 分钟）"
else:
    rate = hours = "样本不足（磁盘行 <2 条）"

body = ("**值守 %s · D 盘只剩 `%.1f` GB，掉速约 `%s` GB/小时：今夜按单导出口占了 ~`%d` GB，值守 0 次删除**\n\n"
        "- 现读：`df -h` D 可用 `%.1f` GB、C 可用 `%.1f` GB（E 还有 129 GB）。\n"
        "- 掉速的两个点都取自仪表日志 `patrol/round_watch.log` 自己的磁盘行（不手写数字）："
        "早一点 `%02d:%02d` 记 `%s GB` → 最近一轮 `%s GB`，跨度 `%s` 分钟 ⇒ `%s` GB/小时；"
        "照这个速度约 **%s 小时**后穿过 8 GB。值守的贴阈值刚从 6 提到 8，就是为了给清理留时间。\n"
        "- 谁在占（`du -sm`，本轮现测，MiB）：\n%s\n"
        "  这批共 `%d` MiB。**注意口径**：`cp -al` 硬链的 node_modules 会在每个目录各计一次，所以真实独占字节小于此数；"
        "但目录数量与时间戳和 `df` 的下降一致——每条新车道开一单就新建一份导出，收口后没人回收。\n"
        "- 我**没有删任何东西**（连我自己的临时件都没删），也没动别人的 worktree。要不要回收哪几份、"
        "还是让每条车道交完自己拆，是你或号令者的决定；号令者的 cron 里本来就写了"
        "「不足则先清理自己名下的派生产物，删前先扫 junction，junction 必须先 `rmdir` 卸下再删树」。\n"
        "- 另一条与盘有关的实测：06:07 那次定点 `du`（14 个目录）跑了约 6 分钟，说明规模已经大到让『随手扫一下』变成阻塞操作"
        "——值守后续只做**列名单的** du，不做全树扫。\n\n"
        "边界：值守只读 `df`/`du`/会话流水/收件目录/GitHub ref；0 次删除、0 次写账本、0 次插块、0 次动权威线、0 次点别人的批准。"
        % (time.strftime("%H:%M"), d_now, rate, sum_miB // 1024, d_now, c_now,
           (base_min if isinstance(base_min, int) else 0) // 60, (base_min if isinstance(base_min, int) else 0) % 60, base_gb, "%.1f" % d_now, span, rate, hours,
           "\n".join("  > `%s`" % r.strip() for r in rows[:8]), sum_miB))

out = os.path.join(HERE, "_bus_disk_rate.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
print("D=%s C=%s rate=%s GB/h top=%d MiB；写好 %d B" % (d_now, c_now, rate, sum_miB, os.path.getsize(out)))
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:600])
raise SystemExit(p.returncode)
