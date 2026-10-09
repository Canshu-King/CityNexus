# -*- coding: utf-8 -*-
"""敲门送达证明 r2：不信回执，只读目标流水。

r1 只扫 role=user 的 message 节点 —— 09-30 实测过一次「已送到但读成没送到」：
承载体可能是 attachment / queued_command。这一版三类承载都扫，并且要求
①标记串逐字出现、②同一条记录里收尾口令逐字等于 CLOSING_LINE.txt 那一行。
判活看流水，不看平台回执。
"""
import hashlib
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSING = os.path.join(os.path.dirname(HERE), "CLOSING_LINE.txt")
PROJ = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

tail = io.open(CLOSING, "rb").read()
TAIL_STR = tail.decode("utf-8").strip()
print(u"收尾口令 %d B sha1 %s" % (len(tail), hashlib.sha1(tail).hexdigest()))

lanes = {}
for name in os.listdir(PROJ):
    # 流水文件名就是会话 uuid（36 位含连字符）+ `.jsonl` = 42 字符；
    # 上一版拿 `len >= 45` 当筛子，把 80 个候选全筛空了 ⇒ 一把恒不命中的尺（会误判成「一记都没送到」）。
    if name.endswith(".jsonl") and len(name) >= 40 and u"/" not in name:
        lanes.setdefault(name[:8], name[:-6])
print(u"名册 %d 扇（按流水文件名前 8 位推）" % len(lanes))

want = sys.argv[1] if len(sys.argv) > 1 else u"05:11"
hits = miss = 0
for lane in sorted(lanes):
    path = os.path.join(PROJ, lanes[lane] + u".jsonl")
    size = os.path.getsize(path)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        f.seek(max(0, size - 400000))
        data = f.read()
    marker = None
    for line in data.split(chr(10)):
        if u"值守敲门 · %s · 10-03 %s" % (lane, want) not in line:
            continue
        try:
            r = json.loads(line.strip())
        except Exception:
            continue
        blob = json.dumps(r, ensure_ascii=False)
        carrier = r.get("type")
        if r.get("attachment"):
            carrier = u"%s/attachment:%s" % (carrier, r["attachment"].get("type"))
        elif (r.get("message") or {}).get("role"):
            carrier = u"%s/role=%s" % (carrier, r["message"]["role"])
        ok_tail = TAIL_STR in blob
        marker = u"%s｜尾行%s" % (carrier, u"逐字" if ok_tail else u"没接上")
    idle = (time.time() - os.path.getmtime(path)) / 60.0
    if marker:
        hits += 1
        print(u"送到 %s｜%s｜流水静 %d 分" % (lane, marker, idle))
    else:
        miss += 1
print(u"—— 本轮标记 %s：命中 %d 扇（没命中的扇名列在上）——" % (want, hits))
for lane in sorted(lanes):
    path = os.path.join(PROJ, lanes[lane] + u".jsonl")
    size = os.path.getsize(path)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        f.seek(max(0, size - 400000))
        data = f.read()
    if u"值守敲门 · %s · 10-03 %s" % (lane, want) in data:
        continue
    idle = (time.time() - os.path.getmtime(path)) / 60.0
    # 三态而不是两态：正在跑那一拍的窗口，消息会先排队、要到回合边界才落成 user 节点。
    # 只有「没找到」这一态会把「排队未落」读成「没送到」，然后就诱导我重发一遍（打双份）。
    if idle < 3.0:
        print(u"未见但静 %d 分（<3 分＝那一拍还在跑，判为排队未落，别重发）%s" % (idle, lane))
    else:
        print(u"未见 %s｜流水静 %d 分（这一形才算真没落到）" % (lane, idle))
