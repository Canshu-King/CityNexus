# -*- coding: utf-8 -*-
"""「车队黑了多久」这一格单独成尺——因为今天 06:00-11:00 自动轮连续五拍到「在写 0」，
，但 18:40 我把脉搏一起并入判据后重算：那 244 分钟里只有 163 分钟是真的整队停（分三段 65/33/65 分钟），另有 10 拍是「会话尾部看着没写、枝还在推」。盘有档、待插有档、闸上有名册，**只有「整队没人干活」没有档**。
用户这句要求是「保证他们至少工作到晚上11点」，所以这一格必须能自己响，而不是等我下一轮想起来查。

只读 `autumn_watch.log`（自动轮每 600 秒写一行名册汇总）。判据：
  暗 = 那一拍「在写」≤ THRESH（默认 1，因为号令者一个人转不动全车队）
  连续暗的分钟数 = 首尾两拍的时间差（含当前这拍），不是拍数×600，因为每拍本身还要 90-150 秒。
  日志行没有日期 ⇒ 见到钟回拨就换天（否则昨晚的 22 时和今天的 00 时会拼成同一格）。
输出：当前连续暗多久、今天最长的一段暗窗、以及今天每一段暗窗的起止。
"""
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
THRESH = int(sys.argv[1]) if len(sys.argv) > 1 else 1

pat = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\] 额度名册：\d\d:\d\d:\d\d 名册：停在额度 (\d+)｜在写 (\d+)｜静默非闸 (\d+)")
# 09-30 18:40 的更正：只凭「尾记录在写」判整队黑着是**过头的**。今天 06:02→10:07 那 16 拍名册确实全报在写 0，
# 同一段时间的脉搏却还在动：06:10 新枝 9 条、07:09 12 条、07:53 4 条、08:00 2 条、08:11 0 条、08:23-08:34 1-2 条。
# ⇒ 那段时间里有车道在推枝/收尾，只是会话尾部看起来不像在写。现在「暗」的定义改成**两条同时成立**：
#   尾记录在写 ≤ THRESH 且 脉搏「新动过的 review 枝」为 0。
pat_pulse = re.compile(u"^\\[(\\d\\d):(\\d\\d):\\d\\d\\] 脉搏 PULSE \\d\\d:\\d\\d 窗口 \\d+ 分：新动过的 review 枝 (\\d+) 条")
rows = []
pulses = {}
day = 0
prev = None
for l in io.open(os.path.join(HERE, "autumn_watch.log"), encoding="utf-8", errors="replace"):
    mp = pat_pulse.match(l)
    if mp:
        pulses[int(mp.group(1)) * 60 + int(mp.group(2))] = int(mp.group(3))
        continue
    m = pat.match(l)
    if not m:
        continue
    hh, mm, ss = (int(m.group(i)) for i in (1, 2, 3))
    if prev is not None and hh < prev:
        day += 1
    prev = hh
    secs = ((day * 24 + hh) * 60 + mm) * 60 + ss
    key = hh * 60 + mm
    pn = None
    for back in range(0, 4):                     # 脉搏行与名册行同一拍，差 1-3 分钟容错
        if key - back in pulses:
            pn = pulses[key - back]
            break
    rows.append((secs, "%02d:%02d:%02d" % (hh, mm, ss), int(m.group(5)), int(m.group(4)), int(m.group(6)), pn))

if not rows:
    print("流水里没有名册行，什么都判不了（自动轮没跑？）")
    raise SystemExit(0)

# 分段：连续「暗」的段。暗 = 尾记录在写 ≤ THRESH **且** 脉搏新枝 = 0（两问同时成立才算整队停）
segs = []
cur = None
tail_only = 0
for r in rows:
    dark = r[2] <= THRESH and r[5] == 0
    if r[2] <= THRESH and r[5] not in (0, None):
        tail_only += 1
    if dark:
        if cur is None:
            cur = [r, r]
        else:
            cur[1] = r
    elif cur is not None:
        segs.append(cur)
        cur = None
if cur is not None:
    segs.append(cur)

print("=== 暗窗（判据：单拍「在写」≤ %d **且** 脉搏新枝 = 0；共 %d 拍名册）===" % (THRESH, len(rows)))
print("另有 %d 拍是「尾记录看着没人写、但脉搏还在推枝」——这一类以前被我算进暗窗，现在不算（今天 06:02→10:07 正是这一类）。" % tail_only)
last_day = rows[-1][0] // (24 * 3600) if rows else 0
for a, b in segs:
    inside = [r for r in rows if a[0] <= r[0] <= b[0]]
    d = int(a[0] // (24 * 3600))
    print("  D%d %s → %s 长 %.0f 分钟（这 %d 拍里在写峰值 %d，闸上峰值 %d，脉搏峰值 %s）" % (
        d, a[1], b[1], (b[0] - a[0]) / 60.0, len(inside),
        max(r[2] for r in inside), max(r[3] for r in inside),
        max([(r[5] if r[5] is not None else 0) for r in inside])))
last = rows[-1]
now_segs = [s for s in segs if s[1][0] == last[0]]
cur_min = (now_segs[0][1][0] - now_segs[0][0][0]) / 60.0 if now_segs else 0.0
day_of = lambda t: int(t // (24 * 3600))
segs_today = [s for s in segs if day_of(s[0][0]) == last_day]
longest = max(((b[0] - a[0]) / 60.0 for a, b in segs_today), default=0.0)
print()
print("最新一拍 %s：在写 %d｜闸上 %d｜静默 %d" % (last[1], last[2], last[3], last[4]))
print("当前是否正处在暗窗里：%s；已黑 %.0f 分钟" % ("是" if now_segs else "否", cur_min))
print("最新一天（D%d）：暗窗 %d 段、合计 %.0f 分钟、最长一段 %.0f 分钟" % (
    last_day, len(segs_today), sum((b[0] - a[0]) / 60.0 for a, b in segs_today), longest))
print("边界：日志里含前一天（按钟回拨分天），所以只有 D%d 那几段算「今天」；分辨率是自动轮自己的 600 秒一拍，"
      "「黑了 30 分钟」这类话只能精确到拍，两拍之间发生的黑→亮→黑看不见。" % last_day)
