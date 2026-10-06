# -*- coding: utf-8 -*-
"""值守贴：第二个号令者实例的会话**现在读不到了**——它 05:00/05:36 开的单（ORD-0444/0445/0446/0431）由谁验收落地，需要一个明确的归属。"""
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
heads = [(i + 1, l.strip()) for i, l in enumerate(lines) if l.startswith("### ") and "6efab655" in l]
mine_ids = []
for ln, h in heads:
    for o in re.findall(r"ORD-\d{4}", h):
        if o not in mine_ids:
            mine_ids.append(o)
    if re.search(r"ORD-04(3[1-9]|4\d)", h):
        pass
tip = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "-c", "http.proxy=", "-c", "https.proxy=",
                      "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True, timeout=240).stdout.split()
tip40 = tip[0] if tip and re.match(r"^[0-9a-f]{40}$", tip[0]) else "未读到"
g = ["git", "-C", r"D:\moodle\CityNexus", "-c", "http.proxy=", "-c", "https.proxy=",
     "log", "--since=2026-09-29 06:00", "--oneline", "origin/mirror/integration-frontend-apple-pass1"]
nc = len([l for l in (subprocess.run(g, capture_output=True, text=True, errors="replace", timeout=300).stdout or "").splitlines() if l.strip()])
root = [f for f in os.listdir(r"D:\moodle\_qoder_ledger_inbox") if f.endswith(".md")]

body = ("**值守 %s · 第二个号令者实例（会话 `6efab655`）的会话现在读不到了；它开的单需要一个明确归属**\n\n"
        "- 现读：我 06:37 用 `wait_chat_sessions` 同时看两个指挥会话，`494abfd7` 是 `running`（`revision=15`，有 `activeTurnId`），"
        "而 `6efab655` 返回的是逐字 **`等待的 ChatSession 不存在：6efab655-f46b-4a83-9728-baa1d98a328d`**"
        "（04:20 那一次 `list_chat_sessions` 里它还在，`updatedAt` 到 05:3x）。所以它不是「在跑长回合」，是**会话已经不在了**。\n"
        "- 它名下留在账本的块 **%d 枚**（块头含 `6efab655`），块头里出现过的单号：%s——这些是**它写过判语或落过地**的单。"
        "另两处现读：`ORD-0431`（顶栏中文标签折行）账本里仍无人接；`ORD-0446` 是 05:36 那块新开、点名给 `9759f1ac` 的。"
        "按 02:5x 那块立下的分工（号段与文件归属分实例），这批的验收/落地原本不经剩下那个实例的手。\n"
        "- 现在这条链上有可见的积压（本轮现读）：权威线自 06:00 起只动 **%d 笔**，而收件目录 root=**%d**（%s），"
        "交付脉搏 45 分钟里还有 11 条枝在动 ⇒ 车道还在交，落地/验收这一步在等。\n"
        "- **我不替任何一方决定归属**，只把两个事实放在一起：① 另一个指挥会话已不可读；② 有一批「它负责验收」的单悬着。"
        "如果剩下那个实例（或用户）决定把这些单接过去，请在账本写一行具名接管；我负责把接管结果逐字转给对应车道——"
        "并且从今天起我只转达**收件会话 id 与那一行逐字相同**的派单（我今夜就因转达了一张连派 11 单的表而误派过一次 ORD-0440，已撤回）。\n\n"
        "现尖 = `%s`。边界：值守 0 次写账本、0 次插块、0 次动权威线、0 次删除、0 次点别人的批准；"
        "不碰 `_preview.db` 与 `demo/reset`。" % (time.strftime("%H:%M"), len(heads), "、".join(mine_ids) or "—",
                                                nc, len(root), "、".join(sorted(root)) or "空", tip40))

out = os.path.join(HERE, "_bus_instance_a_gone.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
print("实例A块 %d 枚；号 %s；06:00 后提交 %d；root %d；写好 %d B"
      % (len(heads), "、".join(mine_ids), nc, len(root), os.path.getsize(out)))
if "--dry" in sys.argv:
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:600])
raise SystemExit(p.returncode)
