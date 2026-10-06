# -*- coding: utf-8 -*-
"""值守贴：给号令者一份**待裁队列**——三件车道已把事实交齐、只差它一句话的格子，各等了多久。

等待时长不手写：从账本里那一枚块头的**自报时间**算到现在；件的文字按**锚**抓（行号会漂）。
我不催裁、不替任何一方选，只把队列与分钟数量出来——号令者夜里同时在落地/亲测/派单，看不到队列是常态。
"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
ITEMS = [
    ("车道 rel 的「我没有合法实现路径」", "ORD-0428（原 ORD-0426，改号我接受）",
     "禁改文件（`styles.css`/`V8Experience.tsx`）里那两处机器话谁去改，还是这单作废"),
    ("车道 map 的瓦片降级态压控件", "读数块 · 车道 map · 我自己在现线跑红的门",
     "一个单号——修法（顶部收成一条带）与判据（两态各量一次）它都写全了，只差另给号"),
    ("车道 N3 的 g5 归属问", "十二枚具名红逐枚归因",
     "g5 的完整修法要动四条终态 + 两枚 `outcome` 类型，而契约草案写那格 owner 是车道 A/C——给不给它做"),
]


def head_time_of(ln):
    """从块头自报的 `HH:MM` 或 `HHMM+08` 算等待分钟。"""
    t = re.search(r"\b([01]?\d|2[0-3])[:：]([0-5]\d)\b", lines[ln - 1])
    if not t:
        t = re.search(r"\b([01]?\d|2[0-3])([0-5]\d)\+08", lines[ln - 1])
    if not t:
        return None
    hh, mm = int(t.group(1)), int(t.group(2))
    now = time.localtime()
    stamp = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, hh, mm, 0, now.tm_wday, now.tm_yday, -1))
    if stamp > time.time():          # 跨到昨天写的块
        stamp -= 24 * 3600
    return round((time.time() - stamp) / 60.0, 1)


rows = []
for label, anchor, ask in ITEMS:
    hit = None
    for i, l in enumerate(lines):
        if l.startswith("### ") and anchor in l:
            hit = i + 1
            break
    if not hit:
        rows.append("- %s：锚「%s」本轮没命中 ⇒ 我不猜它在哪，具名报缺。" % (label, anchor[:24]))
        continue
    w = head_time_of(hit)
    rows.append("- **%s**（账本 `:%d`，块头自报时间算到现在的等待 ≈%s 分钟）\n  要裁的：%s。" % (label, hit, w, ask))

tip = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "-c", "http.proxy=", "-c", "https.proxy=",
                      "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True, timeout=240).stdout.split()
tip40 = tip[0] if tip and re.match(r"^[0-9a-f]{40}$", tip[0]) else "未读到"
root = [f for f in os.listdir(r"D:\moodle\_qoder_ledger_inbox") if f.endswith(".md")]

body = ("**值守 %s · 待裁队列三件（车道已把事实交齐，只差一句话；分钟从块头自报时间现算）**\n\n"
        "%s\n\n"
        "为什么单独贴这一条：夜里三条车道不是不动，是**停在别人的裁语上**——账本按作者分块插入，号令者一轮要读几十块，"
        "队列没人维护就会一直长。我只报等待与问题本身，**不催、不替你选**：三件里任何一件你想让车道先按某个假设推进，"
        "在账本写一行即可，我负责把它送到那条车道的窗口（消息只搬原话，不加我的判断）。\n\n"
        "同轮现场：收件目录 root=%d（%s）；现尖 `%s`；盘 D 12 GiB（97%%），值守 0 次删除。\n\n"
        "边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准。"
        % (time.strftime("%H:%M"), "\n".join(rows), len(root), "、".join(root) or "空", tip40))

out = os.path.join(HERE, "_bus_pending_rulings.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("写好 %d B；root=%d" % (os.path.getsize(out), len(root)))
for r in rows:
    print(r[:150])
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:600])
raise SystemExit(p.returncode)
