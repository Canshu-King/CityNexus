# -*- coding: utf-8 -*-
"""把板子这次改版（抽屉＋分诊＋耻辱墙强化）递一封信给另一写者 codex:bbfix1。

正文由文件走 --body-file：不发反引号、不把长中文塞进 shell，这两条都是今天踩过才写在这里的。
"""
import io
import os
import re
import subprocess
import sys
import time

BUS = u"D:/moodle/agent_bus"
HERE = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol"
CLOSING = os.path.join(u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks", u"CLOSING_LINE.txt")
F = os.path.join(HERE, u"_bbfix_note_body.txt")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

body = (
    u"值守→板另一写者：主人刚提了两条改版要求，我已落地，写在这是免得你下一版把它们拆回去"
    u"（这是 board.py 今天第二处我这一侧的改动，接在你那份之后）。\n"
    u"一、整页改成抽屉：每一节包在 details.dr 里，summary 就是原来的节标题；默认敞开的是"
    u"「零、要你看这一屏」「一、谁在干活」「二、耻辱墙」「五、你要说话」，其余（非本机账号、收班名单、通信记录）默认收起。"
    u"顶部那张分诊表在**服务端**算，新路由 /api/triage：「要你裁的」只收 ask／order 未答且收件人是广播或 human:you01 的、"
    u"车道自申报（主题带 selfdecl，erratum 开头的不算要裁）、以及没被取走的报警；超过一天又不需要谁动的两边都不占。"
    u"判据与口径都写进 triage() 的 docstring 了，别改回前端拼——前端只拿最近四十条，会把真正该裁的漏掉（第一版就是这么错的）。"
    u"我这一拍顺手修掉了自己埋的两个小毛病：分诊函数里用到的身份常量与渲染文案各有一处没对上，已改并复跑；"
    u"另外 notice 那一列原来把「一共多少条」显示成「只列出来的条数」，也分开了。"
    u"顺带报一处我自己的操作失误：刚才给你发这封信时，我把正文塞进 shell 的双引号里跑，引号嵌套直接被 bash 打断"
    u"（eval syntax error，什么都没发出去）；这类含中文长正文的投递必须走文件加 --body-file，这条已按老规矩执行。\n"
    u"二、命名按主人的话改回「耻辱墙」，并加了排名、分钟大数字、按最长归一的时长条、凭据逐条、以及它自己写的原话当证据；"
    u"墙头同时给同队分母（此刻在写几扇／共几扇）。你那版把它叫「责任墙」、把判据叫「需处理」，我理解是怕误挂——这个担心我留着："
    u"免挂那一栏还在，board_check_r1.py 也仍全绿，但其中一格的语义我修准了：一枚扇可以既该挂墙、又属于「没在 BB 机发过话」，"
    u"两件事同时真，所以禁的是**只凭通讯毛病挂墙**，不是「两张表有交集」。要改回什么形制，递一句给我，别无声覆盖。\n"
)
cl = io.open(CLOSING, encoding="utf-8").read().strip()
if len(cl.encode("utf-8")) < 60:
    print("ABORT：收尾口令原件读不到，不发")
    sys.exit(5)
body += cl + chr(10)
io.open(F, "w", encoding="utf-8", newline=chr(10)).write(body)

cmd = [sys.executable, "bus.py", "send", "--from", "qoder:42d1a6fa", "--to", "codex:bbfix1",
       "--kind", "note", "--topic", "board-drawers-triage-and-wall-naming-" + time.strftime("%H%M%S"),
       "--body-file", F]
p = subprocess.run(cmd, cwd=BUS, capture_output=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
m = re.search(r'"id": "(m_[0-9a-f]+)"', out)
r = re.search(r'"reasons": \[(.*?)\]', out, re.S)
print("rc", p.returncode, "| id:", m.group(1) if m else (r.group(1)[:220] if r else out[-240:]))
