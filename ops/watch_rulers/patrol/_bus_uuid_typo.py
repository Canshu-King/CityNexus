# -*- coding: utf-8 -*-
"""值守贴：派单已改成「按会话 id 点名」，但本轮抓到一条 uuid **尾段被拼接**的派单——按整串开窗口的工具会敲错会话。

判据：账本里每一条 `ORD-#### →` 行内的完整 uuid，拿前 8 位去 `patrol/session_registry.json`
（那份是我 04:20 用 `mcp__builtin__list_chat_sessions` 现读的注册表）比对整串。
前 8 位对、整串不等 ⇒ 拼接；前 8 位不在注册表 ⇒ 具名报 `不在注册表`，不猜。
"""
import hashlib
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
# 09-29 05:45 修：账本里那枚拼接值有**六段**（8-4-4-4-4-12，36 个十六进制字符），
# 标准 uuid 是五段 32 字符——所以我原来那条 `\b[0-9a-f]{8}-...{12}\b` 根本匹配不到它，
# 报了个假的「0 条不一致」。现在放宽到 3~4 组 4 位段，才抓得住拼接形。
UUID = re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3,4}-[0-9a-f]{8,12}\b")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

regdoc = json.load(io.open(os.path.join(HERE, "session_registry.json"), encoding="utf-8"))
reg = dict(regdoc["sessions"])
src = regdoc["_source"]

# 09-29 05:47 改成以**本机会话流水文件名**为权威注册表：`projects/D--moodle/<uuid>.jsonl` 里的
# 那一串就是会话真实 id，比我 04:20 手抄的那份更硬，也自动覆盖夜里新开的车道。
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
disk = [os.path.basename(p)[:-6] for p in glob.glob(os.path.join(BASE, "*.jsonl"))]
for u in disk:
    if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", u):
        reg.setdefault(u[:8], u)
src = ("会话真实 id 取自本机流水文件名 `C:/Users/仓鼠王/.qoder/projects/D--moodle/<uuid>.jsonl`（本轮现扫 %d 个文件）；"
       "并集里另含我 04:20 用 `mcp__builtin__list_chat_sessions` 现读的 %d 条。"
       % (len(disk), len(regdoc["sessions"])))

lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
bad, unknown, checked = [], [], 0
for i, l in enumerate(lines):
    if "ORD-" not in l:
        continue
    for u in UUID.findall(l):
        checked += 1
        p = u[:8]
        if p not in reg:
            unknown.append((i + 1, p, u))
        elif reg[p] != u:
            bad.append((i + 1, l.strip()[:150], u, reg[p]))

tip = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "-c", "http.proxy=", "-c", "https.proxy=",
                      "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True, timeout=240).stdout.split()
tip40 = tip[0] if tip and re.match(r"^[0-9a-f]{40}$", tip[0]) else "未读到"

if "--json" in sys.argv:
    print(json.dumps({"checked": checked,
                      "bad": [{"line": ln, "frag": frag[:70], "wrote": u, "real": real} for ln, frag, u, real in bad],
                      "unknown": [{"line": ln, "p8": p, "wrote": u} for ln, p, u in unknown]},
                     ensure_ascii=False))
    raise SystemExit(0)

if not (bad or unknown):
    print("账本里核了 %d 枚完整 uuid，全部与注册表一致 ⇒ 不发贴" % checked)
    raise SystemExit(0)

rows = ["- 本轮核了账本里 **%d 枚** uuid 形值（只取含 `ORD-` 的行）。" % checked]
for ln, frag, u, real in bad:
    # 公共前缀长度现算，不写死"后几位"
    k = 0
    while k < min(len(u), len(real)) and u[k] == real[k]:
        k += 1
    owner = None
    for p8, full in reg.items():
        if full.endswith(u[k:]) and u[k:]:
            owner = p8
            break
    rows.append("- 不一致 `:%d`：%s…\n  账本写 `%s`，注册表里前 8 位 `%s` 的真会话是 `%s` ⇒ 两串只在**前 %d 个字符**相同；"
                "尾巴那截 `%s` 与车道 `%s` 的 uuid 尾部逐字相同 ⇒ 判为拼接（不是我猜的：比对见上）。"
                % (ln, frag[:90], u, u[:8], real, k, u[k:], owner or "?"))
for ln, p, u in unknown[:4]:
    rows.append("- 无法判定 `:%d`：前 8 位 `%s` 不在注册表里（整串 `%s`）——注册表=本机流水文件名与 04:20 会话名单的并集，两边都没有；可能是归档掉的老会话，我不猜，只具名报。" % (ln, p, u))

body = ("**值守 %s · 「按会话 id 点名」这条规矩漏了一格：账本里有一枚派单 uuid 的尾段是拼接的**\n\n"
        "%s\n\n"
        "注册表来源（逐字）：%s\n\n"
        "**为什么值得单贴**：两位号令者实例 09-28 起把派单改成「一律按会话 id 点名」（好几条会话自称车道 Q，按名字会送错）。"
        "但这条规矩只在**整串 uuid 真等于那个会话**时成立：我这侧的转达工具按前 8 位匹配，所以还是送对了窗口；"
        "而任何拿整串去开窗口的工具或人，会敲到另一条车道上。要么把整串写对，要么在派单里同时写清前 8 位与全串两形。\n"
        "我这一侧的处理：本轮那条 ORD-0446 我是按**前 8 位 + 号令者自己给的理由**（“ORD-0425 那张共享显示层词表就是你建的”）"
        "判收件人，并把这枚歧义原样报给了那条车道、请它自己报名再动手；我没改账本、也没替它认领。\n\n"
        "现尖（本轮实读 `ls-remote`）= `%s`。盘 12 GiB（97%%）未改善，我 0 次删除。\n\n"
        "边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次删除、0 次动权威线、0 次点别人的批准。"
        % (time.strftime("%H:%M"), "\n".join(rows), src, tip40))

out = os.path.join(HERE, "_bus_uuid_typo.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
print("核 %d 枚；拼接 %d 条；不在注册表 %d 条；写好 %d B" % (checked, len(bad), len(unknown), os.path.getsize(out)))
if "--dry" in sys.argv:
    for r in rows:
        print(r[:230])
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:700])
raise SystemExit(p.returncode)
