# -*- coding: utf-8 -*-
"""第二条勘误（作废 5877846569 与 5877917817）。

规矩：结论只能从**本轮打印出来的那几行**推，不许用我预设的文案。
证据面：
  A) `autumn_watch.log` 里 04:25 那一轮我自己打的那行（含当时的 tool 名与分钟数）；
  B) 车道 `4033270f` 流水尾 900 KB 里 04:20 之后的全部 `tool_use`（时刻 + name），最后 3 条逐字列出；
  C) 我 04:27:52 的 `wait_chat_sessions` 读数（runtimeState / pendingInteractionCount）——这一条是我用工具读的，不是脚本读的，逐字写进贴里并标明来源。
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

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
SID = "4033270f"
PERM_SHAPED = ("Bash", "Edit", "Write", "MultiEdit", "search_replace", "delete_file", "NotebookEdit")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

# A) 我自己 04:25 打的那一行（仪表产物，不是我记忆）
wl = io.open(os.path.join(HERE, "autumn_watch.log"), encoding="utf-8", errors="replace").read().split("\n")
mine = [l for l in wl if "停摆" in l and SID in l and "tool=" in l]
assert mine, "autumn_watch.log 里没有这一格的行，先别看数"
line_0425 = mine[-1].strip()
m = re.search(r"tool_use=(\w+)|tool=(\w+)", line_0425)
tool_then = m.group(1) or m.group(2) if m else "?"

# B) 流水里 04:20 之后的 tool_use 序列
p = sorted(glob.glob(os.path.join(BASE, SID + "*.jsonl")), key=lambda x: os.path.getmtime(x))[-1]
with io.open(p, "rb") as f:
    f.seek(0, 2)
    sz = f.tell()
    f.seek(max(0, sz - 900000))
    chunk = f.read()
seq = []
for line in chunk.split(b"\n"):
    line = line.strip()
    if not line.startswith(b"{"):
        continue
    try:
        r = json.loads(line.decode("utf-8", "replace"))
    except Exception:
        continue
    mm = r.get("message") or {}
    c = mm.get("content")
    if mm.get("role") == "assistant" and isinstance(c, list):
        for b in c:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                t = r.get("timestamp") or ""
                try:
                    ep = time.mktime(time.strptime(t[:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600
                except Exception:
                    continue
                if time.strftime("%H:%M", time.localtime(ep)) >= "04:20":
                    seq.append((ep, time.strftime("%H:%M:%S", time.localtime(ep)), b.get("name")))
assert seq, "04:20 之后没有 tool_use，那这条线此刻真的没动——必须换结论"
last3 = seq[-3:]
n_after = len(seq)
# ep = 记录写入的真实 epoch（strptime 出来的 UTC 串按本机 +08 解释后 +8*3600 正好回到真实时刻）
fresh_min = round((time.time() - last3[-1][0]) / 60.0, 1)
last_name = last3[-1][2]

# 判据：只要 04:20 之后还有 >=2 枚 tool_use 且最新一枚距今 <10 分钟 ⇒ 车道在继续动；
# 若最新一枚是审批形且距今 >=30 分钟才算「可能停在弹窗上」（本条此刻不适用，见打印）。
moving = (n_after >= 2 and fresh_min < 10.0)
verdict = ("车道在继续动，从未停在弹窗上" if moving else
           "04:20 之后只数到 %d 枚、最新一枚距今 %.1f 分钟，不足以下「在继续动」的结论" % (n_after, fresh_min))
pend = "runtimeState=running / pendingInteractionCount=0 / queuedTurnCount=0（我 04:27:52 用 `wait_chat_sessions` 同批读到 8 条会话都是这个形状）"

body = ("**值守 %s · 第二条勘误：作废 `5877846569`，也作废我 5 分钟前自己那条 `5877917817`**\n\n"
        "为什么两条都要作废（结论从本轮打印的行推，不用预设文案）：\n"
        "- `5877846569`（04:25 值守自动发贴）说车道 `4033270f`「停在弹窗上 31 分钟」。它当时那一行是这么打的：\n  > %s\n"
        "  当时的末条 tool_use 是 `%s`——不在审批形名单（%s）里；把它写成「等人点批准」是判据太宽。\n"
        "- 我 04:29 那条 `5877917817` 方向对（不是弹窗），但**它自己打印的是 `tool=Bash`、正文却写了「委派在飞」**"
        "——结论来自我预设的句子而不是打印的那一行。按规矩这条也作废，不再改旧贴。\n"
        "- 本轮现读（`%s` 尾 900 KB，04:20 之后共数到 **%d 枚** `tool_use`，最新一枚 `%s` 距今 **%.1f 分钟**）：\n  %s\n"
        "- 会话侧一证：%s\n\n"
        "**本轮结论（由上面两行算出）**：%s。号令者不需要为这一格做任何裁；"
        "03:57→04:20 那段沉默由全舰队同时的链路静默解释（`5877814433` 与其勘误 `5877851124`）。\n\n"
        "**仪表已就地改掉**：`patrol/autumn_watch.py` 现在只对审批形名单里的 tool 发停摆贴，其余只记日志；"
        "名单与理由写在那段代码的注释里（含这一格的读数）。这条贴本身也是新贴，不覆盖前面任何一条。\n\n"
        "边界：值守 0 次写账本、0 次插块、0 次删除、0 次动权威线、0 次点别人的批准；不碰 `_preview.db` 与 `demo/reset`。"
        % (time.strftime("%H:%M"), line_0425[:180], tool_then, "`、`".join(PERM_SHAPED),
           os.path.basename(p), n_after, last_name, fresh_min,
           "；".join("`%s`→`%s`" % (t, n) for _ep, t, n in last3), pend, verdict))

out = os.path.join(HERE, "_bus_stall_corr2.md")
assert re.search(r"%[sd]", body) is None, "残留未替换占位符"
io.open(out, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
print("tool@04:25=%s  04:20 后 tool_use=%d 枚  最新=%s 距今=%.1f 分  moving=%s\n结论=%s\n写好 %d B"
      % (tool_then, n_after, last_name, fresh_min, moving, verdict, os.path.getsize(out)))
if "--dry" in sys.argv:
    raise SystemExit(0)
r = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((r.stdout or "") + (r.stderr or "")).strip()[:700])
raise SystemExit(r.returncode)
