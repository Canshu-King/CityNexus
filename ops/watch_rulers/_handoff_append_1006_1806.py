# -*- coding: utf-8 -*-
u"""更正 codex:bbfix1 的推广状态：它**接上了**，不是"只发过 1 条像没接"（五·三十五）。

五·十九／五·二十九 我据"全账只发过 1 条、未取 3 条"把它读成"在活动 ≠ 接上"。现读（10-06 18:06，bus.jsonl），
那 1 条是：`deliver`／id `m_3f73d9b0028a`／**4166 分前**（10-04 19:0x 前后）／topic `bbfix:board-repair`
——**一件真交付**（板子修复）。加上它名册里 `verified` 真，⇒ 它是**接过总线的、交付过东西的**那枚。

那 3 枚未取的是**我（42d1a6fa）发给它的 note**，内容都是板子侧的事（两桶口径、抽屉 triage、
copy-plain-speech 改写），它没取。合起来正确的读法是：
  · **推广对它已完成**：在册、自证、交付过一件；
  · 缺的只是"最近没读我给的三枚 note"——而那三枚是**板子活**的通知，
    它若今晚做板子活自然会用上，不取不算没接上；
  · 别再把它和"没接上的车道"（五·二十六里那批）混为一谈——那是两件不同的事。

那枚"活跃 thread 到底是不是 bbfix1"的问题仍然无解（thread id 与 BB 机地址没有映射，五·二十九），
但它对 bbfix1 这一枚的**推广状态**已经明确：**已完成**。等人点名的只剩"另一个 thread 是不是新车道"。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")
ANCHOR = u"## 五、下一轮的三个前置（照做就行）"
MARK = u"五·三十五"

SEC = u"""## 五·三十五、更正 codex:bbfix1 的推广状态：它**接上了**（不是"只发过 1 条像没接"）

五·十九／五·二十九 我据「全账只发过 1 条、未取 3 条」把它读成"在活动 ≠ 接上"。现读（18:06，bus.jsonl），
那 1 条是：`deliver`／id `m_3f73d9b0028a`／**4166 分前**（10-04 19:0x 前后）／topic `bbfix:board-repair`
——**一件真交付**（板子修复）。加上它名册里 `verified` 真，⇒ 它是**接过总线的、交付过东西的**那一枚。

那 3 枚未取的是**我发给它的 note**，内容都是板子侧的事（两桶口径、抽屉 triage、copy-plain-speech 改写），
它没取。合起来正确的读法：
- **推广对它已完成**：在册、自证、交付过一件；
- 缺的只是"最近没读我给的三枚 note"——而那三枚是**板子活**的通知，它若今晚做板子活自然会用上，不取≠没接上；
- 别再把它和"没接上的车道"（五·二十六那批，压根没发过话）混为一谈——那是两件不同的事。

那枚"活跃 thread 到底是不是 bbfix1"仍然无解（thread id 与 BB 机地址没有映射，五·二十九），
但它对 bbfix1 这一枚的**推广状态**已经明确：**已完成**。等人点名的只剩"另一个 thread 是不是新车道"。

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
