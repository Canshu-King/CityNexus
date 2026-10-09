# -*- coding: utf-8 -*-
"""值守 01:5x 上总线：六扇窗停在『等一句裁语』—— durable 副本。

为什么走总线而不是只敲窗口：窗口那记 01:48:52 已发但还没被消费（他那一轮还在跑，
流水在长，最后一条 active-leaf 01:52:58），回执只证明平台收了。总线是他自己会读的信箱，
落一条耐久的，窗口那记万一被崩溃带走也不丢。

数一律现跑出来：_knock_ruling_queue_r1.py 内部会重跑 _ready_not_landed_r1.py，
并读 _ruling_asks_latest.txt / _burn_curve_latest.txt 的表头时间戳；抓不到任何一格它自己 REFUSE。
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

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()

MAX_AGE_MIN = int(os.environ.get("KNOCK_MAX_AGE_MIN", "20"))
cands = sorted([f for f in os.listdir(HERE) if re.match(r"^_knock_ruling_queue_\d{4}\.txt$", f)],
               key=lambda f: os.path.getmtime(os.path.join(HERE, f)))
if not cands:
    print(u"REFUSE：没有 _knock_ruling_queue_*.txt 可当耐久副本")
    raise SystemExit(7)
fname = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else cands[-1]
kpath = os.path.join(HERE, fname)
age = (time.time() - os.path.getmtime(kpath)) / 60.0
fb = io.open(kpath, "rb").read()
fsize, fsha = len(fb), hashlib.sha1(fb).hexdigest()
if age > MAX_AGE_MIN:
    print(u"REFUSE：`%s` 是 %.1f 分钟前的读数（阈值 %d 分）——要发新数就重跑组合器" % (
        fname, age, MAX_AGE_MIN))
    raise SystemExit(7)
print(u"用现成敲门件作副本：%s（%.1f 分前、%d B、sha1 %s）——不再重跑组合器，"
      u"否则总线与窗口两边的数会对不上。" % (fname, age, fsize, fsha))
ktext = fb.decode("utf-8")
if not ktext.rstrip().endswith(CLOSING):
    print(u"REFUSE：敲门件尾行不逐字，不发")
    raise SystemExit(7)

body_txt = ktext.rstrip()[: -len(CLOSING)].rstrip()     # 尾行只留一枚，由下面统一接

n_wait = len(re.findall(u"^  · [0-9a-f]{8}", body_txt, re.M))
if n_wait == 0:
    print(u"REFUSE：正文里数不到等裁语的车道行")
    raise SystemExit(7)
head = re.search(u"【值守敲门 · ([^】]+)】", body_txt)
stamp = head.group(1) if head else time.strftime("%m-%d %H:%M")

bus = []
bus.append(u"**值守 %s · %d 扇窗停在『等你一句话』上（清单、队列、钱袋三格都是现跑读数）**" % (stamp, n_wait))
bus.append(u"")
bus.append(u"这一条同时是 `494abfd7` 窗口那记敲门的耐久副本（窗口 %s 发过、回执 ok 但那一轮还没消费，"
           u"所以这里落总线；两边内容是同一份，别当两件事处理）。" % stamp)
bus.append(u"")
bus.append(body_txt)
bus.append(u"")
mw = re.search(u"近 (\\d+) 小时内", body_txt)
ms = re.search(u"另有 (\\d+) 条落在", body_txt)
win_min = int(mw.group(1)) * 60 if mw else 0
if not win_min:
    print(u"REFUSE：正文里读不到落地窗口的小时数，复算那行会写错命令")
    raise SystemExit(7)
bus.append(u"复算（三条都只读，0 写账本 0 派单）：")
bus.append(u"- `cd D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\patrol && python _knock_ruling_queue_r1.py`"
            u" ⇒ 本次落盘 `%s`（%d B，sha1 `%s`）；组合器内嵌跑 `_ready_not_landed_r1.py %d`。" % (
                fname, fsize, fsha, win_min))
bus.append(u"- 等裁语清单取自 `_ruling_ask_extract_r1.py`（只取带请求形状的那一行；"
            u"末段是交付陈述的 %s 条已单独列出、没算进 %d）。" % (
                ms.group(1) if ms else u"若干", n_wait))
bus.append(u"- 钱袋取自 `_burn_curve_r1.py`：同一钟点对同一钟点；`credits_burn_r2.py` 在窗口不足 3 小时时**主动拒答**撞墙时刻——"
            u"10-02 01:38 那一径曾给出『17:20 撞墙』，那是把深夜收尾样本当全天速率，已作废。")
bus.append(u"")
bus.append(u"边界：①我不裁语、不落地、不动权威线，这九句只归你；②『静默 N 分』是从 jsonl 尾部量的，"
            u"不是平台 updatedAt（它会滞后）；③外推不是预测。")
text = u"\n".join(bus).rstrip() + u"\n" + CLOSING + u"\n"
outp = os.path.join(HERE, "_bus_ruling_wait_%s.md" % time.strftime("%H%M"))
io.open(outp, "w", encoding="utf-8", newline="\n").write(text)
tb = text.encode("utf-8")
print(u"写好 %d B｜sha1 %s｜尾行逐字=%s（出现 %d 次）" % (
    len(tb), hashlib.sha1(tb).hexdigest(), text.rstrip().endswith(CLOSING), text.count(CLOSING)))
print(text[:700])
if "--dry" in sys.argv:
    raise SystemExit(0)
p2 = subprocess.run([PY, os.path.join(LC, "bus_post.py"), outp], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=900, env=ENV)
print(((p2.stdout or "") + (p2.stderr or "")).strip()[:900])
raise SystemExit(p2.returncode)
