# -*- coding: utf-8 -*-
"""夜班终值单（18:00→23:00）：一条命令把「这段夜里车队到底有没有在干活」的全部证据取齐。

为什么现在建：23:00 那一刻不该现拼工具。18:43 先跑一遍自验（跑得出数、且每格都能被单独复算），
23:00 前后再跑一遍就是终值。

六格证据，全部绝对时刻（不用「今天第几拍」这种跨日会翻错的算法）：
  1 入账枚数/小时    ← `_processed/*.md.inserted_HHMMSS` 文件名戳（mtime 限定今天）
  2 权威尖移动/小时  ← GitHub API 该分支的提交列表（清代理直连；只读）
  3 车队现值          ← `_quota_roster_r1.py`（18:36 起已按「表 ∪ 12 小时内动过的流水」扩过集合）
  4 真暗窗            ← `_dark_window_r1.py`（18:40 起判据＝在写 ≤1 且 脉搏新枝 = 0）
  5 盘                ← `disk_points.txt` 的落档点，18:00 之后的首尾两枚
  6 我这班发出去的贴   ← `bus_ids.txt` 行数 + 自动轮日志里今天真响的报警
边界：每一格都印出自己读的是哪个文件/哪条命令；任何一格取不到数就印「读数不全」而不是补一个猜测值。
"""
import glob
import hashlib
import io
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.join(LC, "patrol")
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
BRANCH = "mirror/integration-frontend-apple-pass1"
PROD = "Canshu-King/CityNexus"
TOKFILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
REPO = r"D:\moodle\CityNexus"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="",
           http_proxy="", https_proxy="")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FRM = os.environ.get("NIGHT_FROM", "18:00")
TO = os.environ.get("NIGHT_TO", "23:00")
# 09-30→10-01 跨午夜实测：过午夜再跑「昨天 18:00→23:00」这一窗时，不能用「今天」当基准日，
# 否则 23 点前的入账戳会被套到 10-01 头上、名册 mtime 过滤也会全部落空。
today = os.environ.get("NIGHT_DATE") or time.strftime("%Y-%m-%d")


def hhmm_to_epoch(hm):
    return time.mktime(time.strptime("%s %s:00" % (today, hm), "%Y-%m-%d %H:%M:%S"))


e_frm, e_to = hhmm_to_epoch(FRM), hhmm_to_epoch(TO)
# 窗口右端：过去的窗就用窗本身，进行中的窗用「现在」（否则 23 点之后发生的事会被算进 18→23 这一窗）
e_cap = e_to if e_to <= time.time() else time.time()
print("=== 夜班终值单  窗口 %s→%s  取数于 %s ===" % (FRM, TO, time.strftime("%m-%d %H:%M:%S")))

# 1) 入账
by_hour = {}
stamps = []
for f in glob.glob(os.path.join(INBOX, "_processed", "*.md.inserted_*")):
    m = re.search(r"(.+)\.md\.inserted_(\d{6})$", os.path.basename(f))
    if not m:
        continue
    try:
        e = time.mktime(time.strptime("%s %s" % (today, m.group(2)), "%Y-%m-%d %H%M%S"))
    except Exception:
        continue
    if time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(f))) != today:
        continue
    if e_frm <= e <= e_cap:
        by_hour[time.strftime("%H", time.localtime(e))] = by_hour.get(time.strftime("%H", time.localtime(e)), 0) + 1
        stamps.append((e, m.group(1)))
print("1) 入账（文件名戳，限定今天）：%s" % ("、".join("%s 时 %d 枚" % (h, n) for h, n in sorted(by_hour.items())) or "窗口内 0 枚"))
print("   合计 %d 枚；最后一枚 %s @ %s" % (len(stamps), (max(stamps)[1] if stamps else "-"),
      time.strftime("%H:%M:%S", time.localtime(max(stamps)[0])) if stamps else "-"))

# 2) 尖上的提交（API，清代理直连）
sub_by_hour = {}
tip_line = "读数不全"
try:
    tok = io.open(TOKFILE, encoding="utf-8").read().strip()
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    req = urllib.request.Request("https://api.github.com/repos/%s/git/ref/heads/%s" % (PROD, BRANCH),
                                 headers={"Authorization": "token " + tok, "Accept": "application/vnd.github+json",
                                          "User-Agent": "night-verdict"})
    d = json.loads(op.open(req, timeout=60).read().decode())
    sha = d["object"]["sha"]
    tip_line = "%s（API 现读）" % sha
    # 10-06 17:2x 修：下面这次 commits 列表**单独**一个 try。
    # 原来它跟"取尖"共用一个 try，第二次调用读不完（IncompleteRead 322868/63581）就把整块打回
    # "读数不全"，连已经取到的 40 位尖一起抹掉 ⇒ 终值单这一格整夜空着。
    # 现在：尖保住，拉不到列表只让"窗口内提交"那一小段写不可得（不许编数）。
    try:
        req2 = urllib.request.Request("https://api.github.com/repos/%s/commits?sha=%s&per_page=100" % (PROD, sha),
                                      headers={"Authorization": "token " + tok, "Accept": "application/vnd.github+json",
                                               "User-Agent": "night-verdict"})
        cs = json.loads(op.open(req2, timeout=60).read().decode())
        n = 0
        for c in cs:
            src = c.get("commit") or c
            ad = (src.get("author") or {}).get("date") or ""
            try:
                e = time.mktime(time.strptime(ad, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
            except Exception:
                continue
            if e_frm <= e <= e_cap:
                n += 1
                sub_by_hour[time.strftime("%H", time.localtime(e))] = sub_by_hour.get(time.strftime("%H", time.localtime(e)), 0) + 1
        tip_line += "；窗口内提交 %d 笔（%s）" % (n, "、".join("%s 时 %d" % (h, k) for h, k in sorted(sub_by_hour.items())) or "无")
    except Exception as exc:
        tip_line += "；窗口内提交读数不全：%s: %s（尖是上头 API 现读的真值）" % (
            exc.__class__.__name__, str(exc)[:70])
except Exception as exc:
    # 兜底：连尖都没取到 ⇒ 用 ls-remote 现读同一枝，把尖保住。
    # 这条路是 `_night_tip_local_r1.py` 每晚都在走的那条（17:18 实跑拿到完整 40 位），不是新假设。
    _lr = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "ls-remote", "origin",
                          "refs/heads/mirror/integration-frontend-apple-pass1"],
                         capture_output=True, timeout=180,
                         env=dict(os.environ, GIT_TERMINAL_PROMPT="0", HTTP_PROXY="", HTTPS_PROXY=""))
    _sha = ((_lr.stdout or b"").decode("utf-8", "replace").split() or [""])[0]
    tip_line = ("%s（ls-remote 兜底现读；API 读数不全：%s: %s）" % (_sha, exc.__class__.__name__, str(exc)[:60])
                if len(_sha) == 40 else
                "API 与 ls-remote 都读不到尖：%s: %s ⇒ 这一格不可得，不许拿旧值充数"
                % (exc.__class__.__name__, str(exc)[:90]))
print("2) 权威尖：%s" % tip_line)

# 3) 车队现值
r = subprocess.run([PYEXE, os.path.join(HERE, "_quota_roster_r1.py")], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", env=ENV, cwd=HERE, timeout=600)
m = re.search(u"名册：停在额度 (\\d+)｜在写 (\\d+)｜静默非闸 (\\d+)", (r.stdout or "") + (r.stderr or ""))
print("3) 车队现值：%s" % (u"停在额度 %s｜在写 %s｜静默非闸 %s" % m.groups() if m else u"读数不全"))

# 4) 暗窗
r = subprocess.run([PYEXE, os.path.join(HERE, "_dark_window_r1.py"), "1"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", env=ENV, cwd=HERE, timeout=300)
db = (r.stdout or "") + (r.stderr or "")
mt = re.search(u"最新一天（D(\\d+)）：暗窗 (\\d+) 段、合计 (\\d+) 分钟、最长一段 (\\d+) 分钟", db)
in_dark = u"暗窗里：是" in db
print("4) 真暗窗（在写 ≤1 且 脉搏新枝 = 0）：当前%s；%s" % (
    u"正处在" if in_dark else u"不在",
    (u"今天 D%s 共 %s 段、合计 %s 分钟、最长 %s 分钟" % mt.groups()) if mt else u"读数不全（尺没给最新一天汇总行）"))

# 5) 盘
pts = []
for l in io.open(os.path.join(HERE, "disk_points.txt"), encoding="utf-8", errors="replace"):
    m = re.match(r"^(\d\d-\d\d (\d\d):\d\d:\d\d) (\d+)$", l.strip())
    if m:
        pts.append((m.group(1), int(m.group(3)) / 1024.0))
inwin = [p for p in pts]
if pts:
    def mk(s):
        return time.mktime(time.strptime("%s %s" % (today[:4], s), "%Y %m-%d %H:%M:%S"))
    a, b = pts[0], pts[-1]
    span_h = max(0.01, (mk(b[0]) - mk(a[0])) / 3600.0)
    win = [(mk(t), v) for t, v in pts if e_frm <= mk(t) <= e_cap]
    w_txt = "窗口内点数不足，算不了段内斜率"
    if len(win) >= 2:
        wh = max(0.01, (win[-1][0] - win[0][0]) / 3600.0)
        w_txt = "%s→%s 共 %.2f 小时：空闲 %.0f → %.0f MiB ⇒ 消耗 %.0f MiB/小时（负值＝空闲在涨）" % (
            FRM, time.strftime("%H:%M", time.localtime(win[-1][0])), wh, win[0][1], win[-1][1],
            (win[0][1] - win[-1][1]) / wh)
    print("5) 盘（数值＝D: 空闲 MiB）：落档点 %d 枚｜全程 %s→%s（%.2f 小时）%.0f → %.0f MiB ⇒ 消耗 %.0f MiB/小时" % (
        len(pts), a[0], b[0], span_h, a[1], b[1], (a[1] - b[1]) / span_h))
    print("   本窗口（%s 起）：%s" % (FRM, w_txt))

# 6) 我这班发了多少、报警响了多少
ids = [l.strip() for l in io.open(os.path.join(HERE, "bus_ids.txt"), encoding="utf-8", errors="replace") if l.strip()]
log_lines = io.open(os.path.join(HERE, "autumn_watch.log"), encoding="utf-8",
                    errors="replace").read().splitlines()
# 日志只有 [HH:MM:SS]，没有日期 ⇒ 用「时钟倒退」把附加大小时切成日段，再按「末段＝取数当天」往前倒推
# （09-30 实测：整份 3832 行只有 1 次倒退，在 1425 行的 [00:45:08] ⇒ 第二段 1425→3832 全是 09-30）
segs, cur, prev = [], [], None
for l in log_lines:
    m = re.match(r"^\[(\d\d):(\d\d):(\d\d)\]", l)
    t = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))) if m else None
    if t is not None and prev is not None and t < prev - 3600:
        segs.append(cur)
        cur = []
    cur.append(l)
    if t is not None:
        prev = t
segs.append(cur)
win_hours = ["%02d" % h for h in range(int(FRM[:2]), (int(TO[:2]) - int(FRM[:2])) % 24 + 1 + int(FRM[:2]))]


def in_window(line, exact=True):
    """按那一行的 [HH:MM:SS] 精确判在不在窗里。win_hours 是「小时桶」，右端那一小时会被整段算进来
    （13:00→15:00 曾把 15:59 那张贴也算成窗内，16:18 实测到）；报警那一格要的是次数，必须按秒判。
    exact=False 时退回小时桶判据（第 7 格按小时列序列，本来就要整小时）。"""
    m = re.match(r"^\[(\d\d:\d\d:\d\d)\]", line)
    if not m:
        return False
    h = m.group(1)
    if not exact:
        return h[:2] in win_hours
    lo, hi = FRM + ":00", TO + ":00"
    if lo <= hi:
        return lo <= h < hi
    return h >= lo or h < hi      # 跨午夜（18:00→次日 02:00 这类）
# 日段只能挂在「取数当天」上倒推：01:08 我把自动轮重启了，日志多出 10-01 一段 ⇒
# 若拿 NIGHT_DATE 当锚点，09-30 那段会被倒推成 09-29（实测错过一次）。锚＝真今天。
real_today = time.strftime("%Y-%m-%d")
base_day = time.mktime(time.strptime(real_today, "%Y-%m-%d"))
seg, best_n = [], -1
cand = []
for i, s in enumerate(segs):
    n = sum(1 for x in s if re.match(u"^\\[(%s):" % "|".join(win_hours), x))
    d = time.strftime("%Y-%m-%d", time.localtime(base_day - (len(segs) - 1 - i) * 86400.0))
    hrs = sorted(set(re.match(r"^\[(\d\d):", x).group(1) for x in s if re.match(r"^\[\d\d:", x)))
    print("   日志日段 #%d：自 %s 起、%d 行、覆盖小时 %s-%s、窗口小时命中 %d 行、按真今天 %s 倒推 ≈ %s%s" % (
        i, (s[0][:10] if s else "-"), len(s), (hrs[0] if hrs else "--"), (hrs[-1] if hrs else "--"), n,
        real_today, d, u"  ← NIGHT_DATE" if d == today else ""))
    if d == today:
        cand.append((n, i, s, hrs))
# 先按日期选段（09-29 那段窗口命中 780 行 > 09-30 的 764 行，只按命中数会取错日子——实测踩过）
if cand:
    cand.sort(key=lambda x: x[0])
    best_n, _, seg, seg_hrs = cand[-1]
    miss = [h for h in win_hours if h not in seg_hrs]
    if miss:
        print(u"   ⚠ 选中的 %s 段里缺这些小时的行：%s ⇒ 第 7 格那几个小时是「无拍」不是「没人写」" % (today, ",".join(miss)))
else:
    print(u"   ⚠ 没有一段的倒推日期等于 NIGHT_DATE=%s ⇒ 下面第 6/7 格退回「命中最多的段」，日期归属不可信，别看" % today)
    seg_hrs = []
    for s in segs:
        n = sum(1 for x in s if re.match(u"^\\[(%s):" % "|".join(win_hours), x))
        if n > best_n:
            seg, best_n = s, n
# 6) 这一格的旧版只数「已发X贴」那种伴生行，于是漏掉了 15:59:48 那类只印 `bus post (tag): POST -> 201 …` 的风险贴——
#    16:16 拿 15:00→16:00 这一窗实测出来：那一窗真有 1 次上贴，旧算法报 0。现在两条形制都数，并分开成功与不判。
alarms, alarm_bad = [], []
for l in seg:
    m = re.search(r"^\[(\d\d:\d\d:\d\d)\] bus post \(([^)]*)\)(.*)$", l)
    if m and in_window(l):
        (alarms if "POST -> 201" in m.group(3) else alarm_bad).append((m.group(1), m.group(2)))
        continue
    m2 = re.search(r"^\[(\d\d:\d\d:\d\d)\] 已发(\S+).*-> (\d+)$", l)
    if m2 and in_window(l):
        alarms.append((m2.group(1), u"已发%s" % m2.group(2)))
seen = set()
alarms = [a for a in alarms if not (a[0] in seen or seen.add(a[0]))]
print("6) 本班上贴：`bus_ids.txt` 累计 %d 条（全时段清单，不是窗口计数）；自动轮在 %s 时段真响的报警 %d 次%s（%s）" % (
    len(ids), u"%s→%s" % (FRM, TO), len(alarms),
    (u"，另有 %d 次没拿到 201" % len(alarm_bad)) if alarm_bad else "",
    u"、".join("%s %s" % (a[0][:5], a[1]) for a in alarms[-8:]) or u"无"))

# 7) 车队按小时「在写」序列：直接回答「这段夜里到底有没有人在干活、谁在干活」
per_hour = {}
writing_names = {}
for l in seg:
    mh = re.match(r"^\[(\d\d):\d\d:\d\d\]", l)
    if not mh or mh.group(1) not in win_hours:
        continue
    h = mh.group(1)
    mm = re.search(u"名册：停在额度 (\\d+)｜在写 (\\d+)｜静默非闸 (\\d+)", l)
    if mm:
        per_hour.setdefault(h, []).append((int(mm.group(2)), int(mm.group(1))))
    d = re.search(u"额度名册：在写：(.+)$", l)
    if d:
        for nm in re.findall(r"([^、()]+?)\((\d+)分\)", d.group(1)):
            writing_names.setdefault(h, set()).add(nm[0])
print("7) 自动轮名册序列（取自倒推日期＝NIGHT_DATE 的那段，自 %s 起、该段窗口小时命中 %d 行；窗口 %s→%s）" % (
    (seg[0][:10] if seg else "-"), best_n, FRM, TO))
for h in sorted(per_hour):
    v = per_hour[h]
    nm = u"、".join(sorted(writing_names.get(h, []))) or u"（该小时无一拍记到在写名）"
    print("   %s 时：拍 %d 枚｜在写 max %d min %d｜额度 max %d｜该小时曾在写的车道：%s" % (
        h, len(v), max(x[0] for x in v), min(x[0] for x in v), max(x[1] for x in v), nm))
allnames = sorted(set().union(*writing_names.values())) if writing_names else []
print("   窗口内曾在写（任一拍在写名里出现过）共 %d 条：%s" % (len(allnames), u"、".join(allnames) or u"无"))
# 8) 值守覆盖——「这一档有没有人盯着」本身也要有数，不是我说盯过就算盯过。
#    为什么要这一格：今天已经三次整机重启（14:06 / 22:11 / 23:49），每一次都会把我的值守栈一起带走；
#    而终值单原本只有车队与门的读数，看不出夜里其实有一段没人盯。覆盖洞要能被算出来，不能靠我记得。
print("\n8) 值守覆盖（哨兵/续跑/监督/取数器）：")
try:
    import ctypes as _ct
    _up_ms = _ct.windll.kernel32.GetTickCount64()
    _boot = time.time() - _up_ms / 1000.0
    print("   本次开机 %s｜已 %.0f 分（若开机时刻晚于今天 18:00，则 18:00→开机之间无人盯）" % (
        time.strftime("%m-%d %H:%M:%S", time.localtime(_boot)), (time.time() - _boot) / 60.0))
except Exception as _e:
    print("   开机时刻：读数不全（%s）" % type(_e).__name__)

_slog = os.path.join(HERE, "_sentinel_relay_latest.log")
# 只算**本支实例**这一段：日志里每支哨兵都以一行「哨兵起来」开头，整份日志跨了好几天，
# 而轮行只有 HH:MM:SS 没有日期。02:04 第一版拿整天回推日期，把跨天的空档全数成断拍
# （93 处、最后一拍距今 -129594 分）——算错的尺比没有尺更坏，所以这里只量这一支。
try:
    _lines = io.open(_slog, encoding="utf-8", errors="replace").read().split(chr(10))
    _starts = [n for n, l in enumerate(_lines) if u"哨兵起来" in l]
    _base = _starts[-1] if _starts else 0
    _rounds = [l for n, l in enumerate(_lines) if n > _base and l.startswith("[") and u"] 轮 " in l]
    _start_hms = None
    if _starts:
        _m0 = re.match(u"^\[(\d\d:\d\d:\d\d)\]", _lines[_starts[-1]])
        _start_hms = _m0.group(1) if _m0 else None
    _st = []
    _se = time.mktime(time.strptime(today + " " + _start_hms, "%Y-%m-%d %H:%M:%S")) if _start_hms else None
    for _l in _rounds:
        _e2 = time.mktime(time.strptime(today + " " + _l[1:9], "%Y-%m-%d %H:%M:%S"))
        if _se is not None and _e2 < _se - 6 * 3600:
            _e2 += 86400.0        # 这支跨了午夜：钟点看着像「昨天」，其实是第二天
        _st.append(_e2)
    _g = [(_b - _a) / 60.0 for _a, _b in zip(_st, _st[1:])]
    _big = [x for x in _g if x > 25.0]
    if _start_hms:
        print(u"   本支哨兵自 %s 起：%d 拍｜相邻拍最大间隔 %.0f 分｜>25 分的断拍 %d 处｜最后一拍距今 %.0f 分" % (
            _start_hms, len(_st), max(_g) if _g else 0.0, len(_big),
            (time.time() - _st[-1]) / 60.0 if _st else -1.0))
        print(u"   这份日志（跨天累积、行内无日期）里共有 %d 个哨兵起点：重启或我手动拉回都会多一个，每支只覆盖它那一段" % len(_starts))
        if _big:
            print(u"   ⚠ 本段内的断拍就是覆盖洞：那些分钟里没人盯，别看成「那段很安静所以没红」")
    else:
        print(u"   哨兵轮次：读数不全（日志里没有「哨兵起来」那行）")
except Exception as _e:
    print(u"   哨兵轮次：读数不全（%s）" % type(_e).__name__)

for _nm, _f in (("续跑器", "_sentinel_keepalive.log"), ("监督", "autumn_supervise.log"),
                ("取数器", "_night_verdict_runner.log"), ("脉搏", "autumn_watch.log")):
    _p = os.path.join(HERE, _f)
    if os.path.isfile(_p):
        # 这两支平时只在「有动作」时落字，所以日志龄**不是**在世证明——在世证明是下面那行按命令行的现数
        print("   {nm} 日志最后一条距今 {age:.0f} 分（只表事件，不表死活）".format(
            nm=_nm, age=(time.time() - os.path.getmtime(_p)) / 60.0))
    else:
        print("   {nm} 日志：读数不全（文件不在）".format(nm=_nm))

_q = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*python*' } | "
      "Select-Object ProcessId,CommandLine | ConvertTo-Csv -NoTypeInformation")
try:
    _o = subprocess.run(["powershell", "-NoProfile", "-Command", _q], capture_output=True, env=ENV).stdout
    _txt = _o.decode("utf-8", "replace")
    _live = {}
    for _key in ("autumn_supervise_r1", "_sentinel_keepalive_r1", "_sentinel_relay_r1",
                 "autumn_watch.py", "_night_verdict_runner_r1"):
        _live[_key] = _txt.count(_key)   # 每行命令行只出现一次，所以出现次数＝在世实例数
    print("   现数在世实例（按命令行）：监督 {a}｜续跑 {b}｜哨兵 {c}｜脉搏 {d}｜取数器 {e}".format(
        a=_live["autumn_supervise_r1"], b=_live["_sentinel_keepalive_r1"], c=_live["_sentinel_relay_r1"],
        d=_live["autumn_watch.py"], e=_live["_night_verdict_runner_r1"]))
except Exception as _e:
    print("   在世实例：读数不全（%s）" % type(_e).__name__)

try:
    _proc = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "_processed")
    _d0 = hhmm_to_epoch("00:00")
    _ins = [p for p in os.listdir(_proc) if ".inserted_" in p and os.path.getmtime(os.path.join(_proc, p)) >= _d0]
    print("   今天（{d} 00:00 起）收件口进账 {n} 枚｜此刻根目录待插 {m} 枚".format(
        d=today, n=len(_ins),
        m=len([x for x in os.listdir(r"D:\moodle\_qoder_ledger_inbox")
               if x.endswith(".md") and os.path.isfile(os.path.join(r"D:\moodle\_qoder_ledger_inbox", x))])))
except Exception as _e:
    print("   进账枚数：读数不全（%s）" % type(_e).__name__)

print("\n边界：每格都印了读数来源；取不到就写「读数不全」，不补猜测值。窗口起点可用 NIGHT_FROM/NIGHT_TO 改。")
print("边界 2：第 7 格的「曾在写」是**该小时任意一拍被记进在写名册**的并集，含未登记车道（`未登记·<id8>`）；"
      u"它不等于「整小时都在写」。第 3 格是取数那一刻的现值，两者口径不同。")
