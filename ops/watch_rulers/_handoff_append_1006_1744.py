# -*- coding: utf-8 -*-
u"""记「Codex 侧推广为什么停在一个不能执行的数上，以及那一步只能由人点」（五·二十九）。

现读（10-06 17:44，`~/.codex/thread_history_1.sqlite` 只读）：
  近 90 分有轮次的活跃 thread **1 枚**：`01a10cd0-05e8-74b1-91a0-32cdb8b180aa`（2 轮，末次 17:24）。
  名册里 codex 身份 **1 枚**：`codex:bbfix1`。⇒ 巡逻第⑦格此刻"缺口多 0 枚"是对的。

但这一格**永远停在一个不能执行的数上**，原因不是缺数据、是没有映射：
那枚活跃 thread 与 `codex:bbfix1` 之间对不上号——bbfix1 是"身份"（BB 机名册里的一个地址），
thread 是 Codex 会话自己的 id，两边没有任何字段能互指。所以：
  · "缺口多 N 枚"（第⑦格）只回答"数量对不对"，不回答"该接哪一枚"；
  · 我**不猜**：猜出来一个 id 让主人去粘，粘错了就是给一个不相干的会话装了身份，是更坏的结果。
要真把"推广到 Codex"做完，缺的只有一件事，而且只能由人做：
  **人（或号令者）看一眼 Codex 那边此刻在跑的那一两个窗口，确认它是不是 bbfix1 那个；
  是就把 `D:/moodle/agent_bus/INVITE_CODEX.txt` 粘进去（join 一条命令做完认领＋读信）；
  不是就把它自己的 thread 身份报给值守，值守登记成第二枚 codex 身份。**
值守这侧没有能把话送进 Codex 会话的口（也没有代点主人正在用的界面的授权），所以这一步不落在我身上。
贴完第⑦格那条"缺口"才有意义——现在它是"数对得上"，不是"接上了"
（同 五·十九：codex:bbfix1 全账只发过 1 条、未取 3 条，在活动 ≠ 接上）。

这条与五·一／五·二〇连着看：五·一是"还差一枚、缺一枚"（10-05 的读数），
今晚第⑦格变成"多 0 枚"，但**变的只是那个数**——那枚活跃 thread 究竟是不是 bbfix1，仍然没人知道。
把"数量对上"当成"推广完成"，正是这堆仪表最容易骗人的地方。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")
ANCHOR = u"## 五、下一轮的三个前置（照做就行）"
MARK = u"五·二十九"

SEC = u"""## 五·二十九、Codex 侧推广停在一个**不能执行的数**上，那一步只能由人点

现读（17:44，`~/.codex/thread_history_1.sqlite` 只读）：近 90 分有轮次的活跃 thread **1 枚**
`01a10cd0-05e8-74b1-91a0-32cdb8b180aa`（2 轮，末次 17:24）；名册里 codex 身份 **1 枚** `codex:bbfix1`
⇒ 第⑦格此刻「缺口多 0 枚」是对的。

但这一格**永远停在一个不能执行的数**上，原因不是缺数据、而是**没有映射**：
那枚活跃 thread 与 `codex:bbfix1` 对不上号——bbfix1 是 BB 机名册里的一个**地址**，
thread 是 Codex 会话自己的 **id**，两边没有任何字段能互指。所以：
  ·「缺口多 N 枚」只回答"数量对不对"，不回答"该接哪一枚"；
  · 值守**不猜**：猜一个 id 让主人去粘，粘错就是给不相干的会话装了身份，比不接更坏。

要真把"推广到 Codex"做完，缺的只有一件事、且只能由人做：
**人（或号令者）看一眼 Codex 此刻在跑的那一两个窗口，确认它是不是 bbfix1 那个；
是就把 `D:/moodle/agent_bus/INVITE_CODEX.txt` 粘进去（join 一条命令做完认领＋读信）；
不是就把它自己的 thread 身份报给值守，值守登记成第二枚 codex 身份。**
值守这侧没有能把话送进 Codex 会话的口，也没有代点主人正在用的界面的授权——这一步不落在我身上。

贴完第⑦格那个"缺口"才有意义：现在它是**数对得上**，不是**接上了**
（同 五·十九：codex:bbfix1 全账只发过 1 条、未取 3 条，在活动 ≠ 接上）。

这条与 五·一／五·二〇 连着看：五·一是"还差一枚"（10-05 的读数），今晚第⑦格变成"多 0 枚"，
**变的只是那个数**——那枚活跃 thread 究竟是不是 bbfix1，仍然没人知道。
把"数量对上"当成"推广完成"，正是这堆仪表最容易骗人的地方。

"""


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    if MARK in t:
        print(u"已写过，不重复写")
        return 0
    a = ANCHOR + u"\n"
    if t.count(a) != 1:
        print(u"REFUSE：锚命中 %d 次 ⇒ 未写盘" % t.count(a))
        return 1
    io.open(HAND, "w", encoding="utf-8", newline="").write(t.replace(a, SEC + a))
    print(u"已插入 %s" % MARK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
