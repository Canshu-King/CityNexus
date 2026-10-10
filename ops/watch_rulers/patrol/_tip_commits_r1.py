# -*- coding: utf-8 -*-
"""权威线现值（绝对时间窗，跨零点可用）。

上一把尺 _night_verdict_r1.py 的 `--since` 只接 HH:MM，内部按**当天** 00:00 起算
（见其 55–58 行 `day0 = today 00:00` + `cut = day0 + h*3600 + m*60`）：00:13 再跑，
阈值成了 09-30 12:00（未来）⇒ 打印「0 笔提交进线」。本件把窗口写成绝对 ISO 串，
并在本地对象库读不到尖时改走 GitHub API，读到哪条渠道要具名打印。
"""
import io
import json as J
import os
import ssl
import subprocess
import sys
import time
import urllib.request as U

REPO = r"D:\moodle\CityNexus"
BR = "mirror/integration-frontend-apple-pass1"
ENV = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(k, None)


def sh(args, t=180):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=ENV, cwd=REPO, timeout=t)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def api(path):
    tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
    op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
    r = U.Request("https://api.github.com" + path,
                  headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol",
                           "Accept": "application/vnd.github+json"})
    return J.loads(op.open(r, timeout=90).read().decode())


def main():
    w0 = sys.argv[1] if len(sys.argv) > 1 else "2026-09-29 12:00"
    w1 = sys.argv[2] if len(sys.argv) > 2 else time.strftime("%Y-%m-%d %H:%M")
    ref = api("/repos/Canshu-King/CityNexus/git/ref/heads/" + BR)["object"]["sha"]
    print("尖（GitHub API 现读 40 位）: %s" % ref)
    print("窗口: %s → %s（本机 +08）" % (w0, w1))
    iso0 = w0.replace(" ", "T") + ":00+08:00"
    iso1 = w1.replace(" ", "T") + ":00+08:00"
    have = sh(["git", "cat-file", "-t", ref])[0] == 0
    print("本地对象库有这枚尖吗: %s" % ("有" if have else "无（改走 API）"))
    rows = []
    if have:
        rc, out, err = sh(["git", "log", "--since=" + w0, "--until=" + w1,
                           "--format=%ad|%s", "--date=format:%m-%d %H:%M", ref])
        if rc == 0:
            rows = [x for x in out.split(chr(10)) if x.strip()]
            src = "本机对象库 git log（尖 %s）" % ref[:12]
        else:
            have = False
    if not have:
        lst = api("/repos/Canshu-King/CityNexus/commits?sha=%s&since=%s&until=%s&per_page=100"
                  % (BR, iso0, iso1))
        for c in lst:
            d = c["commit"]["author"]["date"]
            rows.append("%s %s|%s" % (d[5:10], d[11:16].replace(":", ":"), c["commit"]["message"].split(chr(10))[0]))
        src = "GitHub API commits 列表（渠道：/commits?since&until）"
    print("进线笔数 %d（读数渠道：%s）" % (len(rows), src))
    for r in rows[:20]:
        print("   " + r[:120])
    if len(rows) > 20:
        print("   …另有 %d 笔未打印" % (len(rows) - 20))
    print("边界：只读；0 次 fetch、0 次写任何 ref/工作树、0 次推。")


main()
