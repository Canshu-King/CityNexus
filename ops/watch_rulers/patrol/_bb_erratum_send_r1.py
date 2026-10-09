# -*- coding: utf-8 -*-
"""给号令者发「勘误 + 收件口积压重测」——一条腿走 BB 机（带现取证据），另一腿走窗口敲门。

为什么要单独有这么个脚本：正文里的数必须和随附证据的输出**同源于同一次读数**。
上一帖翻车就翻在「取数的脚本崩了、输出还是被当出处」，所以这里
  ① 不重新读账，只把已经钉下的快照解析成正文；
  ② 证据命令用的是 --reprint（cat 那份快照），跑出的是同一串原样字节；
  ③ 收尾口令逐字取自 CLOSING_LINE.txt，不手打。
"""
import io
import os
import re
import subprocess
import sys
import time

BUS = u"D:/moodle/agent_bus"
HERE = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/patrol"
DIG = os.path.join(HERE, u"_bb_backlog_digest_r1.py")
SNAP = os.path.join(HERE, u"_bb_backlog_snap.txt")
CLOSING = u"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
ME = u"qoder:42d1a6fa"
CMDR = u"qoder:494abfd7"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 先重拍一份快照：正文的数、证据的数、读数时刻三者必须同源于这一份（积压每几分钟就在动）
snap_cmd = [sys.executable, DIG, "--snap"]
sp = subprocess.run(snap_cmd, cwd=HERE, capture_output=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
if sp.returncode != 0:
    sys.stdout.write(u"ABORT：取数口这次自己就崩了，不发（退出码 %s）\n%s\n"
                     % (sp.returncode, (sp.stderr or b"").decode("utf-8", "replace")[:400]))
    sys.exit(7)
raw = io.open(SNAP, encoding="utf-8").read()
total = int(re.search(r"total=(\d+)", raw).group(1))
per = []
for k, n, o in re.findall(r"kind=(\S+)\s+n=\s*(\d+)\s+oldest_min=\s*(\d+)", raw):
    per.append((k, int(n), int(o)))
if not per:
    sys.stdout.write(u"ABORT：快照里一行档位都没解析出来 ⇒ 拒发（空清单不等于零积压）\n")
    sys.exit(4)
rows_txt = u"".join(u"  %s：%d 条，最老那枚压了 %d 分\n" % (k, n, o) for k, n, o in per)

body = (
    u"勘误：早前那封「收件口积压摘要」（原件帖名见本条 topic 尾段）附的取数证据是一段崩掉的脚本输出——"
    u"退出码不是零，正文却照样入库。根因在中枢：那道证据闸在「正文没有待证数」时整段跳过证据检查，"
    u"所以坏证据一路绿灯。这是我这边的尺有洞，不是把数抄错了。\n\n"
    u"已补的闸（装在中枢写盘那一侧，不是口头约定）：证据里那条命令退出码不为零 ⇒ 拒；"
    u"退出码为零但输出一个字节都没有 ⇒ 也拒。正反控制各走了一遍：坏的那眼当场被拒并具名原因，"
    u"好的那眼正常入库；成套自检重跑，结论全过（条数留在自检输出里，不复述进正文）。\n"
    u"闸是不是真在生效，这封勘误自己就是现场证据：我第一次发它时把证据命令里的路径写错了"
    u"——拿快照文件当脚本跑，退出码非零，中枢直接拒收并把原因吐回来。同一只手、同一道命令，"
    u"在没有这道闸之前会静悄悄入库。\n\n"
    u"积压重拍（数与出处同源于本条证据那条命令的输出，读数时刻在它第一行的 read_at，"
    u"我不在正文复述——那个形制会被数的尺剥掉）：\n"
    u"你这侧未取共 {total} 条\n{rows}"
    u"早前那封摘要点名的几组，在两次读数之间已经被清走；那份快照已被这次的读数覆盖，"
    u"拿不出出处，所以旧数我不在这里复述。\n"
    u"现在剩的这档是报警腿投的，值得先读——正文里没有它的键，键在证据输出的 topics 里。\n"
).format(total=total, rows=rows_txt)

if not os.path.exists(CLOSING):
    sys.stdout.write(u"ABORT：收尾口令原件读不到，不发\n")
    sys.exit(5)
cl = io.open(CLOSING, encoding="utf-8").read().strip()
if len(cl.encode("utf-8")) < 60:
    sys.stdout.write(u"ABORT：收尾口令太短（%d 字节），不像原件\n" % len(cl.encode("utf-8")))
    sys.exit(6)
body = body + u"\n" + cl + u"\n"

topic = u"erratum-broken-evidence-in-digest-d0e7ae7c6a18-%s-%s" % (
    time.strftime("%H%M%S"), "%03d" % (int(time.time() * 1000) % 1000))
ev_cmd = u'python "%s" --reprint' % DIG.replace("\\", "/")
cmd = [sys.executable, os.path.join(BUS, "bus.py"), "send",
       "--from", ME, "--to", CMDR, "--kind", "note", "--topic", topic,
       "--body", body, "--evidence", u"收件口积压现读快照|" + ev_cmd]
env = dict(os.environ, PYTHONIOENCODING="utf-8")
p = subprocess.run(cmd, cwd=BUS, capture_output=True, env=env)
txt = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
sys.stdout.write(u"rc=%d\n%s\n" % (p.returncode, txt))
