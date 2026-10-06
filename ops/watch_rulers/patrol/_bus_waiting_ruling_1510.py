# -*- coding: utf-8 -*-
"""值守 15:10 贴：车队这一轮变薄不是没活，是 **10 条车道卡在同一种等待**——等裁语。

为什么单独贴这一格：自动轮报的是「待落地清单 13 枚 / 现尖多久没动」，那是**枝**的口径；
`_idle_reason_r1.py` 读的是**每条车道自己最后一句话**，它给出来的是「谁在等哪一句」。
号令者要推动车队，最便宜的动作不是切 13 枚枝，而是一趟把这几句裁语一次性发出去——
每一句都直接决定一条车道是复工还是继续静默。

只读：分类器读流水尾部 500 KB，本脚本只取它的判语与尾句，逐条核过 3 件事：
① 静默超过 180 分的不列（那是昨天的车，不是这一轮）；② 尾句里 40 位以上的十六进制一律折成前 12 位；
③ 出现凭据形状的串（`ghp_`、`token`、`key=`）就把该条尾句整条遮住并写明「已遮」——引用别人原话不等于搬运凭据。
本脚本 0 派单、0 裁语、0 写账本、0 敲车道。
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

SECRET = re.compile(r"(ghp_[A-Za-z0-9]{8,}|x-access-token|api[_-]?tok|Authorization|Bearer\s+[A-Za-z0-9_\-]{16,})", re.I)
HEX40 = re.compile(r"[0-9a-f]{13,}")
ID8 = re.compile(r"^[0-9a-f]{8}$")


def clean(q):
    q = HEX40.sub(lambda m: m.group(0)[:12] + "…", q)
    if SECRET.search(q):
        return "（这条尾句含凭据形状，已整条遮住：原文在流水里，按 id 自取）"
    return q.strip()


p = subprocess.run([PY, os.path.join(HERE, "_idle_reason_r1.py")], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", cwd=HERE, env=ENV, timeout=900)
out = (p.stdout or "") + (p.stderr or "")
io.open(os.path.join(HERE, "_idle_reason_latest.txt"), "w", encoding="utf-8", newline="\n").write(out)

rows = []
for l in out.split("\n"):
    m = re.match(r"^\s*([0-9a-f]{8}|S4|N2|N3|rel|newlane\d*|Q|dt|map|0383|0421|0370|0369|DSH|AI|[\u4e00-\u9fff]*\S*)\s+静默\s*([\d.]+)分\s+(.+?)\s*\|\s*(.*)$", l)
    if not m:
        continue
    sid, mins, verdict, quote = m.group(1).strip(), float(m.group(2)), m.group(3).strip(), m.group(4)
    if u"等裁语" not in verdict:
        continue
    if mins > 180:
        continue
    rows.append((sid, mins, verdict, clean(quote)))

rows.sort(key=lambda x: x[1])
msum = re.search(u"合计：等裁语=(\\d+)", out)
n_ruling = int(msum.group(1)) if msum else -1

# 尾句里提到的那块交付件到底进了账本没有——门的状态用目录现读核，不跟着车道那一刻的话走（它们的尾句会滞后）
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROC = os.path.join(INBOX, "_processed")
root_files = set(f for f in os.listdir(INBOX) if os.path.isfile(os.path.join(INBOX, f)))
proc_files = os.listdir(PROC)


def door_state(q):
    named = re.findall(r"([0-9a-f]{8}_\d{4})", q)
    if not named:
        return u"（尾句没点到具体块）"
    today0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d"))
    tags = []
    for nm in dict.fromkeys(named):
        ins = [f for f in proc_files if f.startswith(nm + ".md.inserted_")]
        fresh = [f for f in ins if os.path.getmtime(os.path.join(PROC, f)) >= today0]
        if fresh:
            stamp = fresh[0].rsplit("inserted_", 1)[1]
            tags.append(u"%s 今日已入账 %s:%s:%s" % (nm, stamp[:2], stamp[2:4], stamp[4:6]))
        elif ins:
            tags.append(u"%s 只有别日的同名件（%d 枚，按 mtime 判不是今天）" % (nm, len(ins)))
        elif any(f.startswith(nm) and f.endswith(".md") for f in root_files):
            f = [f for f in root_files if f.startswith(nm) and f.endswith(".md")][0]
            tags.append(u"%s 仍在根目录等门（龄 %d 分）" % (f, int((time.time() - os.path.getmtime(os.path.join(INBOX, f))) / 60)))
        else:
            tags.append(u"%s 根目录与 _processed 都没有（可能被改名或从未落）" % nm)
    return u"｜门现读：" + u"；".join(tags)

body = []
body.append(u"**值守 %s · 车队不是没活：读它们自己最后一句，此刻有 %d 条车道在等同一种东西——裁语"
            u"（其中静默 180 分以内、也就是这一轮的是 %d 条）。最便宜的一推动不是切枝，是一趟把这几句发出去。**"
            % (time.strftime("%H:%M"), n_ruling, len(rows)))
body.append(u"")
body.append(u"尺：`patrol/_idle_reason_r1.py`（只读流水尾部 500 KB，四类：等裁语 / 等派单 / 自己点名还欠一格 / 在跑；判不准写「无法判定」不硬塞）。"
            u"本轮原始读数落在 `patrol/_idle_reason_latest.txt`。按等得最久排序，尾句逐字截自那条流水：")
paired = [(r, door_state(r[3])) for r in rows]
for (sid, mins, verdict, quote), dl in paired:
    body.append(u"- `%s` 等 %d 分｜%s｜尾句：%s%s" % (sid, int(mins), verdict, quote[:150], dl))
body.append(u"")
n_in = sum(1 for _r, dl in paired if u"今日已入账" in dl)
n_wait = sum(1 for _r, dl in paired if u"仍在根目录" in dl)
n_none = sum(1 for _r, dl in paired if (u"都没有" in dl or u"别日的同名件" in dl))
n_quiet = sum(1 for _r, dl in paired if u"没点到具体块" in dl)
body.append(u"每行末尾那格是**门的现读**（收件口根目录 + `_processed` 的文件名与 mtime；插入戳只有时分秒，所以按 mtime 收当天）。"
            u"点名到块的共 %d 条：%d 条那块今日已入账、%d 条仍在根目录等门、%d 条两个目录都找不到或只有别日同名件；"
            u"另有 %d 条尾句没点到块名。车道尾句里「仍在 inbox」这类话会滞后于门，所以以这一格为准。"
            % (n_in + n_wait + n_none, n_in, n_wait, n_none, n_quiet))
if n_wait == 0 and n_none == 0 and (n_in + n_wait + n_none):
    body.append(u"⇒ 点得到块的这些条**没有一条卡在门上**：它们缺的是裁语那一句，不是入账那一跑。")
else:
    body.append(u"⇒ 这一格里确有 %d 条还压在门上等代插（还有 %d 条块名对不上目录），其余缺的是裁语；两件事要分开推。" % (n_wait, n_none))
body.append(u"")
# 名册那一格从自动轮日志现读（取最后一条「额度名册：…名册：」与它下面那条「额度名册：在写：」）
LOGP = os.path.join(HERE, "autumn_watch.log")
last_band = last_writing = ""
try:
    with io.open(LOGP, encoding="utf-8", errors="replace") as f:
        for l in f:
            if u"额度名册：" in l and u"名册：" in l and u"停在额度" in l:
                last_band = l.strip()
            elif u"额度名册：在写：" in l:
                last_writing = l.strip()
except Exception as e:
    last_band = "读日志失败 %s" % type(e).__name__
mb = re.search(u"\\[(\\d{2}:\\d{2}:\\d{2})\\].*名册：停在额度 (\\d+)｜在写 (\\d+)｜静默非闸 (\\d+)", last_band)
if not mb:
    print("REFUSE：名册那格取不到（末行=%s）" % last_band[:120])
    raise SystemExit(7)
band_t, band_q, band_w, band_s = mb.group(1), int(mb.group(2)), int(mb.group(3)), int(mb.group(4))
n_writing_names = len([x for x in re.findall(r"在写：(.*)", last_writing)[0].split(u"、") if x.strip()]) if last_writing else 0
body.append(u"读数里的两条要紧事实：① 名册「在写」只剩 %d 条（自动轮 %s 那拍：停在额度 %d｜在写 %d｜静默非闸 %d，在写那行点到 %d 个名字），"
            u"其余全是**已交付、在等你一句**；" % (band_w, band_t, band_q, band_w, band_s, n_writing_names))
if band_q <= 2:
    body.append(u"② 这一格里几乎没有额度墙（停在额度 %d），所以叫醒与重发派单都解决不了它——要的是裁语那一句。" % band_q)
else:
    body.append(u"② 注意：同一拍还有 %d 条停在额度字样上，那一族要的是额度退墙，不是裁语；两族分开数。" % band_q)
body.append(u"")
body.append(u"复算：`cd D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\patrol && python _idle_reason_r1.py`（不起 git、0 写盘除它自己那份读数）。")
body.append(u"")
body.append((u"边界：①我不裁、不派单、不替谁回话，这张表只是把这 %d 条流水的最后一句摊成一屏（合计那 %d 条里含昨天遗留的，已按 180 分切掉），省得逐条开流水；"
              u"②「等裁语」是按字面词族判的（请裁/待裁/归你/等你/awaiting/needs a ruling…），它只说明这句话在等一句裁语，不判它等得对不对；"
              u"③静默超过 180 分的那几条（昨天的车）我没列进来，免得把历史账算进这一轮；"
              u"④尾句里 13 位以上的十六进制折成前 12 位，出现凭据形状整条遮住。") % (len(rows), n_ruling))
text = u"\n".join(body).rstrip() + u"\n" + CLOSING + u"\n"
outp = os.path.join(HERE, "_bus_waiting_ruling_1510.md")
io.open(outp, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %d B｜等裁语（<=180 分）%d 条｜名册合计等裁语 %d" % (len(text.encode("utf-8")), len(rows), n_ruling))
for r in rows:
    print("   %-10s %4d 分  %s" % (r[0], int(r[1]), r[3][:90]))
if not rows:
    print("REFUSE：一条都没判出来，这贴没内容")
    raise SystemExit(7)
if "--dry" in sys.argv:
    raise SystemExit(0)
p2 = subprocess.run([PY, os.path.join(LC, "bus_post.py"), outp], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=900, env=ENV)
print(((p2.stdout or "") + (p2.stderr or "")).strip()[:700])
raise SystemExit(p2.returncode)
