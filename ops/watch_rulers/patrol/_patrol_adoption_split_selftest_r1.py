# -*- coding: utf-8 -*-
u"""第⑩格 adoption_split() 的合成自测：每造一枚该报的输入，验清单会 +1。

规矩来源（都咬过）：
  10-03「汇总器每加一格要故意造一次该报的输入验清单会 +1」；
  10-02「收窄一档会悄悄删掉一类覆盖」——这一格的四态里，C2（只收不发）是今天新拆出来的，
        没有反证就没人知道它哪天会被并回 C。
所以这里逐态造一枚正例、再互相反控（不该进的那一态必须是空）。

跑法：PYTHONIOENCODING=utf-8 python _patrol_adoption_split_selftest_r1.py
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bb_patrol_once_r1 as P   # noqa: E402  只 import，不起巡逻

fails = []


def ck(cond, msg):
    if not cond:
        fails.append(msg)


NOW = time.time()
W = 360.0


def row(i):
    return {u"id8": u"%08x" % i, u"name": u"车道%d" % i}


rows = [row(i) for i in range(6)]
h = [u"qoder:" + r[u"id8"] for r in rows]
# 函数返回的是板上的 id8（不是整枚 qoder:xxx），断言必须按 id8 写——
# 我第一版拿 'qoder:%s'[:8] 当期望值，那是七条假红，代码本身分得没错。
k = [r[u"id8"] for r in rows]

# —— 正例：每态各一枚
spoken = {
    h[0]: NOW - 60,                    # A 在发
    h[1]: NOW - (W + 30) * 60,         # B 发过但静默
    # h[2]：不发不取 ⇒ C 两腿全无
    # h[3]：不发但取过 ⇒ C2 只收不发
    h[4]: NOW - 10,                    # A 第二枚（窗口内）
    h[5]: NOW - (W + 1) * 60,          # B 第二枚（刚好过窗）
}
took = {h[3]: NOW - 300, h[2]: 0.0}    # h[2] 故意给 0：空值不许被当成"取过"

A, B, C, C2 = P.adoption_split(rows, spoken, took, NOW, W)
ck(sorted(A) == sorted([k[0], k[4]]), u"A 态不对：实得 %s" % (A,))
ck(sorted([x[0] for x in B]) == sorted([k[1], k[5]]), u"B 态不对：实得 %s" % (B,))
ck(C == [k[2]], u"C 态（两腿全无）不对：实得 %s" % (C,))
ck(C2 == [k[3]], u"C2 态（只收不发）不对：实得 %s" % (C2,))
ck(len(A) + len(B) + len(C) + len(C2) == len(rows),
   u"四态相加 %d 不等于分母 %d ⇒ 有车道没被归到任何一态"
   % (len(A) + len(B) + len(C) + len(C2), len(rows)))
age = dict(B)
ck(abs(age.get(k[1], -1) - (W + 30)) <= 1, u"B 里那枚的静默分钟算错：实得 %s" % (age.get(k[1]),))

# —— 反控 1：把 took 清空 ⇒ 原本 C2 那枚必须落进 C（这两态的差别只有"取过没有"）
# 返回值顺序是 (A, B, C, C2)，前两版我把第三、四位的名字写反了 —— 那是七条/两条假红，函数分得对。
A2, B2, Cx, C2x = P.adoption_split(rows, spoken, {}, NOW, W)
ck(Cx == [k[2], k[3]] and C2x == [], u"反控失败：took 清空后没有并入 C（C=%s C2=%s）" % (Cx, C2x))

# —— 反控 2：窗口拉到极大 ⇒ 不该再有 B，也不该再有"发过静默"
A3, B3, Cx3, C2x3 = P.adoption_split(rows, spoken, took, NOW, 100000.0)
ck(B3 == [], u"窗口放大后仍有 B：实得 %s" % (B3,))
ck(sorted(A3) == sorted([k[0], k[1], k[4], k[5]]), u"窗口放大后 A 不收：实得 %s" % (A3,))

# —— 反控 3：窗口为 0 ⇒ 一枚都不许算"在发"（巡逻那侧跑过这条现网对照）
A4, B4, Cx4, C2x4 = P.adoption_split(rows, spoken, took, NOW, 0.0)
ck(A4 == [], u"窗口=0 还有 A：实得 %s ⇒ 窗口没生效" % (A4,))
ck(len(A4) + len(B4) + len(Cx4) + len(C2x4) == len(rows), u"窗口=0 时四态不等于分母")

# —— 反控 4：空输入不许抛，且清单为空
ck(P.adoption_split([], {}, {}, NOW, W) == ([], [], [], []), u"空输入没回到四个空清单")

if fails:
    for x in fails:
        print(u"FAIL：" + x)
    print(u"⇒ 自测红 %d 条" % len(fails))
    raise SystemExit(1)
print(u"⇒ 自测绿：四态各造一枚正例（分母守恒）｜took 清空会并入 C｜窗口放大吞掉 B｜"
      u"窗口=0 一枚不算在发｜空输入回四个空清单")
