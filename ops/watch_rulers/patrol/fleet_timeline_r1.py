# -*- coding: utf-8 -*-
"""车队时轴：从自动轮自己的流水里把「每拍谁在写、谁停在闸上」拼成小时表——用来回答用户那句
「你检查 qoder 的工人工作要读取他们的任务，看看有没有在干活」，并且在 23:00 能拿数字证明傍晚这几个小时是不是真有人在干活。

只读，只吃 `autumn_watch.log` 里我自己每拍写的三型行：
  额度名册：HH:MM:SS 名册：停在额度 N｜在写 M｜静默非闸 K
  额度名册：在写：<花名>(<静默分>分)、…
  额度名册：闸上：…   /   额度名册：静默非闸：…
边界：
  * 这些行是每 600 秒一拍，所以时轴分辨率就是 10 分钟；某拍之间的动静看不见。
  * 「在写」= 那一拍该会话最后一条角色记录不是额度字样、且尾记录是工具块或 15 分钟内有新写入（判据在 `_quota_roster_r1.py`，这里不另起一把尺）。
  * 我不把「静默」当成「偷懒」——名册里带等待词的格子是停在别人的裁语上，表里单列。
"""
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LOG = os.path.join(HERE, "autumn_watch.log")

today = time.strftime("%m-%d")
pat_sum = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\] 额度名册：\d\d:\d\d:\d\d 名册：停在额度 (\d+)｜在写 (\d+)｜静默非闸 (\d+)")
pat_w = re.compile(u"^\\[\\d\\d:\\d\\d:\\d\\d\\] 额度名册：在写：(.*)$")
pat_cap = re.compile(u"^\\[\\d\\d:\\d\\d:\\d\\d\\] 额度名册：闸上：(.*)$")
NAME = re.compile(u"([^、(）]+)\\((\\d+)分")

buckets = {}          # "D<n> HH:MM" -> dict
last = None
prev_hh = None
day = 0
for l in io.open(LOG, encoding="utf-8", errors="replace"):
    m = pat_sum.match(l)
    if m:
        hh, mm = m.group(1), m.group(2)
        # 日志行只有时分秒、没有日期 ⇒ 见到「钟回拨」(23:5x 之后又出现 00:xx) 就换一天，
        # 否则 09-29 的晚上和 09-30 的白天会被拼成同一格。
        if prev_hh is not None and int(hh) < prev_hh:
            day += 1
        prev_hh = int(hh)
        key = "D%d %s:%s" % (day, hh, mm[0] + "0")   # 10 分钟一格
        b = buckets.setdefault(key, {"capped": 0, "writing": 0, "silent": 0, "names": set(), "caps": set(), "n": 0})
        b["capped"] = int(m.group(4)); b["writing"] = int(m.group(5)); b["silent"] = int(m.group(6)); b["n"] += 1
        last = key
    else:
        mw = pat_w.match(l)
        mc = pat_cap.match(l)
        if (mw or mc) and last is not None and buckets.get(last) is not None:
            src = (mw or mc).group(1)
            tgt = buckets[last]["names"] if mw else buckets[last]["caps"]
            for n, _idle in NAME.findall(src):
                tgt.add(n.strip())

keys = sorted(buckets)
if not keys:
    print("流水里还没有今天的名册行（自动轮没跑或日志被换），不输出表。")
    raise SystemExit(0)

print("=== 车队时轴（自动轮每 600 秒一拍 ⇒ 分辨率 10 分钟）===")
print("%-6s %-4s %-6s %-6s %-6s %s" % ("格", "拍", "在写", "闸上", "静默", "这一格里出现过的「在写」花名"))
for k in keys:
    b = buckets[k]
    print("%-6s %-4d %-6d %-6d %-6d %s" % (k, b["n"], b["writing"], b["capped"], b["silent"],
                                           u"、".join(sorted(b["names"]))[:150] or u"-"))

# 小时汇总：这一小时内「至少有过一拍在写」的车道数，与全程一次都没在写过的车道
hours = {}
for k in keys:
    h = k[:6]
    e = hours.setdefault(h, {"ever": set(), "capped_peak": 0, "writing_peak": 0})
    e["ever"] |= buckets[k]["names"]
    e["capped_peak"] = max(e["capped_peak"], buckets[k]["capped"])
    e["writing_peak"] = max(e["writing_peak"], buckets[k]["writing"])
print()
print("=== 按小时（在写峰值 / 闸上峰值 / 这一小时里至少动过一拍的车道数）===")
for h in sorted(hours):
    e = hours[h]
    print("  %s 时：在写峰值 %2d｜闸上峰值 %2d｜动过的车道 %d 条" % (h, e["writing_peak"], e["capped_peak"], len(e["ever"])))
last_h = sorted(hours)[-1] if hours else None
if last_h:
    print("最近一格 %s：%s" % (keys[-1], u"在写 %d｜闸上 %d｜静默 %d" % (
        buckets[keys[-1]]["writing"], buckets[keys[-1]]["capped"], buckets[keys[-1]]["silent"])))
print("边界：这只统计自动轮**看见**的（尾记录判据），看不见一次拍与拍之间的动静；也不评价谁该在跑。")
