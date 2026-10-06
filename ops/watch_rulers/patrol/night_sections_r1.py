# -*- coding: utf-8 -*-
"""夜间段落（给 evening_report_r1 用的几节，全部现取）。

覆盖 15:00 之后这段：休眠窗、额度潮两侧口径、此刻名册、我发的帖、我改/新写的工具。
单独成模块的原因：晚报告本身已有 249 行，夜里这几节要能随时重算而不动老代码。
"""
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
PATROL = HERE
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")


def _sleep_events():
    try:
        ps = ("Get-WinEvent -FilterHashtable @{LogName='System'; "
              "ProviderName='Microsoft-Windows-Kernel-Power','Microsoft-Windows-Power-Troubleshooter'; "
              "StartTime=(Get-Date).AddHours(-8)} -ErrorAction SilentlyContinue | "
              "Where-Object { $_.Id -in 1,107 } | "
              "ForEach-Object { $_.TimeCreated.ToString('HH:mm:ss') + ' id=' + $_.Id }")
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=120, env=ENV)
        rows = [x.strip() for x in (out.stdout or "").split("\n") if "id=" in x]
        rows.sort(reverse=True)
        return rows[:6]
    except Exception as e:
        return ["取事件失败：%s: %s" % (type(e).__name__, str(e)[:80])]


def _power():
    try:
        out = subprocess.run(["powercfg", "/q", "SCHEME_CURRENT", "SUB_SLEEP", "STANDBYIDLE"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace",
                             timeout=60, env=ENV)
        vals = [x for x in (out.stdout or "").split("\n") if "0x" in x]
        hexes = []
        for v in vals:
            i = v.rfind("0x")
            hexes.append(v[i:].strip())
        st = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Battery).BatteryStatus"],
                            capture_output=True, text=True, timeout=60, env=ENV)
        return hexes[:5], (st.stdout or "").strip()
    except Exception as e:
        return [], "取不到（%s）" % type(e).__name__


def _wave():
    sys.path.insert(0, HERE)
    import _quota_wave_evidence_r1 as Q
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
            allcap.append((nick, e, nxt[0] if nxt else None))
    rec = [x for x in allcap if x[2] is not None]
    cen = [x for x in allcap if x[2] is None]
    w = sorted((x[2] - x[1]) / 60.0 for x in rec)
    night = [x for x in allcap if x[1] >= day0 + 18.5 * 3600]
    return len(allcap), len(rec), len(cen), w, len(night), len([x for x in night if x[2] is not None]), now


def _roster_now():
    import _quota_roster_r1 as R
    now = time.time()
    capd, writing, quiet = [], [], []
    for sid8, nick in R.NICKS.items():
        c = [f for f in os.listdir(BASE) if f.startswith(sid8) and f.endswith(".jsonl")]
        if not c:
            continue
        p = max([os.path.join(BASE, f) for f in c], key=os.path.getsize)
        recs = []
        n = os.path.getsize(p)
        fh = io.open(p, "rb")
        fh.seek(max(0, n - 150 * 1024))
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
            if o.get("type") not in ("user", "assistant"):
                continue
            m = o.get("message") or {}
            c = m.get("content")
            t = c if isinstance(c, str) else "".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
            if t.strip():
                last = t.strip()
        age = (now - os.path.getmtime(p)) / 60.0
        if last and "daily usage limit" in last:
            capd.append((nick, age))
        elif age < 8:
            writing.append((nick, age))
        else:
            quiet.append((nick, age))
    return capd, writing, quiet


def _files_since(hhmm):
    cut = time.mktime(time.strptime(time.strftime("%Y-%m-%d ") + hhmm, "%Y-%m-%d %H:%M"))
    out = []
    for f in sorted(os.listdir(PATROL)):
        if not f.endswith(".py"):
            continue
        m = os.path.getmtime(os.path.join(PATROL, f))
        if m >= cut:
            out.append((f, time.strftime("%H:%M", time.localtime(m))))
    return out


def _posts_since(hhmm):
    p = os.path.join(PATROL, "bus_ids.txt")
    rows = []
    for l in io.open(p, encoding="utf-8", errors="replace").read().split("\n"):
        parts = l.split("\t")
        if len(parts) >= 2 and parts[1] >= hhmm:
            rows.append((parts[0], parts[1], parts[3].strip() if len(parts) > 3 else ""))
    return rows


def lines():
    o = []
    ev = _sleep_events()
    hx, batt = _power()
    o.append(u"## 二b、15:00 之后这段的三段实情（现取，不靠记忆）\n")
    o.append(u"### (1) 这台机睡过一觉，值守被我 own 的失误放大了两次")
    o.append(u"- 系统事件（近 8 小时，id=107 进睡眠 / id=1 唤醒）：%s" % u"、".join(ev))
    o.append(u"- 电源设置（`powercfg` 原值，依次 min/max/可能值/AC 当前/DC 当前）：%s；电池状态 %s（2=接交流）。"
             u"⇒ 交流待机=从不 ⇒ 插电不会因超时自睡；拔电或合盖仍会，那是要人决定的物理动作，我没改任何设置。" % (u"、".join(hx), batt or "?"))
    o.append(u"- 值守空窗 %s–%s（≈169 分）里，我的自动轮、所有车道窗口、我自己一次 `bus_post` 调用一起被冻住；那一次实际落帖时间比发起晚了 2 小时 49 分。" % (u"15:44", u"18:34"))
    tot, nrec, ncen, w, nn, nnrec, now = _wave()
    o.append(u"")
    o.append(u"### (2) 额度潮：两侧口径一起报（我 19:16 只在总线上报了恢复侧，已另帖更正）")
    if w:
        o.append(u"- 今天撞闸 **%d 枚**：其后确有产出 **%d 枚**（min %.1f｜中位 %.1f｜max %.1f 分）｜至今无后续 **%d 枚**。" % (
            tot, nrec, w[0], w[len(w) // 2], w[-1], ncen))
    else:
        o.append(u"- 今天撞闸 %d 枚，暂无恢复样本可数。" % tot)
    o.append(u"- 今晚 18:30 之后撞的 **%d 枚**里，到本刻恢复 **%d 枚**（本刻 %s）。" % (nn, nnrec, time.strftime("%H:%M")))
    capd, writing, quiet = _roster_now()
    o.append(u"- 此刻名册（判据＝该车道最后一条角色记录本身是不是额度字样）：闸上 **%d** 条（%s）｜在写 **%d** 条（%s）｜静默非闸 **%d** 条（%s）。" % (
        len(capd), u"、".join("%s %.0f分" % (x[0], x[1]) for x in sorted(capd, key=lambda y: -y[1])),
        len(writing), u"、".join(x[0] for x in sorted(writing, key=lambda y: y[1])),
        len(quiet), u"、".join("%s %.0f分" % (x[0], x[1]) for x in sorted(quiet, key=lambda y: -y[1]))))
    o.append(u"- 口径自记：恢复间隔那条是**条件分布**（条件＝它回来了），删失的 %d 枚不在里面；拿它说『都会回血』是把两件事混了，同一错我 19:16 贴过、19:23 另帖勘误。" % ncen)
    o.append(u"")
    o.append(u"### (3) 我这一段做了什么（帖子与工具都列得出坐标）")
    posts = _posts_since("15:00")
    for pid, hh, tail in posts:
        o.append(u"- 总线 `%s`（%s，尾行逐字%s）" % (pid, hh, u"=是" if "True" in tail else ""))
    fs = _files_since("15:00")
    o.append(u"- 15:00 之后新写或改过的工具（%d 枚，`live_checks/patrol/`）：%s" % (
        len(fs), u"、".join("`%s`(%s)" % (f, t) for f, t in fs)))
    o.append(u"- 自动值守轮：19:04:58 换代为 24 轮 ×600 s（加进『额度名册』一步）；换代过程中我自己把 `autumn_watch.py:535` 那一行用 heredoc 拼坏、旧轮已杀、新轮 SyntaxError 退出，值守中断约 2 分钟（19:04:10–19:04:58），修好后 `ast.parse` 过才启动。")
    o.append(u"")
    o.append(u"### (4) 每条车撑到几点（按小时数『有正文的产出』，额度回话与工具块都不算）")
    try:
        tl = subprocess.run([PY, os.path.join(PATROL, "_lane_activity_timeline_r1.py"), "12"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            env=ENV, timeout=1200, cwd=PATROL)
        for x in (((tl.stdout or "") + (tl.stderr or "")).split(chr(10)) or [])[:26]:
            if x.strip():
                o.append(u"  " + x.strip())
    except Exception as e:
        o.append(u"- 时间线没跑起来：%s: %s" % (type(e).__name__, str(e)[:120]))
    return o


if __name__ == "__main__":
    for l in lines():
        print(l)
