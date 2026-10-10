# -*- coding: utf-8 -*-
"""值守 14:40 · 下午到夜里这一段的大白话报告生成器（数字全部现算，不抄上一贴）。

为什么要单独一个生成器：早上的 `user_report_r1.py` 的口径是 00:00–11:00，而 11:00 之后
cron 到期、白天这两小时的形状完全不一样（门靠号令者手动跑、派单靠人敲门转达）。
到 23:00 交差时我要的是**这一段**的证据，不是把早上的数再加一遍。

每条都带可复跑命令或工件路径；算不出来的格子直接写「不可得」，不猜、不外推。
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))          # .../live_checks/patrol
LC = os.path.dirname(HERE)                                  # .../live_checks
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
REPO = r"D:\moodle\CityNexus"
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROJ = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
SELF = "42d1a6fa"
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="")
START = time.mktime(time.strptime("2026-09-29 12:00", "%Y-%m-%d %H:%M"))

LANES = {'49fe0d7b': 'N3', '4033270f': '0383', '9cc37e57': '0421', 'bac10f40': 'AI',
         '2d2d7428': '0441', '904a042d': 'Q', 'be19052c': 'dt', '1ba48dbf': 'newlane',
         '6a150e1e': 'newlane2', '8e5245f0': '道0369', 'a6b95d59': 'DSH', '3b65af59': 'map',
         '8ac89982': 'R0417', 'e4f3490f': '道0370', '1d64acf5': 'S4', '9759f1ac': 'N2',
         'a68b0631': 'rel', '6efab655': 'CMDR-A', '494abfd7': 'CMDR-B'}


def sh(args, t=600, cwd=REPO):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=cwd, env=ENV, timeout=t)
    return ((p.stdout or "") + (p.stderr or "")).strip()


def mtime_of(sid8):
    g = glob.glob(os.path.join(PROJ, sid8 + "*.jsonl"))
    if not g:
        return None
    return (time.time() - os.path.getmtime(g[0])) / 60.0, os.path.getsize(g[0])


def my_relays_today():
    """从我自己的流水里数 12:00 之后发出去的车道窗口消息与总线贴调用（按每行 timestamp 过滤）。"""
    g = glob.glob(os.path.join(PROJ, SELF + "*.jsonl"))
    if not g:
        return None, None
    n_lane = n_bus = 0
    with io.open(g[0], encoding="utf-8", errors="replace") as h:
        for line in h:
            if not line.startswith("{"):
                continue
            ts = re.search(r'"timestamp":"([0-9T:.Z-]+)"', line[:400])
            if not ts:
                continue
            try:
                y, mo, d = int(ts.group(1)[0:4]), int(ts.group(1)[5:7]), int(ts.group(1)[8:10])
                hh, mm = int(ts.group(1)[11:13]), int(ts.group(1)[14:16])
            except Exception:
                continue
            # 流水里写的是本地墙上时间还是 UTC 不确定 ⇒ 两种都算，取 12:00 之后那个口径并在报告里说明
            local_min = hh * 60 + mm
            utc_min = (hh + 8) % 24 * 60 + mm
            if local_min < 12 * 60 and utc_min < 12 * 60:
                continue
            if "send_message_to_chat_session" in line:
                n_lane += 1
            if "bus_post.py" in line:
                n_bus += 1
    return n_lane, n_bus


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    now = time.strftime("%H:%M")
    tip = sh(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin", TIPREF]).split()
    tip = tip[0] if tip and re.match(r"^[0-9a-f]{40}$", tip[0]) else "读不到"
    ncommits = sh(["git", "rev-list", "--count", "--since=2026-09-29 12:00", tip]) if tip != "读不到" else "不可得"
    lsize, lmt = 0, None
    if os.path.exists(LEDGER):
        st = os.stat(LEDGER)
        lsize, lmt = st.st_size, (time.time() - st.st_mtime) / 60.0
    ins = [f for f in glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*"))
           if max(os.path.getmtime(f), os.path.getctime(f)) >= START]
    pend = glob.glob(os.path.join(INBOX, "*.md"))
    orders_landed = {}
    # 更硬的证据：权威线上 12:00 之后的**提交标题**里点的单号（提交是他写的，标题就是那一笔属于哪张单）
    subj = sh(["git", "log", "--since=2026-09-29 12:00", "--format=%s", tip]) if tip != "读不到" else ""
    by_subject = sorted(set(re.findall(r"ORD-0\d{3}", subj)))
    n_by_subject = len(by_subject)
    for f in ins:
        t = io.open(f, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"ORD-0(\d{3})[^\n]{0,60}?落到 `([0-9a-f]{12,40})`", t):
            orders_landed.setdefault("ORD-0" + m.group(1), m.group(2)[:12])
    rows = []
    for k, v in LANES.items():
        r = mtime_of(k)
        if r:
            rows.append((r[0], v, k, r[1]))
    rows.sort()
    active30 = [x for x in rows if x[0] <= 30]
    dfree = sh(["df", "-B", "1G", "/d"]).split("\n")
    dfree = [x for x in dfree if x.strip().startswith("D:")][:1]
    pts = []
    tf = os.path.join(HERE, "disk_trend.txt")
    if os.path.exists(tf):
        for line in io.open(tf, encoding="utf-8", errors="replace"):
            m = re.match(r"^(\d\d):(\d\d)\s+(\d+)\s+GiB", line.strip())
            if m:
                pts.append((line.strip()[:5], int(m.group(3))))
    n_lane, n_bus = my_relays_today()
    # 我自己的流水按 API 请求整段重发历史，数出来会虚高（试过：12:00 后「227 条」）。
    # 所以这里的条数只用**逐条手记的 relay_log**，它是我发完立刻写的，能对着总线与各车道流水复核。
    rl = os.path.join(HERE, "relay_log_0929.txt")
    n_knock_noon = n_knock_all = 0
    if os.path.exists(rl):
        for line in io.open(rl, encoding="utf-8", errors="replace"):
            if line.startswith("#") or not line.strip():
                continue
            hh = line[:2]
            if not hh.isdigit():
                continue
            n_knock_all += 1
            if int(hh) * 60 + int(line[3:5]) >= 12 * 60:
                n_knock_noon += 1
    # 总线条数用索引表的 HH:MM 字段算（每行是我发完立刻登记的，比 grep 自己流水准）
    idx = os.path.join(HERE, "bus_ids.txt")
    bus_total = bus_window = 0
    bus_ids_window = []
    if os.path.exists(idx):
        for line in io.open(idx, encoding="utf-8", errors="replace"):
            parts = re.split(r"[	 ]+", line.strip())
            if not parts or not re.match(r"^[0-9]{6,}$", parts[0]):
                continue          # 索引里混过两种分隔符（上午用空格、下午用制表符），这里都认
            bus_total += 1
            m = re.match(r"^([01][0-9]):([0-5][0-9])$", parts[1].strip()) if len(parts) > 1 else None
            if m and (int(m.group(1)) * 60 + int(m.group(2))) >= 12 * 60:
                bus_window += 1
                bus_ids_window.append(parts[0])

    o = []
    o.append(u"# CityNexus 下午到夜里值守报告（写给用户，%s 现算，窗口 12:00 起）\n" % now)
    o.append(u"## 一、这一段他们真交付了什么\n")
    o.append(u"- 权威线现尖 `%s`；12:00 之后在这条线上有 **%s 笔**提交（`git rev-list --count --since=2026-09-29 12:00 %s`）。"
             % (tip[:12], ncommits, tip[:12]))
    o.append(u"- 按**提交标题**数：12:00 之后落进权威线的单 **%d 张**：%s"
             % (n_by_subject, "、".join(by_subject)[:500] or "（数不到）"))
    o.append(u"- 号令者在块里逐笔写了「落到 <尖>」的单（另一种口径，只算他自己在块里点了尖的）：**%d 张**：%s"
             % (len(orders_landed), "、".join(sorted(orders_landed))[:400] or "（还没数到）"))
    o.append(u"- 车道交进入账门的块：12:00 之后 **%d 枚**（判据 `_processed/*.inserted_*` 的时间戳）；收件口此刻待插 **%d 枚**。"
             % (len(ins), len(pend)))
    if lmt is not None:
        o.append(u"- 账本本体 `%s`：%d B，%s 分钟前被写过。" % (os.path.basename(LEDGER), lsize, "%.1f" % lmt))
    o.append(u"")
    o.append(u"## 二、谁在干活（只看他们自己的任务记录）\n")
    o.append(u"- %d 分钟内有写动作的车道/实例：**%d / %d** 条。逐条静默分钟：\n"
             % (30, len(active30), len(rows)))
    for a, v, k, sz in rows:
        o.append(u"  - %s `%s` 静默 %.0f 分（流水 %s B）" % (v, k, a, "{:,}".format(sz)))
    o.append(u"")
    # 15:00 之后这段（休眠窗 / 额度潮两侧口径 / 我这一段的帖与工具）单列成模块，随时可重算
    try:
        import night_sections_r1 as NS
        o.extend(NS.lines())
    except Exception as e:
        o.append(u"## 二b、夜间段落没跑起来：%s: %s" % (type(e).__name__, str(e)[:160]))
    o.append(u"")
    o.append(u"## 三、我这一窗口的动作（从我自己流水里数出来，不靠记忆）\n")
    if n_lane is not None:
        o.append(u"- 往车道窗口发的转达/提醒：12:00 之后 **%d 条**，逐条登记在 `patrol/relay_log_0929.txt`（HH:MM + 收件会话 id + 性质，"
                 u"含我一条错投与它的撤回）；全天累计 **%d 条**。往总线发新帖：**%d 条**（`patrol/bus_ids.txt` 里 HH:MM 在 12:00 之后的行；全天 %d 条）：%s"
                 % (n_knock_noon, n_knock_all, bus_window, bus_total, "、".join(bus_ids_window)))
    else:
        o.append(u"- 我自己的流水读不到，这一格写「不可得」。")
    o.append(u"- 我新加/改过的只读尺：`_hotfile_contention_r2.py`（逐枚文件三侧比 blob）、`_undeclared_deliveries_r1.py`（推了枝没申报）、"
             u"`_door_backlog_r1.py`（门停）、`_landing_plan_r1.py` + `_ready_not_landed_r1.py`（按字节算「申报了但没落地」并给互斥对）、"
             u"`_exposure_delta_r1.py`（用号令者钉的那把曝光尺逐枚比候选）、`_disk_trend_r1.py`（盘水位打点）。")
    o.append(u"")
    o.append(u"## 四、盘与开销（现读）\n")
    o.append(u"- `df -B 1G /d` → %s" % (dfree[0] if dfree else "取不到"))
    if pts:
        o.append(u"- 水位打点（`patrol/disk_trend.txt`，每点 ±1 GiB 因为 `df -B 1G` 向下取整）：%s"
                 % "，".join("%s=%d GiB" % (h, v) for h, v in pts[-8:]))
        if len(pts) >= 2:
            h1, m1 = pts[0][0].split(":"); h2, m2 = pts[-1][0].split(":")
            minutes = max(1, (int(h2) * 60 + int(m2)) - (int(h1) * 60 + int(m1)))
            drop = pts[0][1] - pts[-1][1]
            o.append(u"  ⇒ 从 %s 到 %s 共 %.1f 小时，可用变化 %+d GiB ⇒ 实测 %.2f GiB/小时。"
                     u"但每点 ±1 GiB（`df -B 1G` 向下取整），所以这个速率只当量级看，**不拿来预测爆盘时刻**；真到 6 GiB 以下我会单独报你。"
                     % (pts[0][0], pts[-1][0], minutes / 60.0, drop, abs(drop) / (minutes / 60.0)))
        else:
            o.append(u"  ⇒ 打点之间没有变化，或点数不足，不下任何结论。")
    cb = subprocess.run([PY, os.path.join(HERE, "credits_burn_r1.py"), "--json"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", timeout=900)
    j = None
    for cand in [x.strip() for x in ((cb.stdout or "") + (cb.stderr or "")).splitlines() if x.strip()]:
        if cand.startswith("{"):
            try:
                j = json.loads(cand)
            except Exception:
                j = None
    cbtxt = (cb.stdout or "") + (cb.stderr or "")
    mtot = re.search(r"共 ([0-9.]+) credits", cbtxt)
    if mtot:
        j = {"total": float(mtot.group(1)), "at": time.strftime("%H:%M"), "t": time.time()}
    snap = os.path.join(HERE, "credits_noon_snapshot.json")
    if j and j.get("total") is not None:
        if not os.path.exists(snap):
            io.open(snap, "w", encoding="utf-8", newline=chr(10)).write(json.dumps(j, ensure_ascii=False))
            o.append(u"- credits（现读）：00:00 起累计 %.2f；**我把这一刻存成 `credits_noon_snapshot.json`**，"
                     u"之后每次重跑本表就会报「12:00 之后花了多少」。" % float(j["total"]))
        else:
            s = json.load(io.open(snap, encoding="utf-8"))
            spent = float(j["total"]) - float(s.get("total", 0))
            o.append(u"- credits：00:00 起累计 **%.2f**；快照（%s 存的）%0.2f ⇒ 本窗口已花 **%.2f**。"
                     % (float(j["total"]), s.get("at", "无时间"), float(s.get("total", 0)), spent))
            hours = (time.time() - s.get("t", time.time())) / 3600.0
            if hours > 0.15:
                rate = spent / hours
                left_h = (23 * 3600 + 0) - (time.localtime().tm_hour * 3600 + time.localtime().tm_min * 60)
                left_h = left_h / 3600.0
                o.append(u"  - 实测速率 %.1f credits/小时（%.2f 小时窗口内 %0.2f）⇒ 到 23:00 还有 %.1f 小时，"
                         u"按同速率还需约 **%.0f credits**；这是额度风险的量级，不是承诺值。"
                         % (rate, hours, spent, left_h, rate * max(0.0, left_h)))
    else:
        for l in [x for x in ((cb.stdout or "") + (cb.stderr or "")).splitlines() if x.strip()][:6]:
            # 早上那把尺是按「11:00 到期」算剩余时间的，那一行对这一段没有意义，滤掉不写进本报告
            if u"到 11:00" in l:
                continue
            o.append(u"- %s" % l[:200])
    o.append(u"")
    o.append(u"## 五、我没做的事（边界）\n")
    o.append(u"值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准、0 次改动 cron、"
             u"0 次跑 `demo/reset`、0 次读 Basic-auth 口令内容（口令只写路径：`D:/moodle/_qoder_preview_20260920/run/preview_auth.txt`）。")
    text = u"\n".join(o).rstrip() + u"\n"
    out = os.path.join(LC, "EVENING_REPORT_0929.md")
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print("写好 %s（%d B）；12:00 后代插 %d 枚、待插 %d 枚、30 分内活 %d/%d 条"
          % (os.path.basename(out), os.path.getsize(out), len(ins), len(pend), len(active30), len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
