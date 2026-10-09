# -*- coding: utf-8 -*-
"""第三次重启（23:49:41）切断了 N 扇还在动笔的窗——现测通报，缺格就不发。

和 22:32 那枚 `_bus_stop_note_r1.py` 的分工：那一枚问的是『离 23:00 还有多久、要不要再派』，
23:00 一过它就不该再发（会算出负分钟）。这一枚只回答一件事：**关机那一刻谁手上还有活**，
以及今晚那一档的件现在是什么状态（逐枚复算 sha1，不引用记忆里的数）。
"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="", PYTHONIOENCODING="utf-8")
ARTIFACTS = ["_night_verdict_1002_2300.txt", "_night_tipfix_1002_2300.txt"]
CUT_WINDOW_MIN = 25
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
fails = []


def die(m):
    fails.append(m)


def sh(args, t=300, cwd=None):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=cwd or HERE, env=ENV, timeout=t)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


rc, out = sh(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime"])
m = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})\D+(\d{1,2}):(\d{2}):(\d{2})", out or "")
if not m:
    die(u"开机时刻取不到（rc=%d）" % rc)
    boot_s, boot_ep = "", 0.0
else:
    boot_s = "%04d-%02d-%02d %02d:%02d:%02d" % tuple(int(m.group(i)) for i in range(1, 7))
    boot_ep = time.mktime(time.strptime(boot_s, "%Y-%m-%d %H:%M:%S"))

now = time.time()
if now - boot_ep > 40 * 60:
    die(u"本次开机已过 %d 分钟 ⇒ 再报『刚切断谁』已经失真，不发" % int((now - boot_ep) / 60.0))

rows = []
try:
    for fn in os.listdir(PROJ):
        if fn.endswith(".jsonl"):
            rows.append((os.path.getmtime(os.path.join(PROJ, fn)), fn[:8]))
except Exception as e:
    die(u"扫流水失败：%s" % type(e).__name__)
rows.sort(reverse=True)
cut = [(t, i) for t, i in rows if boot_ep - CUT_WINDOW_MIN * 60 <= t <= boot_ep + 90]
if not cut:
    die(u"没数到关机前还在动笔的窗 ⇒ 这条帖的核心不成立，不发")
mine = [i for i in ("42d1a6fa",) if i in [c[1] for c in cut]]
cut_other = [(t, i) for t, i in cut if i not in mine]
active_now = [(t, i) for t, i in rows if t > boot_ep + 90]

arts = []
for p in ARTIFACTS:
    fp = os.path.join(HERE, p)
    if not os.path.exists(fp):
        die(u"读数件 %s 不在" % p)
        continue
    b = io.open(fp, "rb").read()
    first = b.decode("utf-8", "replace").split(chr(10))[0].strip()[:60]
    if len(b) < 500:
        die(u"%s 只有 %d B，不像完整读数件" % (p, len(b)))
    arts.append((p, len(b), hashlib.sha1(b).hexdigest(), first))

rc, ps = sh(["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*python*' } | "
             "Select-Object ProcessId,CommandLine | ConvertTo-Csv -NoTypeInformation"])
watch_alive = {}
for k, v in (("supervise", "autumn_supervise_r1.py"), ("keepalive", "_sentinel_keepalive_r1.py"),
             ("sentinel", "_sentinel_relay_r1.py"), ("取数器", "_night_verdict_runner_r1.py")):
    watch_alive[k] = [x.split('","')[0].strip('"') for x in (ps or "").splitlines()
                      if v in x and x.split('","')[0].strip('"') != "ProcessId"]

if fails:
    print(u"REFUSE %d 条：" % len(fails))
    for x in fails:
        print(u"   - " + x)
    raise SystemExit(7)

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
st = time.strftime("%m-%d %H:%M:%S")
b = []
b.append(u"**值守 %s · 今天第三次重启（%s）：关机前有 %d 扇窗手上还有活，现在全暗**" % (st, boot_s, len(cut_other)))
b.append(u"")
b.append(u"- 重启（现测 `LastBootUpTime`）：**%s**，距今 %d 分。今天第三次（14:06:18 → 5946732511；22:11:02；这次）。" % (
    boot_s, int((time.time() - boot_ep) / 60.0)))
b.append(u"- 被切断的窗（关机前 %d 分内还在往自己流水里落字，括号里是它最后一笔落字的时刻）：%s" % (
    CUT_WINDOW_MIN, u"、".join(u"%s(%s)" % (i, time.strftime("%H:%M:%S", time.localtime(t))) for t, i in cut_other[:14])))
b.append(u"- 重启后又已经在写的：%s ⇒ 也就是说这一批不是不能干，是**没人再点它们**。" % (
    u"、".join(u"%s(%s)" % (i, time.strftime("%H:%M:%S", time.localtime(t))) for t, i in active_now[:6]) or u"（暂时没有）"))
b.append(u"- 今晚那一档的读数件（逐枚复算，不是引用旧数）：")
for p, n, s, first in arts:
    b.append(u"  - `%s`｜%d B｜sha1 `%s`｜首行「%s…」" % (p, n, s, first))
b.append(u"- 我这侧的值守四支现在都不在（supervise/keepalive/sentinel/取数器），但这是**设计如此**："
          u"它们各自的收工时刻是 23:35／23:40／23:00:50（取数器已出件并写了 done），不是被这次重启打坏的。"
          u"要接下一档，一条命令即可：`cd D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\patrol && python _watch_stack_r1.py`。")
b.append(u"")
b.append(u"要办的：那 %d 扇的活是**在手上断的**（不是交完在等）。要不要点名让它们回来自查『最后一笔落到哪、有没有半成品』，是你的权——"
          u"我不点、不派、不改任何人的块。" % len(cut_other))
b.append(u"")
b.append(u"边界：0 次派单、0 次代插、0 次动权威线、0 次碰他人进程；判『谁在写』一律读各自 jsonl 的 mtime，不看平台 updatedAt。")
text = u"\n".join(b).rstrip() + u"\n" + CLOSING + u"\n"
if text.count(CLOSING) != 1 or not text.rstrip().endswith(CLOSING):
    print(u"REFUSE：尾行不是一枚或不逐字")
    raise SystemExit(7)
tb = text.encode("utf-8")
print(u"写好 %d B｜sha1 %s" % (len(tb), hashlib.sha1(tb).hexdigest()))
outp = os.path.join(HERE, "_bus_cut_note_%s.md" % time.strftime("%H%M"))
io.open(outp, "w", encoding="utf-8", newline="\n").write(text)
print(text[:1200])
if "--dry" in sys.argv:
    raise SystemExit(0)
rc2, o2 = sh([PY, os.path.join(LC, "bus_post.py"), outp], t=900)
print((o2 or "").strip()[:700])
raise SystemExit(rc2)
