# -*- coding: utf-8 -*-
u"""把 20:35 那次 J 档假红的并排读数，落成**独立档**（不再寄生在会被改写的 HIT 上）。

为什么搬家（20:08 实测出的代价）：那段并排读数原本只写在 `_sentinel_relay_HIT.txt` 末尾。
可 HIT 是哨兵**每轮覆盖**的档——20:08 我做自测时删掉它跑一轮、结果超时没还原，
从备份还原回来的是 **20:41 那一份**，20:39 写进去的并排读数**没了**。
⇒ 凡是要跨轮次留痕的东西，不能寄在会被覆盖的档里。

这个档的边界：只追加，不覆盖；带日期戳；下一班读得到。
"""
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, u"J_ERRATUM_20261006.md")

BODY = u"""# 勘误：20:35:57 哨兵 J 档那次「断在半路」是**假红**

> 这份是**跨轮次留痕**的档。原稿写在 `_sentinel_relay_HIT.txt` 末尾，
> 而那个档每轮被覆盖——20:08 我做自测删掉它跑一轮、结果超时没还原，从备份还原回来的是
> 20:41 那一份，原稿没了（20:09 从备份找回）。所以搬到独立档。

## 报的是什么

哨兵 20:35:57 的 J 档正文写：

> J 车道 1d64acf5 断在半路（尾条是没回音的 tool_use）⇒ 它不会自己回来读账本，
> 该敲号令者把它叫回这一手；叫醒与派单仍归他，我只把话送到。

## 三条独立读数都说「不是断在半路」

| 来源 | 读数 |
|---|---|
| 哨兵**自己**那把分类器 `_why_stopped_r1.py` 的判定 | 1d64acf5 静五十二分｜判：**卡闸、等裁语、谈交付**（**没有"断在半路"这一类**） |
| 末态尺 `_lane_tailform_r1.py`（读流水末三条对话节点） | assistant tool_use:TaskUpdate → **user tool_result** → assistant text ⇒ **交活型停着，有回音** |
| 240 KB 尾窗字节计数 | 尾窗里 tool_result 出现二十次（全文件五千四百一十八次）⇒ "只读尾部看不见回音"被排除 |

## 根因与修法

分类器把「卡闸」与「断在半路」放**同一栏**（「该敲车道本人（卡闸/断在半路）」），
而 J 档那条消息的成因是**手写的**——它把卡闸讲成了断在半路。
**这是 relay 的成因，不是分类器的成因。**

修法（已落）：成因改为**从分类器原文取**（`_sentinel_relay_r1.py` 的 `why_stopped_line()`）。
分类器真报「断在半路」才写那句；否则写「分类器判：XXX（**非断在半路**）⇒ 该敲的是号令者点验收，
不是叫醒这一扇」；读不到判词写「**成因不可判**」——**不回退到手写那句**，那正是假红的路。

## 判语

**1d64acf5 不该被当断在半路叫醒。** 它是卡闸／等裁语／谈交付，
该敲的是号令者点验收（它本来就在分类器"该敲号令者"那一栏里）。

## 两处踩坑（同一晚）

1. 取分类器那一行时，行首**有两个空格**；`line.startswith(id8)` 恒 False，
   取回来一路 None——而"取不到"长得和"没有判词"一模一样。必须先 `strip()`。
2. 跑哨兵做自测时，它 `import` 就 `sys.stdout.reconfigure`，在 GBK 控制台上写不出「⇒」；
   而且**一整轮要十几分钟**，别指望能在自测里跑三轮。真要跑，替掉取数口并给足超时，
   并保证**即使超时也还原 HIT**。

## 未验到的（不报成验过）

新措辞在真网上还没出现过——J 档自 20:35 之后**没有候选**，所以「非断在半路」与「成因不可判」
两个分支都**没有现网反证**。等真出现 J 档候选的那一轮才算数。
"""


def main():
    t = io.open(OUT, encoding="utf-8", errors="replace").read() if os.path.exists(OUT) else u""
    if u"假红" in t:
        print(u"已在 ⇒ 不重复写")
        return 0
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(BODY)
    back = io.open(OUT, encoding="utf-8", errors="replace").read()
    print(u"已写 %s｜%d 字节" % (os.path.basename(OUT), len(back)))
    for k in (u"卡闸、等裁语、谈交付", u"交活型停着", u"why_stopped_line", u"没有现网反证"):
        print(u"  回读含「%s」：%s" % (k, k in back))
    print(u"落盘时刻 %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    return 0


if __name__ == "__main__":
    sys.exit(main())