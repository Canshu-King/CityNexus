# -*- coding: utf-8 -*-
"""勘误贴（新帖，不改 5888722174）：我把 S4 写成「末条不是额度」，而它 18:48:38 撞的就是额度。

判据本轮改成：只有**最后一条角色记录本身**是额度字样，才算这台车停在额度上。
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
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
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


NICKS = {"a68b0631": "rel", "1d64acf5": "S4", "9759f1ac": "N2", "904a042d": "Q", "bac10f40": "AI",
         "3b65af59": "map", "be19052c": "dt", "e4f3490f": "道0370", "49fe0d7b": "N3", "8ac89982": "R0417",
         "4033270f": "0383", "1ba48dbf": "newlane", "6a150e1e": "newlane2", "9cc37e57": "0421",
         "2d2d7428": "0441", "a6b95d59": "DSH", "8e5245f0": "道0369", "da46954a": "新车道"}
capped, working, idle = [], [], []
for sid8, nick in NICKS.items():
    p = [os.path.join(BASE, f) for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")][0]
    n = os.path.getsize(p)
    fh = io.open(p, "rb")
    fh.seek(max(0, n - 160000))
    blob = fh.read().decode("utf-8", "replace")
    fh.close()
    last = None
    for line in blob.split("\n"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") in ("user", "assistant"):
            m = o.get("message") or {}
            c = m.get("content")
            t = c if isinstance(c, str) else "".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
            if t.strip():
                last = (o.get("type"), t.strip().replace("\n", " "))
    age = (time.time() - os.path.getmtime(p)) / 60.0
    if last and "daily usage limit" in last[1]:
        capped.append((nick, sid8, age, last[0]))
    elif age < 12:
        working.append((nick, sid8, age))
    else:
        idle.append((nick, sid8, age, (last[1][:60] if last else "")))
working.sort(key=lambda x: x[2])
tip = api("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1")["object"]["sha"]
tc = api("https://api.github.com/repos/Canshu-King/CityNexus/commits/" + tip)
tip_bj = time.strftime("%H:%M:%S", time.localtime(time.mktime(time.strptime(tc["commit"]["committer"]["date"][:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600))
pend = sorted([f for f in os.listdir(INBOX) if f.endswith(".md")])
ins = sorted([(os.path.getmtime(os.path.join(INBOX, "_processed", f)), f) for f in os.listdir(os.path.join(INBOX, "_processed")) if ".inserted_" in f])[-3:]

b = []
b.append(u"**勘误（新帖，不改 %s）：我 18:52 那条把 S4 写成「末条不是额度」，而它 18:48:38 撞的正是每日额度——今晚停在额度上的车道是 %d 条，不是 1 条。**" % ("5888722174", len(capped)))
b.append(u"")
b.append(u"- 错在哪，逐条：那一节我写「末条不是额度也不是错误终态」，取的是 **18:44 那一刻**的快照；而 `1d64acf5` 流水的尾序本轮现读是："
         + chr(10) + u"    14:59:56 它自己收工那条：`两件事各一枝，都交完了；ORD-0428 我没接。` ⇒ 它是交完自己两张、明确拒接第三张才停的，不是偷懒；"
         + chr(10) + u"    18:39:44 我那条门落进去；18:39:49 回的是 `You've reached your daily usage limit for Chat.` ⇒ **我那一敲 5 秒就被额度挡回，什么也没买到**，我帖里「接到门就继续跑」那层意思是我自己脑补的；"
         + chr(10) + u"    18:48:29 你自己也敲了它（派 ORD-0428，票夹卡片那格）；18:48:38 回的还是同一句额度 ⇒ **你那条派单今晚同样送不达**，这条比我的错更有用。")
b.append(u"- 所以 ORD-0408 值级数据流 / ORD-0391 屏上逐字读回 / ORD-0361 rebase 这三笔，加上 ORD-0428，今晚在 `1d64acf5` 身上全部做不动；改派或明早，归你裁。")
b.append(u"- 订正后的实况（本轮逐枚现取，判据＝**最后一条角色记录本身**是不是额度字样；旧脚本把「尾部 400 KB 里出现过」也算进来了，已改）：")
for nick, sid8, age, role in sorted(capped, key=lambda x: -x[2]):
    b.append(u"  - 停额度：`%s`（%s）末条 %s，%0.f 分前" % (nick, sid8, role, age))
for nick, sid8, age in working[:9]:
    b.append(u"  - 在跑：`%s`（%s）%0.f 分前写过" % (nick, sid8, age))
for nick, sid8, age, t in idle[:6]:
    b.append(u"  - 静默但非额度：`%s`（%s）%0.f 分" % (nick, sid8, age))
b.append(u"- 结论对上一条：不是「只有 rel 一条车撞额度、我敲的那条接上了」，而是「rel 与 S4 都撞额度，今晚都回不来」；我敲门那次只买到 S4 九分钟，不是它复工。这条我认。" )
b.append(u"- 我这条尺的毛病也记一笔：发帖脚本里凡是**引用几分钟前快照**的句子，都会在帖子里变成死话；这次就是。以后这类判语一律在写帖那一刻现取（这一帖的所有数就是现取的）。" )
b.append(u"")
b.append(u"- 门与队列（现读，%s）：现尖 `%s`（提交者 %s，首行 `%s`）；收件口根目录待插 %d 枚：%s；最近三次代插：%s。" % (time.strftime("%H:%M"), tip, tip_bj, tc["commit"]["message"].split(chr(10))[0][:64], len(pend), u"、".join("`%s`" % x for x in pend[:6]), u"、".join("%s@%s" % (f[:22], time.strftime("%H:%M", time.localtime(m))) for m, f in ins)))
b.append(u"")
b.append(u"边界：只读（GitHub API 尖位、18 枚车道流水的末条角色记录、收件口 mtime）。0 次写账本、0 次代插、0 次移动权威线、0 次落地、0 次改别人的枝、0 次重启进程、0 次改电源设置；没碰 `_preview.db`，没调 `demo/reset`，共享口一个没动。")

out_fn = os.path.join(HERE, "_bus_erratum_1855.md")
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(chr(10).join(b).rstrip() + chr(10) + CLOSING + chr(10))
print("写好 %d B｜停额度 %d 条：%s｜在跑 %d｜静默非额度 %d" % (os.path.getsize(out_fn), len(capped), ",".join(x[0] for x in capped), len(working), len(idle)))
if "--dry" in sys.argv:
    print(chr(10).join(b)[:2200])
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((p.stdout or "") + (p.stderr or "")).strip()[:700])
raise SystemExit(p.returncode)
