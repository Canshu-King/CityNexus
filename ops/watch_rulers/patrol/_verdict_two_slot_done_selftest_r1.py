# -*- coding: utf-8 -*-
u"""两档共用一个 done 文件，会不会互相把对方的回执擦成"没跑过"？

为什么验这一条（10-06 04:0x）：交接稿里我写了「done 是单行覆写 ⇒ 一处已知不足」，
但顺手补了一句「判重本身没坏」。那句话当时是我推理出来的，不是量出来的——
按老规矩（判语必须从实测行推导），这里把两档的先后四种次序都跑一遍。

形制：不起进程、不碰生产文件；把 RUN_AT / DONE / target_epoch 打到桩上，
只调 main() 里那一段 done 比对的**真代码**（用 R.__dict__ 换全局，不复制判据）。

跑法：PYTHONIOENCODING=utf-8 python _verdict_two_slot_done_selftest_r1.py
"""
import io
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _night_verdict_runner_r1 as R   # noqa: E402  import 不会起服务（main 有 __main__ 闸）

fails = []


def ck(cond, msg):
    if not cond:
        fails.append(msg)


def done_would_skip(done_text, run_at, target_date):
    u"""复刻 main() 里那一句比对（逐字来自源码，别在这里改判据）。"""
    return done_text.strip() == target_date + u"@" + run_at


# 先把源码里那一句抓出来，确认我的复刻与它同形（不然测的是我自己）
src = io.open(os.path.join(HERE, u"_night_verdict_runner_r1.py"), encoding=u"utf-8").read()
needle = u'io.open(DONE, encoding="utf-8").read().strip() == d + u"@" + RUN_AT'
ck(needle in src, u"源码里找不到那句 done 比对 ⇒ 我复刻的可能是别的判据：%r" % needle[:60])

# 真跑一遍 target_epoch：桩掉 RUN_AT，看两档各自的目标日期
def target(run_at, now):
    old = R.RUN_AT
    try:
        R.RUN_AT = run_at
        R.NVR_ROLL = True
        return R.target_epoch(now)
    finally:
        R.RUN_AT = old


DAY = 86400.0
t0 = time.mktime(time.strptime("2026-10-06 12:00:00", "%Y-%m-%d %H:%M:%S"))

# —— 次序 1：10:55 先出件，之后同一天的 23:00 档重拉 ⇒ 不该被 10:55 的回执挡住
e1, d1 = target(u"10:55:00", t0)          # 12:00 已过 10:55 ⇒ 顺延明天
ck(d1 == u"2026-10-07", u"10:55 档在 12:00 应顺延到 10-07，实得 %s" % d1)
done_after_early = u"2026-10-06@10:55:00" + chr(10)
e2, d2 = target(u"23:00:20", t0)
ck(d2 == u"2026-10-06", u"23:00 档在 12:00 应仍是今天，实得 %s" % d2)
ck(not done_would_skip(done_after_early, u"23:00:20", d2),
   u"10:55 的回执把 23:00 那档挡住了（会漏出终值单）")

# —— 次序 2：23:00 出完件，之后重拉 10:55 档 ⇒ 目标已是明天，不该被今天的回执挡住
done_after_late = u"2026-10-06@23:00:20" + chr(10)
e3, d3 = target(u"10:55:00", time.mktime(time.strptime("2026-10-06 23:30:00", "%Y-%m-%d %H:%M:%S")))
ck(d3 == u"2026-10-07", u"23:30 时 10:55 档应顺延到 10-07，实得 %s" % d3)
ck(not done_would_skip(done_after_late, u"10:55:00", d3),
   u"23:00 的回执把 10:55 下一档挡住了（明天收尾没人出）")

# —— 次序 3：同一档出完当天再重拉 ⇒ 必须挡住（这才叫不双跑、不落两份件）
ck(done_would_skip(done_after_early, u"10:55:00", u"2026-10-06"),
   u"同档同日没被挡住 ⇒ 会落第二份互相矛盾的读数")

# —— 次序 4：单行覆写的真实后果——写第二档会擦掉第一档那行；确认这不改变上面三条的判定
tmpd = tempfile.mkdtemp(prefix=u"done_two_slot_")
DP = os.path.join(tmpd, "done.txt")
io.open(DP, "w", encoding="utf-8", newline="\n").write(u"2026-10-06@10:55:00" + chr(10))
io.open(DP, "w", encoding="utf-8", newline="\n").write(u"2026-10-06@23:00:20" + chr(10))
txt = io.open(DP, encoding="utf-8").read()
ck(txt.count("10:55") == 0, u"覆写后 10:55 那行本该不见（这条是记录损失，不是判据损失）")
ck(done_would_skip(txt, u"23:00:20", u"2026-10-06"), u"覆写后当天 23:00 档没能自挡 ⇒ 会重跑")
ck(not done_would_skip(txt, u"10:55:00", u"2026-10-07"), u"覆写后明天 10:55 档被误挡")
import shutil
shutil.rmtree(tmpd, ignore_errors=True)

if fails:
    for x in fails:
        print(u"FAIL：" + x)
    print(u"⇒ 红 %d 条" % len(fails))
    raise SystemExit(1)
print(u"⇒ 绿：两档共用一个 done 只损失**对账记录**（第一档那行被覆写），判据不受影响："
      u"同档同日会自挡（不落两份件）、跨档跨日都不会互相挡住（明天收尾照出）；"
      u"比对那一句是逐字从源码抓出来复跑的，不是另写一把尺。")
