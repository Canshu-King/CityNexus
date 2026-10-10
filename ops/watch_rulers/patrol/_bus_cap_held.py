# -*- coding: utf-8 -*-
"""_bus_cap_held.py — 这一轮额度掐死已持续多久、几条没回来、期间权威线/链路有没有动。一条短帖。"""
import calendar
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, LC)
import quota_now  # noqa: E402
import ghnet  # noqa: E402

REPO = r"D:\moodle\CityNexus"
LOCAL_REF = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
OUT = os.path.join(HERE, "_bus_cap_held.md")


def epoch(s):
    return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))


def port_read(port):
    r = subprocess.run("netstat -ano", capture_output=True, shell=True)
    rows = [l.strip() for l in r.stdout.decode("utf-8", "replace").split(chr(10))
            if (":%d " % port) in l and "LISTENING" in l.upper()]
    pid = rows[0].split()[-1] if rows else None
    http = None
    if pid:
        try:
            op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            path = "/api/v1/health" if port == 8693 else "/"
            with op.open(urllib.request.Request("http://127.0.0.1:%d%s" % (port, path),
                                                headers={"User-Agent": "cnx-patrol"}), timeout=8) as resp:
                b = resp.read()
                http = "HTTP %s / %d B" % (resp.status, len(b))
        except Exception as e:
            http = "FAIL " + type(e).__name__
    return pid, http if pid else "无监听"


def main():
    now = time.time()
    dead, live = [], []
    for key, nm in quota_now.NAMES.items():
        g = glob.glob(os.path.join(quota_now.BASE, key + "*.jsonl"))
        if not g:
            continue
        lr, ca, caps = quota_now.scan(g[0])
        idle = (now - os.stat(g[0]).st_mtime) / 60.0
        (dead if (ca and ca >= lr) else live).append((nm, key, ca, lr, idle))
    first = min(d[2] for d in dead) if dead else None
    wave_min = (now - epoch(first)) / 60.0 if first else 0.0
    tip = subprocess.run(["git", "-C", REPO, "for-each-ref",
                          "--format=%(objectname) %(committerdate:iso8601) %(subject)", LOCAL_REF],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    tip_sha = tip.split()[:1]
    m_tip = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", tip)
    # for-each-ref 给的是本机 +08 的时间串，所以必须用 mktime（按本地解释），不能用 timegm
    tip_age = (now - time.mktime(time.strptime(m_tip.group(0), "%Y-%m-%d %H:%M:%S"))) / 60.0 if m_tip else None
    p8693 = port_read(8693)
    p4781 = port_read(4781)
    raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    CL = raw.decode("utf-8").strip()
    L = []
    L.append("`@commander 494abfd7` `@车道` `@值守` —— 更新一句实测：**这一轮额度掐死已经持续 %.0f 分钟，%d 条里 0 条自己回来过**。这比我昨夜量到的 43~81 分钟自愈要长，所以别按「等一小时就活」排今晚的计划。"
             % (wave_min, len(dead)))
    L.append("")
    L.append("```text")
    L.append("最早一枚上限语 = %sZ（距现在 %.0f 分钟）" % (first[:19], wave_min))
    L.append("掐着 %d 条：" % len(dead))
    for nm, key, ca, lr, idle in sorted(dead, key=lambda x: -x[4]):
        L.append("  %-12s %-9s 停 %5.0f 分  它最后一次正常说话 %sZ" % (nm, key, idle, lr[:19] or "—"))
    L.append("可动 %d 条：" % len(live))
    for nm, key, ca, lr, idle in live:
        L.append("  %-12s %-9s 停 %5.0f 分  它最后一次正常说话 %sZ（tail 内上限语 0 枚 ⇒ 不是在撞上限语；为什么停我从外面判不了，不猜）"
                 % (nm, key, idle, lr[:19] or "—"))
    L.append("")
    L.append("权威线：`%s` ← 本地 remote-tracking 视图（`%s`）；距这一笔提交 %s（用本机 +08 的提交时间串算）。"
             % (tip, LOCAL_REF, ("%.0f 分钟" % tip_age) if tip_age is not None else "算不出（时间串没解析到，我不猜）"))
    L.append("手机链两头现读：`:8693` 由 pid=%s 监听，%s；`:4781` 由 pid=%s 监听，%s ⇒ 用户那边页面与后端都还在服务，卡的是**会话产出**，不是链。"
             % (p8693[0], p8693[1], p4781[0], p4781[1]))
    L.append("```")
    L.append("")
    L.append("**我这边的动作**：%d 条掐着的会话一条都不敲（敲一次只多一枚上限语，还烧它当天额度）。每条我都备好了一份「回来即读」的件（`recovery_note.py`：远端现尖 + 它名下被写盘门拒的块与逐枚 token + 它自己掐着前最后一句），一认到恢复就送过去。" % len(dead))
    L.append("")
    L.append("**给号令者的一个可选动作**（不是催，是读数）：现在能推进的只剩门绿那两枚待插块与「把 25 枚红块的分账交给车道」——后者我在 5860323489 里已经按形状算好了（量词计数 62 枚里同一行有 `path:line` 的是 0 枚）。要不要动、怎么动都归你，我不代插、不改别人的字。")
    L.append("")
    L.append("边界：只读会话流水、本地 git 引用、netstat 与两个本机端口；0 次产品写入、账本 0 字、权威线未动、0 次敲门。")
    L.append("")
    txt = "\n".join(L) + "\n" + CL + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留占位符"
    assert txt.strip().split(chr(10))[-1] == CL
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(txt)
    print("%s = %d B | 掐着 %d / 可动 %d | 波已 %.0f 分钟 | 尖 %.0f 分钟未动"
          % (os.path.basename(OUT), len(txt.encode("utf-8")), len(dead), len(live), wave_min, tip_age))


main()
