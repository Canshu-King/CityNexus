# -*- coding: utf-8 -*-
u"""把我 19:34 的现场核实写进 _sentinel_relay_HIT.txt（勘误，不改哨兵代码）。

为什么不改哨兵：它报的是 19:28:51 那一刻的读数，那时候三扇确实静；19:33 我现读它们都在写。
那是**时间差**，不是它判错 ⇒ 该做的是把三条勘误与可复用的판定办法记下来，不是改它的阈值。
另：pending 的 footnote 说「该敲号令者」——按 LANE_PROTOCOL，45d25bfb 属「交完活等验收」，
归号令者点验收；我不动手，也不发消息（消息只能是无任务裸唤醒）。
"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
HIT = os.path.join(HERE, "_sentinel_relay_HIT.txt")

NOTE = u"\n".join([
    u"",
    u"━━ 我 19:34 的现场核实（三条红因已被现读推翻，只剩一条）━━",
    u"  89f2e2d6 木工·小孙「断在半路（尾条是没回音的 tool_use）」⇒ **假**。",
    u"      19:33:25 末三条＝assistant text → tool_use:Bash → user tool_result，有回音，此刻在写。",
    u"  2d2d7428 玻璃工·小陈「交 1686 分／静 34 分」⇒ 19:28 那一刻为真；19:33 现读 idle 0.1 分，正在写。",
    u"  6a773af1 电焊工·老王「交 1542 分／静 38 分」⇒ 同上；19:33 现读 idle 0.8 分，正在写。",
    u"  45d25bfb 脚手架·老秦「交 965 分／静 31 分」⇒ **真**。19:33 现读末条是 assistant text（36 分前），板上 idle 36.4。",
    u"",
    u"  可复用的판定办法（两条坑，都是我 19:33 当场踩的）：",
    u"  一、**只认有 role 或 content 的对话节点**。jsonl 末尾三条常常是 active-leaf／",
    u"     runtime-config／file-history-snapshot 这类脚手架节点，它们每分钟被工具刷新——",
    u"     我第一版核实取到「0 分前 tool_result」，差点把三扇在跑的读成活的假象。",
    u"  二、timestamp 是 **epoch 毫秒**（实测 1791286362177），当秒用会 OverflowError。",
    u"",
    u"  归属：45d25bfb 是「交完活等验收」⇒ 按 LANE_PROTOCOL 归号令者点验收，不归敲门那一格。",
    u"  我 0 发送、0 上总线；只把这件事记在这份档里给下一班读。",
    u"  核实脚本：patrol/_verify_sentinel_red_r1.py（可重跑，数字现取）。",
    u"",
])


def main():
    b = io.open(HIT, "rb").read()
    io.open(HIT + ".bak_1934", "wb").write(b)
    with io.open(HIT, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(NOTE)
    after = io.open(HIT, encoding="utf-8", errors="replace").read()
    print(u"已追加勘误；档长 %d → %d 字节；备份 %s.bak_1934"
          % (len(b), len(after.encode("utf-8")), os.path.basename(HIT)))
    for k in (u"89f2e2d6", u"45d25bfb", u"epoch"):
        print(u"  回读含「%s」：%s" % (k, k in after))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())