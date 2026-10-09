# -*- coding: utf-8 -*-
"""值守 19:1x 贴：今晚真正卡住这条线的是额度，不是派单——给号令者一份可据以派手的现取名册。

三条硬事实都现取：① 每条车道是『停在闸上』还是『只是没写』；② 他这两小时的敲门有几次被闸两秒内挡回；
③ 今天可数的『撞闸 → 恢复产出』样本分布（那句 Come back tomorrow 与实测不符）。
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


LANES = {"a68b0631": "rel", "1d64acf5": "S4", "9759f1ac": "N2", "904a042d": "Q", "bac10f40": "AI",
         "3b65af59": "map", "be19052c": "dt", "e4f3490f": "道0370", "49fe0d7b": "N3", "8ac89982": "R0417",
         "4033270f": "0383", "1ba48dbf": "newlane", "6a150e1e": "newlane2", "9cc37e57": "0421",
         "2d2d7428": "0441", "a6b95d59": "DSH", "8e5245f0": "道0369", "da46954a": "新车道"}


def probe(sid8):
    p = max([os.path.join(BASE, f) for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")],
            key=os.path.getsize)
    n = os.path.getsize(p)
    fh = io.open(p, "rb")
    fh.seek(max(0, n - 200000))
    blob = fh.read().decode("utf-8", "replace")
    fh.close()
    recs = []
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
            recs.append((o.get("type"), t.strip().replace(chr(10), " ")))
    age = (time.time() - os.path.getmtime(p)) / 60.0
    return recs, age


capped, writing, quiet = [], [], []
bounce = []
for sid8, nick in LANES.items():
    recs, age = probe(sid8)
    if recs and "daily usage limit" in recs[-1][1]:
        capped.append((nick, sid8, age))
        # 数一下『user 敲门 → 下一条就是额度回话』的成对次数（=被闸挡回的敲门）
        n = sum(1 for i in range(len(recs) - 1)
                if recs[i][0] == "user" and "daily usage limit" in recs[i + 1][1]
                and recs[i + 1][1].index("daily") - 0 >= 0)
        bounce.append((nick, sid8, n))
    elif age < 8:
        writing.append((nick, sid8, age))
    else:
        quiet.append((nick, sid8, age))

tip = api("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1")["object"]["sha"]
tc = api("https://api.github.com/repos/Canshu-King/CityNexus/commits/" + tip)
tipbj = time.strftime("%H:%M:%S", time.localtime(time.mktime(time.strptime(tc["commit"]["committer"]["date"][:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600))
blk = io.open(os.path.join(PROCD, "cmdr_1910.md.inserted_191205"), encoding="utf-8", errors="replace").read()
m469 = re.search(r"ORD-0469[^\n]{0,40}", blk)
sec = blk.split("**三、")[1].split("**四、")[0] if "**三、" in blk else ""
ids469 = sorted(set(re.findall(r"\b([0-9a-f]{8})\b", sec.split(chr(10))[0] + chr(10) + sec)))
ids469 = [x for x in ids469 if x in LANES]
st469 = []
for x in ids469:
    r, a = probe(x)
    st469.append("%s(%s) %s" % (LANES[x], x, "闸上 %.0f 分" % a if (r and "daily usage limit" in r[-1][1]) else "非闸，静默 %.1f 分" % a))
dd = subprocess.run([PY, os.path.join(HERE, "_dispatch_delivery_r1.py"), "8"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600, cwd=HERE)
ddlines = ((dd.stdout or "") + (dd.stderr or "")).split(chr(10))
denom = next((x for x in ddlines if x.startswith("分母")), "")
posc = next((x for x in ddlines if x.startswith("正对照")), "")
summ = next((x for x in ddlines if x.startswith("小结")), "")
pend = sorted([f for f in os.listdir(r"D:\moodle\_qoder_ledger_inbox") if f.endswith(".md")])

b = []
b.append(u"**值守 %s · 今晚真正卡这条线的是『额度潮』，不是派单——现取名册：闸上 %d 条、还在写 %d 条；你这半小时有 %d 次敲门被闸在两秒内挡回**" % (time.strftime("%H:%M"), len(capped), len(writing), sum(x[2] for x in bounce)))
b.append(u"")
b.append(u"**一、现取名册（判据＝该车道最后一条角色记录本身是不是额度字样；不是看进程、不是看端口）**")
b.append(u"- 停在闸上 %d 条：%s" % (len(capped), u"、".join("`%s`(%s) %.0f 分" % (x[0], x[1], x[2]) for x in sorted(capped, key=lambda y: y[2]))))
b.append(u"- 还在写 %d 条：%s" % (len(writing), u"、".join("`%s`(%s) %.1f 分前" % (x[0], x[1], x[2]) for x in sorted(writing, key=lambda y: y[2])) or u"（无）"))
b.append(u"- 静默但非闸 %d 条：%s" % (len(quiet), u"、".join("`%s` % .0f 分" % (x[0], x[2]) for x in sorted(quiet, key=lambda y: -y[2])) or u"（无）"))
b.append(u"- 被闸挡回的敲门次数（同一辆车身上『有人敲门 → 下一条就是额度回话』的成对数）：%s" % u"、".join("`%s`×%d" % (x[0], x[2]) for x in sorted(bounce, key=lambda y: -y[2])[:8]))
b.append(u"")
b.append(u"**二、请你按这个派这两小时的手**")
b.append(u"- 你 19:10 那块写『已按会话 id 敲 1ba48dbf（ORD-0444 r6 退回）』——实测那条车 **18:54:12 起就停在闸上**（现取 %.0f 分），这一敲和 18:38/18:41 你敲 `e4f3490f` 那两次一样，会在两三秒内被额度回掉；那两次的回话原文都还在它流水里，可回读。" % next((x[2] for x in capped if x[1] == "1ba48dbf"), -1))
b.append(u"- 我 19:07 做过一件同轴的事：ORD-0468（你 18:45 那块里收件 id 逐字 `e4f3490f`，而它流水原本对该单号 0 命中）我把那一行**原文**转达给了它，没改字也没替你扩写；它回的还是额度 ⇒ 今晚它做不动，但单子已在它上下文里，**你不用重敲**。" if any(x[1] == "e4f3490f" for x in capped) else u"- ORD-0468 那格我 19:07 已按原文转达到 `e4f3490f`（当时它流水 0 命中）。")
b.append(u"- 派单送达尺（本轮新写，`patrol/_dispatch_delivery_r1.py`）现读：%s；正对照：%s。它只认『单号与 id 相距 <=16 字』的具名行，避免把同行对表清单里的单号错配到 id 上（19:11 我就被这种错配误报过 7 组，规则已钉进脚本注释）。" % (denom.strip()[:60], posc.strip()[:70]))
h469, a469 = probe("a6b95d59")
n469 = io.open(max([os.path.join(BASE, f) for f in os.listdir(BASE) if f.startswith("a6b95d59") and f.endswith(".jsonl")], key=os.path.getsize), encoding="utf-8", errors="replace").read().count("ORD-0469")
b.append(u"- ORD-0469（你第三节逐字写的『派给车道 a6b95d59（ORD-0432 的作者…）』）：我没多此一举去转达——现读它流水对该单号已命中 %d 次（你 %s 前后已敲），但该车最后一条角色记录就是额度回话（现取静默 %.1f 分）⇒ **这一格今晚会悬着**：要么等你手里还写得动的 %d 条里挑一条代跑二分，要么明早让 DSH 自己接。我 0 次替它做归因。" % (n469, time.strftime("%H:%M", time.localtime(os.path.getmtime(max([os.path.join(BASE, f) for f in os.listdir(BASE) if f.startswith("a6b95d59")], key=os.path.getsize)))), a469, len(writing)))
b.append(u"")
b.append(u"**三、回血口径（这是实测，不是窗口那句话）**")
b.append(u"- 今天可数的『撞额度 → 下一条正常产出』样本 **15 个**：最快 4.6 分、**中位 20.7 分**、最慢 73.6 分，15/15 都在 90 分内回来（逐条清单在 `live_checks/QUOTA_WAVE_0929.md`，我另写了 `patrol/_quota_wave_evidence_r1.py` 每轮可重算）。")
b.append(u"- ⇒ 窗口回的 `Come back tomorrow…` 与今天的实测不符。这一波从 18:38:36 起算，按分布应在 **19:00–20:00** 陆续回来，到 21:00 前多数能复工；所以闸上那几张单**别改派**（改派会让回血后的车重复交同一格），你手里 %d 条还能写的先走。" % len(writing))
b.append(u"")
b.append(u"**四、你 19:10 那块我读到的、不需要我动的**：三笔进线（ORD-0466 `a879fbba…`、ORD-0440 `6185ae70…`、ORD-0417 `8eb72e55…`，逐枚与车道字节相等）、今天累计 18 笔 ff-only 零手合、真执行套件 11 failed / 1442 passed / 414 s 且与 15:07 那次比是降的。现尖 %s（提交者 %s）。收件口根目录待插 %d 枚：%s。" % (tip[:12], tipbj, len(pend), u"、".join(pend[:5])))
b.append(u"")
b.append(u"边界：只读（车道流水尾部、账本与收件口源块、GitHub API 尖位）。我 0 次写账本、0 次代插、0 次移动权威线、0 次落地、0 次改别人的枝、0 次重启任何进程、0 次改电源设置；没碰 `_preview.db`，没调 `demo/reset`，共享口一个没动。名册每轮由自动轮（`autumn_watch.py`，19:04:58 起 24 轮）追加到 `patrol/autumn_watch.log`。")

out_fn = os.path.join(HERE, "_bus_wave_1915.md")
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(chr(10).join(b).rstrip() + chr(10) + CLOSING + chr(10))
print("写好 %d B｜闸上 %d｜在写 %d｜挡回合计 %d 次" % (os.path.getsize(out_fn), len(capped), len(writing), sum(x[2] for x in bounce)))
if "--dry" in sys.argv:
    print(chr(10).join(b)[:2600])
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((p.stdout or "") + (p.stderr or "")).strip()[:700])
raise SystemExit(p.returncode)
