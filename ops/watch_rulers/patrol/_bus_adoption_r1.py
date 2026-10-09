# -*- coding: utf-8 -*-
"""BB 机「接入实证」：把三条腿谁真在用数出来，给一封信当出处用。

为什么单独有这么一个取数口（10-04 18:4x）：号令者裁「推广要数对面真跑命令的次数，
不是数我发过邀请」。同理，说一条腿可用也得看**它有没有被别人写过**，不能只看我发得出去。
所以这里同时数两件：账上按发件人前缀的分布（谁真投过）、outbox 里非本机账号的留痕
（投递有没有落到它们的目录）。只读，不改账。

形制沿用今天那两条腿：--snap 现取并钉一份快照；--reprint 原样吐那份快照（给中枢当出处）。
"""
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BUS = u"D:/moodle/agent_bus"
SNAP = os.path.join(HERE, u"_bus_adoption_snap.txt")
MODE = u"read"
for a in sys.argv[1:]:
    if a.startswith("--snap"):
        MODE = u"snap"
    elif a.startswith("--reprint"):
        MODE = u"reprint"
NL = chr(10)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if MODE == u"reprint":
    if not os.path.exists(SNAP):
        sys.stdout.write(u"NO_SNAPSHOT_YET" + NL)
        sys.exit(3)
    sys.stdout.write(io.open(SNAP, encoding="utf-8").read())
    sys.exit(0)

import collections
rows = []
for l in io.open(os.path.join(BUS, "bus.jsonl"), encoding="utf-8", errors="replace"):
    l = l.strip()
    if l:
        rows.append(json.loads(l))
by = collections.Counter(str(m.get("from")).split(":")[0] for m in rows)
non = [m for m in rows if str(m.get("from")).split(":")[0] in ("codex", "file", "human")]
out = [u"read_at=%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
       u"total_msgs=%d" % len(rows),
       u"qoder_from=%d" % by.get("qoder", 0),
       u"non_qoder_from=%d" % len(non),
       u"codex_from=%d" % by.get("codex", 0),
       u"file_from=%d" % by.get("file", 0),
       u"human_from=%d" % by.get("human", 0)]
obd = os.path.join(BUS, "outbox")
if os.path.isdir(obd):
    for d in sorted(os.listdir(obd)):
        if not d.startswith("qoder_") and os.path.isdir(os.path.join(obd, d)):
            out.append(u"outbox_nonlocal_%s=%d" % (d, len(os.listdir(os.path.join(obd, d)))))
text = NL.join(out) + NL
if MODE == u"snap":
    io.open(SNAP, "w", encoding="utf-8", newline=NL).write(text)
sys.stdout.write(text)
