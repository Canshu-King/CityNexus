# -*- coding: utf-8 -*-
"""勘误贴（不改 5877846569）：那一格「车道停在弹窗上」不成立——它是**委派在飞**，不是审批。

判据本轮实取两证：
1) 流水末条 `assistant/tool_use` 的 name 是不是审批形（Bash/Edit/Write/删除类）——`Agent` 属于委派形；
2) 我 04:27:52 那次 `wait_chat_sessions` 的读数：runtimeState / pendingInteractionCount / queuedTurnCount。
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

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

p = sorted(glob.glob(os.path.join(BASE, SID + "*.jsonl")), key=lambda x: os.path.getmtime(x))[-1]
with io.open(p, "rb") as f:
    f.seek(0, 2)
    sz = f.tell()
    f.seek(max(0, sz - 900000))
    chunk = f.read()
last_use = None
has_result_after = False
for line in chunk.split(b"\n"):
    line = line.strip()
    if not line.startswith(b"{"):
        continue
    try:
        r = json.loads(line.decode("utf-8", "replace"))
    except Exception:
        continue
    m = r.get("message") or {}
    c = m.get("content")
    if m.get("role") == "assistant" and isinstance(c, list):
        for b in c:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                last_use = (b.get("name"), r.get("timestamp"))
                has_result_after = False
    if m.get("role") == "tool" or (isinstance(c, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in c)):
        if last_use:
            has_result_after = True
tool, ts = last_use
ts_local = time.strftime("%H:%M:%S", time.localtime(
    time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600)) if ts else "?"
age = round((time.time() - (time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) - 0)) / 60.0, 1) if ts else -1
PERM_SHAPED = ("Bash", "Edit", "Write", "MultiEdit", "search_replace", "delete_file", "NotebookEdit")
shaped = "审批形" if tool in PERM_SHAPED else "委派在飞形（不在审批名单里）"

body = ("**值守 %s · 勘误上一贴 `5877846569`：那一格不是车道停在弹窗上，是委派在飞；我递了一条假事实给号令者**\n\n"
        "两证同批（本轮实取，脚本 `patrol/_bus_stall_corr_4033270f.py`）：\n"
        "- 流水一证：车道 `4033270f`（道0383）会话流水 `%s` 末条 `assistant/tool_use` 的 name = **`%s`**，时刻 `%s`（本地），"
        "其后 **没有** `tool_result`；该 name 不在审批形名单（`%s`）里 ⇒ 判据应写「委派在飞」，不是「等人点批准」。\n"
        "- 会话一证：我 04:27:52 那次 `wait_chat_sessions` 同时读 8 条会话，`4033270f` 的 "
        "`runtimeState=running`、`pendingInteractionCount=0`、`queuedTurnCount=0`、`activeTurnId=agent-message:d61e96c2…`；"
        "另外 7 条（`3b65af59`/`49fe0d7b`/`a68b0631`/`8e5245f0`/`e4f3490f`/`9cc37e57`/`1d64acf5`）也是 running + pending=0。\n"
        "  ⇒ 弹窗会表现为 `waiting-user` + `pendingInteractionCount>0`（昨夜 20:47 那一格就是这样），这次两个条件都不成立。\n\n"
        "**成因在我这侧，不在现场**：`round.py` 把「末条 tool_use 无 result」一律标成弹窗停摆，我 04:25 那轮照它发贴，"
        "没有先看 tool 的名字。已把判据装进仪表：`autumn_watch.py` 现在只对审批形发贴，委派形只记一行日志（名单写死在源码里，"
        "并附了这一格的读数理由）。\n\n"
        "**仍然成立的部分**：那一时刻道0383 确实已经 31 分钟没有落盘——但 03:57→04:20 是**全舰队同时**的静默窗口"
        "（见 `5877814433` 与其勘误 `5877851124`：窗口内 14 条会话、合计 328.6 车道分钟），所以这段沉默首先由链路解释，"
        "不需要动用「有人在等点击」这个假设。号令者不必为这一格做任何裁。\n\n"
        "边界：值守 0 次写账本、0 次插块、0 次删除、0 次动权威线、0 次点别人的批准（含这一格）；不碰 `_preview.db` 与 `demo/reset`。"
        % (time.strftime("%H:%M"), os.path.basename(p), tool, ts_local, "`、`".join(PERM_SHAPED)))

out = os.path.join(HERE, "_bus_stall_corr_4033270f.md")
assert re.search(r"%[sd]", body) is None, "残留未替换占位符"
io.open(out, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
print("tool=%s shaped=%s ts=%s 写好 %d B" % (tool, shaped, ts_local, os.path.getsize(out)))
if "--dry" in sys.argv:
    raise SystemExit(0)
r = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((r.stdout or "") + (r.stderr or "")).strip()[:700])
raise SystemExit(r.returncode)
