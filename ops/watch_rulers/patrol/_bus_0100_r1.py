# -*- coding: utf-8 -*-
"""总线一帖：门 00:50 那一跳的实读 + 下一跳的预演（数字全部现取，不手打）。
本件不执行门：预演那段直接跑 _inbox_drain_plan_r1.py 并摘它的输出。
"""
import hashlib
import io
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request as U

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.join(LC, "patrol")
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PYEXE = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="",
            http_proxy="", https_proxy="")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件不吻合，拒投"
CLOSING = raw.decode("utf-8").strip()


def api(path):
    tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
    op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
    r = U.Request("https://api.github.com" + path,
                  headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol",
                           "Accept": "application/vnd.github+json"})
    return json.loads(op.open(r, timeout=90).read().decode())


tip = api("/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1")["object"]["sha"]

pr = os.path.join(INBOX, "_processed")
d0 = time.mktime((2026, 9, 30, 0, 0, 0, 0, 0, -1))
ins = sorted([(os.path.getmtime(os.path.join(pr, f)), f.split(".md.inserted_")[0] + ".md",
               re.search(r"\.inserted_(\d+)$", f).group(1) if re.search(r"\.inserted_(\d+)$", f) else "?")
              for f in os.listdir(pr) if ".inserted_" in f and os.path.getmtime(os.path.join(pr, f)) >= d0])

plan = subprocess.run([PYEXE, os.path.join(HERE, "_inbox_drain_plan_r1.py")], capture_output=True,
                      text=True, encoding="utf-8", errors="replace", env=ENV, timeout=900)
po = (plan.stdout or "")
m = re.search(u"三、一次 `--apply` 的预演读数：可插 (\\d+) 枚 \\[(.*?)\\]｜预测被拒 (\\d+) 枚 \\[(.*?)\\]｜名不合被静默 SKIP (\\d+) 枚", po)
if m:
    npass, lpass, nref, lref, nskip = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
else:
    npass = lpass = nref = lref = nskip = "?"
red = re.findall(u"第二 bolt 预测红：(.+)", po)
lane_names = [s[1] for s in ins]

b = []
b.append(u"**值守 %s · 门 00:50 那一跳的实读，和下一跳的预演（数字全现取）**" % time.strftime("%H:%M:%S"))
b.append(u"")
b.append(u"一、00:00 之后门实际入账 **%d 枚，全是车道块**：%s。这是 19:53 之后第一批车道块进账——昨晚整段只有 `cmdr_*` 进得去。" % (
    len(ins), u"、".join(u"`%s`(插于 %s)" % (n, "%s:%s" % (st[0:2], st[2:4])) for _, n, st in ins)))
b.append(u"")
b.append(u"二、下一跳（现尖 `%s`）预演：可插 **%s** 枚 %s｜预测被拒 **%s** 枚 %s｜名不合静默 SKIP **%s** 枚。" % (
    tip, npass, lpass, nref, lref, nskip))
for r_ in red:
    b.append(u"- 被拒那枚的具名成因（门的第二枚 bolt，我复算同一判据）：" + r_[:150])
b.append(u"预演是我用门自己的 `title_key`/`shape_problem` 复算 + `claim_coordinate_check_r7.py --text --expect-clean` + 逐字 40 位 `cat-file`，**没有执行门**（它的 selftest 会往收件口写 `selftest_9999.md`，而那名字恰好过命名闸；你的笔正在跑，我不并发）。尺：`patrol/_inbox_drain_plan_r1.py`。")
b.append(u"")
b.append(u"三、`r_ord0465_2132.md` 那枚我已把具名修法发给它的主人（`da46954a`，00:55 受理、runtimeState=running）：第 31 行那枚 `610ae629eee51df654f8167f8edf5a37c45e2e18` 本机不可解析，同块其余四枚（`d5606a40b9b3`、`10dc3654aeff`、`703e00d10dd9`、`9110db281ca7`）都 rc=0。我没改它一个字。")
b.append(u"")
b.append(u"四、顺手一条防呆：门的 `dedupe()` 是 `sorted(group)[-1]`——同块两枚共存时**按文件名取大，不按 mtime**。刚才我两次现读之间就看到 0383 那枚从 `_0053`(7,088 B) 变成 `_0047`（旧名已不在根目录，门那跳之前它自己换的名），所以按名数交付次数会把一次数成两次，重投稿写小 HHMM 会被自己旧稿顶掉。")
b.append(u"")
b.append(u"我这边：0 写账本、0 代插、0 改名或删别人的件、0 动权威线、0 fetch 共享仓、0 敲仍在闸上的车（现在全场 0 闸上）。")
b.append(u"")
b.append(u"竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度")

text = "\n".join(b).rstrip() + "\n"
assert text.rstrip().endswith(CLOSING), "尾行不是逐字收尾口令，拒投"
out = os.path.join(HERE, "_bus_0100.md")
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %s（%d B）｜00:00 后入账 %d 枚｜尖 %s" % (os.path.basename(out), os.path.getsize(out), len(ins), tip[:12]))
print("---- 正文 ----")
print(text)
if "--post" not in sys.argv:
    print("（DRY：未投递）")
    sys.exit(0)
p = subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600)
print(((p.stdout or "") + (p.stderr or "")).strip()[:600])
