# -*- coding: utf-8 -*-
"""现读 BB 机账，把某一收件人的未取积压按 kind 分组打出来。

为什么要有它：值守要给号令者压一封「先做哪几条」的摘要，摘要里的数必须现取，
不能从我上一轮的对话里抄——账每几分钟就在动（04 日 01:5x 实测：十几分钟内未取从十九涨到二十六）。

三种形制（**取数与送闸必须同形，否则正文与证据差一分钟**）：
  --who <id>            只现读、打印，不留快照（平时自己看）
  --snap                现读 + 把这份输出钉进 _bb_backlog_snap.txt，打印的就是快照
  --reprint             只 cat 那份快照，不重新读账 ⇒ 给中枢当「取数命令」用。
                        快照里带了真读的时刻，所以「这条命令跑出这串数」仍然成立：
                        它就是那次真读的原样字节，不是我手打的。
"""
import io
import json
import os
import sys
import time

BUS = u"D:/moodle/agent_bus"   # 用正斜杠：反斜杠+a 会被写成 BEL（同一个坑第三次咬人）
SNAP = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol/_bb_backlog_snap.txt"
MODE = u"read"
for a in sys.argv[1:]:
    if a.startswith("--snap"):
        MODE = "snap"
    elif a.startswith("--reprint"):
        MODE = "reprint"
WHO = u"qoder:494abfd7"
for i, a in enumerate(sys.argv[1:]):
    if a == "--who" and len(sys.argv) > i + 2:
        WHO = sys.argv[i + 2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if MODE == "reprint":
    if not os.path.exists(SNAP):
        sys.stdout.write(u"NO_SNAPSHOT_YET\n")
        sys.exit(3)
    sys.stdout.write(io.open(SNAP, encoding="utf-8").read())
    sys.exit(0)

rows = [json.loads(l) for l in io.open(os.path.join(BUS, "bus.jsonl"), encoding="utf-8", errors="replace") if l.strip()]
acks = json.load(io.open(os.path.join(BUS, "state.json"), encoding="utf-8")).get("acks", {})
now = time.time()
out = [u"read_at=%s recipient=%s" % (time.strftime("%Y-%m-%d %H:%M:%S"), WHO)]
pend = [m for m in rows if str(m.get("to")) == WHO and not (m.get("delivered_at") or acks.get(m.get("id")))]
out.append("total=%d" % len(pend))
by = {}
for m in pend:
    by.setdefault(m.get("kind"), []).append(m)
for k in sorted(by, key=lambda x: -len(by[x])):
    v = by[k]
    old = max((now - float(m.get("ts", now))) / 60.0 for m in v)
    out.append("  kind=%-8s n=%2d oldest_min=%4d topics=%s"
               % (k, len(v), old, u"、".join(str(m.get("topic"))[:26] for m in v[:4])))
text = u"\n".join(out) + u"\n"
sys.stdout.write(text)
if MODE == "snap":
    io.open(SNAP, "w", encoding="utf-8", newline="\n").write(text)
    sys.stderr.write(u"[snap 已落 %s]\n" % SNAP)
