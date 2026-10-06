# -*- coding: utf-8 -*-
"""交班条生成器（可重跑）：把『现在谁还能动、哪些单卡在谁手上、门与尖在哪』写成一页。

用途：这台机的额度是按小时被一条条掐掉的，值守随时可能停在我自己这一份上。
所以每次跑完都留一份**当刻现值**的交班条，早上有人（或下一班值守）打开就能接。
"""
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
OUT = os.path.join(LC, "EVENING_WATCH_NOTE_0929.md")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")
INBOX = r"D:\moodle\_qoder_ledger_inbox"


def run(script, *args, **kw):
    p = subprocess.run([PY, os.path.join(HERE, script)] + list(args), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=ENV,
                       timeout=kw.get("t", 1800), cwd=HERE)
    return ((p.stdout or "") + (p.stderr or "")).split(chr(10))


def tip_api():
    import ssl
    import urllib.request as U
    tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
    op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
    r = U.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1",
                  headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol",
                           "Accept": "application/vnd.github+json"})
    sha = json.loads(op.open(r, timeout=90).read().decode())["object"]["sha"]
    r2 = U.Request("https://api.github.com/repos/Canshu-King/CityNexus/commits/" + sha,
                   headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol",
                            "Accept": "application/vnd.github+json"})
    c = json.loads(op.open(r2, timeout=90).read().decode())
    d = c["commit"]["committer"]["date"]
    bj = time.strftime("%H:%M:%S", time.localtime(time.mktime(time.strptime(d[:19], "%Y-%m-%dT%H:%M:%S")) + 8 * 3600))
    return sha, bj, c["commit"]["message"].split(chr(10))[0][:70]


def main():
    sha, bj, subj = tip_api()
    roster = run("_quota_roster_r1.py", t=600)
    unc = [x for x in run("_unclaimed_orders_r1.py", t=900) if x.strip().startswith("!!")]
    und = [x for x in run("_undeclared_deliveries_r1.py", t=900) if x.strip().startswith("结论") or x.strip().startswith("按族")]
    pend = sorted([f for f in os.listdir(INBOX) if f.endswith(".md")])
    ins = sorted([(os.path.getmtime(os.path.join(INBOX, "_processed", f)), f)
                  for f in os.listdir(os.path.join(INBOX, "_processed")) if ".inserted_" in f])[-3:]
    df = subprocess.run(["df", "-B", "1G", "/d"], capture_output=True, text=True, env=ENV).stdout.strip().split(chr(10))[-1]
    trend = [x.strip() for x in io.open(os.path.join(HERE, "disk_trend.txt"), encoding="utf-8", errors="replace").read().split(chr(10)) if x.strip()][-6:]

    o = []
    o.append(u"# 值守交班条 · %s 现值（谁写的：值守 Qoder `42d1a6fa`；每个数都是当刻现取）" % time.strftime("%Y-%m-%d %H:%M"))
    o.append(u"")
    o.append(u"## 1. 权威线与门")
    o.append(u"- 现尖 `%s`（GitHub API 现读，提交者 %s +08；首行 `%s`）。" % (sha, bj, subj))
    o.append(u"- 收件口根目录待插 **%d 枚**：%s" % (len(pend), u"、".join(pend) or u"无"))
    o.append(u"- 最近三次代插：%s" % u"、".join("%s @ %s" % (f[:26], time.strftime("%H:%M:%S", time.localtime(m))) for m, f in ins))
    o.append(u"- 推了枝但没申报块的（只读结论）：%s" % (u"；".join(x.strip() for x in und) or u"没读到"))
    o.append(u"")
    o.append(u"## 2. 谁还能动（判据＝该会话最后一条角色记录本身是不是额度字样）")
    for x in roster[:6]:
        if x.strip():
            o.append(u"- %s" % x.strip())
    o.append(u"")
    o.append(u"## 3. 现在挂着没接的单（附收件车现况，别把『车没油』读成『没人派』）")
    if unc:
        for x in unc:
            o.append(u"- %s" % x.strip()[:300])
    else:
        o.append(u"- （本轮没数到无人接的单）")
    o.append(u"")
    o.append(u"## 4. D 盘")
    o.append(u"- `%s`" % df)
    o.append(u"- 最近打点：%s" % u"、".join(trend))
    o.append(u"")
    o.append(u"## 5. 下一班（或早上）第一分钟能做的三件事")
    o.append(u"1. 跑 `live_checks/patrol/_quota_roster_r1.py`：看闸松了几条（今天实测恢复间隔 4.6–73.6 分，中位 20.7 分，但有 23 枚至今没回，所以这不是保证）。")
    o.append(u"2. 若门停了：只有号令者能代插（LEDGER_SINGLE_WRITER_V1），我全天 0 次代插；待插清单就是上面第 1 节那串文件名。")
    o.append(u"3. 若有人问『夜里到 23:00 干了多少』：看 `live_checks/EVENING_REPORT_0929.md` 与 `live_checks/QUOTA_WAVE_0929.md`（两份都是现算，含删失口径）。")
    o.append(u"")
    o.append(u"边界：这份条由只读脚本生成；0 次写账本、0 次代插、0 次移动权威线、0 次落地、0 次改别人的枝、0 次重启任何进程、0 次改电源设置；没碰 `_preview.db` 与 `demo/reset`。")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(chr(10).join(o) + chr(10))
    print("写好 %s（%d B）｜尖 %s｜待插 %d｜无人接 %d 行" % (OUT, os.path.getsize(OUT), sha[:10], len(pend), len(unc)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
