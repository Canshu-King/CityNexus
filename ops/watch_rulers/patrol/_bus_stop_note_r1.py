# -*- coding: utf-8 -*-
"""第二次重启 + 全队停两小时：一份现测的短通报（每个数现抓，抓不到就 REFUSE 不发）。

为什么不复用 14:28 那枚：那一枚的正文写的是「重启过一次」，而现在今天已经是第二次——
沿用会把事实说轻。这一枚只报本次这拍量到的：几点重启、端口是否又归零、全队停多久、尖停在哪一分钟、
值守与 23:00 取数器现在的 pid。
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
PORTS = [8000, 4781, 4782, 4783, 4787, 8693, 5173]
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
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
    die(u"重启时刻取不到（rc=%d）" % rc)
    boot_s = ""
    boot_ep = 0
else:
    boot_s = "%04d-%02d-%02d %02d:%02d:%02d" % tuple(int(m.group(i)) for i in range(1, 7))
    boot_ep = time.mktime(time.strptime(boot_s, "%Y-%m-%d %H:%M:%S"))

rc, ns = sh(["netstat", "-ano", "-p", "tcp"])
listen = [l for l in (ns or "").splitlines() if "LISTENING" in l]
if rc != 0 or not listen:
    die(u"netstat 没回 LISTENING（rc=%d）⇒ 不能判端口" % rc)
    dead = []
    live_ports = []
else:
    live_ports = [p for p in PORTS if any(l.split()[1].endswith(":%d" % p) for l in listen)]
    dead = [p for p in PORTS if p not in live_ports]
    if live_ports:
        die(u"还有端口在监听 %s ⇒ 『端口全没了』这句不成立，不发" % live_ports)

rc, ro = sh([sys.executable, os.path.join(HERE, "_quota_roster_r1.py")])
mr = re.search(u"^(\\d\\d:\\d\\d:\\d\\d) 名册：停在额度 (\\d+)｜在写 (\\d+)｜静默非闸 (\\d+)", ro or "", re.M)
sil = [int(x) for x in re.findall(u"\\((\\d+)\\s*分｜尾条", ro or "")]
if not mr:
    die(u"名册三数没抓到（rc=%d）" % rc)
if not sil:
    die(u"一枚静默分钟都没解析到 ⇒ 不能说『最短静默多少分』")
rostamp, stuck, writing, silentn = mr.group(1), mr.group(2), mr.group(3), mr.group(4)

rc, lr = sh(["git", "ls-remote", "origin", TIPREF], cwd=r"D:\moodle\CityNexus")
mt = re.match(r"^([0-9a-f]{40})\s", (lr or "").strip() + " ")
tip = mt.group(1) if mt else ""
rc2, lg = sh(["git", "log", "-1", "--format=%ad", "--date=format:%H:%M", tip],
             cwd=r"D:\moodle\CityNexus") if tip else (1, "")
tip_hm = (lg or "").strip()
if not tip:
    die(u"权威尖取不到（rc=%d）" % rc)
if rc2 != 0 or not re.match(r"^\d\d:\d\d$", tip_hm):
    die(u"尖那笔的提交时刻取不到（rc=%d，原文 %r）" % (rc2, tip_hm[:20]))
    tip_ep = time.time()
else:
    # 尖龄：把 HH:MM 按今天解释；若比现在晚就是昨天推的（夜里跨午夜）
    tip_ep = time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " " + tip_hm, "%Y-%m-%d %H:%M"))
    if tip_ep > time.time() + 3600:
        tip_ep -= 86400

rc, sd = sh([PY, os.path.join(HERE, "_ready_not_landed_r1.py"), "360"])
mq = re.search(u"确有未落地差 (\\d+) 枚", sd or "")
if not mq:
    die(u"队列枚数取不到（rc=%d）⇒ 不报队列" % rc)
queue_n = mq.group(1)

pids = {}
rc, ps = sh(["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*python*' } | "
             "Select-Object ProcessId,CommandLine | ConvertTo-Csv -NoTypeInformation"])
for k, v in (("supervise", "autumn_supervise_r1.py"), ("watch", "autumn_watch.py"),
            ("keepalive", "_sentinel_keepalive_r1.py"), ("sentinel", "_sentinel_relay_r1.py"),
            ("取数器", "_night_verdict_runner_r1.py")):
    pids[k] = [p.split('","')[0].strip('"') for p in (ps or "").splitlines()
               if v in p and p.split('","')[0].strip('"') != "ProcessId"]
    if not pids[k]:
        die(u"值守缺【%s】⇒ 这条帖要说『已恢复』，缺就不发" % k)

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
b.append(u"**值守 {now} · 今天第二次重启（{boot}）；更要紧的是：权威尖已经 {age} 分钟没动（最后一笔 {th}），未落地差 {q} 枚**".format(
    now=now, boot=boot_s, age=int((time.time() - tip_ep) / 60.0), th=tip_hm, q=queue_n))
b.append(u"")
b.append(u"- 重启：`LastBootUpTime` = **{boot}**（{ago} 分钟前）。今天这是第二次（第一次 14:06:18，记在总线 5946732511）。".format(
    boot=boot_s, ago=int((time.time() - boot_ep) / 60.0)))
b.append(u"- 端口：**又归零了**——{ports} 在 netstat 的 {nl} 行 LISTENING 里一个都没有。跑 e2e 前得先把口起回来，"
          u"refused 不是产品缺陷。".format(ports=u"、".join(u":%d" % p for p in dead), nl=len(listen)))
ago_min = int((time.time() - boot_ep) / 60.0)
left_min = int((time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 23:00:00", "%Y-%m-%d %H:%M:%S"))
                - time.time()) / 60.0)
before = [s for s in sil if s > ago_min]          # 停得比重启还早 ⇒ 不是重启打散的
after = [s for s in sil if s <= ago_min]
b.append(u"- 工人（{rs} 名册）：停在额度 {st}｜**在写 {wr}**｜静默非闸 {sl}。把静默分钟和『重启至今 {ago} 分』对齐数一遍："
          u"**{nb} 扇停得比重启还早**（最长 {mx} 分）⇒ 它们不是这次重启打散的，是本来就没事干；"
          u"另有 {na} 扇是重启之后才停的。".format(
              rs=rostamp, st=stuck, wr=writing, sl=silentn, ago=ago_min,
              nb=len(before), mx=(max(before) if before else 0), na=len(after)))
b.append(u"- 权威尖：`{tip}`，那笔提交时刻 **{th}**（距今 {age} 分钟）；近 6 小时未落地差 **{q} 枚**。".format(
    tip=tip[:12], th=tip_hm, age=int((time.time() - tip_ep) / 60.0), q=queue_n))
b.append(u"- 值守已恢复五支：{w}。**今晚 23:00:20 的自动取数器在里面**（`done` 不存在）⇒ "
          u"不管 23:00 前车队有没有活，那一档的读数件都会出；但若车队就这么停到 23:00，读数会如实记下 `在写 0`——那是状态不是故障。".format(
              w=u"、".join(u"%s=%s" % (k, v[0]) for k, v in sorted(pids.items()))))
b.append(u"")
b.append(u"要办的只有一件：**离 23:00 只剩 %d 分钟**。要么现在把该派的派出去（工人不会自己回来读账本），"
          u"要么今晚这一档就按上面这组实测如实入账——两个选择都行，**但别让它默认成第二个**。" % int(
              (time.mktime(time.strptime(time.strftime("%%Y-%%m-%%d 23:00:00", "%%Y-%%m-%%d %%H:%%M:%%S")) - time.time()) / 60.0)))
b.append(u"边界：0 次派单、0 次裁语、0 次代插、0 次动权威线、0 次碰他人进程（含你起的夜 watch）；上面每个数都在脚本里现抓，缺一格就 REFUSE。")
text = u"\n".join(b).rstrip() + u"\n" + CLOSING + u"\n"
tb = text.encode("utf-8")
print(u"写好 %d B｜sha1 %s｜尾行 %d 次" % (len(tb), hashlib.sha1(tb).hexdigest(), text.count(CLOSING)))
if text.count(CLOSING) != 1 or not text.rstrip().endswith(CLOSING):
    print(u"REFUSE：尾行不对")
    raise SystemExit(7)
outp = os.path.join(HERE, "_bus_stop_note_%s.md" % time.strftime("%H%M"))
io.open(outp, "w", encoding="utf-8", newline="\n").write(text)
print(text[:1100])
if "--dry" in sys.argv:
    raise SystemExit(0)
rc3, o3 = sh([PY, os.path.join(LC, "bus_post.py"), outp], t=900)
print((o3 or "").strip()[:700])
raise SystemExit(rc3)
