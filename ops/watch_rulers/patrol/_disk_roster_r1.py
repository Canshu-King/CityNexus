# -*- coding: utf-8 -*-
"""盘的「够做决定」量法：不全树 du（白天 269 枚 _build_* walk 实测 >15 分，会把人也一起卡住），
而是 ① 名单（每枚 `_qoder_*` 顶层目录 + 最后动过的时间）② 抽样若干枚 du -sh，给每枚一个硬超时
③ 由抽样均值估总量，并把不确定度一起写出来。

只读：不删、不改、不动任何人的目录。Q(904a042d) 与 0383(4033270f) 两条车道的尾条都说
「要清得你点头，我可以先只列名单扫一遍占用」——那份「列名单」是只读的，所以这一轮我先把
读数交出来，清不清、清谁的仍由号令者或用户决定。
"""
import os
import subprocess
import sys
import time

ROOT = r"D:\moodle"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
now = time.time()
dirs = sorted([d for d in os.listdir(ROOT) if d.startswith("_qoder_")
                and os.path.isdir(os.path.join(ROOT, d))])
rows = []
for d in dirs:
    p = os.path.join(ROOT, d)
    mt = os.path.getmtime(p)
    rows.append((d, mt, None))

# 抽样：按「最近动过」取前 k 枚，另加最老的两枚作对照，每枚 du 限时 10 秒
K = 10
by_new = sorted(rows, key=lambda x: -x[1])
sample = [x[0] for x in by_new[:K]] + [x[0] for x in sorted(rows, key=lambda x: x[1])[:2]]
sample = list(dict.fromkeys(sample))
sizes = {}
t0 = time.time()
for d in sample:
    p = os.path.join(ROOT, d)
    try:
        r = subprocess.run(["du", "-sk", p], capture_output=True, text=True, timeout=10,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or "").strip()
        if out.split("\t")[0].isdigit():
            sizes[d] = int(out.split("\t")[0])
    except Exception as exc:
        sizes[d] = None
    if time.time() - t0 > 180:
        print("（抽样到 %d 枚为止满 180 秒，剩下的标 TIMEOUT 不再走，避免把这台机器的 IO 抢光）" % len(sizes))
        break

ok = {d: v for d, v in sizes.items() if v}
print("名单：%d 枚顶层 `_qoder_*` 目录；抽样走到 %d 枚，用时 %.0f 秒（每枚 du 限时 10 秒）" % (
    len(dirs), len(sizes), time.time() - t0))
print()
print("抽到的大小（MiB，按最近动过排序）：")
for d in sample:
    if d in sizes and sizes[d] is not None:
        print("  %-44s %8.1f MiB   最后动过 %s" % (d, sizes[d] / 1024.0,
              time.strftime("%m-%d %H:%M", time.localtime(os.path.getmtime(os.path.join(ROOT, d))))))
    elif d in sizes:
        print("  %-44s %8s   （du 超时或读不到）" % (d, "TIMEOUT"))

if ok:
    vals = sorted(v for v in ok.values())
    mean = sum(vals) / len(vals)
    print()
    print("抽样统计：n=%d 枚｜中位 %.1f MiB｜均值 %.1f MiB｜最大 %s = %.1f MiB｜最小 %s = %.1f MiB" % (
        len(vals), vals[len(vals) // 2] / 1024.0, mean / 1024.0,
        max(ok, key=ok.get), max(ok.values()) / 1024.0, min(ok, key=ok.get), min(ok.values()) / 1024.0))
    print("外推（**只作量级，不是实测**）：%d 枚 × 均值 %.1f MiB ≈ %.1f GiB；" % (len(dirs), mean / 1024.0, len(dirs) * mean / 1024.0 / 1024.0))
    print("  抽样里既有 12:3x 新导出的树也有 09-2x 的旧树，所以这个均值会把「空目录/小目录」和「整棵导出树」混在一起——"
          "要按它决定清哪些，必须先逐枚点名，不要按均值删。")

df = subprocess.run(["df", "-k", "/d"], capture_output=True, text=True).stdout
import re as _re
m = _re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%", df)
print()
print("盘现值：%s  余 %.1f MiB（used %s%%）@ %s" % (
    "/d", int(m.group(3)) / 1024.0, m.group(4), time.strftime("%H:%M:%S")))
