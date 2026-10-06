# -*- coding: utf-8 -*-
u"""改板子那枚 badge 的措辞：把「N 分没出字」改成「N 分钟前还在动」那一族的话。

**为什么必须改**（22:5x 主人一句"除了包工头都在偷懒，没有在工作"量出来的）：
数据层**早就算对了**——`self_idle` 取的是 `tail_read(p)["self_ts"]`，也就是
"它自己产出的最后一个节点距今多久"，而且代码注释明写"外壳那些记账节点会把 mtime 刷新，
那是有人碰过它、不是它在干活"。所以那个数**本来就是新鲜度**。

问题全在显示层：`badge()` 两个分支把同一个数说成「**N 分没出字**」。
那个措辞把「50 分钟前刚交完活、此刻在等下一件」读成了「50 分钟什么也没产出」——
**数对、话错**，而人是看话不看数的。今晚据此判出的假红有四次（19:28／20:35／巡逻②格两次）。

改法（只改这两句显示话，一行逻辑不碰）：
  · 在动但刚停  → 「刚停 N 分｜上一手交完了」
  · 静默档      → 「静 N 分｜末条是『交完了/在等』还是『断了』看下一列」
为什么不直接写「N 分钟前还在动」：静默档那两句更要紧的是**分不出形状**——
"静 50 分"既可能是交完活在等（不该敲），也可能是断了（该敲），而形状由末条决定。

改前备份；改后**回读**那两句确实是新话，并跑一次 `board_check_r1.py` 看结构锁没被咬红。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUS = r"D:\moodle\agent_bus"
BOARD = os.path.join(BUS, "board.py")

PAIRS = [
    (u"if(s==='quiet45')return '<span class=\"badge x\">'+min+' 分没出字</span>';",
     u"if(s==='quiet45')return '<span class=\"badge x\" title=\"数：他多久自己产出过（不是文件 mtime，外壳记账节点不算）\">静 '+min+' 分｜形状看下一列</span>';"),
    (u"return '<span class=\"badge i\">'+min+' 分没出字</span>'}",
     u"return '<span class=\"badge i\" title=\"数：他多久自己产出过（不是文件 mtime，外壳记账节点不算）\">刚停 '+min+' 分｜上一手交完了</span>'}"),
]


def main():
    t = io.open(BOARD, encoding="utf-8", newline="").read()
    if u"分没出字" not in t:
        print(u"已改过（没有『分没出字』这句）⇒ 不重复改")
        return 0
    new = t
    for old, rep in PAIRS:
        c = new.count(old)
        print(u"锚命中 %d：%s" % (c, old[:46]))
        if c != 1:
            print(u"REFUSE：锚命中数不对，未写盘")
            return 1
        new = new.replace(old, rep, 1)
    bak = BOARD + u".bak_badgewording_2258"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(BOARD, "w", encoding="utf-8", newline="").write(new)
    back = io.open(BOARD, encoding="utf-8", errors="replace").read()
    print(u"已写（备份 %s）" % os.path.basename(bak))
    print(u"  旧话「分没出字」还在：%s（应为 False）" % (u"分没出字" in back))
    for k in (u"静 ',min,' 分｜形状看下一列", u"刚停 '+min+' 分｜上一手交完了"):
        print(u"  新话含「%s…」：%s" % (k[:18], k in back))
    return 0


if __name__ == "__main__":
    sys.exit(main())