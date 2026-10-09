# -*- coding: utf-8 -*-
"""把「一车一单」那种批量派单行拆开逐张对账——旧件 `open_orders_r1.py` 只认「同一行里出现 ORD 与 8 位 id」，
号令者 18:04 那块把十四张写在**一行**里（`长图多天导出排版 ORD-0501（e766b154）· …`），于是旧件只报出 1 张，
剩下 13 张要么被我误判成「无主单」，要么看不出谁接了。这一件按 `ORD-####（收件人）` 成对正则逐张抽出来。

只读。收件人既认 8 位会话 id（从 jsonl 文件名验存在，不猜），也认花名（phone 车道 / rel 车道 这种非 id 写法照原样列出并标「没给 id」）。
每张给：收件人、这刻流水尾记录与静默分钟、这张单的证据（收件口块名/`review/*` 枝名/账本更晚块头里提到它）。
判语只有两种：`已接`（有任一处证据）/ `没找到证据`（这时才谈得上敲，且我只在号令者那行逐字点名它的收件人时才转达）。
"""
import glob
import io
import json
import os
import re
import sys
import time

BASE = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
REPO = r"D:\moodle\CityNexus"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import quota_now as Q

PAIR = re.compile(u"ORD-(0\\d{3})（([^）]{2,40})）")
led = io.open(LEDGER, encoding="utf-8", errors="replace").read()
# 只看 ORDERS 起前 6000 行（新件都在这带），免得把历史里同一单号的旧话也算进来
i0 = next((i for i, l in enumerate(led.split("\n")) if l.startswith(u"## ORDERS")), 0)
region = "\n".join(led.split("\n")[i0:i0 + 6000])

pairs = {}
for m in PAIR.finditer(region):
    ordn, who = "ORD-" + m.group(1), m.group(2).strip()
    ids = re.findall(r"[0-9a-f]{8}", who)
    pairs.setdefault(ordn, set()).add((who, ids[0] if ids else ""))
# 也收 `（车道 1ba48dbf）`／`（`da46954a` 那枝）` 这类：ORD 后不紧邻括号但同行成对的
for m in re.finditer(u"ORD-(0\\d{3})[^\\n]{0,40}?（[^）]{0,12}?(?:车道|会话) ?([0-9a-f]{8})[^）]{0,12}）", region):
    pairs.setdefault("ORD-" + m.group(1), set()).add((u"车道 " + m.group(2), m.group(2)))

import subprocess
branches = subprocess.run(["git", "-C", REPO, "ls-remote", "--heads", "origin"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240).stdout
inbox_files = [f for f in os.listdir(INBOX) if f.endswith(".md")]
processed = os.listdir(os.path.join(INBOX, "_processed"))


def tail_state(id8):
    hs = glob.glob(os.path.join(BASE, id8 + "*.jsonl"))
    if not id8 or not hs:
        return u"没有这枚流水文件", -1.0
    p = max(hs, key=os.path.getmtime)
    kinds = u"?"
    sz = os.path.getsize(p)
    with io.open(p, "rb") as f:
        f.seek(max(0, sz - 262144))
        blob = f.read().decode("utf-8", "replace")
    for rec in blob.split("\n"):
        rec = rec.strip()
        if not rec:
            continue
        try:
            d = json.loads(rec)
        except Exception:
            continue
        m = d.get("message") or {}
        c = m.get("content")
        if isinstance(c, str) and c.strip():
            kinds = u"text"
        elif isinstance(c, list):
            ks = [b.get("type") for b in c if isinstance(b, dict) and b.get("type")]
            if ks:
                kinds = u",".join(ks)
    return kinds, (time.time() - os.path.getmtime(p)) / 60.0


print("=== 批量派单行拆开对账（区域：ORDERS 起 6000 行；成对形制 `ORD-####（收件人）`）===")
rows = []
for ordn in sorted(pairs):
    for who, id8 in sorted(pairs[ordn]):
        ev = []
        short = ordn.replace("ORD-0", "ord0").replace("ORD-", "ord").lstrip("0")
        cand = ["ord" + ordn.split("-")[1].lstrip("0"), ordn.lower(), ordn]
        for f in inbox_files + processed:
            if any(c.replace("ORD-0", "ord0").lower() in f.lower() for c in cand) or (id8 and id8 in f):
                ev.append(u"收件口")
                break
        if any(re.search(r"ord-?0*%s" % ordn.split("-")[1].lstrip("0"), b, re.I) for b in branches.split("\n")):
            ev.append(u"枝名")
        if led.count(ordn) > 1:
            ev.append(u"账本多枚提及(%d)" % led.count(ordn))
        kinds, idle = tail_state(id8)
        rows.append((ordn, who, id8, kinds, idle, u"、".join(ev) or u"没找到证据"))

for ordn, who, id8, kinds, idle, ev in rows:
    flag = u"  ⟵ 没有证据" if ev == u"没找到证据" else u""
    print("  %-9s 收件 %-28s id %-9s 尾记录 %-11s 静默 %6s 分｜证据 %s%s" % (
        ordn, who[:28], id8 or u"(没给 id)", kinds, ("%.0f" % idle) if idle >= 0 else u"?", ev, flag))
# 机读件：格式化那几行是给人看的，别拿它当解析面（我 18:20 那条帖的草稿就是栽在按空格数正则上）
TSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dispatch_pairs_last.tsv")
io.open(TSV, "w", encoding="utf-8", newline=chr(10)).write(
    chr(10).join(chr(9).join(str(c) for c in x) for x in rows) + chr(10))
print("机读件：%s（%d 行；列：单号/收件原文/8位id/尾记录/静默分/证据）" % (os.path.basename(TSV), len(rows)))
print()
noid = [r for r in rows if not r[2]]
print("小结合成对读到 %d 张：其中收件人没给会话 id 的 %d 张（花名派单，我按规矩不猜人）；"
      "名下没找到证据的 %d 张。" % (len(rows), len(noid), len([r for r in rows if r[5] == u"没找到证据"])))
print("边界：证据三处（收件口块名/枝名/账本提及）任一命中只说明**有据可查**，不等于验收通过；也不说明它就是这张单的交付。")
