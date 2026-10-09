# -*- coding: utf-8 -*-
u"""值守栈的"跑的是改前代码"体检：逐腿比 进程起 与 文件改于。

为什么要有它（10-06 04:2x）：常设规矩写的是「改脚本要重启＋种去重」，可这句话只活在我的记忆里；
上一班我改了 `_sentinel_relay_r1.py` 却没确认那一枚哨兵是不是重启后起的——
场上很容易出现"文件已改、进程照跑旧代码"，而这种红仪表看不见（`--check` 只会说"栈完整"）。
今天顺手量了一遍，八条腿都是现行；正因为"没问题"，才更要把尺留下——
下一班改完腿不必靠记性，跑这一条就知道该不该重启。

一处测量坑（我第一版就踩了）：只打印 `HH:MM` 会比错——
文件 10-05 03:02 改的、进程 10-06 01:26 起的，看着像"文件比进程新"，其实是跨了天。
⇒ 判定与打印都必须带日期（%m-%d %H:%M）。

只读：0 次起进程、0 次杀进程、0 次改文件；要不要重启由人（或巡逻那一格）决定。
跑法：PYTHONIOENCODING=utf-8 python _stack_staleness_check_r1.py [--json]
退出码：0＝全部现行；1＝有腿在跑改前代码；7＝取不到进程表（不许当绿）。
"""
import csv
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# 每条腿的常驻脚本（不在表里的＝短命/一次性，不参与判定）
LEGS = [
    (u"supervise", u"autumn_supervise_r1.py"),
    (u"watch", u"autumn_watch.py"),
    (u"keepalive", u"_sentinel_keepalive_r1.py"),
    (u"sentinel", u"_sentinel_relay_r1.py"),
    (u"keeper", u"_stack_keeper_r1.py"),
    (u"inbox_applier", u"_inbox_applier_r2.py"),
    (u"verdict", u"_night_verdict_runner_r1.py"),
    (u"bus_hub", u"D:/moodle/agent_bus/bus_hub.py"),
    (u"board", u"D:/moodle/agent_bus/board.py"),
    # 巡检跑批 19:18 进 COMPONENTS；这把尺原先不认它（19:36 现读实测），
    # 不补 ⇒ 以后改它的代码尺不会报，等于这条腿脱管。
    (u"patrol_loop", u"_patrol_loop_r1.py"),
]

Q = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' } | "
     "ForEach-Object { [PSCustomObject]@{pid=$_.ProcessId;cl=$_.CommandLine;"
     "start=$_.CreationDate} } | ConvertTo-Csv -NoTypeInformation")


# 每条腿的收工时刻从哪儿取：先 env（它启动时真正拿到的那个），取不到就用它文件里的默认值。
# 形制与各腿自己的 stop_at 一致：`HHMM`＝今天该刻、`MMDD-HHMM`＝指定那天。
STOP_ENV = {
    u"supervise": u"SUP_STOP",
    u"keepalive": u"SENTINEL_STOP",
    u"sentinel": u"SENTINEL_STOP",
    u"keeper": u"STACK_KEEPER_STOP",
    u"inbox_applier": u"APPLIER_STOP",
    u"verdict": u"NVR_AT",
    u"patrol_loop": u"PATROL_LOOP_STOP",
}
STOP_DEFAULT = {
    u"supervise": u"2340",
    u"keepalive": u"2335",
    u"sentinel": u"2335",
    u"keeper": u"2340",
    u"inbox_applier": u"2340",
    u"verdict": u"23:00:20",
    # 跑批默认到 1105（守到 11:00 之后五分钟，留写快照）
    u"patrol_loop": u"1105",
}


def stop_epoch(leg):
    """这条腿的**实际**收工时刻（epoch 秒）。取不到返回 None——不猜。"""
    raw = os.environ.get(STOP_ENV.get(leg, u""), u"") or STOP_DEFAULT.get(leg)
    if not raw:
        return None
    raw = str(raw)
    try:
        if "-" in raw:
            md, hm = raw.split("-", 1)
            base = u"%s-%s-%s" % (time.strftime(u"%Y"), md[:2], md[2:])
        else:
            base = time.strftime(u"%Y-%m-%d")
            hm = raw
        h, m = int(hm[:2]), int(hm[2:4])
        return time.mktime(time.strptime(base + u" %02d:%02d:00" % (h, m),
                                          u"%Y-%m-%d %H:%M:%S"))
    except Exception:
        return None


def parse_start(s):
    s = (s or u"").strip()
    for fmt in (u"%Y/%m/%d %H:%M:%S", u"%Y-%m-%d %H:%M:%S"):
        try:
            return time.mktime(time.strptime(s, fmt))
        except ValueError:
            continue
    return 0.0


def rows():
    p = subprocess.run(["powershell", "-NoProfile", "-Command", Q],
                       capture_output=True, timeout=180)
    if p.returncode != 0:
        return None
    txt = (p.stdout or b"").decode("utf-8", "replace")
    try:
        return list(csv.DictReader(io.StringIO(txt)))
    except Exception:
        return None


def main():
    as_json = u"--json" in sys.argv
    rs = rows()
    if not rs:
        sys.stdout.write((u"取不到进程表 ⇒ 这一格不可得，不许当'都是现行代码'\n"
                          if not as_json else json.dumps({"error": "no_proc_table"}) + u"\n"))
        return 7
    out = []
    stale = missing = 0
    for name, script in LEGS:
        base = os.path.basename(script)
        path = script if (os.path.isabs(script) or u":" in script[:3]) else os.path.join(HERE, script)
        pr = [r for r in rs if base in (r.get(u"cl") or u"")]
        if not os.path.exists(path):
            out.append({u"leg": name, u"verdict": u"file_missing", u"path": path})
            missing += 1
            continue
        m = os.path.getmtime(path)
        if not pr:
            out.append({u"leg": name, u"verdict": u"not_running", u"file_mtime": m})
            continue
        st = max(parse_start(p.get(u"start")) for p in pr)
        if not st:
            out.append({u"leg": name, u"verdict": u"start_unparsable", u"file_mtime": m})
            missing += 1
            continue
        v = u"current" if st >= m else u"stale"
        if v == u"stale":
            stale += 1
        out.append({u"leg": name, u"verdict": v, u"pids": [p[u"pid"] for p in pr],
                    u"proc_start": st, u"file_mtime": m})
    if as_json:
        sys.stdout.write(json.dumps({u"at": time.time(), u"stale": stale,
                                     u"unknown": missing, u"legs": out},
                                    ensure_ascii=False) + u"\n")
    else:
        f = lambda t: time.strftime(u"%m-%d %H:%M", time.localtime(t)) if t else u"—"
        sys.stdout.write(u"值守栈体检（现读 %s｜判定带日期，只比 HH:MM 会跨天比错）\n"
                         % time.strftime(u"%H:%M:%S"))
        for r in out:
            if r[u"verdict"] == u"current":
                sys.stdout.write(u"  ✓ %-13s 进程起 %s ≥ 文件改于 %s（pid %s）\n"
                                 % (r[u"leg"], f(r.get(u"proc_start")), f(r.get(u"file_mtime")),
                                    u",".join(r.get(u"pids") or [])))
            elif r[u"verdict"] == u"stale":
                e = stop_epoch(r[u"leg"])
                if e is None:
                    tail = u"这条腿不带收工时刻 ⇒ 按老规矩：重启"
                elif e <= time.time():
                    tail = u"**实际到点已过（%s）⇒ 立刻重启**" % f(e)
                else:
                    tail = (u"实际到点 %s（还有 %d 分）⇒ 只是看着旧，**不必现在动**，"
                            u"让它自然重启时带上新代码" % (f(e), (e - time.time()) / 60.0))
                sys.stdout.write(u"  !! %-13s 进程起 %s 早于文件改于 %s ⇒ 跑的是改前代码；%s\n"
                                 % (r[u"leg"], f(r.get(u"proc_start")), f(r.get(u"file_mtime")), tail))
            elif r[u"verdict"] == u"not_running":
                sys.stdout.write(u"  -- %-13s 不在场（短命腿/或被 restart 拉起，看栈那一格）\n" % r[u"leg"])
            else:
                sys.stdout.write(u"  ?? %-13s %s ⇒ 不可得，不当绿\n" % (r[u"leg"], r[u"verdict"]))
        sys.stdout.write(u"⇒ %s（改前代码 %d 条｜不可判 %d 条｜在场且现行 %d 条）\n"
                         % (u"全部现行" if stale == 0 and missing == 0 else
                            (u"有腿在跑改前代码" if stale else u"有腿不可判"),
                            stale, missing, sum(1 for r in out if r[u"verdict"] == u"current")))
    return 1 if stale else (7 if missing else 0)


if __name__ == u"__main__":
    sys.exit(main())
