# -*- coding: utf-8 -*-
u"""`_knock_gate_shape_r1.py` 的自测：造一次"该红的那一次"，验闸咬得住。

为什么必须做：20:11 现读静默超 45 分的是 **0 扇** ⇒ 真网上它没东西可咬。
**不咬人的闸等于没有闸**（这条我自己的纪律），所以用假数据先验它会红：
  ① 一扇静 51 分 + 末态「断在半路」⇒ 必须落进"真该敲"
  ② 一扇静 63 分 + 末态「交活型停着」⇒ 必须落进"看着像停、现读在动"（不列该敲）
  ③ 两扇同时在列 ⇒ 两态都要分开归，不得混成一枚
  ④ 判词读不到时（tailform 返回空）⇒ **当不可判，不当该敲**（不拿默认值冒充读数）
做法：不改闸的代码，只把它的两个取数口换掉（board_rows / tail_verdict），
这样验的是**它自己的分类逻辑**，不是我重写一遍。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _knock_gate_shape_r1 as G

fails = []


def ck(cond, msg):
    if not cond:
        fails.append(msg)


FAKE_ROWS = [{"id8": "aaaa1111", "name": u"甲", "idle_min": 51.0, "live": "idle"},
             {"id8": "bbbb2222", "name": u"乙", "idle_min": 63.0, "live": "idle"},
             {"id8": "cccc3333", "name": u"丙", "idle_min": 10.0, "live": "running_tool"}]

FAKE_VERDICT = {"aaaa1111": u"**断在半路**：末条 tool_use 且近五条无 tool_result",
                "bbbb2222": u"**交活型停着**：末条是 text",
                "cccc3333": u"tool_use 已回音"}


def run(fake_verdict):
    real_rows, real_tv = G.board_rows, G.tail_verdict
    G.board_rows = lambda: FAKE_ROWS
    G.tail_verdict = lambda pre: (fake_verdict.get(pre, u"（读不到判词）"), u"")
    buf = io.StringIO()
    so = sys.stdout
    sys.stdout = buf
    try:
        G.main()
    finally:
        sys.stdout = so
        G.board_rows, G.tail_verdict = real_rows, real_tv
    return buf.getvalue()


out = run(FAKE_VERDICT)
ck(u"真该敲 1 扇" in out, u"① 断在半路那扇没落进真该敲：\\n%s" % out)
ck(u"看着像停、现读在动 1 扇" in out, u"② 交活型那扇没落进看着像停：\\n%s" % out)
ck(u"aaaa1111" in out and u"bbbb2222" in out, u"③ 两扇的 id 没都报出来")
ck(u"真该敲 1 扇：aaaa1111" in out, u"③ 真该敲那一栏 id 不对：\\n%s" % out)
print(u"①②③ 通过")

# ④ 判词读不到 ⇒ 不可判，不当该敲
G.READABLE = True
out4 = run({})
ck(u"真该敲 0 扇" in out4, u"④ 判词读不到却判成该敲：\\n%s" % out4)
ck(u"看着像停、现读在动 2 扇" in out4, u"④ 不可判那两扇没落进不可判那一栏：\\n%s" % out4)
print(u"④ 通过")

if fails:
    for x in fails:
        print(u"FAIL：" + x)
    raise SystemExit(1)
print(u"⇒ 自测绿：断在半路→真该敲｜交活型→不列｜两态分开｜判词读不到→不可判不当该敲")