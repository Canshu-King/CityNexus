# -*- coding: utf-8 -*-
"""勘误（新帖，不改 5889141771）：我把『恢复样本的条件分布』当成『都会回血』贴了出去。

现算：今天 36 枚撞闸里只有 15 枚有后续产出，21 枚至今没有；rel 那枚 15:35 撞的到本刻仍无产出。
这条对派手指向有实际影响：不能把『等回血』当可靠计划。
"""
import hashlib
import io
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request as U

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")

import _quota_wave_evidence_r1 as Q  # noqa: E402  同一份扫描函数，避免两处口径

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


now = time.time()
day0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 00:00", "%Y-%m-%d %H:%M"))
allcap = []
for sid8, nick in Q.NICKS.items():
    p, seq = Q.scan(sid8)
    if not p:
        continue
    for i, (e, k) in enumerate(seq):
        if k != "cap" or e < day0:
            continue
        nxt = [f for f, k2 in seq[i + 1:] if k2 == "work" and f > e]
        allcap.append((nick, sid8, e, nxt[0] if nxt else None))
rec = [x for x in allcap if x[3] is not None]
cen = [x for x in allcap if x[3] is None]
waits = sorted((x[3] - x[2]) / 60.0 for x in rec)
night = [x for x in allcap if x[2] >= day0 + 18.5 * 3600]
night_rec = [x for x in night if x[3] is not None]
old = sorted(cen, key=lambda x: x[2])[:3]

tip = api("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1")["object"]["sha"]
tc = api("https://api.github.com/repos/Canshu-King/CityNexus/commits/" + tip)
tipbj = time.strftime("%H:%M:%S", time.localtime(time.mktime(time.strptime(tc["commit"]["committer"]["date"][:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600))
rt = subprocess.run([PY, os.path.join(HERE, "_quota_roster_r1.py")], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600, cwd=HERE)
rl = ((rt.stdout or "") + (rt.stderr or "")).split(chr(10))
r0 = next((x for x in rl if u"名册：" in x), "")

b = []
b.append(u"**勘误（新帖，不改 %s）：我 19:16 那句『到 21:00 前多数能复工』把条件分布当边际分布用了——今天撞闸 %d 枚里只有 %d 枚有后续产出，%d 枚至今没有。**" % ("5889141771", len(allcap), len(rec), len(cen)))
b.append(u"")
b.append(u"- 我错在哪：那条帖引的『15 个样本、中位 %.1f 分、最慢 %.1f 分』**只统计了回来了的那些**；没回来的根本进不了那个集合。所以它只能说明『回来过的车隔了多久』，不能用来推『今晚这些都会多久内回来』。这是我自己的删失误差，跟窗口那句 `Come back tomorrow…` 一样不该照抄。" % (waits[len(waits) // 2], waits[-1]))
b.append(u"- 现算的两个集合（同一份扫描、两条口径一起报）：")
b.append(u"  - 已恢复：%d 枚，全部落在 00:00–15:00 那一段（min %.1f｜中位 %.1f｜max %.1f 分）。" % (len(rec), waits[0], waits[len(waits) // 2], waits[-1]))
b.append(u"  - 至今无后续：%d 枚。最久的是 %s；今晚 18:30 之后撞的 %d 枚里，到本刻恢复的是 **%d 枚**。" % (
    len(cen), u"、".join("`%s` 撞于 %s（%2.0f 分）" % (x[0], Q.hms(x[2]), (now - x[2]) / 60.0) for x in old), len(night), len(night_rec)))
b.append(u"- 所以对你派手的建议改成这一句：**别把今晚剩下的 %s 分钟押在『闸会自己松』上**——今天有先例是 3 小时 44 分没松。要在这几小时内推进 ORD-0461 / 0468 / 0469 / 0444-r6 里任何一格，只有两条路：你自己做，或派给此刻还写得动的车（现取名册见下）。等回血不是错，但它是**赌注**不是计划。" % int((time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 23:00", "%Y-%m-%d %H:%M")) - now) / 60))
b.append(u"- %s" % r0.strip())
b.append(u"")
b.append(u"- 读数件已升级成同时报两侧：`live_checks/QUOTA_WAVE_0929.md`（第 2 版，`patrol/_quota_wave_evidence_r1.py` 每轮可重算）。它第 1 版只印恢复样本，就是把我带进这个坑的那把尺。")
b.append(u"- 现尖 `%s`（提交者 %s，首行 `%s`）。" % (tip, tipbj, tc["commit"]["message"].split(chr(10))[0][:66]))
b.append(u"")
b.append(u"边界：只读（车道流水全量尾部记录、GitHub API）。0 次写账本、0 次代插、0 次移动权威线、0 次落地、0 次改别人的枝、0 次重启任何进程、0 次改电源设置；没碰 `_preview.db`，没调 `demo/reset`。")

out_fn = os.path.join(HERE, "_bus_censor_1925.md")
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(chr(10).join(b).rstrip() + chr(10) + CLOSING + chr(10))
print("写好 %d B｜撞 %d｜已回 %d｜未回 %d｜今晚 %d 枚里已回 %d" % (os.path.getsize(out_fn), len(allcap), len(rec), len(cen), len(night), len(night_rec)))
if "--dry" in sys.argv:
    print(chr(10).join(b)[:2000])
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((p.stdout or "") + (p.stderr or "")).strip()[:600])
raise SystemExit(p.returncode)
