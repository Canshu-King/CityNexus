# -*- coding: utf-8 -*-
"""把「M 档复述件口径已装」这块短件写进收件口：数从自测现跑重算，锚同行现取，过门才交。

为什么另开一块而不是在 BB 机里说完就算：账本是任务/验收的唯一信道（常设裁定 LANE_PROTOCOL），
BB 机只承报警·传话·块副本。我上一块自申报的第一件已经办完，账上必须自己跟上。
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.dirname(HERE)
INBOX = u"D:/moodle/_qoder_ledger_inbox"
GATE = os.path.join(LIVE, "claim_coordinate_check_r7.py")
ST = os.path.join(HERE, u"_m_band_relay_selftest_r1.py")
SENT = os.path.join(HERE, u"_sentinel_relay_r1.py")
BUS = u"D:/moodle/agent_bus"
PYEXE = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(args, cwd, timeout=600):
    p = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return p.returncode, ((p.stdout or b"") + (p.stderr or b"")).decode("utf-8", "replace")


def line_of(path, needle):
    hits = [i + 1 for i, l in enumerate(io.open(path, encoding="utf-8", errors="replace")) if needle in l]
    if len(hits) != 1:
        raise SystemExit(u"ABORT：%s 里 %r 命中 %d 处（要唯一）" % (os.path.basename(path), needle, len(hits)))
    return hits[0]


def main():
    rc, out = sh([PYEXE, ST], HERE, timeout=600)
    m = re.search(r"(\d+)/(\d+) 过", out)
    if rc != 0 or not m:
        raise SystemExit(u"ABORT：自测没绿或没吐计数（rc=%d）" % rc)
    art = os.path.join(HERE, u"_m_band_relay_selftest_out.txt")
    io.open(art, "w", encoding="utf-8", newline=chr(10)).write(out)
    A = {u"sp": m.group(1), u"sa": m.group(2), u"ver": time.strftime("%m-%d %H:%M"),
         u"cmdr_line": line_of(SENT, u"CMDR_IDS = frozenset("),
         u"fn_line": line_of(SENT, u"def bus_unread_alarms():"),
         u"st_line": line_of(ST, u"旧写法在同一份账上数到三枚"),
         u"art_p": u"live_checks/patrol/_m_band_relay_selftest_out.txt:1",
         u"rows": sum(1 for _ in io.open(os.path.join(BUS, u"bus.jsonl"),
                                        encoding=u"utf-8", errors=u"replace"))}
    body = u"""### 值守车道｜M 档那条「复述件不进分母」已装，另一条量出它本来住在哪
自申报（打更人·值守 `42d1a6fa`，{ver}）：我上一块名下第一件办完了，这块是它的验收面。

装了的那条（副号令者·夜班具名要求）：号令者两扇之间互递的复述件不再进「谁压着信没取」的分子，数不藏——单列一格并具名写进日志。位置 {cmdr_line} 那张名单与 {fn_line} 那个取数口。{sp}/{sa} 格过（自测原文留档 {art_p}，出处 live_checks/patrol/_m_band_relay_selftest_r1.py:{st_line}）。这组里两格是关键：一格负对照——车道→号令者 的过档 order 照旧进分母，装完不许把尺弄瞎；一格是「该红的那一次」——把旧谓词在同一份合成账上真跑一遍，必须比新写法多数出那两枚，否则这条口径等于没在管事。

没装的那条，原因实测不省事：「被写盘门拒的车道块算 deliver 类堆积」已经在 F 档数着了（door_backlog 吐门拒枚数与闸拒枚数，且 F 属 actionable，到档就叫人）。同一件事在两档各报一次＝双报警——昨夜我数过那一格的未取分子，一半以上是哨兵自己投出去的回声，那一课就摆在这儿。要并档还是各管一头，请号令者或副号令者裁一句，裁到我我就动。

现场一条：本班三档值守脚本已按 STOP 到点自退，此刻哨兵不在跑（BB 机中枢与工地板都还在，判活读的是各会话自己的流水），所以这条改动从下一班起口才生效；我没有为了让它「现在就生效」去手起第二支。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
"""
    txt = body.format(**A)
    outp = os.path.join(INBOX, u"42d1a6fa_%s.md" % time.strftime("%H%M"))
    io.open(outp, u"w", encoding="utf-8", newline=chr(10)).write(txt)
    print(u"块已写：%s｜%d 字节" % (outp, os.path.getsize(outp)))
    rc2, o2 = sh([PYEXE, GATE, u"--text", outp, u"--expect-clean"], LIVE, timeout=600)
    tail = o2.strip().splitlines()[-3:] if o2.strip() else []
    print(u"入账门 rc=%d｜%s" % (rc2, u" ⏎ ".join(x[:170] for x in tail)))
    if rc2 != 0:
        os.rename(outp, outp + u".my_superseded_gate_red_%s" % time.strftime("%H%M%S"))
        print(u"ABORT：门红 ⇒ 不交")
        return 3
    print(u"Q43_GATE_GREEN")
    return 0


if __name__ == u"__main__":
    sys.exit(main())
