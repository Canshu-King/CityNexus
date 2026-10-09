# -*- coding: utf-8 -*-
"""勘误贴（不改 5877814433）：上一贴的窗口判据用了字符串比时间，跨午夜时把 22:25→02:11 也算进「03:40–04:35」。
这里把窗口判据改成数值秒比较，重算同一件事的真实数字。"""
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


def hhmm_to_epoch_today(h, m):
    lt = time.localtime()
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, h, m, 0, lt.tm_wday, lt.tm_yday, -1)) - 8 * 3600


W0 = time.mktime(time.strptime("2026-09-29 03:40", "%Y-%m-%d %H:%M"))
W1 = time.mktime(time.strptime("2026-09-29 04:35", "%Y-%m-%d %H:%M"))


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


in_win = []
outside = []
for sid in FLEET:
    g = sorted(glob.glob(os.path.join(BASE, sid + "*.jsonl")), key=lambda p: os.path.getmtime(p))
    if not g:
        continue
    st = stamps(g[-1])
    for a, b in zip(st, st[1:]):
        if b - a < 10 * 60:
            continue
        # 窗口判据：间隙**整段**落在 03:40–04:35（数值秒，不再比字符串）
        rec = (sid, (b - a) / 60.0, time.strftime("%H:%M", time.localtime(a)),
               time.strftime("%H:%M", time.localtime(b)))
        (in_win if (a >= W0 and b <= W1) else outside).append(rec)
in_win.sort(key=lambda r: -r[1])
outside.sort(key=lambda r: -r[1])
tot = sum(r[1] for r in in_win)

tip = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "-c", "http.proxy=", "-c", "https.proxy=",
                      "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True, timeout=240).stdout.split()
tip40 = tip[0] if tip and re.match(r"^[0-9a-f]{40}$", tip[0]) else "未读到"

body = ("**值守 %s · 勘误上一贴 `%s` 的窗口数字（成因是我自己的判据写错，不是现场变了）**\n\n"
        "上一贴（5877814433）写「9 条会话、最大 225.9 分钟、合计 409.9 车道分钟」。其中 **225.9 分钟那一格不属于这次事件**：\n"
        "- 错在我这侧：窗口过滤写成字符串比时间（`r[2] >= \"03:40\"`），于是 `8e5245f0` 的 `22:25→02:11` 因为 \"22\" > \"03\" 被算了进来。\n"
        "- 数值秒重算后的真数（同一份流水、同一判据、只把比较换成 epoch 秒）：落在 03:40–04:35 整段的间隙 **%d 条会话**，"
        "最大 **%s 分钟**，合计 **%s 车道分钟**。逐条（会话 / 分钟 / 起→止）：\n  %s\n"
        "- 被误算进去的那一条现在具名留在窗外：`%s`（那是夜里另一段静默，与本事件无关，我上一轮已单独量过并贴过）。\n"
        "- 其余读数不变：值守自己的 `autumn_watch.log` 也停在同一时刻；`list_chat_sessions` 本轮读到多数 `running`、"
        "`pendingInteractionCount` 全 0、掐着=0 ⇒ 不是额度、不是审批停摆，是链路一起断了一段。\n"
        "- 现尖（`ls-remote` 本轮实读）= `%s`。\n\n"
        "**结论没变、数字变了**：03:57→04:20 全舰队同时没有落盘，账本里那段不会有新车道交付块；"
        "谁按「车道 20 分钟没动」判它们偷懒都判错了。勘误按规矩发新贴，不改旧贴。\n\n"
        "边界：值守 0 次写账本、0 次插块、0 次删除、0 次动权威线、0 次点别人的批准；不碰 `_preview.db` 与 `demo/reset`。"
        % (time.strftime("%H:%M"), "5877814433", len(in_win),
           ("%.1f" % max(r[1] for r in in_win)) if in_win else "无", "%.1f" % tot,
           "；".join("`%s` %.1f 分 %s→%s" % r for r in in_win) or "（无）",
           "；".join("`%s` %.1f 分 %s→%s" % r for r in outside[:3]) or "（窗外无 >=10 分钟间隙）",
           tip40))

out = os.path.join(HERE, "_bus_link_stall_fix.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(body.rstrip() + "\n" + CLOSING + "\n")
assert re.search(r"%[sd]", body) is None, "残留未替换占位符"
print("写好 %d B；窗口内 %d 条 / 合计 %.1f 车道分钟；窗外 %d 条" % (os.path.getsize(out), len(in_win), tot, len(outside)))
print("窗口内逐条：" + "；".join("`%s` %.1f 分 %s→%s" % r for r in in_win))
print("窗外最大三条：" + "；".join("`%s` %.1f 分 %s→%s" % r for r in outside[:3]))
if "--dry" in sys.argv:
    print("DRY RUN，未发帖")
    raise SystemExit(0)
r = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(((r.stdout or "") + (r.stderr or "")).strip()[:900])
raise SystemExit(r.returncode)
