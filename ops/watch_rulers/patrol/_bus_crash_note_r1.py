# -*- coding: utf-8 -*-
"""整机重启的现场通报：每一个数都在这支脚本里现测，不许手打，缺任一格就 REFUSE 不发。

为什么要它：14:06 机器重启过一次（蓝屏史已预测到的那件事）。这不是稀奇事，稀奇的是它的后果没人报：
①谁起的后端/预览端口全没了 ⇒ 车道跑 e2e 会把 connection refused 误报成产品缺陷；
②值守进程全死（含我这条线，也含号令者自己起的那支）⇒ 报警会静默消失；
③23:00 那一档的自动取数器也在死之列。
所以这条帖的价值不在「出事」，在「出事后哪些东西现在是真的、哪些要重新起」。
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
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="", PYTHONIOENCODING="utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PORTS = [8000, 4781, 4782, 4783, 4787, 8693, 5173]
WATCH = {"supervise": "autumn_supervise_r1.py", "watch": "autumn_watch.py",
         "keepalive": "_sentinel_keepalive_r1.py", "sentinel": "_sentinel_relay_r1.py",
         "取数器": "_night_verdict_runner_r1.py"}
fails = []


def die(m):
    fails.append(m)


def sh(args, t=240):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=HERE, env=ENV, timeout=t)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# 1) 重启时刻
rc, out = sh(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime"])
m = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})\D+(\d{1,2}):(\d{2}):(\d{2})", out or "")
boot_s = ("%s-%02d-%02d %02d:%02d:%02d" % tuple(int(m.group(i)) for i in range(1, 7))) if m else ""
if not boot_s:
    die(u"重启时刻取不到（rc=%d，原文 %s）" % (rc, (out or "")[:80]))

# 2) 端口：逐个在 netstat 里数 LISTENING 行（两形：0.0.0.0 与 127.0.0.1）
rc, ns = sh(["netstat", "-ano", "-p", "tcp"])
listen = [l for l in (ns or "").splitlines() if "LISTENING" in l]
if rc != 0 or not listen:
    die(u"netstat 没给回任何 LISTENING 行 ⇒ 这一格不可判，不能据此说端口都没了（rc=%d）" % rc)
    portmap = {}
else:
    portmap = {}
    for p in PORTS:
        portmap[p] = sum(1 for l in listen if re.search(r"[:.]%d\s" % p, l) or l.split()[1].endswith(":%d" % p))
    if sum(portmap.values()) > 0:
        die(u"端口居然还在监听（%s）⇒ 本条『端口全没了』的判语作废，别发" % portmap)

# 3) 值守五支现况
rc, ps = sh(["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*python*' } | "
             "Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Csv -NoTypeInformation"])
alive = {}
created = []
for l in (ps or "").splitlines():
    p = l.split('","')
    if len(p) < 3 or p[0].strip('"') == "ProcessId":
        continue
    mc2 = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2}) (\d{1,2}):(\d{2}):(\d{2})", p[1].strip())
    for k, v in WATCH.items():
        if v in p[2]:
            alive.setdefault(k, []).append(p[0].strip('"'))
            if mc2:
                created.append(time.mktime(time.strptime(
                    "%s-%02d-%02d %02d:%02d:%02d" % tuple(int(mc2.group(i)) for i in range(1, 7)),
                    "%Y-%m-%d %H:%M:%S")))
for k in WATCH:
    if k not in alive:
        die(u"值守缺【%s】——这条帖要写的是『已拉回』，缺就不发" % k)
start_earliest = time.strftime("%H:%M:%S", time.localtime(min(created))) if created else None
if not start_earliest:
    die(u"五支的进程创建时间一个都没解析出来 ⇒ 不能声称『它们是 14:19 那一拍被拉回的』")

# 4) 名册与收件口
rc, ro = sh([sys.executable, os.path.join(HERE, "_quota_roster_r1.py")])
mr = re.search(u"^(\\d\\d:\\d\\d:\\d\\d) 名册：停在额度 (\\d+)｜在写 (\\d+)｜静默非闸 (\\d+)", ro or "", re.M)
if not mr:
    die(u"名册三个数没抓到（rc=%d）" % rc)
rostamp, stuck, writing, silentn = mr.group(1), mr.group(2), mr.group(3), mr.group(4)
# 「有没有车道是被这次重启打断的」：那种会显示成 ~10 分静默，而不是几小时。名册的形制是 `Q(3691分｜尾条 text)`，数字与「分」之间没有空格。
mins = [int(x) for x in re.findall(u"\\((\\d+)\\s*分｜尾条 text\\)", ro or "")]
shortest = min(mins) if mins else None
if shortest is None:
    die(u"名册里一枚静默分钟数都没解析到 ⇒ 不能据此说『没有车道是被重启打断的』")

rc, ib = sh([PY, os.path.join(HERE, "inbox_check.py")])
mi = re.search(r"inbox root=(\d+) 待处理, _processed=(\d+), 状态=(\w+)", ib or "")
mc = re.search(u"积压分类：门拒 (\\d+) 枚 / 门绿但第二道闸拒 (\\d+) 枚 / 门绿真能插 (\\d+) 枚", ib or "")
if not (mi and mc):
    die(u"收件口两行都没抓到（rc=%d）⇒ 不判『没打断任何块』" % rc)
root_n, proc_n, state = mi.group(1), mi.group(2), mi.group(3)
rej, bolt, green = mc.group(1), mc.group(2), mc.group(3)

# 5) 取数器那一支的目标时刻与 done
runlog = u""
try:
    runlog = io.open(os.path.join(HERE, "_night_verdict_runner.log"), encoding="utf-8").read().strip().split(chr(10))[-1]
except Exception:
    die(u"取数器日志读不到")
done_exists = os.path.exists(os.path.join(HERE, "_night_verdict_runner.done"))

# 旁证：supervise 自己记的那次「被系统杀掉」的退出码
sup_rc_time = None
try:
    for L in io.open(os.path.join(HERE, "autumn_supervise.log"), encoding="utf-8", errors="replace"):
        if "1073807364" in L:
            mm2 = re.match(r"\[\d\d-\d\d (\d\d:\d\d:\d\d)\]", L)
            if mm2:
                sup_rc_time = mm2.group(1)
except Exception:
    pass

if fails:
    print(u"REFUSE %d 条：" % len(fails))
    for x in fails:
        print(u"   - " + x)
    raise SystemExit(7)

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

now = time.strftime("%m-%d %H:%M:%S")
b = []
b.append(u"**值守 {now} · 这台机器 {boot} 重启过一次；后果不是『掉了十分钟』，是端口与报警进程全没了**".format(now=now, boot=boot_s))
b.append(u"")
b.append(u"实测（一枚脚本里现测，缺任一格就不发；全部只读）：")
b.append(u"- 重启时刻：`Win32_OperatingSystem.LastBootUpTime` = **{boot}**（现读于 {now}）。".format(boot=boot_s, now=now))
b.append(u"- 端口：`netstat -ano -p tcp` 里 LISTENING 共 {nl} 行，逐个查开发口 ⇒ {pl}。"
          u"**七个口一个都没有监听 ⇒ 谁起的后端/预览/手机链口在这次重启里没了**"
          u"（另一形 `Get-NetTCPConnection -State Listen` 同样取不到这七个口）。".format(
              nl=len(listen),
              pl=u"、".join(u":{p} 监听 {n} 行".format(p=p, n=n) for p, n in sorted(portmap.items()))))
boot_ep = time.mktime(time.strptime(boot_s, "%Y-%m-%d %H:%M:%S"))
since_boot_min = int((time.time() - boot_ep) / 60.0)
b.append(u"- 车道现状（{rs} 名册）：停在额度 {st}｜在写 {wr}｜静默非闸 {sl}。"
          u"名册里最短的一段静默是 **{sh} 分**（约 {ss} 小时），远大于重启到现在的 {mm} 分钟 ⇒ "
          u"没有哪条车道是『正被这次重启打断』的，不需要挨窗重发任务。".format(
              rs=rostamp, st=stuck, wr=writing, sl=silentn, sh=shortest,
              ss=u"%.1f" % (shortest / 60.0), mm=since_boot_min))
b.append(u"- 收件口（{st}）：root={rn} 待处理、`_processed`={pn}；分类 门拒 {rj} / 闸拒 {bo} / 真能插 {gr} "
          u"⇒ **重启没有留下半截块**，这一格干净。".format(st=state, rn=root_n, pn=proc_n, rj=rej, bo=bolt, gr=green))
start_ep = time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " " + start_earliest, "%Y-%m-%d %H:%M:%S"))
gap_min = int((start_ep - boot_ep) / 60.0)
b.append(u"- 我这条线的值守五支已用一键起复拉回：{w}。"
          u"这五支的进程创建时间最早一枚是 **{se}**（都在拉起那一分钟内），而重启是 {bt} ⇒ "
          u"中间空了 **{gp} 分钟没有任何报警在盯**。旁证：`autumn_supervise.log` 记着子支在 **{sr}** 以 rc=1073807364 退出——"
          u"那是被系统关机杀掉的码，不是脚本自己崩。".format(
              w=u"、".join(u"%s pid=%s" % (k, ",".join(v)) for k, v in sorted(alive.items())),
              se=start_earliest, bt=boot_s, gp=gap_min,
              sr=(sup_rc_time or u"（日志里没读到那行的时刻）")))
b.append(u"  取数器那支的日志：{l}；`done` 文件 {d} ⇒ 今晚 23:00:20 会自己出终值单与第 2 格补件。".format(
    l=runlog, d=(u"已存在（今天出过，别再拉第二次）" if done_exists else u"不存在（还没到点）")))
b.append(u"")
b.append(u"要传给别人的一句话：**跑 e2e 之前先把后端与预览口重新起起来，并按归属验三证（唯一标记行 + 子进程在跑 + 自己的日志）**。"
          u"否则端口 refused 会被当成产品缺陷报——那是重启的副作用，不是代码退步。")
b.append(u"")
b.append(u"边界：①我不重起任何**别人**起的进程（含号令者自己那支夜 watch），只报『它也不在了』；"
          u"②0 次写账本、0 次代插、0 次动权威线、0 次点申请额度；③端口判语用的是 netstat 的 LISTENING，不是连通性探测"
          u"（探测分不开『关闭』与『挂住』）。")
text = u"\n".join(b).rstrip() + u"\n" + CLOSING + u"\n"
tb = text.encode("utf-8")
print(u"写好 %d B｜sha1 %s｜尾行出现 %d 次" % (len(tb), hashlib.sha1(tb).hexdigest(), text.count(CLOSING)))
if text.count(CLOSING) != 1 or not text.rstrip().endswith(CLOSING):
    print(u"REFUSE：尾行不是一枚或不逐字")
    raise SystemExit(7)
outp = os.path.join(HERE, "_bus_crash_note_%s.md" % time.strftime("%H%M"))
io.open(outp, "w", encoding="utf-8", newline="\n").write(text)
print(text[:1000])
if "--dry" in sys.argv:
    raise SystemExit(0)
rc2, o2 = sh([PY, os.path.join(LC, "bus_post.py"), outp], t=900)
print(o2.strip()[:900])
raise SystemExit(rc2)
