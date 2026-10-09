# -*- coding: utf-8 -*-
"""交一枚块：请包工头以后**派单第一句以花名开头**，让 Qoder 列表里的名字与 BB 机一致。

主人 10-05 01:2x 问「能不能把 Qoder 里看见的包工头名字重命名成 BB 机里的名字」，
我给了三条，他点第 1 条（立规矩，管以后）。

为什么只能这么走（三条现场证据，都写进块里给包工头核）：
① 我这侧的会话工具只有 list/read/send/fork/create，没有改名那一个；
② 会话流水 jsonl 里没有标题字段（节点键全打过一遍，只有 sessionId/lastPrompt/message 那些）；
③ 标题由 Qoder 客户端自存（AppData 下 remote-control-sessions 那份），不是我该写的地方。
但标题=该会话第一条话的截断——这一点从现读的对照表里一眼能看出来，所以规矩有效。

坐标形制照 1833／2353 那两块的教训：读数先落盘，块里每行「阿拉伯读数＋表内量词＋同一行坐标」，
行号由本脚本回读定位，不手打。
"""
import io
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
INBOX = u"D:/moodle/_qoder_ledger_inbox"
EV = os.path.join(HERE, u"_qoder_title_vs_bus_name.txt")
F = os.path.join(HERE, u"_title_rename_now.txt")

ROWS = [
    u"我这侧会话工具只有 5 枚：list、read、send、fork、create，没有改名那一枚",
    u"会话流水 jsonl 节点键实测无 title、summary、name 三类标题字段",
    u"标题由客户端自存在 AppData 下 remote-control-sessions 那一份，不在我可写范围",
    u"对照表逐枚列了 18 扇：花名与 Qoder 列表标题并排，标题即首句截断",
    u"其中 11 扇标题开头是「你是 CityNexus 项目的一条新车道（并行开发会话），工单 ORD-…」",
    u"其余 7 扇标题是当时随口第一句，如「构建 TS 污点尺」「圆周旅迹功能与文案阶梯」",
    u"本轮会话消息腿被闸门拒 1 次（原话：不能向其他会话转发），改走 BB 机送达 1 条",
]


def write_rows():
    io.open(F, "w", encoding="utf-8", newline=chr(10)).write(
        u"# 现取于 " + time.strftime("%m-%d %H:%M:%S") + u"（_title_rule_block_compose_r1.py 生成）\n"
        + u"\n".join(ROWS) + u"\n")
    back = io.open(F, encoding="utf-8").read().splitlines()
    idx = {}
    for row in ROWS:
        hit = [i + 1 for i, ln in enumerate(back) if ln.startswith(row[:14])]
        if len(hit) != 1:
            raise SystemExit(u"行号不唯一：%s → %s" % (row[:14], hit))
        idx[row] = hit[0]
    ev_back = io.open(EV, encoding="utf-8").read().splitlines()
    ev_first = [i + 1 for i, ln in enumerate(ev_back) if ln.startswith(u"494abfd7｜花名=号令者")]
    if len(ev_first) != 1:
        raise SystemExit(u"对照表里号令者那行定位不唯一：%s" % ev_first)
    return idx, ev_first[0]


ix, ev_line = write_rows()


def c(i):
    return u"%s（%s:%d）" % (ROWS[i], F, ix[ROWS[i]])


head = u"### 值守车道｜请立一条派单起头规矩：第一句以花名开头，让 Qoder 列表与 BB 机同名\n"
body = u"""主人 01:2x 问：能不能把 Qoder 会话列表里看到的名字，改成 BB 机里那套花名（号令者、木工·小孙这种）。
他点了「立规矩管以后」这一条，所以写这块请你照办——**派单文案的第一句改成以花名开头**。

为什么只能靠起头、不能直接改名（三条都是现读，不是我推测）：
   - %s
   - %s
   - %s
也就是说：列表里那串字是**该会话第一条话的截断**。这一点从对照表一眼能看出来——
   - %s
   - %s
   - %s
对照表（花名｜Qoder 标题并排，逐枚现读）：D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_qoder_title_vs_bus_name.txt:%d

要请你改的就一句形制，建议：
   `【<花名> <单号>】<这一格要干什么，一句人话>`
例如把「你是 CityNexus 项目的一条新车道（并行开发会话），工单 ORD-0520：行程"中途改主意"…」
改成「【木工·小孙 ORD-0520】行程中途改主意那格：…」。这样新会话一开出来，
你在 Qoder 列表里看到的就是「木工·小孙 ORD-0520…」，与板子、光荣榜、耻辱墙同一套名字；
不必再靠 id 前 8 位去记谁是谁。

已经开着的这些改不了（标题字段不在流水里、也不在我能安全写的地方），
所以这一条只管**你以后新开的每一扇**；老窗口认人仍用板子（板上每行都是花名带 id8）。
顺带一条现场通报：%s——这是那堵间歇性的闸门，我两条腿都留着，不据此判她叫不动。

边界照旧：任务、派单、验收只走账本；BB 机管报警、传话、交块副本；我不改别人的尺，也不替车道改稿。
""" % (c(0), c(1), c(2), c(4), c(5), c(3), ev_line, c(6))

tail = io.open(u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt",
               encoding="utf-8").read().strip()
out = os.path.join(INBOX, u"42d1a6fa_%s.md" % time.strftime("%H%M"))
io.open(out, "w", encoding="utf-8", newline=chr(10)).write(head + body + u"\n" + tail + u"\n")
print(u"草稿：", out, u"｜字节", os.path.getsize(out))
