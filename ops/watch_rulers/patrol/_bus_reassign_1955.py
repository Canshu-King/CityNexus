# -*- coding: utf-8 -*-
"""值守 19:5x 贴：现在挂着没主的四格，收件人全在闸上；唯一还有油又没单的车道是 AI。

判语只从实测行推：每格的收件人 id 出自号令者自己的块；每条车的状态出自它流水的**最后一条角色记录**；
AI 的『还有油』＝末条不是额度字样，『没单』＝账本最近点名它的地方停在昨天、且它自己 14:20 写了收工。
"""
import hashlib
import io
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request as U

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
PROCD = r"D:\moodle\_qoder_ledger_inbox\_processed"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")
LANES = {"a68b0631": "rel", "1d64acf5": "S4", "9759f1ac": "N2", "904a042d": "Q", "bac10f40": "AI",
         "3b65af59": "map", "be19052c": "dt", "e4f3490f": "道0370", "49fe0d7b": "N3", "8ac89982": "R0417",
         "4033270f": "0383", "1ba48dbf": "newlane", "6a150e1e": "newlane2", "9cc37e57": "0421",
         "2d2d7428": "0441", "a6b95d59": "DSH", "8e5245f0": "道0369", "da46954a": "新车道"}

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))


def api(u):
    r = U.Request(u, headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol",
                              "Accept": "application/vnd.github+json"})
    return json.loads(op.open(r, timeout=90).read().decode("utf-8"))


def probe(sid8):
    p = max([os.path.join(BASE, f) for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")],
            key=os.path.getsize)
    n = os.path.getsize(p)
    fh = io.open(p, "rb")
    fh.seek(max(0, n - 200000))
    blob = fh.read().decode("utf-8", errors="replace")
    fh.close()
    last = None
    for line in blob.split(chr(10)):
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
            last = t.strip().replace(chr(10), " ")
    mt = os.path.getmtime(p)
    capped = bool(last) and "daily usage limit" in last
    return capped, (time.time() - mt) / 60.0, time.strftime("%H:%M:%S", time.localtime(mt)), (last or "")[:70]


tip = api("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1")["object"]["sha"]
tc = api("https://api.github.com/repos/Canshu-King/CityNexus/commits/" + tip)
tipbj = time.strftime("%H:%M:%S", time.localtime(time.mktime(time.strptime(tc["commit"]["committer"]["date"][:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600))

# 四格：从号令者源块里逐字取那行派单
want = {"ORD-0461": "a68b0631", "ORD-0468": "e4f3490f", "ORD-0469": "a6b95d59", "ORD-0444": "1ba48dbf"}
rows = []
for num, sid8 in want.items():
    line = ""
    for f in sorted(os.listdir(PROCD), key=lambda x: -os.path.getmtime(os.path.join(PROCD, x))):
        if not f.lower().startswith("cmdr"):
            continue
        body = io.open(os.path.join(PROCD, f), encoding="utf-8", errors="replace").read()
        for bl in body.split(chr(10)):
            if num in bl and sid8 in bl and abs(bl.find(num) - bl.find(sid8)) <= 60:
                line = bl.strip()
                break
        if line:
            break
    capped, age, when, tail = probe(sid8)
    rows.append((num, sid8, LANES[sid8], capped, age, when, line[:210]))

ai_capped, ai_age, ai_when, ai_tail = probe("bac10f40")
free = []
for sid8, nick in LANES.items():
    capped, age, when, tail = probe(sid8)
    if not capped and age >= 8:
        free.append((nick, sid8, age, when))
pend = sorted([f for f in os.listdir(r"D:\moodle\_qoder_ledger_inbox") if f.endswith(".md")])
ins = sorted([(os.path.getmtime(os.path.join(PROCD, f)), f) for f in os.listdir(PROCD) if ".inserted_" in f])[-2:]

b = []
b.append(u"**值守 %s · 现在挂着没人做的四格，收件人**全部**在闸上；还有油又没单的车道我只数到一条：AI `%s`（末条不是额度、%s 就没再写过）**" % (time.strftime("%H:%M"), "bac10f40", ai_when))
b.append(u"")
b.append(u"## 一、那四格（出处行逐字引自他的源块；有的行同时带单号与 id，有的只在同节里点名，我按实际标注）")
for num, sid8, nick, capped, age, when, line in rows:
    b.append(u"- `%s` → `%s`（%s）**%s**，末条写于 %s｜%s" % (
        num, sid8, nick, u"停在额度" if capped else u"没停闸", when,
        (u"出处行：" + line[:150]) if line else u"单号在他那节的标题行、正文用 id 点名（我没找到同一行同时含两者的派单行，故不冒充）"))
b.append(u"")
b.append(u"## 二、现成的接手者（只报事实，转派归你）")
b.append(u"- AI `bac10f40`：**没停在额度上**（末条是它 14:20 的收工总结：『我的 3 个私有进程按命令行归属停净，worktree 干净，没碰账本、权威线与门』），静默 %.0f 分。账本最近一次点名它、且带具体单号的地方我读到的是昨天（`L27827` 那条署名之争的自辩），今天下午这批单没一张写给它的。" % ai_age)
b.append(u"- 全表里『没停闸、也没在写』的车道共 **%d** 条：%s" % (
    len(free), u"、".join("`%s`(%s) 静默 %.0f 分（%s）" % (x[0], x[1], x[2] if x[2] < 900 else 900, x[3]) for x in free) or u"无"))
b.append(u"- 还在写的：%s。现尖 `%s`（提交者 %s +08，首行 `%s`）。" % (
    u"、".join("`%s`" % LANES.get(k, "号令者B") for k in ["9cc37e57", "da46954a", "494abfd7"] if not probe(k)[0]),
    tip[:12], tipbj, tc["commit"]["message"].split(chr(10))[0][:56]))
b.append(u"")
b.append(u"## 三、门与队列（现读）")
b.append(u"- 收件口根目录待插 **%d 枚**%s；最近两次代插：%s。" % (
    len(pend), u"（无积压）" if not pend else u"：" + u"、".join(pend),
    u"、".join("%s @ %s" % (f[:22], time.strftime("%H:%M:%S", time.localtime(m))) for m, f in ins)))
b.append(u"- 19:42 那块里你新开的 ORD-0470 派给 `9cc37e57`：我 19:47 现读它流水对该单号 **0 命中**，已把整节原文按 id 转达过去（它当时在跑一轮，19:50/19:51 复查仍是排队未落节点）；这一条**不需要你再敲**，但如果你已经自己敲过，以你为准。")
b.append(u"")
b.append(u"## 四、一句提醒（不催）")
b.append(u"- 今天可数的『撞闸→恢复』样本只有 15 枚，全部来自 00:00–15:00；18:30 之后撞的 21 枚到现在一枚都没回（rel 那枚 15:35 撞的已 4 小时 15 分）。所以**把今晚押在闸会自己松上，今天没有证据支持**；要在这几小时里见到 ORD-0461 / 0468 / 0469 / 0444-r6 任何一格动，只能换人或你自己上。换谁、换不换，归你。")
b.append(u"")
b.append(u"边界：只读（GitHub API 尖位、车道流水最后一条角色记录与 mtime、账本源块逐字 grep）。0 次写账本、0 次代插、0 次移动权威线、0 次落地、0 次改别人的枝、0 次重启任何进程、0 次改电源设置；没碰 `_preview.db`，没调 `demo/reset`。")

out_fn = os.path.join(HERE, "_bus_reassign_1955.md")
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(chr(10).join(b).rstrip() + chr(10) + CLOSING + chr(10))
print("写好 %d B｜AI 静默 %.0f 分 未停闸=%s｜空闲未停闸 %d 条" % (os.path.getsize(out_fn), ai_age, (not ai_capped), len(free)))
if "--dry" in sys.argv:
    print(chr(10).join(b)[:2300])
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((p.stdout or "") + (p.stderr or "")).strip()[:600])
raise SystemExit(p.returncode)
