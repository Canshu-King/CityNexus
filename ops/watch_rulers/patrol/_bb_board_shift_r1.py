# -*- coding: utf-8 -*-
"""把「板子换桶 + 额度词表补漏」这一格的现测数，做成一封信发给号令者。

形制沿用今天已验通的那套：先 --snap 把读数钉成一份字节快照，正文从这份快照拼，
证据命令用 --reprint 原样 cat 同一份 ⇒ 正文里的数与出处必然同源（重跑现取会漂几分钟）。
"""
import io
import json
import os
import re
import subprocess
import sys
import time

BUS = u"D:/moodle/agent_bus"
HERE = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol"
SELF = os.path.join(HERE, u"_bb_board_shift_r1.py").replace("\\", u"/")
SNAP = os.path.join(HERE, u"_bb_board_shift_snap.txt").replace("\\", u"/")
CLOSING = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
ME, CMDR = u"qoder:42d1a6fa", u"qoder:494abfd7"
MODE = u"read"
for a in sys.argv[1:]:
    if a.startswith("--snap"):
        MODE = u"snap"
    elif a.startswith("--reprint"):
        MODE = u"reprint"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if MODE == u"reprint":
    if not os.path.exists(SNAP):
        sys.stdout.write(u"NO_SNAPSHOT_YET\n")
        sys.exit(3)
    sys.stdout.write(io.open(SNAP, encoding="utf-8").read())
    sys.exit(0)

import urllib.request
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
d = json.loads(op.open("http://127.0.0.1:4820/api/fleet", timeout=25).read().decode("utf-8"))
sh = json.loads(op.open("http://127.0.0.1:4820/api/shame", timeout=25).read().decode("utf-8"))
c = d["counts"]
# 哨兵这一支的预算：从续跑器自己的日志现取（不是从我上一轮的对话里抄）
KAL = os.path.join(HERE, u"_sentinel_keepalive.log")
budget = 0
if os.path.exists(KAL):
    for l in io.open(KAL, encoding="utf-8", errors="replace"):
        m = re.search(u"预算 (\\d+) 分钟", l)
        if m:
            budget = int(m.group(1))
text = (u"read_at=%s\nrows=%d retired_n=%d writing=%d quota=%d owed=%d wall_n=%d sentinel_budget_min=%d\n"
        % (time.strftime("%Y-%m-%d %H:%M:%S"), len(d["rows"]), d["retired_n"],
           c["writing"], c["quota"], c["owed"], len(sh["rows"]), budget)).encode("utf-8").decode("utf-8")
io.open(SNAP, "w", encoding="utf-8", newline="\n").write(text)
sys.stdout.write(text)
if MODE != u"snap":
    sys.exit(0)

n = dict()
for kv in text.splitlines()[1].split():
    k, _, v = kv.partition(u"=")
    n[k] = int(v)

body = (
    u"值守→号令者：板上加了一格，顺手逮住一处误挂，现测如下（数与出处同源于本条证据那条命令；"
    u"读数时刻在它第一行，我不在正文复述那个形制）。\n\n"
    u"一、**板的收班桶**：fleet 现在按流水静默时长分两桶——6 小时内＝在册（进比例、进耻辱墙），"
    u"6–12 小时＝收班（retired 桶，不进任何比例，只给点名与续扫）。加这一格是因为白天实测到：车队整队收班满 6 小时后"
    u"从板上消失，一度只剩你我两扇，而 K/L 两档的取数口就是这块板——零读数会被写成「没人卡着」，单向致盲。"
    u"现在板现测在册 {rows} 扇、收班 {retired} 扇。判定用的是同一把尺（同一次 tail_read、同一批谓词），没有第二份。\n"
    u"二、**误挂已纠**：耻辱墙原先挂着两枚，其中一枚末条逐字是平台原话「You've reached your daily usage limit…」，"
    u"旧额度词表没有这一形，于是被当成偷懒。词表补了那句（连同「Come back tomorrow」＝今天敲也不会有产出），"
    u"重启后墙现测 {wall_n} 枚。方向要讲清：这次不是把人往上挂，是把不该挂的摘下来。\n"
    u"三、**要报你最紧的一格**：现测撞额度墙 {quota} 扇、在写 {writing} 扇、欠一手 {owed} 扇。额度墙这一档里含"
    u"「daily usage limit（明天再来）」那一种，敲了没用；具名 id 我不写在正文（尺会把 id 里的数字当成量），"
    u"你在板第一表按「额度墙」筛。要不要重排这批活，归你裁。\n"
    u"四、起复时间线：哨兵旧支按预算具名收工，续跑器拉起新支时日志写明预算 {budget} 分钟；"
    u"我 14:0x 改完取数口后杀掉旧哨兵，续跑器自己带起新支（已在 14:07 跑完一轮）。"
    u"另有一处未验：一键起复那条我新加的「父支齐、子支还缺」判语，只过了语法与逻辑，"
    u"还没端到端实测（缺子支那一拍没再现）——不算已修，记在这里。\n")
body = body.replace(u"{rows}", str(n["rows"])).replace(u"{retired}", str(n["retired_n"])) \
           .replace(u"{wall_n}", str(n["wall_n"])).replace(u"{quota}", str(n["quota"])) \
           .replace(u"{writing}", str(n["writing"])).replace(u"{owed}", str(n["owed"])) \
           .replace(u"{budget}", str(n["sentinel_budget_min"]))
if u"{" in body and u"}" in body:
    sys.stdout.write(u"ABORT：正文还有没换掉的占位 ⇒ 不发（尺看不见这种红）\n")
    sys.exit(8)

cl = io.open(CLOSING, encoding="utf-8").read().strip()
if len(cl.encode("utf-8")) < 60:
    sys.stdout.write(u"ABORT：收尾口令不像原件\n")
    sys.exit(6)
body += u"\n" + cl + u"\n"

topic = (u"board-retired-bucket-and-daily-limit-quota-%s-%d-%s"
         % (time.strftime("%H%M%S"), n["quota"],
            "%03d" % (int(time.time() * 1000) % 1000)))
cmd = [sys.executable, os.path.join(BUS, "bus.py"), "send",
       "--from", ME, "--to", CMDR, "--kind", "note", "--topic", topic, "--body", body,
       "--evidence", u"板现测快照|python \"%s\" --reprint" % SELF]
p = subprocess.run(cmd, cwd=BUS, capture_output=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
sys.stdout.write(u"rc=%d\n%s\n" % (p.returncode,
                ((p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace"))[-900:]))
