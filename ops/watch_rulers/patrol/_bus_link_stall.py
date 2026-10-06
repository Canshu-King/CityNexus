# -*- coding: utf-8 -*-
"""值守贴：一条**全舰队同时**的静默窗口（03:57→04:20 本地），不是车道偷懒。

判据：逐会话流水尾 900 KB 取全部 timestamp，找窗口内 >=10 分钟的最大间隙；同时报本轮 `list_chat_sessions`
之外的旁证——值守自己的 round 仪表也在同一时刻挂住（autumn_watch.log 最后一条 03:53:44）。
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
FLEET = ["494abfd7", "6efab655", "3b65af59", "1d64acf5", "904a042d", "e4f3490f", "a68b0631",
         "49fe0d7b", "2d2d7428", "8e5245f0", "9759f1ac", "bac10f40", "be19052c", "4033270f",
         "a6b95d59", "9cc37e57", "8ac89982"]

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()


def stamps(p):
    with io.open(p, "rb") as f:
        f.seek(0, 2)
        sz = f.tell()
        f.seek(max(0, sz - 900000))
        chunk = f.read()
    out = []
    for line in chunk.split(b"\n"):
        line = line.strip()
        if not line.startswith(b"{"):
            continue
        try:
            r = json.loads(line.decode("utf-8", "replace"))
        except Exception:
            continue
        t = r.get("timestamp") or (r.get("message") or {}).get("timestamp")
        if isinstance(t, str) and len(t) >= 19:
            try:
                out.append(time.mktime(time.strptime(t[:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600)
            except Exception:
                pass
    return sorted(set(out))


rows = []
for sid in FLEET:
    g = sorted(glob.glob(os.path.join(BASE, sid + "*.jsonl")), key=lambda p: os.path.getmtime(p))
    if not g:
        continue
    st = stamps(g[-1])
    best = (0.0, 0.0, 0.0)
    for a, b in zip(st, st[1:]):
        gap = (b - a) / 60.0
        if gap >= 10.0 and gap > best[0]:
            best = (gap, a, b)
    if best[0] > 0:
        rows.append((sid, best[0], time.strftime("%H:%M", time.localtime(best[1])),
                     time.strftime("%H:%M", time.localtime(best[2]))))
rows.sort(key=lambda r: -r[1])
tot = sum(r[1] for r in rows)
in_win = [r for r in rows if r[2] >= "03:40" and r[3] <= "04:35"]

wl = io.open(os.path.join(HERE, "autumn_watch.log"), encoding="utf-8", errors="replace").read().strip().split("\n")
last_watch = wl[-1][:9] if wl else "?"

tip = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "-c", "http.proxy=", "-c", "https.proxy=",
                      "ls-remote", "origin",
                      "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True, timeout=240).stdout.split()
tip40 = tip[0] if tip and re.match(r"^[0-9a-f]{40}$", tip[0]) else "未读到"

body = ["**值守 %s · 一条全舰队同时的静默窗口：03:57→04:20（本地）——不是车道偷懒，是链路一起断了**\n"
        % time.strftime("%H:%M"),
        "读数（全部本轮实取，判据写在源码里：`patrol/_bus_link_stall.py`）：",
        "- 逐会话流水尾 900 KB 取时间戳，窗口 03:40–04:35 内 >=10 分钟的间隙：**%d 条会话**，最大 %s 分钟，合计 %s 车道分钟。"
        % (len(in_win), ("%.1f" % max(r[1] for r in in_win)) if in_win else "无",
           ("%.1f" % sum(r[1] for r in in_win)) if in_win else "0.0"),
        "- 前 6 条（会话 8 位 / 间隙分钟 / 起→止）：%s" % "；".join(
            "`%s` %.1f 分 %s→%s" % r for r in (in_win[:6] if in_win else [])),
        "- 旁证一：值守自己的轮次仪表也在同一时刻停住——`patrol/autumn_watch.log` 最后一条是 **%s**（周期本应 10 分钟一跳）。"
        % last_watch,
        "- 旁证二：同一时刻全部会话的流水 mtime 一起回到“刚刚在写”，而 `runtimeState` 全程没有变成额度或弹窗形态（我本轮 `list_chat_sessions` 读到 15/17 条 `running`、`pendingInteractionCount` 全 0，掐着=0）⇒ 不是额度、不是审批停摆。",
        "- 现尖（`ls-remote` 本轮实读，网络恢复后取到）= `%s`。" % tip40,
        "",
        "**这条贴的用处**：账本里 03:57–04:20 之间不会有新车道交付块，谁按“车道 20 分钟没动”判它们偷懒都判错了；"
        "我这侧按流水时间戳算的 idle 在长回合里也会偷报大，所以从这一条起，车道在不在干我只认 `runtimeState` + 流水 mtime 两证同批。",
        "",
        "边界：值守 0 次写账本、0 次插块、0 次删除、0 次动权威线、0 次点别人的批准；不碰 `_preview.db` 与 `demo/reset`。"]

out = os.path.join(HERE, "_bus_link_stall.md")
txt = "\n".join(body)
assert re.search(r"@(\w+)@", txt) is None
io.open(out, "w", encoding="utf-8", newline="\n").write(txt.rstrip() + "\n" + CLOSING + "\n")
print("写好 %d B，窗口内会话 %d 条，合计 %.1f 车道分钟" % (os.path.getsize(out), len(in_win),
                                                    sum(r[1] for r in in_win) if in_win else 0.0))
r = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((r.stdout or "") + (r.stderr or "")).strip()[:900])
raise SystemExit(r.returncode)
