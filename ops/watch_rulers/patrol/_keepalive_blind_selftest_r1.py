# -*- coding: utf-8 -*-
u"""续跑器新装的 blind 分支：查不到现支时**绝不**起哨兵，且要具名点名。

为什么单独测（10-06 04:1x）：这条分支的动机是"CIM 全表枚举一晚上超时六次，把续跑器打死"，
而修法是"看不见就当不知道"。两个方向都会出错：
  修过头（看不见就起）⇒ 双哨兵＝双报警，这是这堆仪表点名的真事故；
  修不足（照样 raise）⇒ 空窗照旧。
所以这里打桩把 instances() 变成"永远查不到"，跑真 main() 的循环若干拍，验它一枚都不起。

不碰生产：launch() 与 instances() 都打桩；日志写临时文件（K.LOG 换掉）；time.sleep 换成计数器。
跑法：PYTHONIOENCODING=utf-8 python _keepalive_blind_selftest_r1.py
"""
import io
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _sentinel_keepalive_r1 as K   # noqa: E402

tmpd = tempfile.mkdtemp(prefix=u"ka_blind_")
LOG = os.path.join(tmpd, "ka.log")
K.LOG = LOG

launched = []
K.launch = lambda mins: launched.append(mins)
K.instances = lambda: None           # 永远"这一拍查不到"

ticks = {"n": 0}


class StopTest(Exception):
    pass


def fake_sleep(sec):
    ticks["n"] += 1
    if ticks["n"] >= 9:              # blind 每拍 120 秒 ⇒ 9 拍够看到两次点名
        raise StopTest()


real_sleep = time.sleep
K.time.sleep = fake_sleep
# 收工时刻推到两小时后，别让 main 走到 stop 分支
real_stop_today = K.stop_today
K.stop_today = lambda *a, **kw: time.time() + 7200.0

fails = []
try:
    K.main()
except StopTest:
    pass
except Exception as e:
    fails.append(u"main() 抛了没接住的异常（%s: %s）⇒ 这一支还是会死" % (type(e).__name__, e))
finally:
    K.time.sleep = real_sleep
    K.stop_today = real_stop_today

txt = io.open(LOG, encoding="utf-8", errors="replace").read() if os.path.exists(LOG) else u""
if launched:
    fails.append(u"查不到现支却起了哨兵（%d 次）⇒ 双报警风险" % len(launched))
if u"查不到" not in txt:
    fails.append(u"日志里没有「查不到」那行 ⇒ instances 吞异常的那句没跑到")
if u"不可信" not in txt:
    fails.append(u"日志里没有连续盲拍的点名 ⇒ 单向致盲没人知道")
if ticks["n"] < 9:
    fails.append(u"只跑了 %d 拍就退出，没验到第二行点名" % ticks["n"])

import shutil
shutil.rmtree(tmpd, ignore_errors=True)

if fails:
    for x in fails:
        print(u"FAIL：" + x)
    print(u"⇒ 红 %d 条" % len(fails))
    raise SystemExit(1)
n = txt.count(u"不可信")
print(u"⇒ 绿：连 %d 拍查不到现支，launch 调用 0 次（不会起第二支哨兵），"
      u"日志里点名 %d 行（第 1、4、7 拍各一行，不刷屏）" % (ticks["n"], n))
