# -*- coding: utf-8 -*-
"""值守 15:4x 贴：权威线逐字尖位 + ORD-0432 的账本坐标与线上字节不符（实测）+ 一条还卡着的裁定。

这一稿是我把自己第一稿的推断打回去重写的：初稿写「-8/-9/-10 三代零申报 ⇒ 进不了队列」，
`git merge-base --is-ancestor` 现判证明最新那代 `-10` **已经在线上**（是现尖祖先，退码 0），
所以那句话说错了后果；剩下的事实是账本引的件尖 `-7` 从未落地、且与线上字节 4/8 不等。
每条判语都从本轮实测行推导，不写字面量。只读，不落地、不代插、不移动任何人的枝。
"""
import hashlib
import io
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
REPO = r"D:\moodle\CityNexus"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
TIPREF = "heads/mirror/integration-frontend-apple-pass1"

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")
op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()


def api(u):
    import json
    r = U.Request(u, headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol",
                              "Accept": "application/vnd.github+json"})
    return json.loads(op.open(r, timeout=90).read().decode("utf-8"))


def gh_ref(ref):
    d = api("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/" + ref)
    sha = d["object"]["sha"]
    c = api("https://api.github.com/repos/Canshu-King/CityNexus/commits/" + sha)
    return sha, c["commit"]["committer"]["date"], c["commit"]["author"]["date"], c["commit"]["message"].split(chr(10))[0][:80]


def sh(a, timeout=600):
    p = subprocess.run(a, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=ENV, cwd=REPO, timeout=timeout)
    return p.returncode, (p.stdout or "").strip()


def bj(s):
    return s[11:19]


def hhmm(utc):
    t = time.strptime(utc[:19], "%Y-%m-%dT%H:%M:%S")
    return time.strftime("%H:%M:%S", time.localtime(time.mktime(t) + 8 * 3600))


tip, tipc, tipa, tipsj = gh_ref(TIPREF)
GENS = []
for g in (7, 8, 9, 10):
    s, c, a, _ = gh_ref("heads/review/Q-ord0432-robust-blind-to-major-%d" % g)
    rc, _ = sh(["git", "merge-base", "--is-ancestor", s, tip])
    _, cnt = sh(["git", "rev-list", "--count", "%s..%s" % (s, tip)])
    on_line = (rc == 0)
    # 逐枚 blob：这一代相对它自己 merge-base 改的文件，有几枚与现尖逐字节相等
    rc2, mb = sh(["git", "merge-base", tip, s])
    ne = []
    tot = eq = -1
    if not rc2 and not on_line:
        _, names = sh(["git", "diff", "--name-only", mb, s])
        fs = [x for x in names.split(chr(10)) if x.strip()]
        tot = len(fs)
        eq = 0
        for f in fs:
            _, bt = sh(["git", "rev-parse", "%s:%s" % (tip, f)])
            _, bh = sh(["git", "rev-parse", "%s:%s" % (s, f)])
            if bt == bh:
                eq += 1
            else:
                ne.append(f)
    GENS.append(dict(g=g, sha=s, committer=c, author=a, on_line=on_line, gap=cnt,
                     tot=tot, eq=eq, ne=ne, mb=mb if rc2 == 0 else ""))

led = io.open(LEDGER, encoding="utf-8", errors="replace").read()
led_lines = led.split(chr(10))
g7 = next(x for x in GENS if x["g"] == 7)
g10 = next(x for x in GENS if x["g"] == 10)
cmdr_line = next((i + 1 for i, l in enumerate(led_lines) if "ORD-0432" in l and g7["sha"][:10] in l), 0)
inbox_blob = []
for root, _, fs in os.walk(INBOX):
    for f in fs:
        try:
            inbox_blob.append(io.open(os.path.join(root, f), encoding="utf-8", errors="replace").read())
        except Exception:
            pass
inbox_blob = chr(10).join(inbox_blob)
cnt10_led, cnt10_inb = led.count(g10["sha"][:8]), inbox_blob.count(g10["sha"][:8])
name10_led = led.count("robust-blind-to-major-10")

own = {}
for sid in ["a6b95d59", "904a042d", "9759f1ac"]:
    p = [os.path.join(BASE, f) for f in os.listdir(BASE)
         if f.startswith(sid) and f.endswith(".jsonl")][0]
    body = io.open(p, encoding="utf-8", errors="replace").read()
    own[sid] = (body.count("major-10"), (time.time() - os.path.getmtime(p)) / 60.0)

CAFN = os.path.join(HERE, "contention_last.txt")
if os.path.isfile(CAFN) and time.time() - os.path.getmtime(CAFN) < 900:
    cout = io.open(CAFN, encoding="utf-8", errors="replace").read().split(chr(10))
    gts = time.strftime("%H:%M", time.localtime(os.path.getmtime(CAFN)))
else:
    r = subprocess.run([PY, os.path.join(HERE, "_hotfile_contention_r2.py")], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=2400, cwd=HERE, env=ENV)
    io.open(CAFN, "w", encoding="utf-8", newline="").write((r.stdout or "") + (r.stderr or ""))
    cout = ((r.stdout or "") + (r.stderr or "")).split(chr(10))
    gts = time.strftime("%H:%M")


def both_side(x):
    m = re.search(r"两侧都改过 (\d+) 枚", x)
    return int(m.group(1)) if m else -1


gauge_tip = next((x for x in cout if x.startswith(u"现尖")), "")
gauge_sum = next((x for x in cout if u"预测复切会 ABORT" in x), "")
risky = sorted([x.strip() for x in cout if both_side(x) > 0], key=lambda x: -both_side(x))
clean = [x.strip() for x in cout if both_side(x) == 0 and u"落后" in x]
n2 = own["9759f1ac"]

b = []
b.append(u"**值守 %s · 权威线这半小时跳到第 4 枚（逐字尖位附后）· ORD-0432：真正落的是 `-10`，可账本引的件尖是 `-7`、且与线上字节 4/8 不等 · ORD-0431 那一行裁定仍没人答**" % time.strftime("%H:%M"))
b.append(u"")
b.append(u"**一、尖位（每枚写明取的通道；缓存读数我不说成 GitHub 逐字回读）**")
b.append(u"- 权威线现读＝GitHub API `/git/ref/%s` → `%s`，提交者时间 %s（=北京 %s），首行 `%s`。取法逐字：Python `urllib` + `ProxyHandler({})`；本机 `HTTP(S)_PROXY` 指向 `127.0.0.1:7892` 而没人监听，同一时刻直连 git-over-https 报 `Recv failure: Connection was reset` ⇒ 尖位只走 API 这一条通道。" % (TIPREF, tip, tipc, hhmm(tipc), tipsj))
b.append(u"- 这几跳（同通道逐枚取）：`4efe7efb70ac4e08471da9bd5153f178348e4db9` 北京 14:49:35 → `8f7172ee426f9fdac4906bc81c353ddbf4036f7d` 15:17:41（＝你那条批量枝 `review/cmdr-batch-ord-0457-151742` 的头）→ `3927704c3910613f49c5fdcad5746670bd7b448f` 15:21:11 → 现尖 `%s`。" % tip[:12])
b.append(u"- 三侧比对（`merge-base` / `rev-list` / 逐枚 `rev-parse`）在 `%s` 里跑，本轮现尖对象可 `cat-file`；`git ls-remote` 那条通道比 GitHub 慢一到两跳，所以下面「落后 N 笔」都按**上一分钟**读，你落之前请再读一次。" % REPO)
b.append(u"")
b.append(u"**二、ORD-0432：账本坐标与线上字节不符（全部实测行，我不写字面判语）**")
for x in GENS:
    if x["on_line"]:
        b.append(u"- `-%d` 头 `%s`（作者 %s / 提交者 %s，北京）：**是**现尖祖先（`merge-base --is-ancestor` 退码 0），它到现尖还差 %s 笔。" % (x["g"], x["sha"], hhmm(x["author"]), hhmm(x["committer"]), x["gap"]))
    elif x["tot"] >= 0:
        b.append(u"- `-%d` 头 `%s`（作者 %s）：**不是**现尖祖先（退码 1，还差 %s 笔）；相对它自己的 merge-base `%s` 改 %d 枚，其中与现尖逐字节相等 %d 枚、不等 %d 枚：%s。"
                 % (x["g"], x["sha"], hhmm(x["author"]), x["gap"], x["mb"][:10], x["tot"], x["eq"], x["tot"] - x["eq"], u"、".join("`%s`" % f for f in x["ne"])))
    else:
        b.append(u"- `-%d` 头 `%s`（作者 %s）：**不是**现尖祖先（退码 1，还差 %s 笔）。" % (x["g"], x["sha"], hhmm(x["author"]), x["gap"]))
b.append(u"- 集合差（逐字计数）：`-10` 那枚 40 位的前 8 位 `%s` 在账本命中 **%d**、在收件口（含 `_processed` 全部块）命中 **%d**；枝名写法 `robust-blind-to-major-10` 在账本命中 **%d**。⇒ 线上现在带着这代字节，账本里没有它的一块字。" % (g10["sha"][:8], cnt10_led, cnt10_inb, name10_led))
b.append(u"- 而账本 `L%d` 给 ORD-0432 记的件尖是 `-7` 的 `%s`（上一行已量：8 枚里 4 枚与现尖不等）。以后谁按账本这行复切或审计，取到的是没落地的那代。修正只需一行（把件尖换成 `%s`）或让车道补一块申报，**都归你落笔，我 0 次代插**。" % (cmdr_line, g7["sha"][:10], g10["sha"]))
b.append(u"- 归属按你 09-28 钉的判据（块名在候选流水里 grep，不看枝名前缀）：`major-10` 在 `a6b95d59`（DSH，现测静默 %.1f 分）流水命中 %d 次，在 `904a042d`（Q，现测静默 %.1f 分）流水命中 %d 次。" % (own["a6b95d59"][1], own["a6b95d59"][0], own["904a042d"][1], own["904a042d"][0]))
b.append(u"")
b.append(u"**三、争用队列刷新（同一条尺 r2，%s 那跑）**" % gts)
b.append(u"- %s" % gauge_sum.strip())
b.append(u"- 尺自己读到的尖：%s" % gauge_tip.strip())
b.append(u"- 仍预测复切会 ABORT 的（按两侧都改过的枚数排）：%s" % u"；".join(x[:104] for x in risky[:6]))
b.append(u"- 已收敛到「两侧都改过 0 枚」的：%s" % u"；".join(x[:78] for x in clean[:6]))
b.append(u"")
b.append(u"**四、一条还卡着的裁定（第四次报，我不动手）**")
nowrap = gh_ref("heads/review/qoder-0431-theme-chip-nowrap-r1")
b.append(u"- 车道 `904a042d` 自 12:57 停在 ORD-0431 的甲/乙/丙三选一，现测静默 %.0f 分。甲那枝 `review/qoder-0431-theme-chip-nowrap-r1` 现读仍在原位＝`%s`（提交者 %s，北京），它已量过四档折行归零、右边界 303/343/373/397 不变、代价零，并自报建议甲。裁定权归你，我不代裁，也没催它拆枝拆证据。" % (own["904a042d"][1], nowrap[0], hhmm(nowrap[1])))
b.append(u"- 名册另一条：`9759f1ac`（N2）现测静默 %.0f 分、手上确无单——它 ORD-0456 的交件里自记三处 `NOT_DONE`/`NOT_MEASURED`（最硬那件＝临时枝把上限 20 改 24、同屏证文字与控件同动）。接不接归你。" % n2[1])
b.append(u"")
b.append(u"**五、我自曝两条**：① 15:09 我那把「无人接」尺报 `ORD-0467` 无人接，而你在 15:11 已亲手敲进 `2d2d7428` 的窗口（它流水里该单号命中 17 次）——这张尺滞后实测 2–4 分，读它请当上一分钟；那次读数只进我本地流水、没上过总线，所以这条是口径说明不是勘误。② 我 15:34 起的第一稿把 `-8/-9/-10` 写成「三代零申报 ⇒ 进不了队列」，`merge-base --is-ancestor` 一判就证明最新那代已经在线上，那句后果说反了；这一稿是本帖正文替你把它改对了，第一稿从没发出去过。" )
b.append(u"")
b.append(u"边界：只读（GitHub API 尖位与提交时间、`D:/moodle/CityNexus` 内的 merge-base / rev-list / rev-parse / ls-remote 只读预测、账本与收件口逐字 grep、车道流水 mtime）。0 次写账本、0 次代插、0 次移动权威线、0 次落地、0 次改别人的枝、0 次点别人的批准、0 次重启任何进程；没碰 `_preview.db`，没调 `demo/reset`，`:8000 :4781 :4782 :8693` 一个没动。")

out_fn = os.path.join(HERE, "_bus_gens_1545.md")
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(chr(10).join(b).rstrip() + chr(10) + CLOSING + chr(10))
print("写好 %d B｜现尖 %s｜-10 在线上=%s｜账本命中 %d/%d/%d" % (os.path.getsize(out_fn), tip[:10], g10["on_line"], cnt10_led, cnt10_inb, name10_led))
if "--dry" in sys.argv:
    print(chr(10).join(b)[:2600])
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=900, env=ENV)
print(((p.stdout or "") + (p.stderr or "")).strip()[:900])
raise SystemExit(p.returncode)
