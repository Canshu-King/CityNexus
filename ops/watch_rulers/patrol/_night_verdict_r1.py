# -*- coding: utf-8 -*-
"""夜间终判（只读）：一条命令回答『他们到底工作到几点、还剩谁能动、这一段落了什么』。

设计取向：夜里额度随时可能把我自己也掐掉，所以这一段的话必须能**一条命令重算**，
不能靠我记忆或前面几轮的聊天。三个问题各自对应一段实测：
  1) 权威线在这一段还在不在动 → `git rev-list` 与提交标题（哪些单进线了）；
  2) 每条车道最后一次真产出是几点 → 它流水里有正文的 assistant 记录的最大时间；
  3) 谁现在还有油 → 该车道**最后一条角色记录**本身是不是额度字样。
"""
import calendar
import io
import json
import os
import subprocess
import sys
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
REPO = r"D:\moodle\CityNexus"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")
SINCE_HHMM = sys.argv[1] if len(sys.argv) > 1 else "19:00"

LANES = [
    ("a68b0631", "rel", "rel"), ("1d64acf5", "S4", "s4"), ("9759f1ac", "N2", "n2"),
    ("904a042d", "Q", "q"), ("bac10f40", "AI", "ai"), ("3b65af59", "map", "map"),
    ("be19052c", "dt", "dt"), ("e4f3490f", "道0370", "dao0370"), ("49fe0d7b", "N3", "n3"),
    ("8ac89982", "R0417", "r0417"), ("4033270f", "0383", "0383"), ("1ba48dbf", "newlane", "newlane"),
    ("6a150e1e", "newlane2", "newlane2"), ("9cc37e57", "0421", "qoder-0421"),
    ("2d2d7428", "0441", "qoder-0441"), ("a6b95d59", "DSH", "dsh"), ("8e5245f0", "道0369", "dao0369"),
    ("da46954a", "新车道", "car"), ("e766b154", "新车道472", ""), ("494abfd7", "号令者B", "cmdr"), ("6efab655", "CMDR-A", ""),
]


def epoch(ts, fb):
    if isinstance(ts, (int, float)):
        return ts / 1000.0 if ts > 1e12 else float(ts)
    if isinstance(ts, str) and len(ts) > 18:
        try:
            return calendar.timegm(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            return fb
    return fb


def sh(args, cwd=REPO, t=600):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=ENV, cwd=cwd, timeout=t)
    return p.returncode, (p.stdout or "").strip()


def main():
    now = time.time()
    day0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 00:00", "%Y-%m-%d %H:%M"))
    h, m = [int(x) for x in SINCE_HHMM.split(":")]
    cut = day0 + h * 3600 + m * 60
    print("=== 夜间终判 %s（问的是 %s 之后）===" % (time.strftime("%H:%M:%S"), SINCE_HHMM))

    # 尖必须走 GitHub API：上一版我图省事读 `D:/moodle/CityNexus` 的 FETCH_HEAD，
    # 那是**共享仓里别人也会写的可变引用**——20:20 它指向 45b0a5e2，于是「12:00 后 0 笔」这种
    # 自相矛盾的话就进了我的报告。以后凡是要引用权威线，一律 API 现读 40 位。
    import json as _j, ssl as _s, urllib.request as _U
    _tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
    _op = _U.build_opener(_U.ProxyHandler({}), _U.HTTPSHandler(context=_s.create_default_context()))
    _r = _U.Request("https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1",
                    headers={"Authorization": "Bearer " + _tok, "User-Agent": "cnx-patrol",
                             "Accept": "application/vnd.github+json"})
    tip = _j.loads(_op.open(_r, timeout=90).read().decode())["object"]["sha"]
    cnt = sh(["git", "rev-list", "--count", "--since=%s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cut)), tip])[1] if tip else "?"
    subs = sh(["git", "log", "--since=%s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cut)),
               "--format=%ad %s", "--date=format:%H:%M", tip])[1].split(chr(10)) if tip else []
    print("1) 权威线 %s：这段有 %s 笔提交进线。逐笔标题（最多 12 行）：" % ((tip[:12] or "取不到"), cnt))
    for s in [x for x in subs if x.strip()][:12]:
        print("   " + s[:120])

    ins = []
    pd = os.path.join(INBOX, "_processed")
    for f in os.listdir(pd):
        if ".inserted_" in f:
            mt = os.path.getmtime(os.path.join(pd, f))
            if mt >= cut:
                ins.append((mt, f))
    ins.sort()
    print(chr(10) + "2) 门：这段入账 %d 枚（判据 `_processed/*.inserted_*` 的时间）：" % len(ins))
    for mt, f in ins[-10:]:
        print("   %s %s" % (time.strftime("%H:%M:%S", time.localtime(mt)), f[:46]))

    print(chr(10) + "3) 每条车：末次有正文产出 / 今日撞闸次数 / 此刻是否有油")
    rows = []
    for sid8, nick, pre in LANES:
        c = [f for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")]
        if not c:
            continue
        p = max([os.path.join(BASE, f) for f in c], key=os.path.getsize)
        last_txt = None
        caps = 0
        last_cap = None
        last_rec = None
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if '"type":"assistant"' not in line and '"type": "assistant"' not in line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("type") != "assistant":
                continue
            e = epoch(o.get("timestamp"), os.path.getmtime(p))
            m2 = o.get("message") or {}
            txt = "".join(x.get("text", "") for x in (m2.get("content") or []) if isinstance(x, dict))
            if not txt.strip():
                continue
            if "daily usage limit" in txt:
                if e >= day0:
                    caps += 1
                    if last_cap is None or e > last_cap:
                        last_cap = e
                last_rec = "cap"
            else:
                last_rec = "work"
                if e >= day0 and (last_txt is None or e > last_txt):
                    last_txt = e
        blocks = 0
        if pre:
            for f in os.listdir(pd):
                if f.lower().startswith(pre) and ".inserted_" in f:
                    blocks += 1
        rows.append((nick, sid8, last_txt, caps, last_rec, blocks, last_cap))
    rows.sort(key=lambda r: -(r[2] or 0))
    for nick, sid8, lt, caps, lr, blocks, lcap in rows:
        print("   %-8s %-8s 末次产出 %s｜今日撞闸 %2d 次｜最后一次额度回话 %s｜末条 %s" % (
            nick, sid8, time.strftime("%H:%M:%S", time.localtime(lt)) if lt else "—",
            caps,
            time.strftime("%H:%M:%S", time.localtime(lcap)) if lcap else "—",
            ("额度回话" if lr == "cap" else ("有产出" if lr else "无"))))
    live = [r for r in rows if r[4] != "cap"]
    print(chr(10) + "小结：%d 条会话里，末条不是额度回话的 %d 条：%s。" % (
        len(rows), len(live), u"、".join(r[0] for r in live)))
    print("边界：尖位＝GitHub API 现读 40 位；`--since` 笔数与标题＝同一枚 40 位在 `D:/moodle/CityNexus` 对象库里的历史（不再读 FETCH_HEAD，那是共享可变引用）；门＝收件口 `_processed` 的 mtime；车道＝各自流水的角色记录。0 次写账本、0 次代插、0 次落地、0 次动权威线。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
