# -*- coding: utf-8 -*-
u"""把「11:00 覆盖曾经靠运气」这一节写进交接稿。

为什么用文件不用 heredoc：今天在命令行里现拼中文长段已经折行四次
（AssertionError／PYTHONIOENCODING=utf-10／\\\\n 断行／这次 unterminated triple-quote）。
这条纪律就写在五·二十四里，这一段是它的第一次执行。

重复执行不会写两遍（按标记判重）。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")
ANCHOR = u"## 五、下一轮的三个前置（照做就行）"
MARK = u"五·二十五"

SEC = u"""## 五·二十五、11:00 覆盖曾经**靠运气**：两条腿的默认收工时刻写死了日期，已改成不带日期

17:3x 我现算每条腿的 STOP 与「守到 11:00」的关系，发现一处真隐患：
代插腿默认 `APPLIER_STOP="1005-1100"`、看门人默认 `STACK_KEEPER_STOP="1004-1100"`
——这两个**写死的日期都已经过去**（距 11:00 分别 −1440／−2880 分）。
今天跑着的两枚（代插 23444、看门人 14248）是 01:27 被**显式传 env**（2340）带起来的，所以此刻没问题；
但只要它们死一次、由值守栈按默认值补起，就会**一起步就自退**——而栈那一格照样打「栈完整」。
这不是理论：22:46 那次重启之后，补起来的腿正是这条路径。

已修：两处默认都改成不带日期的 `"2340"`（各自的 stop_at 本来就认纯 `HHMM`＝今天该刻），
备份 `_inbox_applier_r2.py.bak_stop_1733`、`_stack_keeper_r1.py.bak_stop_1733`。
改完现算：两条默认都落到今天 23:40（距 11:00 +760 分）。

**故意没重启现役那两枚**——它们的 env 传对了、正在干活，重启只会换来一个空窗。
「改脚本要重启」这条规矩在这里有个正当例外：**当现役进程行为已经正确时，重启只有风险没有收益**；
修复留给下一次自然重启生效。下一班若看到「文件已改、进程起于改动之前」
（`_stack_staleness_check_r1.py` 一眼可辨），那是对的，不是漏。

**这一节的病根值得记住**：把「某一班次的收工时刻」写进默认值，等于给这一格装了个定时炸弹——
今天凑巧 env 传对了所以没炸，可配置本身是错的。**凡是会过期的值，别写死日期**；
要么不带日期（纯 HHMM 每次现算），要么启动时由看护器显式传下去（现在两条路都占了）。

"""


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    if MARK in t:
        print(u"已写过（%s 在文件里），不重复写" % MARK)
        return 0
    a = ANCHOR + u"\n"
    n = t.count(a)
    if n != 1:
        print(u"REFUSE：锚命中 %d 次，要 1 次 ⇒ 未写盘" % n)
        return 1
    io.open(HAND, "w", encoding="utf-8", newline="").write(t.replace(a, SEC + a))
    print(u"已插入 %s（现 %d 字符）" % (MARK, len(t) + len(SEC)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
