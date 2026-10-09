# -*- coding: utf-8 -*-
"""切断 M 档的自激环：别把"哨兵自己投的报警"当成「传话断了」的证据（10-05 00:2x 实测）。

现场读数：号令者未取 29 条，其中 **14 条（48%）是哨兵自己投的 `band:*` alarm**，最老 18 分。
环长这样：M 档发现"某人压着 alarm 没取" ⇒ 投一条 alarm 给号令者 ⇒
这条 alarm 本身又落进"号令者压着 alarm 没取"的口径 ⇒ 下一轮再投一条……
报警越多 ⇒ 积压越多 ⇒ 报警更多。收件框被自己的回声填满，真需要他动的那几条反而被埋。

修法不是关掉 M 档，也不是放宽阈值：**把自己投的那类从"谁的信被压着"的分母里剔出去，单独数、单独写日志**。
「号令者没读哨兵的报警」这件事的正确出口是板子与日志（人看得见），不是再往他收件框灌一条 alarm。
别人的 deliver／order／note 照旧计——那才是"最后一公里真断了"。
"""
import ast
import io
import sys

P = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_sentinel_relay_r1.py"
s0 = io.open(P, encoding="utf-8", errors="replace").read()
s = s0
miss = []


def rep(old, new):
    global s
    if s.count(old) != 1:
        miss.append(u"锚命中 %d 次：%s" % (s.count(old), old.strip().splitlines()[0][:46]))
        return
    s = s.replace(old, new, 1)


rep(u'''_M_DEAD = {"n": 0, "oldest": 0, "who": []}''',
    u'''_M_DEAD = {"n": 0, "oldest": 0, "who": []}
_M_ECHO = {"n": 0, "oldest": 0}
SENTINEL_ID = u"qoder:42d1a6fa"


def is_own_alarm(m):
    u"""哨兵自己投出去的那类报警（topic 以 band: 开头）。它不该再当「信被压着」的证据。"""
    return (str(m.get("from")) == SENTINEL_ID and str(m.get("kind")) == u"alarm"
            and str(m.get("topic", u"")).startswith(u"band:"))''')

rep(u'''    dead = [(m, a) for m, a in pend if str(m.get("to")) in forgotten]
    aged = [(m, a) for m, a in pend if str(m.get("to")) not in forgotten
            and a >= thr[m.get("kind")]]''',
    u'''    dead = [(m, a) for m, a in pend if str(m.get("to")) in forgotten]
    # 自己的回声单独数：00:2x 实测号令者未取 29 条里 14 条（48%）是哨兵自己投的 band: alarm，
    # 再拿它当证据就是"你没读我的报警"→"又多一条我的报警"的自激环。
    echo = [(m, a) for m, a in pend if is_own_alarm(m) and a >= thr[m.get("kind")]]
    aged = [(m, a) for m, a in pend if str(m.get("to")) not in forgotten
            and not is_own_alarm(m) and a >= thr[m.get("kind")]]''')

rep(u'''    if dead:
        say(u"M 档死信 %d 条不计入分母（收件人已作废：%s，最老 %d 分）"
            % (len(dead), u"、".join(_M_DEAD["who"]), _M_DEAD["oldest"]))''',
    u'''    if dead:
        say(u"M 档死信 %d 条不计入分母（收件人已作废：%s，最老 %d 分）"
            % (len(dead), u"、".join(_M_DEAD["who"]), _M_DEAD["oldest"]))
    _M_ECHO["n"] = len(echo)
    _M_ECHO["oldest"] = int(max([a for _m, a in echo])) if echo else 0
    if echo:
        say(u"M 档自回声 %d 条不计入分母（哨兵自己投的 band: alarm，最老 %d 分）"
            u"⇒ 这类要人读，靠板子与日志，不靠再投一条 alarm"
            % (len(echo), _M_ECHO["oldest"]))''')

if miss:
    for m in miss:
        print(m)
    sys.exit(u"ABORT：哨兵未改动")
ast.parse(s)
io.open(P, "w", encoding="utf-8", newline=chr(10)).write(s)
print(u"M 档自回声已分列｜%d → %d 字节" % (len(s0.encode("utf-8")), len(s.encode("utf-8"))))
