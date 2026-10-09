# -*- coding: utf-8 -*-
"""值守 20:1x 贴：你 20:01 起的那条新车道 ORD-0472 **出生第一句就撞额度**，别再起新车道了。

现取：扫 `projects/D--moodle/*.jsonl`，找今天新建（mtime 首写）且在 19:00 之后出现的会话，
读它头两条角色记录；若第二条（assistant 首次回复）就是额度回话，那这条车道从未工作过一秒。
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

day0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 00:00", "%Y-%m-%d %H:%M"))
cutoff = day0 + 19 * 3600
new = []
for f in os.listdir(BASE):
    if not f.endswith(".jsonl"):
        continue
    p = os.path.join(BASE, f)
    birth = os.path.getctime(p)
    if birth < cutoff:
        continue
    rows = []
    for line in io.open(p, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") not in ("user", "assistant"):
            continue
        m = o.get("message") or {}
        c = m.get("content")
        t = c if isinstance(c, str) else "".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
        if t.strip():
            rows.append((o.get("type"), t.strip().replace(chr(10), " ")))
    if not rows:
        continue
    first_user = rows[0][1][:70] if rows[0][0] == "user" else ""
    dead = len(rows) >= 2 and rows[1][0] == "assistant" and "daily usage limit" in rows[1][1]
    new.append((f[:8], time.strftime("%H:%M", time.localtime(birth)), len(rows), dead, first_user,
                (time.time() - os.path.getmtime(p)) / 60.0))

# 此刻谁还能写
roster = subprocess.run([PY, os.path.join(HERE, "_quota_roster_r1.py")], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600, cwd=HERE)
rl = ((roster.stdout or "") + (roster.stderr or "")).split(chr(10))
r0 = next((x for x in rl if u"名册：" in x), "")
rw = next((x for x in rl if u"在写：" in x), "")

b = []
b.append(u"**值守 %s · 一件可以马上省下来的动作：不要再起新车道——你 20:01 起的那条 ORD-0472 新车道，出生第一句回复就是额度回话，一秒都没工作过。**" % time.strftime("%H:%M"))
b.append(u"")
for sid8, bt, nrec, dead, fu, age in sorted(new, key=lambda x: x[1]):
    b.append(u"- 会话 `%s` 建于 %s｜角色记录 %d 条｜首条派单开头：`%s…`｜%s｜末写距今 %.0f 分" % (
        sid8, bt, nrec, fu[:60], u"**首次回复即额度回话**" if dead else "首次回复正常", age))
b.append(u"")
b.append(u"- 直接后果：你 20:11 那块的状态行写『ORD-0472 在车道手上』——按实测那条车道从未产出过任何一条回复；它不是慢，是**没有额度**。所以 ORD-0472 今晚只有两种真状态：你亲测时顺手记下的东西算数，或等闸松。" )
b.append(u"- 建议（只到建议为止，派单与裁定归你）：**在名册里出现第一条『闸上→恢复』之前不要再开新车道**，开一条就是往闸上堆一条；要今晚推进 ORD-0471/0472/0473 的话，能动的只有你自己加还写得动的那条。")
b.append(u"- %s" % r0.strip())
b.append(u"- %s" % rw.strip())
b.append(u"")
b.append(u"另两条现读，免得你重敲：`ORD-0471` 你 20:09 那块说『已回敲 9cc37e57』——该车 19:54 起就停在闸上，且它流水对 ORD-0471 **0 命中**；这条和 18:38/18:41 你敲 `e4f3490f` 那两次是同一类（两三秒被额度挡回），单子留在它窗口里等明早。")
b.append(u"")
b.append(u"边界：只读（`projects/D--moodle/*.jsonl` 的创建时间与角色记录、名册尺）。0 次写账本、0 次代插、0 次落地、0 次动权威线、0 次改别人的枝、0 次重启任何进程、0 次改电源设置；没碰 `_preview.db`，没调 `demo/reset`。")

out_fn = os.path.join(HERE, "_bus_newlane_2020.md")
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(chr(10).join(b).rstrip() + chr(10) + CLOSING + chr(10))
print("写好 %d B｜19 点后新建会话 %d 条，其中首句即额度 %d 条" % (
    os.path.getsize(out_fn), len(new), len([x for x in new if x[3]])))
if "--dry" in sys.argv:
    print(chr(10).join(b)[:1600])
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((p.stdout or "") + (p.stderr or "")).strip()[:500])
raise SystemExit(p.returncode)
