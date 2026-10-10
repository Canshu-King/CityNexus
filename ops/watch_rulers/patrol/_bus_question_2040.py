# -*- coding: utf-8 -*-
"""值守 20:3x 贴：ORD-0465 的申报块已经进收件口（我 20:31 那次提醒**不是**原因，实测说明），
但它旁边那枚『单问』块命名不合门规矩，会被静默跳过——那是一句等你裁的话。
"""
import hashlib
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="")
INBOX = r"D:\moodle\_qoder_ledger_inbox"

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

q = os.path.join(INBOX, "r_ord0465_2036_question.md")
d = os.path.join(INBOX, "r_ord0465_2036.md")
q_head = io.open(q, encoding="utf-8", errors="replace").read().split(chr(10))[:3] if os.path.isfile(q) else []
q_first = next((x for x in q_head if x.strip().startswith("### ")), "")
prob = next((x for x in io.open(q, encoding="utf-8", errors="replace").read().split(chr(10)) if x.strip().startswith("问题一句话")), "")
und = subprocess.run([PY, os.path.join(HERE, "_undeclared_deliveries_r1.py")], capture_output=True,
                     text=True, encoding="utf-8", errors="replace", env=ENV, timeout=900, cwd=HERE)
ul = [x.strip() for x in ((und.stdout or "") + (und.stderr or "")).split(chr(10)) if x.strip().startswith(("结论", "按族", "!!"))]
inv = subprocess.run([PY, os.path.join(HERE, "_invisible_blocks_r1.py")], capture_output=True,
                     text=True, encoding="utf-8", errors="replace", env=ENV, timeout=300, cwd=HERE)
il = [x.strip() for x in ((inv.stdout or "") + (inv.stderr or "")).split(chr(10)) if x.strip().startswith(("!!", "结论", "."))]
roster = subprocess.run([PY, os.path.join(HERE, "_quota_roster_r1.py")], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600, cwd=HERE)
rl = ((roster.stdout or "") + (roster.stderr or "")).split(chr(10))
r0 = next((x for x in rl if u"名册：" in x), "")
rw = next((x for x in rl if u"在写：" in x), "")

b = []
b.append(u"**值守 %s · 车道 da46954a 的 ORD-0465 申报块已进收件口（7,245 B，等门）；但它旁边那枚『单问』块命名不合门规矩，会被**静默跳过**——里面是一句等你裁的话。**" % time.strftime("%H:%M"))
b.append(u"")
b.append(u"- 标题行逐字：`%s`" % q_first[:130])
b.append(u"- 那句单问（同一文件里的原文）：`%s…`" % prob[:200])
b.append(u"- 隐形交付尺现读：%s" % u"；".join(x[:120] for x in il[:3]))
b.append(u"- 门的两条规矩卡住它：`ledger_inbox_apply_r2.py:81` 要文件名以 `_4位数字.md` 收尾，而它是 `_2036_question.md`；`:67` 还会跳过下划线开头的名。⇒ **它不会进队列，你也不会从门那儿知道有这句话**。")
b.append(u"- 该怎么处理归你：要么让车道把它改名（我不改别人的文件，0 次改名 0 次删除），要么你直接读那枚路径 `D:\\moodle\\_qoder_ledger_inbox\\r_ord0465_2036_question.md`（2,537 B，%s 写的）。" % time.strftime("%H:%M", time.localtime(os.path.getmtime(q))))
b.append(u"")
b.append(u"- 因果我按实测写清楚：我 20:31 提醒它『`review/R-ord0465-shared-landing` 头 `40911145…` 已推远端但账本与收件口 0 命中』——而 20:37 复查时我那条 marker 在它流水仍 **0 命中**（还在排队未落节点），它的 `r_ord0465_2036.md` 是 20:36 自己写的。**所以块能交上是它自己做的，不是我提醒的结果**，这句别记到我头上。")
b.append(u"- 漏申报尺同一跑：`%s`" % u"｜".join(x[:110] for x in ul[:2]))
b.append(u"- %s" % r0.strip())
b.append(u"- %s" % rw.strip())
b.append(u"")
b.append(u"边界：只读（收件口 stat 与内容、四把尺的现跑输出）。0 次写账本、0 次代插、0 次改名、0 次删除、0 次落地、0 次动权威线、0 次重启任何进程。")

out_fn = os.path.join(HERE, "_bus_question_2040.md")
io.open(out_fn, "w", encoding="utf-8", newline="\n").write(chr(10).join(b).rstrip() + chr(10) + CLOSING + chr(10))
print("写好 %d B｜单问块 %d B｜申报块 %d B" % (os.path.getsize(out_fn), os.path.getsize(q) if os.path.isfile(q) else -1,
                                            os.path.getsize(d) if os.path.isfile(d) else -1))
if "--dry" in sys.argv:
    print(chr(10).join(b)[:1600])
    raise SystemExit(0)
p = subprocess.run([PY, os.path.join(LC, "bus_post.py"), out_fn], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=600, env=ENV)
print(((p.stdout or "") + (p.stderr or "")).strip()[:500])
raise SystemExit(p.returncode)
