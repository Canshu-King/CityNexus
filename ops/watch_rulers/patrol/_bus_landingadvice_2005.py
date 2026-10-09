# -*- coding: utf-8 -*-
"""值守 20:0x 贴：你正在连落的这几枚，落到第几枚该停手——4 枚候选两两相冲，而它们的主人全在闸上。

外加一条今晚的硬读数：18:38 起到 20:0x，撞闸的车**零恢复**，最久的 rel 已 76 分，
超过今早那批恢复样本的最大值 73.6 分 ⇒ 『等回血』到今天晚上已经不适用。
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
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")

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


def cap_state(sid8):
    p = max([os.path.join(BASE, f) for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")],
            key=os.path.getsize)
    n = os.path.getsize(p)
    fh = io.open(p, "rb")
    fh.seek(max(0, n - 200000))
    blob = fh.read().decode("utf-8", "replace")
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
            last = t.strip()
    return ("闸上" if (last and "daily usage limit" in last) else "没停闸"), (time.time() - os.path.getmtime(p)) / 60.0


plan = io.open(os.path.join(HERE, "landing_plan_2000.txt"), encoding="utf-8", errors="replace").read()
tip_plan = next((re.search(r"现尖 `([0-9a-f]{12})", x).group(1) for x in plan.split(chr(10)) if "现尖" in x), "")
cands = re.findall(r"review/(\S+)\s+头 ([0-9a-f]{10})", plan)
pairs = re.findall(r"review/(\S+)\s+× review/(\S+)\s+共 (\d+) 枚：([^\n]{0,110})", plan)
def norm(s):
    s = s.split()[0]
    return re.sub(r"-(r\d+|\d+)$", "", s)
deg = {}
for a, b, k, files in pairs:
    for x in (a, b):
        deg[norm(x)] = deg.get(norm(x), 0) + 1
tip = api("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1")["object"]["sha"]
tc = api("https://api.github.com/repos/Canshu-King/CityNexus/commits/" + tip)
tipbj = time.strftime("%H:%M:%S", time.localtime(time.mktime(time.strptime(tc["commit"]["committer"]["date"][:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600))
OWNER = {"qoder-0462-member-card-r2": ("4033270f", "0383"),
         "newlane2-ord0463-screenshot-shell": ("6a150e1e", "newlane2"),
         "newlane-ord0444-collections-r6": ("1ba48dbf", "newlane"),
         "Q-ord0467-v13-contract-enum-r1": ("2d2d7428", "0441")}
own = {}
for name, _h in cands:
    key = name.split()[0]
    for k2, v in OWNER.items():
        if key.startswith(k2.split("-r")[0][:22]) or key == k2:
            own[key] = v
own = {k: v for k, v in own.items() if k in [c[0].split()[0] for c in cands]}
# 今晚有没有人回血：末条不是额度、且最近 12 分内写过
live = []
capped_now = []
for sid8, nick in [("9cc37e57", "0421"), ("2d2d7428", "0441"), ("a6b95d59", "DSH"), ("e4f3490f", "道0370"),
                   ("a68b0631", "rel"), ("1ba48dbf", "newlane"), ("6a150e1e", "newlane2"), ("4033270f", "0383"),
                   ("49fe0d7b", "N3"), ("9759f1ac", "N2"), ("1d64acf5", "S4"), ("3b65af59", "map"),
                   ("be19052c", "dt"), ("8ac89982", "R0417"), ("8e5245f0", "道0369"), ("904a042d", "Q"), ("da46954a", "新车道"), ("494abfd7", "号令者B")]:
    st, age = cap_state(sid8)
    (capped_now if st == "闸上" else live).append((nick, sid8, age))

b = []
b.append(u"**值守 %s · 你要落的这 4 枚两两相冲 4 对，而它们的主人**现在全部**停在闸上：每多落一枚，就多一条只有明早才还得上的 rebase 债。另：今晚 18:38 起撞闸的车到现在零恢复。**" % time.strftime("%H:%M"))
b.append(u"")
b.append(u"## 一、落地顺序表（%s 那跑，只读；现尖按该跑读到的 `%s`，此刻 API 现读已是 `%s`／%s）" % (u"20:02", tip_plan, tip[:12], tipbj))
for name, h in cands:
    key = name.split()[0]
    o = own.get(key)
    st = u"车主未知"
    if o:
        s, a = cap_state(o[0])
        st = u"车主 %s `%s` %s（末写 %.0f 分前）" % (o[1], o[0], s, a)
    b.append(u"- `review/%s` 头 %s｜与别人相冲 %d 对｜%s" % (key, h, deg.get(norm(key), 0), st))
b.append(u"- 互斥明细：%s" % u"；".join("`%s`×`%s` 共 %s 枚（%s）" % (a.split()[0][:30], b_.split()[0][:30], k, files.strip()[:66]) for a, b_, k, files in pairs))
b.append(u"- 我的读法（落不落归你，我 0 次落地、0 次动权威线）：4 枚里**没有任何一枚是「与谁都不同改」**，也就是说**任何一枚落地都会让另外几枚的下一代需要 rebase**；而那几枚的车主此刻全在闸上（上面逐枚标了）。所以按今天的油量，今晚这一轮**最多少落**：要落只落你最需要亲测的那一枚（`Q-ord0467-v13-contract-enum-r1` 是 ORD-0467 的新契约枚举、`qoder-0462-member-card-r2` 只与 0463 在 `frontend/src/i18n/LocaleContext.tsx` 一处相冲），其余三枚挂到明早车道自己 rebase，比现在硬落更省。" )
b.append(u"")
b.append(u"## 二、今晚的回血实测（这条推翻我 19:16 的语气）")
b.append(u"- 18:38:36 第一枚撞闸（道0370）到 %s 为止：**撞过闸的 16 条里，此刻仍停在闸上 %d 条**；`rel` 已连撞 3 次、末写距今 %.0f 分。" % (
    time.strftime("%H:%M"), len(capped_now), sorted([x[2] for x in capped_now])[-1] if capped_now else 0))
b.append(u"- 今早可数的恢复样本最大 **73.6 分**；现在最早那批（18:38–18:44）已经 78–84 分没回 ⇒ **今晚这一波比早上那波更硬**，我 19:16 说的『到 21:00 前多数能复工』今天没有依据（19:23 已另帖勘误，这里再报一次现值）。")
b.append(u"- 此刻末条不是额度、还在写的只有 %d 条：%s（另：AI `bac10f40` 没撞闸但 14:20 起没单，CMDR-A 是另一份号令者实例、11:36 起没写）。" % (
    len([x for x in live if x[2] < 12]), u"、".join("`%s`(%s) %.0f 分前" % (x[0], x[1], x[2]) for x in live if x[2] < 12)))
b.append(u"")
b.append(u"边界：只读（GitHub API 尖位与提交时间、`landing_plan` 那跑的 ls-remote/merge-base/ls-tree 预测、车道流水最后一条角色记录）。0 次写账本、0 次代插、0 次落地、0 次移动权威线、0 次改别人的枝、0 次重启任何进程、0 次改电源设置；没碰 `_preview.db`，没调 `demo/reset`。")

out_fn = os.path.join(HERE, "_bus_landingadvice_2005.md")
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(chr(10).join(b).rstrip() + chr(10) + CLOSING + chr(10))
print("写好 %d B｜候选 %d 枚｜互斥 %d 对｜仍闸上 %d｜在写 %d" % (os.path.getsize(out_fn), len(cands), len(pairs), len(capped_now), len([x for x in live if x[2] < 12])))
if "--dry" in sys.argv:
    print(chr(10).join(b)[:2200])
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((p.stdout or "") + (p.stderr or "")).strip()[:600])
raise SystemExit(p.returncode)
