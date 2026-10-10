# -*- coding: utf-8 -*-
"""总线一帖（15:2x）：账本里挂着的「请裁」清单，逐条标上提问人此刻是停着还是在跑。r2（r1 未投即改：它误把 quota_now.scan 当字典用，那函数回三元组）。

为什么要这一件：裁语入口只有号令者一枝笔，车道不许自己改守卫、不许自己定产品语义 ⇒ 一句埋在正文中段的
「请裁一格」挂一小时，那条车道就整条停一小时。他一轮要亲测十几枚块，最容易被这种**不在派单行里的问句**漏掉。

判据全部现场重算、只读：
  问句 = 账本 `## ORDERS` 起前 6000 行里命中词面的行（词面随帖给出，别人能复算）
  人   = 块头里逐字出现的 8 位会话 id（不从标题猜花名，取不到就写「块头没写 id」）
  状态 = 那条会话流水尾记录的 kinds 与静默分钟（与我另一件 `_lane_tail_r1.py` 同一把尺）
限度：**我没有判哪一条其实已经裁过**——那要读上下文，那正是裁语本身的活。我只摆出「谁在等、等多久、此刻停不停」。
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

ASK = re.compile(u"请裁|求裁|要你裁|等你裁|需要你裁|要你定|得你点头|得由你或用户点头|请裁决|二选一|该不该|一处要你裁")
TOP = 6000
txt = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
start = next((i for i, l in enumerate(txt) if l.startswith(u"## ORDERS")), 0)
region = txt[start:start + TOP]

hits = []
head, hline = None, 0
for i, l in enumerate(region):
    if l.startswith(u"### "):
        head, hline = l[4:].strip(), start + i + 1
    elif head and ASK.search(l):
        hits.append((head, hline, l.strip()))

# 合并同一车道同一问句（r1/r2 各提一遍只能算一条），并记下提过几遍
merged = {}
for head, ln, q in hits:
    ids = re.findall(r"[0-9a-f]{8}", head)
    lane = ids[0] if ids else ""
    key = (lane, q[:70])
    if key in merged:
        e = merged[key]
        merged[key] = {"head": head, "line": min(ln, e["line"]), "q": q, "n": e["n"] + 1}
    else:
        merged[key] = {"head": head, "line": ln, "q": q, "n": 1}


def lane_state(id8):
    """尾记录 kinds + 静默分钟 + 是否停在额度字样上（与 _lane_tail_r1.py 同一判据）。"""
    hs = glob.glob(os.path.join(BASE, id8 + "*.jsonl"))
    if not hs:
        return u"没有这枚流水文件", -1.0, u"?"
    p = max(hs, key=os.path.getmtime)
    size = os.path.getsize(p)
    with io.open(p, "rb") as f:
        if size > 512 * 1024:
            f.seek(size - 512 * 1024)
        blob = f.read().decode("utf-8", "replace")
    kinds, last_text = None, ""
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
            kinds, last_text = "text", c
        elif isinstance(c, list):
            ks = [b.get("type") for b in c if isinstance(b, dict) and b.get("type")]
            if ks:
                kinds = ",".join(ks)
            for b in c:
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                    last_text = b["text"]
    capped = u"是" if u"daily usage limit" in last_text.lower() else u"否"
    return kinds or u"?", (time.time() - os.path.getmtime(p)) / 60.0, capped


items = []
for (lane, _k), e in merged.items():
    kinds, idle, capped = lane_state(lane) if lane else (u"块头没写 id", -1.0, u"?")
    items.append({"idle": idle, "lane": lane, "name": Q.NAMES.get(lane, ""), "kinds": kinds,
                  "capped": capped, "head": e["head"][:92], "line": e["line"], "q": e["q"][:200],
                  "n": e["n"]})
items.sort(key=lambda x: -x["idle"])
shown = items[:14]

S = {
    "when": time.strftime("%H:%M:%S"),
    "n_hits": str(len(hits)), "n_merged": str(len(merged)), "n_shown": str(len(shown)),
    "n_rest": str(max(0, len(merged) - len(shown))),
    "region": str(start + 1), "top": str(TOP),
    "pattern": u"请裁|求裁|要你裁|等你裁|需要你裁|要你定|得你点头|得由你或用户点头|请裁决|二选一|该不该|一处要你裁",
    "items": u"\n".join(
        u"- `%s`%s｜尾记录 %s｜静默 %s 分｜停在额度上：%s｜提过 %s 遍｜账本第 %s 行\n  块头：%s\n  问句：「%s」" % (
            it["lane"] or u"块头没写 id",
            (u"（" + it["name"] + u"）") if it["name"] else u"",
            it["kinds"], ("%.0f" % it["idle"]) if it["idle"] >= 0 else "?", it["capped"],
            str(it["n"]), str(it["line"]), it["head"], it["q"])
        for it in shown),
    "rerun": u"%s %s" % (PYEXE, HERE.replace("\\", "/") + "/_pending_rulings_r1.py"),
}

TPL = u"""**值守 {when} · 账本里挂着的「请裁」合并后 {n_merged} 条（{n_hits} 处命中），逐条标了提问人此刻停不停——停着的那几条就是那条车道整条停着的原因**

判据（可复算）：账本 `## ORDERS`（第 {region} 行）起前 {top} 行，正文命中这套词面的行——
`{pattern}`
人＝块头里逐字出现的 8 位会话 id（不从标题猜花名）；状态＝该会话流水尾记录 kinds 与静默分钟（与自动轮同一把尺）。
**限度说在前面：我没有判哪一条其实已经裁过**——那要读上下文，那正是裁语本身的活，我不越。我只摆出「谁在等、等多久、此刻停不停」。

{items}

（按静默分钟从长到短排，列前 {n_shown} 条，另有 {n_rest} 条在更早的块里。）
- 可重跑（只读；0 写账本、0 代插、0 改车道文件）：`{rerun}`

""".format(**S)

text = TPL + CLOSING + u"\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字口令，拒投"
out = os.path.join(HERE, "_bus_1520_body.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("bytes=%d hits=%s merged=%s" % (len(text.encode("utf-8")), S["n_hits"], S["n_merged"]))
if "--dry" in sys.argv:
    print(text)
else:
    print(subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout)
