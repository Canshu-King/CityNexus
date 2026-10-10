# -*- coding: utf-8 -*-
"""谁的手上还有一张没交完的单？——把账本里的派单行与三处收口证据对账。

派单：账本里 `ORD-####` 与某条车道的会话 id（前 8 位）或花名**同现**的行（号令者 09-28 起按会话 id 点名）。
收口证据三处，任一命中即算"有交代"（**注意：这只说明有据可查，不等于验收通过**）：
  ① `_processed` 里该车道的块正文提到这张单（交件块）；
  ② `refs/heads/review/*` 枝名里带这张单的号（`ord04xx`）；
  ③ 账本里更晚的块头（按块头自报时间）把这张单配上状态词（ACCEPTED/DELIVERED/PARTIAL/退回/收了/已交）。
判语只有两种：`有据` / `没找到收口证据`——后者才是要去敲的。
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
REPO = r"D:\moodle\CityNexus"
LANES = {
    "3b65af59": "map", "1d64acf5": "S4", "904a042d": "Q", "e4f3490f": "道0370", "a68b0631": "rel",
    "49fe0d7b": "N3", "2d2d7428": "0388", "8e5245f0": "道0369", "9759f1ac": "N2",
    "bac10f40": "AI", "be19052c": "道tokens", "4033270f": "道0383", "a6b95d59": "DSH",
    "8ac89982": "R0417", "9cc37e57": "0421", "6efab655": "号令者实例A", "494abfd7": "号令者",
}
STATUS = re.compile(u"ACCEPTED|DELIVERED|PARTIAL|REJECTED|CLOSED|已交|收了|已落地|退回|判 ")
from_s = sys.argv[1] if len(sys.argv) > 1 else "425"   # 只看这一段号（ORD-0425 起）
lo = int(from_s)

text = io.open(LEDGER, encoding="utf-8", errors="replace").read()
lines = text.split("\n")

# 1) 派单：ORD 与车道同现的行
disp = {}
for i, l in enumerate(lines):
    for o in re.findall(r"ORD-(0\d{3})", l):
        n = int(o)
        if n < lo or n > lo + 60:
            continue
        ids = [k for k in LANES if k in l and k not in ("494abfd7", "6efab655")]
        # 06:27 修的一眼：号令者一块里那张「ORD-0430…0443 各点名一条车道」的名单行会一次命中 11 个 id，
        # 拿它当派单会把每张单都算成"人人有份"。⇒ 只认**一行里只点一家**的派单（与 wake_from_commits 的收窄同一条规矩）。
        if len(ids) == 1:
            disp.setdefault("ORD-" + o, set()).add(ids[0])

# 2) 块头时间：用来比较"更晚的块"
heads = []
for i, l in enumerate(lines):
    if l.startswith("### "):
        d = re.search(r"2026-(\d\d)-(\d\d)", l)
        t = re.search(r"\b([01]?\d|2[0-3])[:：]([0-5]\d)\b", l)
        if d and t:
            heads.append((i, "%s-%s %02d:%s" % (d.group(1), d.group(2), int(t.group(1)), t.group(2))))

# 3) 三处收口证据
proc = {}
for p in glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*")):
    try:
        body = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    who = os.path.basename(p).split("_")[0]
    for o in re.findall(r"ORD-(0\d{3})", body):
        proc.setdefault("ORD-" + o, set()).add(who)

g = ["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy="]
subprocess.run(g + ["fetch", "--quiet", "origin", "+refs/heads/*:refs/remotes/origin/*"], capture_output=True, timeout=900)
refs = subprocess.run(g + ["for-each-ref", "--format=%(refname:short)\t%(committerdate:unix)",
                           "refs/remotes/origin/review/*"], capture_output=True, text=True,
                      encoding="utf-8", errors="replace", timeout=300).stdout or ""
branch = {}
for line in refs.splitlines():
    name, _, ts = line.partition("\t")
    for o in re.findall(r"ord-?0?(\d{3,4})", name.lower()):
        k = "ORD-0" + o[-3:] if len(o) == 3 else "ORD-" + o
        branch.setdefault(k, []).append((name.replace("origin/review/", ""), ts))

print("号段 ORD-%04d..ORD-%04d｜派单 %d 张" % (lo, lo + 60, len(disp)))
for o in sorted(disp):
    ids = sorted(disp[o])
    who = "、".join("%s(%s)" % (LANES[i], i) for i in ids if i in LANES)
    ev = []
    key = o.replace("ORD-0", "ord0").lower()
    if proc.get(o):
        ev.append("块×%d" % len(proc[o]))
    if branch.get(o):
        ev.append("枝×%d" % len(branch[o]))
    later = 0
    for i, l in enumerate(lines):
        if o in l and STATUS.search(l):
            hm = next((h for k, h in heads if k == i), None)
            later += 1
    if later:
        ev.append("判语×%d" % later)
    idles = []
    for k in ids:
        gg = glob.glob(os.path.join(BASE, k + "*.jsonl"))
        if gg:
            idles.append((LANES[k], round((time.time() - max(os.path.getmtime(x) for x in gg)) / 60.0, 1)))
    idle = "、".join("%s %.0f分" % (n, v) for n, v in idles) or "—"
    verdict = u"有据" if ev else u"没找到收口证据 ⇒ 该敲"
    print(u"  %-10s %-26s idle=%-6s %-16s %s" % (o, who, idle, "、".join(ev) or "—", verdict))
