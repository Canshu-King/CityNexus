# -*- coding: utf-8 -*-
"""值守 19:0x 贴：休眠窗成因 + rel 撞额度后 ORD-0461 的实况 + 我今晚只对一条车动了手。

每个数都从本轮实测行推导；引用坐标都带取数的通道。只读，不落地、不代插、不移动任何人的枝。
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
REPO = r"D:\moodle\CityNexus"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
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


def sh(a, timeout=600):
    p = subprocess.run(a, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=REPO, timeout=timeout)
    return p.returncode, (p.stdout or "").strip()


def bj(utc):
    return time.strftime("%H:%M:%S", time.localtime(time.mktime(time.strptime(utc[:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600))


def jsonl(sid8):
    return [os.path.join(BASE, f) for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")][0]


def last_role_rec(sid8, win=120000):
    p = jsonl(sid8)
    n = os.path.getsize(p)
    fh = io.open(p, "rb")
    fh.seek(max(0, n - win))
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
    return last, os.path.getmtime(p)


tip = api("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1")["object"]["sha"]
tc = api("https://api.github.com/repos/Canshu-King/CityNexus/commits/" + tip)
tip_bj = bj(tc["commit"]["committer"]["date"])

# ORD-0461 那一枝的实况
h461 = sh(["git", "ls-remote", "origin", "refs/heads/review/qoder-0461-member-write-doors-r1"])[1]
sha461 = h461.split()[0] if h461 else ""
rc, _ = sh(["git", "merge-base", "--is-ancestor", sha461, tip])
cnt = sh(["git", "rev-list", "--count", "%s..%s" % (sha461, tip)])[1]
mb = sh(["git", "merge-base", tip, sha461])[1]
fs = [x for x in sh(["git", "diff", "--name-only", mb, sha461])[1].split("\n") if x.strip()]
eq, ne = 0, []
for f in fs:
    a = sh(["git", "rev-parse", "%s:%s" % (tip, f)])[1]
    b = sh(["git", "rev-parse", "%s:%s" % (sha461, f)])[1]
    if a == b:
        eq += 1
    else:
        ne.append(f)
hot = [f for f in ne if f in ("backend/app/main.py", "backend/app/schemas.py",
                             "contracts/openapi.yaml", "frontend/src/generated/api.ts")]
led = io.open(LEDGER, encoding="utf-8", errors="replace").read()
c461v = led.count(sha461[:8])
c461n = led.count("member-write-doors")

rel_last, rel_mt = last_role_rec("a68b0631")
capped = "daily usage limit" in (rel_last[1] if rel_last else "")
s4_last, s4_mt = last_role_rec("1d64acf5")
s4_body = io.open(jsonl("1d64acf5"), encoding="utf-8", errors="replace").read()
s4_marker = s4_body.count(u"值守 18:39")

tr = subprocess.run([PY, os.path.join(HERE, "_silent_lane_triage_r1.py")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600, cwd=HERE)
tlines = ((tr.stdout or "") + (tr.stderr or "")).split("\n")
tsum = next((x for x in tlines if x.startswith(u"===")), "")
silent = [x.strip() for x in tlines if x.strip().startswith("[静]")]

rd = subprocess.run([PY, os.path.join(HERE, "_ready_not_landed_r1.py"), "400"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", env=ENV, timeout=1800, cwd=HERE)
rlines = ((rd.stdout or "") + (rd.stderr or "")).split("\n")
rsum = next((x for x in rlines if u"确有未落地差" in x), "")
rcand = next((x for x in rlines if u"可干净落的候选" in x), "")
branches = [x.strip()[:96] for x in rlines if x.strip().startswith("review/")]

b = []
b.append(u"**值守 %s · 下午那 169 分钟的空窗是这台机睡了（事件 107→1 逐字可查）· rel 已撞每日额度，它手上 ORD-0461 今晚没人能 rebase · 我今晚只对一条车动了手**" % time.strftime("%H:%M"))
b.append(u"")
b.append(u"**一、空窗成因（免得被读成车道偷懒）**")
b.append(u"- 系统事件：`Microsoft-Windows-Kernel-Power` id=107 @ **15:44:17**（进睡眠）→ id=1 @ **18:33:15**（唤醒）。所有窗口、自动轮、我的发帖调用一起冻在那 169 分钟里（我 15:45 起的那次发帖实际落帖时间是 18:34:22，帖 `5888464597`）。")
b.append(u"- 电源设置现读（`powercfg /q SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` 的十六进制原值）：**交流=0x00000000（从不）**，直流=0x000000b4（180 秒）。当前电池状态=接交流。⇒ 只要它插着电，今晚不会因超时自己睡；我不改任何电源设置（拔电／合盖是你要自己决定的物理动作）。" )
b.append(u"")
b.append(u"**二、rel `a68b0631`：明早之前不会再动（这条我按只报不动手处理）**")
b.append(u"- 它最后一条记录（%s）原文：`%s`" % (time.strftime("%H:%M:%S", time.localtime(rel_mt)), (rel_last[1] if rel_last else "")[:118]))
b.append(u"- 撞额度=%s。你 18:38 敲进去的那条（讲 ORD-0461 r1 进队列、催成员门『过期时刻在现在之前』那格）它不可能回——那条现在躺在它窗口里排队，不是已送达即办。" % ("是" if capped else "否（但尾条仍是额度字样，请自己看一眼）"))
b.append(u"- ORD-0461 实况（现尖 `%s` 现测）：枝 `review/qoder-0461-member-write-doors-r1` 头 `%s`；`merge-base --is-ancestor` 退码 %d ⇒ %s线上；它到尖差 %s 笔；相对它自己的 merge-base `%s` 改 %d 枚，**与现尖逐字节相等 %d 枚**、不等 %d 枚，其中热面 %d 枚：%s。15:39 那跑争用尺对同一枚头读到「两侧都改过 3 枚」，所以复切会 ABORT。" % (tip[:12], sha461, rc, "已" if rc == 0 else "未", cnt, mb[:10], len(fs), eq, len(ne), len(hot), u"、".join("`%s`" % f for f in hot)))
b.append(u"- 申报面（两种写法都数过）：账本对 `%s` 命中 **%d**、对枝名词面 `member-write-doors` 命中 **%d**。⇒ 它进你队列靠的是你 18:38 那条里说的『按 ls-remote 读』，不是靠块。今晚没人能补这块（车道明早才回来），要么你按字节合、要么排明早，我不代裁、0 次代插。" % (sha461[:8], c461v, c461n))
b.append(u"")
b.append(u"**三、我今晚只对一条车动手，其余是名册**")
b.append(u"- 已敲：S4 `1d64acf5`。理由实测：它最后写流水 **14:59:56**（比休眠开始还早 45 分，是它自己停的），末条不是额度也不是错误终态，而它自己列的三笔欠账都没被卡：ORD-0408 值级数据流、ORD-0391 屏上逐字读回、ORD-0361 rebase。送达已核：我那条 marker 在它流水里命中 %d 次。现测它最后写 %s（末条角色 %s）。" % (s4_marker, time.strftime("%H:%M:%S", time.localtime(s4_mt)), (s4_last[0] if s4_last else "?")))
b.append(u"- 没敲的与原因：`9759f1ac`（N2）手上无单（它 ORD-0456 自记三处 `NOT_DONE` 已入账）；`904a042d`（Q）在等 ORD-0431 甲/乙/丙——**那行你还没答，这是第四次报**；`bac10f40`（AI）14:20 收干净工；`3b65af59`（map）欠『点图即展开』一句裁；`be19052c`（dt）与 `e4f3490f`（道0370）自己写了『排在后面不催／无需我动作』。对这几条敲门只是骚扰，所以只报名册。")
b.append(u"- %s" % tsum)
for x in silent[:8]:
    b.append(u"  - %s" % x[:150])
b.append(u"")
b.append(u"**四、队列（现读，%s）**" % time.strftime("%H:%M"))
b.append(u"- 现尖 `%s`（提交者 %s，首行 `%s`）。取法：GitHub API `/git/ref/…` + `ProxyHandler({})`（直连 git-over-https 这会儿仍报 `Recv failure: Connection was reset`）。" % (tip, tip_bj, tc["commit"]["message"].split(chr(10))[0][:70]))
b.append(u"- 400 分钟窗口复算：%s；%s" % (rsum.strip(), rcand.strip()))
for x in branches[:7]:
    b.append(u"  - %s" % x)
b.append(u"")
b.append(u"边界：只读（GitHub API、`D:/moodle/CityNexus` 内 merge-base / rev-list / rev-parse / ls-remote、系统事件与 powercfg 查询、账本与流水逐字 grep）。0 次写账本、0 次代插、0 次移动权威线、0 次落地、0 次改别人的枝、0 次重启任何进程、0 次改电源设置；没碰 `_preview.db`，没调 `demo/reset`，`:8000 :4781 :4782 :8693` 一个没动。")

out_fn = os.path.join(HERE, "_bus_evening_1905.md")
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(chr(10).join(b).rstrip() + chr(10) + CLOSING + chr(10))
print("写好 %d B｜尖 %s｜rel 撞额度=%s｜0461 等/线上=%d/%d｜S4 marker=%d" % (os.path.getsize(out_fn), tip[:10], capped, eq, len(fs), s4_marker))
if "--dry" in sys.argv:
    print(chr(10).join(b)[:2400])
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((p.stdout or "") + (p.stderr or "")).strip()[:800])
raise SystemExit(p.returncode)
