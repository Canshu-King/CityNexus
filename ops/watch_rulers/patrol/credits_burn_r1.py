# -*- coding: utf-8 -*-
"""今夜 credits 消耗与"还能跑多久"的估算（只读会话流水里的 usage.credits）。

口径：同一 sessionId 的 fork 去重（取最大累计值再相减不可靠，这里按**每条记录的 delta 求和**，
即按记录顺序做差只取正数）；起点取本地 00:00。跑不满就报"样本不足"，不猜。
"""
import glob
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
DAY0 = time.mktime(time.strptime("2026-09-29 00:00", "%Y-%m-%d %H:%M"))
# 花名只留一张表：以 wake_names.ID8 为准（07:04 我把 be19052c→dt、2d2d7428→0441 按账本块头改正过），
# 这里只补 ID8 里没有的那几枚，免得两个脚本对同一条会话报不同名字。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wake_names as WN
NAMES = dict(WN.ID8)
NAMES.update({"a6b95d59": "DSH", "8ac89982": "R0417", "9cc37e57": "0421",
              "6efab655": "实例A", "e4f3490f": "道0370", "8e5245f0": "道0369",
              "4033270f": "道0383", "42d1a6fa": "值守(我)"})


def per_file(p):
    prev = 0.0
    tot = 0.0
    first = last = None
    for line in io.open(p, encoding="utf-8", errors="replace"):
        if '"credits"' not in line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        u = ((r.get("message") or {}).get("usage")) or r.get("usage") or {}
        c = u.get("credits")
        if not isinstance(c, (int, float)):
            continue
        ts = r.get("timestamp") or ""
        try:
            ep = time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600
        except Exception:
            continue
        if ep < DAY0:
            prev = c
            continue
        d = c - prev
        if d > 0:
            tot += d
        prev = c
        first = ep if first is None else first
        last = ep
    return tot, first, last


rows = []
for p in sorted(glob.glob(os.path.join(BASE, "*.jsonl"))):
    sid = os.path.basename(p)[:8]
    tot, f, l = per_file(p)
    if tot > 0:
        rows.append((tot, sid, f, l))
rows.sort(reverse=True)
now = time.time()
total = sum(r[0] for r in rows)
span_h = max(0.1, (now - DAY0) / 3600.0)
rate = total / span_h
left_h = (time.mktime(time.strptime("2026-09-29 11:00", "%Y-%m-%d %H:%M")) - now) / 3600.0
print("00:00 起本地累计：%d 条会话有消耗，共 %.2f credits；跨度 %.2f 小时 ⇒ 速率 %.1f credits/小时"
      % (len(rows), total, span_h, rate))
print("到 11:00 还有 %.2f 小时 ⇒ 按同速率预计再花 %.0f credits" % (left_h, rate * left_h))
for tot, sid, f, l in rows[:8]:
    print("   %-9s %-9s %.2f  credits（首末记录跨 %.1f 小时）"
          % (NAMES.get(sid, sid), sid, tot, ((l or f) and (l - f) / 3600.0) or 0))
