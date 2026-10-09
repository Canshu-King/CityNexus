# -*- coding: utf-8 -*-
"""勘外贴：0afdb49b  parked 在前置上，而前置已经在线上 several 小时——这是实测，不是猜测。

只认证据：ls-remote 取两枚 40 位 + 本地 git merge-base --is-ancestor 的 rc。
不派单、不裁语、不敲门叫醒车道（叫醒与派后续归号令者）。
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
REPO = r"D:\moodle\CityNexus"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, HTTP_PROXY="", HTTPS_PROXY="", PYTHONIOENCODING="utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
BR = "refs/heads/review/e766b154-ord0542-poster-day-line"

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()


def sh(args, t=240):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=REPO, env=ENV, timeout=t)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


rc, o = sh(["git", "ls-remote", "origin", TIPREF, BR])
heads = {}
for l in o.splitlines():
    parts = l.split("\t")
    if len(parts) == 2 and len(parts[0]) == 40:
        heads[parts[1].strip()] = parts[0].strip()
if TIPREF not in heads or BR not in heads:
    print("REFUSE：ls-remote 没同时给回两枚头，不判 ancestry\n" + o[:400])
    raise SystemExit(7)
tip, head = heads[TIPREF], heads[BR]
ancstamp = time.strftime("%H:%M:%S")
rc2, _ = sh(["git", "merge-base", "--is-ancestor", head, tip])
rc3, sub = sh(["git", "log", "-1", "--format=%h %ad %s", "--date=format:%m-%d %H:%M", head])
rc4, tipsub = sh(["git", "log", "-1", "--format=%h %ad %s", "--date=format:%m-%d %H:%M", tip])
if rc3 != 0 or rc4 != 0:
    print("REFUSE：本地读不到提交标题，不贴")
    raise SystemExit(7)
landed = (rc2 == 0)

# 同一时刻的另一组读数：静默分钟与「停在额度」的条数从名册现跑取，不许抄 01:59 那一拍的数
rp = subprocess.run([sys.executable, os.path.join(HERE, "_quota_roster_r1.py")],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    cwd=HERE, env=ENV, timeout=600)
roster = (rp.stdout or "") + (rp.stderr or "")
m_cnt = re.search(u"名册：停在额度 (\\d+)｜在写 (\\d+)｜静默非闸 (\\d+)", roster)
m_sil = re.search(u"0afdb49b\\((\\d+)\\s*分前\\)", roster)
m_stamp = re.search(u"^(\\d\\d:\\d\\d:\\d\\d) 名册", roster, re.M)
if not (m_cnt and m_sil and m_stamp) or rp.returncode != 0:
    print(u"REFUSE：名册那三个数没同时抓到（rc=%d），一条帖里不许混用两拍的读数" % rp.returncode)
    print(roster[:400])
    raise SystemExit(7)
stuck, writing, silent_n = m_cnt.group(1), m_cnt.group(2), m_cnt.group(3)
sil = m_sil.group(1)
rostamp = m_stamp.group(1)

# 裁语那行的行号会随账本重写腐烂，所以贴之前现读一次、连原文一起取（不手抄）
LED = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
LED_NEEDLE = u"ORD-0485 字典那笔作废"
led_lines = io.open(LED, encoding="utf-8", errors="replace").read().split(chr(10))
hits = [(i + 1, x.strip()) for i, x in enumerate(led_lines) if LED_NEEDLE in x]
if not hits:
    print(u"REFUSE：账本里找不到『%s』那笔裁语 ⇒ 不引行号也不引原文" % LED_NEEDLE)
    raise SystemExit(7)
led_no, led_text = hits[-1]
if len(led_text) > 320:
    led_text = led_text[:320] + u"…"

body = []
body.append(u"**值守 %s · 勘外（接 5937286888）：一条 parked 了 5 小时以上的车道，它等的前置其实已经在线上**"
            % time.strftime("%m-%d %H:%M"))
body.append(u"")
body.append(u"- 现场：%s 的名册是「停在额度 %s 条｜在写 %s｜静默非闸 %s」，其中 `0afdb49b` 静默 **%s 分**；"
            u"它名下最后一笔裁语是账本（现读）第 %d 行：" % (rostamp, stuck, writing, silent_n, sil, led_no))
body.append(u"  %s" % led_text)
body.append(u"- 实测前置状态（两枚 40 位是 %s 现取的，不是抄账本）：`ls-remote` 回" % ancstamp)
body.append(u"  - `%s` ⇒ `%s`" % (TIPREF, tip))
body.append(u"  - `%s` ⇒ `%s`" % (BR, head))
body.append(u"- 判据：`git merge-base --is-ancestor %s %s` 的 **rc=%d**（0=头一枚是第二枚的祖先 ⇒ 已在权威尖上）。" % (
    head[:12], tip[:12], rc2))
body.append(u"- 所以：**ORD-0542 已在线上**（提交 {sub}），那一格的前置条件已经满足。"
            u"同一拍名册里「在写」有 {w} 条 ⇒ 额度通道此刻是开着的，那 `0afdb49b` 更可能是停在一条**已经没有前置的 parked 单**上，"
            u"而不是停在额度上；要不要点名叫它做后续，是你的权。".format(sub=sub.strip(), w=writing))
body.append(u"")
body.append(u"- 现尖那笔是：%s（顺带说明队列确实在动）。" % tipsub.strip())
body.append(u"")
body.append(u"边界：①我只测 ancestry 与静默分钟，0 次派单、0 次叫醒该车道、0 次动权威线；"
            u"②『停在额度』那一格是 `_quota_roster_r1.py` 在 {rs} 现读的（尾条带额度字样且之后无动作），"
            u"静默 {sil} 分同样取自 jsonl mtime，都不看平台 updatedAt（它会滞后）；"
            u"③这是两拍读数、各自带时间戳：ancestry {anc}、名册 {rs}、账本现读紧随其后；"
            u"若你判定那格该并入别的单，这条读数就当参考，不必回话。".format(rs=rostamp, sil=sil, anc=ancstamp))
text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
tb = text.encode("utf-8")
print(u"写好 %d B｜sha1 %s｜ancestry rc=%d ⇒ landed=%s" % (len(tb), hashlib.sha1(tb).hexdigest(), rc2, landed))
print(text[:1200])
if not landed:
    print(u"REFUSE：ancestry 说没落地，这条勘外就不发")
    raise SystemExit(7)
outp = os.path.join(HERE, "_bus_addendum_0542_%s.md" % time.strftime("%H%M"))
io.open(outp, "w", encoding="utf-8", newline="\n").write(text)
if "--dry" in sys.argv:
    raise SystemExit(0)
p2 = subprocess.run([PY, os.path.join(LC, "bus_post.py"), outp], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=900, env=ENV)
print(((p2.stdout or "") + (p2.stderr or "")).strip()[:900])
raise SystemExit(p2.returncode)
