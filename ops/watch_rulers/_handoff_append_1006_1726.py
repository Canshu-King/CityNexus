# -*- coding: utf-8 -*-
u"""把"停投闸的现网凭据"这一段写进交接稿（17:2x 三连拦下 I 档）。

为什么用文件而不用 heredoc：今天两次 heredoc 里带中文长段都被 shell 折行吃掉
（一次报 AssertionError、一次 PYTHONIOENCODING 打错），写不进去又不留痕。
这段值守事实必须落盘，所以改成一个能重跑的小脚本，重复执行也不会写两遍。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")
ANCHOR = u"## 五、下一轮的三个前置（照做就行）\n"
TAG = u"五·二三"

SEC = u"""## 五·二三、停投闸的**现网凭据**（17:2x 三连）：拦得住、且拦的是残骸不是待办

哨兵日志连着三拍（现读 `_sentinel_relay_latest.log`）：
`[17:21:06] 停投：band:I 收件人 qoder:494abfd7 名下已欠 3 枚未取（最老 1391 分）⇒ 本拍停投；事实见板子 M 档那一格与日志，不往不读的收件框里加码`
（17:23:09、17:25:07 同形，最老分钟数随时间走到 1393／1395），
跟一行 `[17:25:07] I 档 alarm 未投出去 ⇒ 不记进重账，下一轮再试（band:I：blocked）`
——**调用方"没投出就不记重账"那条老规矩没被破坏**。

三点值得记：
一、**每拍重算**，不是一次性关闭：欠账降到上限以下（他取走、或欠账变少），下一拍自动放行。
二、拦的确实是残骸（按 五·一八 的判读：那一档 46 枚内容早已作废、**0 枚还悬着**）。
三、这条是"告警事实落板子那一格"那条处置原则的第一个现网执行者：
   告警**不再**进那个他从不打开的收件框，改为每拍在哨兵日志与板子 M 档那一格里报。

顺带记盘（不必动手，只记）：17:25 现读 **C 剩 24.56 GiB、D 剩 6.54 GiB**；一小时前是 C 7.60／D 6.67
⇒ C 那边明显被释放过（临时文件清退一类）。`_disk_slope_r1.py` 的斜率本来就在噪声里，
两次读数并起来说明一件事：**别拿单点余量推爆盘时刻**，也别因为某一拍低就动手删东西。

"""


def main():
    t = io.open(HAND, encoding="utf-8").read()
    if TAG in t:
        print(u"已写过（%s 在文件里），不重复写" % TAG)
        return 0
    n = t.count(ANCHOR)
    if n != 1:
        print(u"REFUSE：锚命中 %d 次，要 1 次 ⇒ 未写盘" % n)
        return 1
    io.open(HAND, "w", encoding="utf-8", newline="\n").write(t.replace(ANCHOR, SEC + ANCHOR))
    print(u"已插入 %s（现 %d 字符）" % (TAG, len(t) + len(SEC)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
