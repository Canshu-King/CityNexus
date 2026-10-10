# -*- coding: utf-8 -*-
"""总线一帖（15:2x）：账本里挂着的「请裁」按车道收成一行一条，并标出哪几条此刻真的把人卡停。r3（r2 未投即改：它把号令者自己写的二选一也算成"等他裁"，且同一个人同一件事拆成三条）。

判据（可复算，全只读）：
  问句 = 账本 `## ORDERS` 起前 6000 行里，命中这套词面的行；块头以 `cmdr` 开头的**剔出**（那是他自己写的二选一，不是别人等他裁）
  人   = 块头里逐字出现的 8 位会话 id；取不到就归到「块头没写 id」并单列，不猜花名
  状态 = 该会话流水尾记录 kinds 与静默分钟（与自动轮同一把尺）；**静默 > 30 分算「此刻停着」**
限度：**我没有判哪一条其实已经裁过**——那要读上下文，那是裁语本身的活，我不越。我只说「谁在等、等了多久、此刻停不停」。
收尾口令逐字取自 CLOSING_LINE.txt；投后按 id 回读比对。
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.join(LC, "patrol")
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
BASE = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="",
           http_proxy="", https_proxy="")
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import quota_now as Q

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()

ASK = re.compile(u"请裁|求裁|要你裁|等你裁|需要你裁|要你定|得你点头|得由你或用户点头|请裁决|二选一|该不该|一处要我裁|需要裁决")
TOP, STALL = 6000, 30.0
txt = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
start = next((i for i, l in enumerate(txt) if l.startswith(u"## ORDERS")), 0)

head, hline, hits, mine = None, 0, [], 0
for i, l in enumerate(txt[start:start + TOP]):
    line = txt[start + i]
    if line.startswith(u"### "):
        head, hline = line[4:].strip(), start + i + 1
    elif head and ASK.search(line):
        if head.lower().startswith("cmdr"):
            mine += 1          # 他自己写的二选一，不算"别人等他裁"
            continue
        hits.append((head, hline, line.strip()))

by_lane = {}
for head, ln, q in hits:
    ids = re.findall(r"[0-9a-f]{8}", head)
    lane = ids[0] if ids else ""
    e = by_lane.setdefault(lane, {"asks": [], "lines": [], "heads": []})
    e["asks"].append(q)
    e["lines"].append(ln)
    e["heads"].append(head)


def lane_state(id8):
    hs = glob.glob(os.path.join(BASE, id8 + "*.jsonl"))
    if not id8 or not hs:
        return u"?", -1.0, u"?"
    p = max(hs, key=os.path.getmtime)
    size = os.path.getsize(p)
    with io.open(p, "rb") as f:
        if size > 512 * 1024:
            f.seek(size - 512 * 1024)
        blob = f.read().decode("utf-8", "replace")
    kinds, last_text = u"?", ""
    for rec in blob.split(chr(10)):
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
            kinds, last_text = u"text", c
        elif isinstance(c, list):
            ks = [b.get("type") for b in c if isinstance(b, dict) and b.get("type")]
            if ks:
                kinds = u",".join(ks)
            for b in c:
                if isinstance(b, dict) and b.get("type") == u"text" and b.get(u"text", "").strip():
                    last_text = b[u"text"]
    return kinds, (time.time() - os.path.getmtime(p)) / 60.0, (u"是" if u"daily usage limit" in last_text.lower() else u"否")


rows = []
for lane, e in by_lane.items():
    kinds, idle, capped = lane_state(lane)
    newest = e["asks"][e["lines"].index(min(e["lines"]))] if False else e["asks"][-1]
    rows.append({"lane": lane, "name": Q.NAMES.get(lane, ""), "n": len(e["asks"]),
                 "first_line": min(e["lines"]), "kinds": kinds, "idle": idle, "capped": capped,
                 "ask": newest[:230], "head": e["heads"][-1][:80]})
rows.sort(key=lambda r: -r["idle"])
stopped = [r for r in rows if r["idle"] > STALL]
running = [r for r in rows if 0 <= r["idle"] <= STALL]
noid = [r for r in rows if r["idle"] < 0]

S = {
    "when": time.strftime("%H:%M:%S"),
    "n_hits": str(len(hits)), "n_lane": str(len(by_lane)), "mine": str(mine),
    "n_stopped": str(len(stopped)), "n_running": str(len(running)), "n_noid": str(len(noid)),
    "stopped": u"\n".join(u"- `%s`%s｜静默 **%.0f 分**（尾记录 %s，停在额度上：%s）｜这条上提了 %s 次，最早账本第 %s 行\n  最近一次原文：「%s」" % (
        r["lane"], (u"（" + r["name"] + u"）") if r["name"] else u"", r["idle"], r["kinds"], r["capped"],
        str(r["n"]), str(r["first_line"]), r["ask"]) for r in stopped) or u"- （没有：所有提过问的车道此刻都在跑）",
    "running": u"\n".join(u"- `%s`%s｜静默 %.0f 分（尾记录 %s）｜提了 %s 次，最早第 %s 行" % (
        r["lane"], (u"（" + r["name"] + u"）") if r["name"] else u"", r["idle"], r["kinds"],
        str(r["n"]), str(r["first_line"])) for r in running) or u"- 无",
    "noid": (u"%s 处（块头里取不到 8 位 id，我不猜归属；最早在账本第 %s 行）" % (
        str(len(noid)), str(min(r["first_line"] for r in noid))) if noid else u"0 处"),
    "noid_line": u"",
    "region": str(start + 1), "top": str(TOP),
    "rerun": u"%s %s" % (PYEXE, HERE.replace("\\", "/") + "/_pending_rulings_r1.py"),
}
S["noid_line"] = (u"\n另有块头里取不到会话 id 的待裁问句：" + S["noid"]) if noid else u""

TPL = u"""**值守 {when} · 账本里的「请裁」合并成 {n_lane} 条（{n_hits} 处命中；另有 {mine} 处是号令者自己写的二选一，已按块头剔出，没算成别人等他裁）**

这 {n_lane} 条里，**此刻把人真的卡停的（流水静默 > 30 分）只有 {n_stopped} 条**：
{stopped}

剩下 {n_running} 条的提问人**此刻还在跑**（静默 ≤ 30 分），它们不急，但同样会在他下一轮排队时被他自己的实测盖过去：
{running}
{noid_line}

判据（都能复算）：账本 `## ORDERS`（第 {region} 行）起前 {top} 行，正文命中「请裁｜求裁｜要你裁｜等你裁｜需要你裁｜要你定｜得你点头｜得由你或用户点头｜请裁决｜二选一｜该不该｜一处要我裁｜需要裁决」这些词面的行；块头以 `cmdr` 开头的剔出；人＝块头里逐字出现的 8 位会话 id；状态＝那条会话流水尾记录 kinds 与静默分钟。
**限度：我没有判哪一条其实已经裁过**——那要读上下文，那是裁语本身的活，我不越。上面每条都给了账本行号与逐字原文，你裁哪条就按行号取全文，不必再让车道重讲一遍。
- 可重跑（只读；0 写账本、0 代插、0 改车道文件）：`{rerun}`

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1525_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d hits=%s lanes=%s stopped=%s running=%s mine=%s" % (
    len(text.encode("utf-8")), S["n_hits"], S["n_lane"], S["n_stopped"], S["n_running"], S["mine"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
