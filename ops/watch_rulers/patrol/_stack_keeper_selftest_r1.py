# -*- coding: utf-8 -*-
"""`_stack_keeper_r1.py` 的自测：收工时刻、到点即退、每轮只转交栈脚本、认得出「补起过档」。

为什么必须自测：这枚是「无人值守时靠它自己拉回来」的那一层。它若过午夜就下班、
或者把「齐」当成「补起」写日志，下一班看日志就会被骗。全程喂假 subprocess、写自己的临时日志，
不碰真进程也不污染生产日志。
"""
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import _stack_keeper_r1 as K

res = []
TMPLOG = os.path.join(HERE, "_stack_keeper_selftest.log")


def check(name, got, want):
    ok = str(want) in str(got)
    res.append(ok)
    print(u"%-58s %s" % (name, u"对" if ok else u"错（实读：%s｜期望含：%s）" % (str(got)[:180], want)))


class Fake(object):
    def __init__(self, out, rc=0):
        self.stdout = out.encode("utf-8")
        self.returncode = rc


def fake(out, rc=0):
    return lambda *a, **k: Fake(out, rc)


# ①②③ 收工时刻：跨天形制与当天形制都要认（objective 要守到明天 11 点，旧写法过午夜就下班）
e = K.stop_at("1004-1100")
check("MMDD-HHMM 形制收在次日 11:00", time.strftime("%m-%d %H:%M", time.localtime(e)), "10-04 11:00")
check("四位形制仍按今天 23:35", time.strftime("%H:%M", time.localtime(K.stop_at("2335"))), "23:35")
check("跨天那枚确实晚于现在", e > time.time(), "True")
check("还没到点 ⇒ 还剩正数分钟", K.decide(time.time(), time.time() + 3600) > 0, "True")
check("过了点 ⇒ 返回 None（收工）", K.decide(time.time(), time.time() - 1), "None")

# ④⑤⑥⑦ 每轮只是转交栈脚本，且「补起过档」必须显出来、取不到数不许当成齐
old_log, old_run = K.LOG, K.subprocess.run
K.LOG = TMPLOG
try:
    if os.path.isfile(TMPLOG):
        os.remove(TMPLOG)
    K.subprocess.run = fake(u"   保留：supervise 已在（pid=1）\n⇒ 栈完整，0 次启动")
    started, out, rc = K.run_once()
    check("栈完整那一轮 ⇒ 不报补起", started, "False")
    log = io.open(TMPLOG, encoding="utf-8").read()
    check("齐的那轮也要写进日志（下一班看得出它在跑）", log, u"齐 ")
    K.subprocess.run = fake(u"   动作：keepalive 起了一枚 pid=41001\n   动作：bus_hub 起了一枚 pid=41002")
    started2, out2, rc2 = K.run_once()
    check("栈脚本补起过东西 ⇒ 这一轮必须显出来", started2, "True")
    log2 = io.open(TMPLOG, encoding="utf-8").read()
    check("断过档在日志里以「补起」开头标出", log2, u"补起 ")
    K.subprocess.run = fake(u"", rc=2)
    started3, out3, rc3 = K.run_once()
    log3 = io.open(TMPLOG, encoding="utf-8").read()
    check("栈脚本没回话 ⇒ 不许判成齐，要写「不可判」并带退码", log3, u"不可判")
    # 到点时 main 一次都不跑
    calls = []
    K.run_once = lambda: (calls.append(1), (False, u"", 0))[1]
    old_stop_at, sys.argv = K.stop_at, ["_stack_keeper_r1.py"]
    K.stop_at = lambda stop=None: time.time() - 5
    rc_main = K.main()
    K.stop_at = old_stop_at
    check("到点收工 ⇒ 一轮都不跑、退码 0", "%d %d" % (len(calls), rc_main), "0 0")
finally:
    K.LOG, K.subprocess.run = old_log, old_run
    if os.path.isfile(TMPLOG):
        os.remove(TMPLOG)

# ⑧ 纪律：除了自己这条线的仪表，谁的进程都不碰
src = io.open(os.path.join(HERE, "_stack_keeper_r1.py"), encoding="utf-8").read()
code_only = src.split(u'"""')[2] if src.count(u'"""') >= 3 else src
check("代码段里不出现号令者助手脚本名（只写在自己的文档段里）", "cmdr_night_watch" in code_only, "False")

print("PASS %d/%d" % (sum(1 for x in res if x), len(res)))
sys.exit(0 if all(res) else 1)
