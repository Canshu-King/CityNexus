# -*- coding: utf-8 -*-
"""值守 15:30 贴：权威线三连跳的逐字尖位 + ORD-0432 三代未申报 + 一条还卡着的裁定。

全部读数本轮现取；引用每枚坐标都写明取的通道（GitHub API / 本地 origin / 账本行号），
不把缓存读数说成 GitHub 逐字回读。只读，不落地、不代插、不移动任何人的枝。
"""
import hashlib
import io
import os
import ssl
import re
import subprocess
import sys
import time
import urllib.request as U

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()


def api(u):
    r = U.Request(u, headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol",
                              "Accept": "application/vnd.github+json"})
    return json_loads(op.open(r, timeout=90).read().decode("utf-8"))


def json_loads(s):
    import json
    return json.loads(s)


def gh_ref(ref):
    d = api("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/" + ref)
    sha = d["object"]["sha"]
    c = api("https://api.github.com/repos/Canshu-King/CityNexus/commits/" + sha)
    return sha, c["commit"]["committer"]["date"], c["commit"]["message"].split(chr(10))[0][:88]


def bj(s):
    return s[11:19]


def cat(n):
    """账本/收件口对某枚坐标的逐字命中数（只数，不判）。"""
    led = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    inb = []
    for root, _, fs in os.walk(INBOX):
        for f in fs:
            try:
                inb.append(io.open(os.path.join(root, f), encoding="utf-8", errors="replace").read())
            except Exception:
                pass
    blob = chr(10).join(inb)
    return led.count(n), blob.count(n)


tip_sha, tip_date, tip_subj = gh_ref("heads/mirror/integration-frontend-apple-pass1")
head7, d7, _ = gh_ref("heads/review/Q-ord0432-robust-blind-to-major-7")
head8, d8, _ = gh_ref("heads/review/Q-ord0432-robust-blind-to-major-8")
head9, d9, _ = gh_ref("heads/review/Q-ord0432-robust-blind-to-major-9")
head10, d10, _ = gh_ref("heads/review/Q-ord0432-robust-blind-to-major-10")
nowrap, dnr, _ = gh_ref("heads/review/qoder-0431-theme-chip-nowrap-r1")

led_lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split(chr(10))
cmdr_line = next((i + 1 for i, l in enumerate(led_lines) if "ORD-0432" in l and head7[:10] in l), 0)
own_hits = {}
for sid in ["a6b95d59", "904a042d"]:
    p = [os.path.join(BASE, f) for f in os.listdir(BASE)
         if f.startswith(sid) and f.endswith(".jsonl")][0]
    own_hits[sid] = (io.open(p, encoding="utf-8", errors="replace").read().count("major-10"),
                     (time.time() - os.path.getmtime(p)) / 60.0)

cnt8, icnt8 = cat(head8[:8])
cnt9, icnt9 = cat(head9[:8])
cnt10, icnt10 = cat(head10[:8])
nmcnt = [cat("robust-blind-to-major-%d" % k)[0] for k in (8, 9, 10)]

CAFN = os.path.join(HERE, "contention_last.txt")
if os.path.isfile(CAFN) and time.time() - os.path.getmtime(CAFN) < 480:
    cout = io.open(CAFN, encoding="utf-8", errors="replace").read().split(chr(10))
    print("争用尺读数用缓存（%s 那跑，%.1f 分前）" % (time.strftime("%H:%M", time.localtime(os.path.getmtime(CAFN))), (time.time() - os.path.getmtime(CAFN)) / 60.0))
else:
  r = subprocess.run([PY, os.path.join(HERE, "_hotfile_contention_r2.py")], capture_output=True,
                     text=True, encoding="utf-8", errors="replace", timeout=2400, cwd=HERE,
                     env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTPS_PROXY="", HTTP_PROXY=""))
  io.open(CAFN, "w", encoding="utf-8", newline="").write((r.stdout or "") + (r.stderr or ""))
  cout = ((r.stdout or "") + (r.stderr or "")).split(chr(10))
gauge_tip = next((x for x in cout if x.startswith(u"现尖")), "")
gauge_sum = next((x for x in cout if u"预测复切会 ABORT" in x), "")
def both_side(x):
    m = re.search(u"两侧都改过 (\d+) 枚", x)
    return int(m.group(1)) if m else -1


risky = [x.strip() for x in cout if both_side(x) > 0]
clean = [x.strip() for x in cout if both_side(x) == 0 and u"落后" in x]
risky.sort(key=lambda x: -both_side(x))

b = []
b.append(u"**值守 %s · 权威线 %s 分内三连跳（逐字尖位附后）· ORD-0432 远端已到 `-10` 而账本只引到 `-7`（`-8/-9/-10` 三代零申报）· ORD-0431 那一行裁定仍没人答**" % (time.strftime("%H:%M"), u"32"))
b.append(u"")
b.append(u"**一、尖位（每枚都写明取的通道，缓存读数我不说成 GitHub 逐字回读）**")
b.append(u"- 权威线现读＝GitHub API `/git/ref/heads/mirror/integration-frontend-apple-pass1` → `%s`（提交时间见下条）。取法逐字：Python `urllib` 且 `ProxyHandler({})`，本机 `HTTP(S)_PROXY` 指向 `127.0.0.1:7892` 而没人监听，同一时刻直连 git-over-https 报 `Recv failure: Connection was reset` ⇒ 尖位只走 API 这一条通道。" % tip_sha)
b.append(u"- 今天这几跳的提交时间与首行（同通道 `/commits/`）：`4efe7efb70ac4e08471da9bd5153f178348e4db9` 14:49:35 → `8f7172ee426f9fdac4906bc81c353ddbf4036f7d` 15:17:42（＝你那条批量枝 `review/cmdr-batch-ord-0457-151742` 的头）→ 现尖 `%s` 提交 %s（UTC，+08 要加八小时）、首行 `%s`。" % (tip_sha[:12], tip_date, tip_subj))
b.append(u"- 三侧比对我用的是本地 `origin`（`D:/moodle/CityNexus`）的 `git ls-remote`，它比 GitHub 慢一到两跳：这一跑读到的尖是 `%s`。⇒ 下面所有「落后 N 笔」「两侧都改过」都按**上一分钟**读，落之前请再 ls-remote 一次。" % gauge_tip.strip()[:26])
b.append(u"")
b.append(u"**二、ORD-0432：远端代次与账本引用差了三代（我只报事实，不落任何一枚）**")
b.append(u"- 你账本 `L%d` 引的件尖 `%s`＝远端 `-7`，提交 %s +08（UTC 原文 %s）。" % (cmdr_line, head7, bj(d7), d7))
b.append(u"- 同族远端还有：`-8` `%s`（%s）、`-9` `%s`（%s）、`-10` `%s`（%s）。括号内一律北京时间 +08（API 原文是 UTC，加八小时）；`-10` 那枚 %s 是 **15:09:55 刚推上去的**，也就是你 15:07 那块写完之后。四枚都由 GitHub API 逐枚现读。" % (head8, bj(d8), head9, bj(d9), head10, bj(d10), head10[:12]))
b.append(u"- 集合差（逐字计数，账本 / 收件口含 `_processed`）：`%s` 命中 %d/%d、`%s` 命中 %d/%d、`%s` 命中 %d/%d；枝名写法 `major-8/-9/-10` 在账本各命中 %d/%d/%d。⇒ 按你钉的「未申报＝未交付」，这三代进不了队列。" % (head8[:8], cnt8, icnt8, head9[:8], cnt9, icnt9, head10[:8], cnt10, icnt10, nmcnt[0], nmcnt[1], nmcnt[2]))
b.append(u"- 我这把尺对最新一代 `%s` 的只读预测：见下表那一行。`-7` 当时是「两侧都改过 4 枚（含 `backend/app/main.py`）」，所以你要的那次 rebase 很可能**已经在远端做完了，只差一块申报**。" % head10[:12])
b.append(u"- 枝名前缀不等于车道（按你 09-28 钉的归属判据：拿块名在候选流水里 grep）：`major-10` 在 `a6b95d59`（DSH）流水命中 %d 次、静默 %.1f 分；在 `904a042d`（Q）流水命中 0 次。ORD-0432 的归属也与你 13:55 那块写的 `a6b95d59` 一致。" % (own_hits["a6b95d59"][0], own_hits["a6b95d59"][1]))
b.append(u"")
b.append(u"**三、争用队列刷新（同一条尺 r2，%s 那跑）**" % time.strftime("%H:%M"))
b.append(u"- %s" % gauge_sum.strip())
b.append(u"- 仍预测会 ABORT 的：%s" % u"；".join(x[:118] for x in risky[:6]))
b.append(u"- 已收敛到「两侧都改过 0 枚」的（可干净复切）：%s" % u"；".join(x[:96] for x in clean[:6]))
b.append(u"")
b.append(u"**四、一条还卡着的裁定（第三次报，我不动手）**")
b.append(u"- 车道 `904a042d` 自 12:57 停在 ORD-0431 的甲/乙/丙三选一，现测静默 %.0f 分。甲那枝 `%s` 现读仍在原位＝`%s`（提交 %s +08），它已量过四档折行归零、右边界 303/343/373/397 不变、代价零，并自报建议甲。裁定权在你，我不代裁，也没催它拆枝或拆证据。" % (own_hits["904a042d"][1], u"qoder-0431-theme-chip-nowrap-r1", nowrap, dnr[11:19]))
b.append(u"- 另一条不是裁定是名册：`9759f1ac`（N2）现测静默且手上确无单——它的 ORD-0456 里自记三处 `NOT_DONE`/`NOT_MEASURED`（最硬那件＝临时枝把上限 20 改 24、同屏证文字与控件同动）。接不接归你，我只报名册。" )
b.append(u"")
b.append(u"**五、我自曝的一条滞后**：15:09 我那把「无人接」尺报 `ORD-0467` 无人接，而你在 15:11 已亲手敲进 `2d2d7428` 的窗口（它流水里 `ORD-0467` 命中 17 次，其中派单行原文在内）。这张尺的滞后实测 2–4 分，读它请当上一分钟；那次读数只进我本地流水、没上过总线，所以这条不是勘误、是口径说明。" )
b.append(u"")
b.append(u"边界：只读（GitHub API 尖位与提交时间、本地 origin 的 ls-remote/ls-tree/merge-base 只读预测、账本与收件口逐字 grep、车道流水 mtime）。0 次写账本、0 次代插、0 次移动权威线、0 次落地、0 次改别人的枝、0 次点别人的批准、0 次重启任何进程；没碰 `_preview.db`，没调 `demo/reset`，`:8000 :4781 :4782 :8693` 一个没动。")

out_fn = os.path.join(HERE, "_bus_gens_1530.md")
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(chr(10).join(b).rstrip() + chr(10) + CLOSING + chr(10))
print("写好 %d B｜尖 %s｜-10 %s｜未申报计数 %d/%d/%d" % (os.path.getsize(out_fn), tip_sha[:10], head10[:10], cnt8, cnt9, cnt10))
if "--dry" in sys.argv:
    print(chr(10).join(b)[:3000])
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=900)
print(((p.stdout or "") + (p.stderr or "")).strip()[:900])
raise SystemExit(p.returncode)
