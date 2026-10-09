# -*- coding: utf-8 -*-
"""车道任务对账表（用户原话：检查工人工作要**读取他们的任务**）。

注意 `账本最后同现行` 一列**不等于**"当前派单"：它只是账本里最后一枚同时含该 id 与 `ORD-` 的行（派单行、交件行、
状态行都可能命中）。要读**真任务**请配合 `relay/relay_*.txt` 与总线 5879549046 的待裁队列，别只看这一列下结论。

每行一条车道：它最近被派的那张单（账本里 `ORD-#### → <id8>` 或 `（车道 `id8`）` 的行）、
块在账本第几行、它自己最近一次入账的块、最后落盘时间、以及**是否停在待裁**。
只读：账本 + `_processed` 文件名 + 会话流水 mtime。
"""
import glob
import io
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LANES = {
    "3b65af59": "map", "1d64acf5": "S4", "904a042d": "Q", "e4f3490f": "道0370", "a68b0631": "rel",
    "49fe0d7b": "N3", "2d2d7428": "0388/0389", "8e5245f0": "道0369", "9759f1ac": "N2",
    "bac10f40": "AI", "be19052c": "道tokens", "4033270f": "道0383", "a6b95d59": "DSH",
    "8ac89982": "R-0417", "9cc37e57": "0421/0426", "9cc37e57x": "",
}
PREFIXES = {"map": "map", "S4": "s4", "Q": "q", "道0370": "道0370", "rel": "rel", "N3": "n3",
            "0388/0389": "qoder-04", "道0369": "8e5245f0", "N2": "n2", "AI": "ai",
            "道tokens": "dt", "道0383": "qoder-0383", "DSH": "dsh", "R-0417": "R_", "0421/0426": "qoder-04"}
now = time.time()
lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
ins = glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*"))


def last_block(pref):
    best, bt = None, 0
    for p in ins:
        n = os.path.basename(p)
        if n.startswith(pref + "_") or (pref.endswith("-04") and n.startswith("qoder-04")):
            if os.path.getmtime(p) > bt:
                best, bt = n, os.path.getmtime(p)
    return best, (round((now - bt) / 60.0, 1) if bt else None)


def last_dispatch(id8):
    hits = [(i + 1, l.strip()) for i, l in enumerate(lines)
            if id8 in l and re.search(r"ORD-\d{4}", l)]
    return hits[-1] if hits else None


print("%-11s %-8s %-11s %-26s %-9s %s" % (u"车道", "id8", u"账本最后同现行", u"最近入账块", u"块龄(分)", u"最后落盘(分)"))
for id8, nm in sorted(LANES.items(), key=lambda kv: kv[1]):
    if not id8 or len(id8) != 8:
        continue
    d = last_dispatch(id8)
    pref = None
    for k, v in PREFIXES.items():
        if v and nm.startswith(k):
            pref = v
    blk, age = last_block(pref or nm)
    g = glob.glob(os.path.join(BASE, id8 + "*.jsonl"))
    idle = round((now - max([os.path.getmtime(p) for p in g])) / 60.0, 1) if g else None
    ordno = ""
    if d:
        m = re.findall(r"ORD-\d{4}", d[1])
        ordno = ",".join(sorted(set(m))[:3])
    print("%-11s %-8s %-11s %-26s %-9s %-9s %s"
          % (nm, id8, (":%d %s" % (d[0], ordno)) if d else "—", (blk or "—")[:26],
             age if age is not None else "—", idle if idle is not None else "—",
             "停在待裁？" if d and "ORD-0428" in ordno else ""))
