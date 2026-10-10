# -*- coding: utf-8 -*-
u"""记「栈体检尺学会回答『现在要不要重启』」这一节（五·二十八）。

现读（10-06 17:41，`_stack_staleness_check_r1.py`，备份 `*.bak_stopfield_1741`）：
它照旧按"进程起 vs 文件改于"报 stale（判定逻辑一个字没改），但 stale 的每一条现在**补一句可执行的裁决**：
按那条腿**实际**的收工时刻（先 env＝它启动时真拿到的那个，再文件默认值，形制与各腿 stop_at 同）算——
  实际到点已过 ⇒ 「立刻重启」；
  实际到点仍晚于下班 ⇒ 「只是看着旧，**不必现在动**，让它自然重启时带上新代码」。
今天的两条 stale（keeper 与 inbox_applier，17:32 我改了它们的默认 STOP 但故意没重启）现在报：
  实际到点 10-06 23:40（还有 358 分）⇒ 不必现在动。
这就对了：它们 env 传的是 2340、正在干活，重启只有空窗没有收益；尺以前只会喊"要重启"，
逼我每拍都手工判断一遍——现在它自己答。

两类价值分开记：① 改完脚本要不要重启，这把尺能给答案了；
② 真有腿的到点已过时，它会直接喊立刻重启（那是以前会被"看着旧"掩盖掉的真事故）。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")
ANCHOR = u"## 五、下一轮的三个前置（照做就行）"
MARK = u"五·二十八"

SEC = u"""## 五·二十八、栈体检尺现在能回答「改完要不要现在重启」，不只是喊"要重启"

现读（17:41，`_stack_staleness_check_r1.py`，备份 `*.bak_stopfield_1741`）：
它照旧按"进程起 vs 文件改于"报 stale（判定逻辑一个字没改），但 stale 的每一条现在**补一句可执行的裁决**——
按那条腿**实际**的收工时刻算（先 env＝它启动时真拿到的那个，再文件默认值，形制与各腿 `stop_at` 同）：
实际到点**已过** ⇒ 喊「立刻重启」；到点**仍晚于下班** ⇒ 喊「只是看着旧，**不必现在动**，让它自然重启时带上新代码」。

今天的两条 stale（keeper 与 inbox_applier，我 17:32 改了它们的默认 STOP 但**故意没重启**）现在报：
「实际到点 10-06 23:40（还有 358 分）⇒ 不必现在动」——对了。它们 env 传的是 2340、正在干活，
重启只有空窗没有收益。尺以前只会喊"要重启"，逼我每拍手工判断一遍；现在它自己答。

两类价值分开记：① 改完脚本要不要重启，尺能给答案了；
② 真有腿到点已过时它会直接喊立刻重启（那正是以前会被"看着旧"掩盖掉的真事故）。

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
