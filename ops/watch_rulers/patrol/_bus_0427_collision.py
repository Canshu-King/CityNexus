# -*- coding: utf-8 -*-
"""值守贴：ORD-0427 这一枚号在账本里有两种用法（本轮实读，行号按本轮重算，不用上一轮的）。

只报数，不裁、不改号、不写账本。引用全部按**文字锚**在本轮现盘里定位，因为账本行号会被别人重写漂掉
（我第一次硬写 :16702 就在下一轮变成空行——这条本身就是贴里的一个读数）。
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
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令文件变了"
CLOSING = raw.decode("utf-8").strip()

L = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")

ANCHORS = [
    ("开单（块头）", "开 ORD-0427"),
    ("当未开", "ORD-0427 未开"),
    ("未落地", "ORD-0427 未落地"),
    ("投递状态", "ORD-0427（head 行被放宽的选择器带坏"),
    ("要件", "ORD-0427 要件"),
]
found = []
for label, a in ANCHORS:
    hits = [(i + 1, L[i].strip()) for i in range(len(L)) if a in L[i]]
    assert hits, "锚没命中：「%s」——账本形状变了，先别看数" % a
    ln, t = hits[0]
    found.append((label, a, ln, t, len(hits)))

n_lines = sum(1 for l in L if "ORD-0427" in l)
n_heads = [i + 1 for i, l in enumerate(L) if l.startswith("### ") and "ORD-0427" in l]

tip = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "-c", "http.proxy=", "-c", "https.proxy=",
                      "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True, timeout=240).stdout.split()
assert len(tip) >= 2 and re.match(r"^[0-9a-f]{40}$", tip[0]), "现尖没读到，不发贴"
tp = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "log", "-1", "--format=%ad | %s", tip[0]],
                    capture_output=True, text=True, errors="replace", timeout=240).stdout.strip()

lines = []
for label, a, ln, t, k in found:
    lines.append("- 「%s」锚「%s」本轮命中 %d 行，第一条在 `CITYNEXUS_AGENT_CONTROL.md:%d`，逐字：\n  > %s"
                 % (label, a, k, ln, t[:520]))

body = (
    "**值守 %s · `ORD-0427` 这一枚号在账本里同时是两格：「head 行回归」与「顶栏中文标签折行」**\n\n"
    "读数全部本轮实取（账本现盘，按**文字锚**定位；行号会漂——我 20 秒前硬写的那枚 `:16702` 本轮已变成空行，"
    "所以每条同时给出锚与本轮算出的行号）：\n\n"
    "- 账本里含 `ORD-0427` 的行共 **%d 行**，块头 **%d 枚**（本轮行号：%s）。\n%s\n\n"
    "**我没做的、与不敢下的结论**：没动账本、没改号、没派单。我不按「块头相邻」判定某一行属于哪个作者——"
    "账本会被整文件重写，块插入按作者分块不等于全局时间序，邻接关系不可靠；上面每条只报该行自己写明的内容。\n"
    "对车道的实际影响，往小里说：领到 head 行那一格的车道拿到的要件是具体到符号名的，不会走错；"
    "风险在后面——同一枚号若再被按另一种意思开一次，交件与验收会互相指错，`_processed` 里的块也就对不上单。\n\n"
    "现尖（`git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1` 本轮实读）= `%s`（%s）。\n\n"
    "边界：值守只读会话流水 / 收件目录 / GitHub ref；0 次写账本、0 次插块、0 次删除、0 次动权威线、0 次敲门给掐着的会话。"
    % (time.strftime("%H:%M"), n_lines, len(n_heads), ",".join(str(x) for x in n_heads),
       "\n".join(lines), tip[0], tp)
)

out = os.path.join(HERE, "_bus_0427_collision.md")
assert re.search(r"%[sd]", body) is None, "残留未替换占位符"
io.open(out, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
print("写好 %d B -> %s" % (os.path.getsize(out), out))
r = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((r.stdout or "") + (r.stderr or "")).strip()[:1500])
raise SystemExit(r.returncode)
