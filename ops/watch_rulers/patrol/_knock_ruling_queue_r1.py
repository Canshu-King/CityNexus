# -*- coding: utf-8 -*-
"""把「九扇窗等裁语 + 队列现况 + 钱袋」编成一记敲门帖，交给号令者那扇窗。

为什么要有这个组合器而不是手打：帖子里每个数都必须来自那一刻真跑出来的巡检工件，
手打会把上一轮的读数当这一轮的（10-01 就这么错过一次）。解析不到任何一格就拒投，
不许用「大约」填坑。
"""
import hashlib
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ASKS = os.path.join(HERE, "_ruling_asks_latest.txt")
CURVE = os.path.join(HERE, "_burn_curve_latest.txt")
CLOSING = os.path.join(os.path.dirname(HERE), "CLOSING_LINE.txt")
CLOSING_SHA1 = "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
OUT = os.path.join(HERE, "_knock_ruling_queue_%s.txt" % time.strftime("%H%M"))
WIN_MIN = 360          # 落地窗口取 6 小时；帖子里那句「近 N 小时」由它算，不手写

fails = []


def die(msg):
    fails.append(msg)


# ---------- 1) 等裁语的车道（从工件解析，不手打） ----------
if not os.path.exists(ASKS):
    die(u"裁语工件不在：%s" % ASKS)
    lines = []
else:
    lines = io.open(ASKS, encoding="utf-8").read().split(chr(10))

stamp = ""
for l in lines:
    m = re.match(u"^_ruling_ask_extract_r1\\.py 于 ([\\d\\-: ]+)", l)
    if m:
        stamp = m.group(1)
        break

lanes = {}          # id -> (静默分, 档位, [原文行])
cur = None
order = []
for l in lines:
    mh = re.match(u"^([0-9a-f]{8})\\s+(\\S+)\\s+([\\d.]+) 分｜(\\S+)$", l)
    if mh:
        cur = mh.group(1)
        lanes[cur] = (mh.group(3), mh.group(4), [])
        order.append(cur)
        continue
    md = re.match(u"^\\s+└ (.*)$", l)
    if md and cur:
        lanes[cur][2].append(md.group(1))

tot_line = u""
ruling_ids = []
for l in lines:
    if u"分档合计" in l:
        tot_line = l
m = re.search(u"号令者可裁 (\\d+) 条（([^）]*)）", tot_line)
if not m:
    die(u"合计行读不出号令者可裁的条数：%s" % tot_line[:80])
else:
    n_claim = int(m.group(1))
    ids_claim = [x.strip() for x in m.group(2).split(u"、") if x.strip()]
    mine = [i for i in order if lanes[i][1] == u"号令者可裁"]
    if n_claim != len(mine) or sorted(ids_claim) != sorted(mine):
        die(u"合计与逐条对不上：合计 %d/%s，逐条数到 %d/%s ⇒ 解析漏了道" % (
            n_claim, u",".join(ids_claim), len(mine), u",".join(mine)))
    ruling_ids = mine

# 「号令者可裁」这一档是抽取器按关键词给的，末段原文有可能只是交付陈述（0495/0543 那种「做完并交付」）。
# 把没在等人的那些挑出来分开列，否则帖子里会出现「N 扇窗在等你」其实人家在报完成。
REQ = re.compile(u"等你一句|等一句|要一句|要你裁|请你|请点明|给不了|不自造|不擅自|等你|Open\\b")
wait_ids, stmt_ids = [], []
asks_pick = {}
for i in ruling_ids:
    hit = None
    for a in lanes[i][2]:
        if REQ.search(a):
            hit = a
            break
    if hit:
        wait_ids.append(i)
        asks_pick[i] = hit
    else:
        stmt_ids.append(i)

# ---------- 2) 落地队列（现跑一次只读巡检） ----------
p = subprocess.run([sys.executable, os.path.join(HERE, "_ready_not_landed_r1.py"), str(WIN_MIN)],
                   capture_output=True)
rl = p.stdout.decode("utf-8", "replace").split(chr(10))
tip, tip_age, landed, gap = "", "", "", ""
for l in rl:
    mt = re.search(u"现尖 `([0-9a-f]{40})`（提交时间 ([\\d.]+) 分前）", l)
    if mt:
        tip, tip_age = mt.group(1), mt.group(2)
    mg = re.search(u"已在线上 (\\d+) 枚", l)
    if mg:
        landed = mg.group(1)
    mx = re.search(u"确有未落地差 (\\d+) 枚", l)
    if mx:
        gap = mx.group(1)
cands = [l.strip() for l in rl if l.startswith(u"  review/")]
if p.returncode != 0:
    die(u"落地队列巡检 rc=%d，不拿它的数" % p.returncode)
for num, var in ((u"现尖", tip), (u"尖龄", tip_age), (u"已在线上", landed), (u"未落地差", gap)):
    if not var:
        die(u"落地队列读数缺【%s】一格" % num)
if len(cands) != int(gap or -1):
    die(u"候选行数(%d)与未落地差(%s)不一致 ⇒ 行列没收齐" % (len(cands), gap))

# ---------- 3) 钱袋（同钟点份额口径） ----------
cl = io.open(CURVE, encoding="utf-8").read().split(chr(10)) if os.path.exists(CURVE) else []
cstamp = today_tot = ysame_tot = share = proj = floor_y = ""
for l in cl:
    m1 = re.match(u"^_burn_curve_r1\\.py 于 ([\\d\\-: ]+)", l)
    if m1:
        cstamp = m1.group(1)
    m2 = re.search(u"同钟点份额：今天 [^用]* 用 ([\\d.]+)，昨天同一段用 ([\\d.]+) ⇒ 今天跑到昨天的 (\\d+)%", l)
    if m2:
        today_tot, ysame_tot, share = m2.group(1), m2.group(2), m2.group(3)
    m3 = re.search(u"按同钟点形状外推今天全天：昨天全天 ([\\d.]+) × [\\d.]+ ≈ ([\\d.]+) credits", l)
    if m3:
        floor_y, proj = m3.group(1), m3.group(2)
for num, var in ((u"份额三数", share), (u"外推全天", proj), (u"昨天钱袋", floor_y)):
    if not var:
        die(u"钱袋读数缺【%s】一格" % num)
tight = float(proj) > float(floor_y)

# ---------- 4) 组装 ----------
now = time.strftime("%m-%d %H:%M:%S")
msg = []
msg.append(u"【值守敲门 · {now}】{w} 扇窗停在『等你一句话』上；另有 {s} 扇只是报完成（分开列，别混着读）。"
           u"队列与钱袋附现跑读数（非手打，口径见文末）。".format(
               now=now, w=len(wait_ids), s=len(stmt_ids)))
msg.append(u"")
msg.append(u"一、真的在等裁语的 {w} 条（摘自 _ruling_asks_latest.txt，跑批于 {stamp}，只取带请求形状那一行）：".format(
    w=len(wait_ids), stamp=stamp))
for i in wait_ids:
    silent = lanes[i][0]
    take = asks_pick[i]
    if len(take) > 165:
        take = take[:165] + u"…"
    msg.append(u"  · {i}（静默 {s} 分）：{t}".format(i=i, s=silent, t=take))
if stmt_ids:
    msg.append(u"  （另有 {n} 条落在「号令者可裁」档但末段是交付陈述、没在等人：{i}——"
               u"它们要不要回话由你定，我没把它们算进上面的 {w} 条。）".format(
                   n=len(stmt_ids), i=u"、".join(stmt_ids), w=len(wait_ids)))
msg.append(u"")
msg.append(u"二、落地队列：现尖 {tip}（{age} 分前）；近 {win} 小时内 {landed} 枚已在线上、{gap} 枚确有未落地差，"
           u"逐枚 merge-tree 只读预测都是干净——差的只有你那一笔移动。".format(
               tip=tip, age=tip_age, landed=landed, gap=gap, win=WIN_MIN // 60))
msg.append(u"三、钱袋：{cs} 量到今天已用 {t} credits，昨天同一钟点用 {y} ⇒ 今天只跑到昨天的 {s}%；"
           u"按同形状外推今天全天约 {p} credits，昨天真花掉 {f} 才撞墙 ⇒ {verdict}。".format(
               cs=cstamp, t=today_tot, y=ysame_tot, s=share, p=proj, f=floor_y,
               verdict=(u"钱袋到 23:00 是紧的，要前压交付" if tight else
                        u"照这个形状今天的花费只有昨天一半量级、压力应比昨天小")))
to23 = max(0.0, (time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 23:00:00",
                                           "%Y-%m-%d %H:%M:%S")) - time.time()) / 3600.0)
msg.append(u"  （这不是『保证不撞墙』：昨天的 {f} 只证明钱袋至少那么宽，今天到 23:00 还有 {h} 小时，"
           u"白天若有人补跑份额就会变——所以我把它当排班参考，不当结论。".format(f=floor_y, h=u"%.1f" % to23) + u"）")
msg.append(u"")
msg.append(u"要的动作：每条只需要一句裁语（或者点名『先放着、白天再说』）。车道拿到就走，不用再等我转。")
msg.append(u"读数口径：_ruling_ask_extract_r1.py（{s1}）｜_ready_not_landed_r1.py 360（本次现跑，rc=0）｜"
           u"_burn_curve_r1.py（{s2}）。外推不是预测；撞墙时刻在窗口不足 3 小时时由 credits_burn_r2.py 主动拒答。".format(
               s1=stamp, s2=cstamp))
body = u"\n".join(msg)

raw = io.open(CLOSING, "rb").read()
if len(raw) != 83 or hashlib.sha1(raw).hexdigest() != CLOSING_SHA1:
    die(u"收尾口令字节不吻合：len=%d sha1=%s ⇒ 不投递" % (len(raw), hashlib.sha1(raw).hexdigest()))
tail = raw.decode("utf-8").rstrip(u"\r\n")

full = body + u"\n\n" + tail + u"\n"
if u"竭尽所能的替qoder铺路" not in full or not full.rstrip().endswith(tail):
    die(u"逐字尾行没接上")

if fails:
    sys.stdout.write(u"REFUSE %d 条：\n" % len(fails))
    for x in fails:
        sys.stdout.write(u"   - " + x + u"\n")
    sys.exit(1)

io.open(OUT, "w", encoding="utf-8", newline="\n").write(full)
sys.stdout.write(full)
sys.stdout.write(u"\n[落盘 %s｜%d 字节｜sha1 %s]\n" % (
    os.path.basename(OUT), len(full.encode("utf-8")),
    hashlib.sha1(full.encode("utf-8")).hexdigest()))
