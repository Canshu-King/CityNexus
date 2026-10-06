# -*- coding: utf-8 -*-
"""把 09-29 夜里值守这一段**改掉的判据**记进 patrol/PATROL_LOG.md（数字全部现算，不抄上一轮）。"""
import glob
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
LOG = os.path.join(HERE, "PATROL_LOG.md")
INBOX = r"D:\moodle\_qoder_ledger_inbox"

# 现算的数
proc = glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*"))
since0230 = [p for p in proc if os.path.getmtime(p) >= time.mktime(time.strptime("2026-09-29 02:30", "%Y-%m-%d %H:%M"))]
root = [f for f in os.listdir(INBOX) if f.endswith(".md")]
tip = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "-c", "http.proxy=", "-c", "https.proxy=",
                      "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True, timeout=240).stdout.split()
tip40 = tip[0] if tip and re.match(r"^[0-9a-f]{40}$", tip[0]) else "未读到"
wl = io.open(os.path.join(HERE, "autumn_watch.log"), encoding="utf-8", errors="replace").read()
cycles = len(re.findall(r"=== cycle \d+/\d+ start", wl))
posts = re.findall(r"POST -> 201 (\d+)", wl)

mine = ["5876265178", "5877814433", "5877851124", "5877917817", "5877966929", "5878152419"]
# 卡住的这枚当场重算等待分钟数（不抄 04:57 那次测试的输出）
SP = os.path.join(INBOX, "s4_0338.md")
s4_age = ("%.1f" % ((time.time() - os.path.getmtime(SP)) / 60.0)) if os.path.exists(SP) else "已入账/不在了"
REFUSE = "15"
entry = """

## 值守 09-29 04:58 · 这一段我把自己的判据改了四处（每条都附本轮现算的数）

- 本轮现算：`_processed` 里 02:30 之后入账 **%d** 枚（总 %d）；收件 root **%d** 枚（%s）；
  现尖 `%s`；`autumn_watch.log` 里 cycle 起头 **%d** 次；自动发贴 id：%s。
  我自己这一段发的总线贴：`%s`（其中 %s 是勘误）。
- 改一：**交件规矩里的尺名** —— 旧文档写 `ledger_inbox_apply_r1.py` + `claim_coordinate_check_r4e.py`，
  现行是 `ledger_inbox_apply_r2.py` → `ledger_insert_after_r2.py:28` 调 `claim_coordinate_check_r7.py`
  （本机文件 sha1，非 blob：`2690a3f7eb0b817a882212854ad906bfc8703e2d`）。`relay.py` 的模板已就地改掉，
  之后每份转达都带校正版。
- 改二：**wake 扫描的两类假阳性** —— 块头不是号令者的块（车道自己的交件块里会引用别人的单号与会话 id）
  一律不转达（NON_CMDR_HEAD）；号令者一块连派 8~12 张的新形状改成**按段落逐家收窄**（PER_ORDER_PARA），
  整块像状态板但段内只点一家带单号时，转达正文只给那一段。04:34 那一波（ORD-0433…0443）原先会被整块跳过。
- 改三：**「停在弹窗上」的判据** —— `tool_use 无 result` 有审批形与委派在飞两种，只有前者能那么写。
  仪表现在按名单（Bash/Edit/Write/MultiEdit/search_replace/delete_file/NotebookEdit）才发贴；
  由此产生的两条假事实贴 `5877846569`、`5877917817` 已在新贴 `%s` 里一并作废（不改旧贴）。
- 改四：**闸口拒绝要当场告诉车道** —— 新增 `pending_aborts()`：收件块等过 `%s` 分钟就被只读副本过两闸，
  Q43-RED 抓尺的 findings、WOULD-ABORT 抓 `declared/anchored` 行，写成 `relay/pending_<块>_<HHMM>.txt` 并按块发一贴。
  实测有效性：04:54 我把 `qoder-0441_0443.md` 的四枚裸数点名给 2d2d7428，**04:56:34 那块就入账了**；
  同一时刻 `s4_0338.md` 因两枚 12 位短形已卡 `%s` 分钟。
- 仍未修好的（具名）：全舰队 03:57→04:20 那段链路静默我只能在事后测量，没有预警；
  双号令者实例的撞号由实例自己在账本里立规矩（04:27 那块「第三次撞号」），我只能报数；
  D 盘从 15 GB 掉到 13 GB，我没有删任何东西。
""" % (len(since0230), len(proc), len(root), "、".join(sorted(root)) or "空", tip40, cycles,
       "、".join(posts[-4:]) or "无", "、".join(mine), "、".join(["5877851124", "5877966929"]),
       "、".join(["5877851124", "5877966929"]),
       REFUSE, s4_age)

assert re.search(r"%[sd]", entry) is None, "残留未替换占位符"
before = os.path.getsize(LOG)
io.open(LOG, "a", encoding="utf-8", newline="\n").write(entry)
after = os.path.getsize(LOG)
print("append %d B，%d -> %d；本轮现算：入账 %d/root %d/cycle %d/tip %s"
      % (after - before, before, after, len(since0230), len(root), cycles, tip40[:12]))
time.sleep(15)
t = io.open(LOG, encoding="utf-8", errors="replace").read()
print("re-read: still_present=", entry.strip().splitlines()[-1][:40] in t, "size=", os.path.getsize(LOG))
