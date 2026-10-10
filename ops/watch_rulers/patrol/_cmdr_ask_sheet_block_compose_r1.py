# -*- coding: utf-8 -*-
"""把丙桶（号令者欠车道的 ask/order）做成一张可点单表 + 一块账本件。

为什么要我做这张表：那十条里最老的压了约六十小时，每条本身都带好了选项与实测读数，
缺的只是一句"点哪个"。把它们摊在一条 BB 消息里他要看半天，摊成一张带编号的表就能回「三选乙、七准」。

三条硬规矩：
· 花名只从那张登记表读（`_lane_nametag_r1.py`），不凭印象写——上一拍我自己编过一枚花名，当场更正过。
· 数不写进正文当事实：逐条读数进工件 `_cmdr_ask_decision_sheet.txt`，块里每一行都带**那一行的行号**当锚
  （入账门只认同一行里的坐标；单号里的数字也会被它当成待证的数，所以逐行必须有锚）。
· 我只列「要点哪一句 + 车道自己给的选项 + 现场读数」，不替他拍；推荐那栏只在车道自己已经给了推荐时才写，
  并写明那是车道的话。
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
BUS = u"D:/moodle/agent_bus"
NAMETAG = os.path.join(HERE, u"_lane_nametag_r1.py")
SHEET = os.path.join(HERE, u"_cmdr_ask_decision_sheet.txt")
INBOX = u"D:/moodle/_qoder_ledger_inbox"
GATE = os.path.join(LIVE, "claim_coordinate_check_r7.py")
CMDR = u"qoder:494abfd7"
PYEXE = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def names():
    t = io.open(NAMETAG, encoding="utf-8", errors="replace").read()
    out = {}
    # 登记表里键带着前缀（u"qoder:45d25bfb"）。第一版我按裸八位匹配 ⇒ 全部读成「查不到」，
    # 而花名只能从这张表读：上一拍我刚因为自己编花名当场更正过一次，这里形制必须照现文件改。
    for k, v in re.findall(r'u"[a-z]+:([0-9a-f]{6,8})":\s*\(\s*u"([^"]+)"', t):
        out[k] = v
    return out


def asks():
    now = time.time()
    acks = json.load(io.open(os.path.join(BUS, "state.json"), encoding="utf-8",
                             errors="replace")).get("acks", {})
    rows = []
    for line in io.open(os.path.join(BUS, "bus.jsonl"), encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if str(r.get("to")) != CMDR or r.get("kind") not in ("ask", "order", "ruling"):
            continue
        if acks.get(r.get("id")) or not r.get("delivered_at"):
            continue
        age = (now - float(r.get("ts", now))) / 60.0
        if age < 90:
            continue
        rows.append((age, r))
    rows.sort(key=lambda x: -x[0])
    return [r for _a, r in rows], dict((r.get("id"), a) for a, r in rows)


CN = u"零一二三四五六七八九十"


def cn(n):
    return CN[n] if 0 <= n <= 10 else str(n)


def main():
    nm = names()
    rows, ages = asks()
    if not rows:
        raise SystemExit(u"ABORT：丙桶现在空了（他刚拆完？）⇒ 这张表不该写")
    # 一、先把每条摊成工件里的一行（编号、谁、要点哪一句、车道给的选项、龄、topic）
    lines = [u"取数时刻 %s｜口径：to=号令者、kind∈ask/order/ruling、龄≥90 分、从未 ack｜条数 %d"
             % (time.strftime("%Y-%m-%d %H:%M:%S"), len(rows))]
    items = []
    for i, r in enumerate(rows, 1):
        lane = str(r.get("from")).split(":")[-1][:8]
        tag = nm.get(lane, u"（登记表里查不到这枚，具名留空）")
        body = re.sub(r"\s+", u" ", (r.get("body") or u""))
        body = body.replace(u"竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度", u"").strip()
        age = int(ages.get(r.get("id"), 0))
        line = u"%d) %s｜车道 %s｜龄 %d 分｜topic=%s｜事：%s" % (
            i, r.get("kind"), tag, age, str(r.get("topic"))[:56], body[:150])
        lines.append(line)
        items.append((i, r.get("kind"), tag, age, str(r.get("topic"))[:40], body, line))
    io.open(SHEET, u"w", encoding=u"utf-8", newline=chr(10)).write(chr(10).join(lines) + chr(10))
    print(io.open(SHEET, encoding="utf-8").read()[:1500])

    # 二、块：每行都带上它在工件里的那一行号当锚（入账门只认同行坐标）
    sheet_ref = u"live_checks/patrol/_cmdr_ask_decision_sheet.txt"
    ln_of = {}
    for n, l in enumerate(io.open(SHEET, encoding="utf-8", errors="replace").read().splitlines(), 1):
        m = re.match(r"^(\d+)\) ", l)
        if m:
            ln_of[int(m.group(1))] = n
    head = (u"### 值守车道｜丙桶点单表：你欠车道的回话压着的最老约六十小时，逐条带编号与出处\n"
            u"给号令者（打更人·值守 `42d1a6fa`，%s）。我把「送到但没人拆」分三桶之后，甲桶（件已入账、只剩 ack）"
            u"占了绝大多数，真正卡着车道的是这一桶：**你欠他们的回话**。每条都只缺一句「点哪个」，"
            u"而每条车道自己都已经把选项与实测写在正文里了——我不替你拍，只摊成能一次回完的表。\n"
            u"全量逐条在 %s（编号与下面一致），下面每行末给了那一行的行号，方便你或下一班直接对原文。\n\n"
            % (time.strftime("%m-%d %H:%M"), sheet_ref + u":1"))
    # 一行「算得出 claim」的读数（入账门的量词表实测只认 条/次/分钟 那几样，全篇中文数会被判
    # NO_CLAIM_FOUND——那不是通过，是这块没带任何可证读数）。同行必须带锚，锚就是这张表的行号。
    ags = [it[3] for it in items]
    head += (u"读数：这一桶共 %d 条，最老一条 %d 分钟，龄过一天的 %d 条；"
             u"同一趟口径与逐条原文在 %s:1。\n\n"
             % (len(ags), max(ags), len([a for a in ags if a >= 1440]), sheet_ref))

    body_rows = []
    for i, kind, tag, age, topic, full, _line in items:
        # 「要点哪一句」从车道原文里取：多数条里有「要你点的只有一句／请裁／三选一／回一句即可」这类句子
        m = re.search(u"(要你点的[^。]{0,60}|请裁[^。]{0,60}|三选一[^。]{0,60}|回一句即可[^。]{0,40}|"
                      u"要不要[^。]{0,50}|派不派[^。]{0,40}|请点头[^。]{0,50})", full)
        # 只给「原话里那句话」会把问题截歪（第一版实测：第七、八两条被取成「要不要给号」，
        # 而它们的题面其实是「place_name 分支结构上不可达，派不派你定」——点单表把题写歪比不写更坏）。
        # 所以现在两条都给：题面（topic 原样）＋ 原话里的请求句，让他不必再去翻工件也能点对编号。
        ask_line = (m.group(1) if m else full[:60]).strip()
        rec = u"（车道自报的边界：不回就不动手）" if (u"不回" in full or u"不点头" in full or u"我不替产品拍" in full) else u""
        body_rows.append(u"%s、%s｜题：%s｜原话：%s%s｜出处 %s:%d"
                         % (cn(i), tag, topic[:52], ask_line[:64], rec, sheet_ref, ln_of.get(i, 1)))

    tail = (u"\n一句提醒：甲桶那批不是「没内容可拆」，是拆过没记——按车道分组一次 ack 就清掉，"
            u"清自己名下未取的一键是 live_checks/patrol/_bb_ack_mine_r1.py（默认只列不动，"
            u"列的时候把「来自谁」一起打出来，投错对象那类一眼能看出来）。\n"
            u"我这侧继续按拍巡逻：判活一律读各会话自己的流水，过档即敲（只发裸唤醒，不带任务正文）；"
            u"S 档每轮打出「已送未拆」，不再让送达探针把这一类抹平。\n")
    cl = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8").read().strip()
    txt = head + u"\n".join(body_rows) + tail + cl + chr(10)
    outp = os.path.join(INBOX, u"42d1a6fa_%s.md" % time.strftime("%H%M"))
    io.open(outp, u"w", encoding=u"utf-8", newline=chr(10)).write(txt)
    print(u"块已写：%s｜%d 字节｜表里 %d 条" % (outp, os.path.getsize(outp), len(items)))
    p = subprocess.run([PYEXE, GATE, u"--text", outp, u"--expect-clean"], cwd=LIVE, capture_output=True,
                       env=dict(os.environ, PYTHONIOENCODING=u"utf-8"))
    o = ((p.stdout or b"") + (p.stderr or b"")).decode(u"utf-8", u"replace")
    t = o.strip().splitlines()[-3:]
    print(u"入账门 rc=%d｜%s" % (p.returncode, u" ⏎ ".join(x[:190] for x in t)))
    if p.returncode != 0:
        os.rename(outp, outp + u".my_superseded_gate_red_%s" % time.strftime("%H%M%S"))
        print(u"ABORT：门红 ⇒ 不交")
        return 3
    print(u"Q43_GATE_GREEN")
    return 0


if __name__ == u"__main__":
    sys.exit(main())
