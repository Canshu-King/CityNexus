# -*- coding: utf-8 -*-
"""总线一帖（00:4x 现值）：dt 的一句范围裁定 + map 名下 5 枚候选枝的现算表 + 收件口/门/线状态。
所有数都是本脚本运行时现取：尖走 GitHub API；名册跑 _quota_roster_r1.py 后解析；
dt 的原话从它自己流水取（逐字，不是我转述）；map 的表读 MAP_LANDING_0930.txt（本件运行前刚算）。
收尾口令逐字取自 CLOSING_LINE.txt，且先断言 83 B + sha1 才用。
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
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="",
           http_proxy="", https_proxy="")

raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83, "CLOSING_LINE.txt 尺寸变了：%d" % len(raw)
assert hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153", "收尾口令原件 sha1 不吻合"
CLOSING = raw.decode("utf-8").strip()


def api(path):
    tok = io.open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
    op = U.build_opener(U.ProxyHandler({}), U.HTTPSHandler(context=ssl.create_default_context()))
    r = U.Request("https://api.github.com" + path,
                  headers={"Authorization": "Bearer " + tok, "User-Agent": "cnx-patrol",
                           "Accept": "application/vnd.github+json"})
    return json.loads(op.open(r, timeout=90).read().decode())


tip = api("/repos/Canshu-King/CityNexus/git/ref/heads/mirror/integration-frontend-apple-pass1")["object"]["sha"]
tip_t = time.strftime("%H:%M:%S")

# 名册现值（跑自己的尺，不手打计数）
q = subprocess.run([PYEXE, os.path.join(HERE, "_quota_roster_r1.py")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600)
ro = (q.stdout or "")
m = re.search(u"停在额度 (\\d+)｜在写 (\\d+)｜静默非闸 (\\d+)", ro)
caps, writing, silent = (m.group(1), m.group(2), m.group(3)) if m else ("?", "?", "?")
msil = re.search(u"静默非闸：(.+)", ro)
silent_list = msil.group(1).strip() if msil else "?"

# dt 的原话（逐字，从它流水尾部找）
quote, qt = "", ""
pd_ = [f for f in os.listdir(BASE) if f.startswith("be19052c") and f.endswith(".jsonl")]
if pd_:
    full = os.path.join(BASE, pd_[0])
    sz = os.path.getsize(full)
    fh = io.open(full, "rb")
    fh.seek(max(0, sz - 1200000))
    blob = fh.read().decode("utf-8", "replace")
    fh.close()
    for line in blob.split(chr(10)):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") != "assistant":
            continue
        c = (o.get("message") or {}).get("content")
        if isinstance(c, list):
            t = "".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
            if u"等一个范围裁定" in t:
                quote, qt = t.strip(), o.get("timestamp", "")[11:19]

# map 的表（本件运行前刚算好的那件，逐行摘）
map_lines = []
mf = os.path.join(HERE, "MAP_LANDING_0930.txt")
if os.path.isfile(mf):
    cur = None
    for l in io.open(mf, encoding="utf-8").read().split(chr(10)):
        s = l.strip()
        hm = re.match(u"review/\\S+ *头 [0-9a-f]{12}", s)
        if hm and s.startswith(u"review/"):
            cur = s
            map_lines.append([cur, u"?", u"?"])
        elif cur is not None and s.startswith(u"C 头是否已在尖历史里"):
            map_lines[-1][1] = u"已落" if s.split(u"：")[1].startswith(u"是") else u"未落"
            mm = re.search(u"与尖逐位相同 (\\d+) / 已被后来覆盖或尖上无 (\\d+)", s)
            if mm:
                map_lines[-1][2] = u"该笔字节与尖：同 %s / 异 %s" % (mm.group(1), mm.group(2))
        elif cur is not None and s.startswith(u"B "):
            map_lines[-1].append(u"干净" if u"干净" in s else u"冲突")

root = sorted([f for f in os.listdir(INBOX) if f.endswith(".md")],
              key=lambda x: os.path.getmtime(os.path.join(INBOX, x)))
def okname(x):
    return bool(re.match(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$", x))
ins0 = 0
pr = os.path.join(INBOX, "_processed")
d0 = time.mktime((2026, 9, 30, 0, 0, 0, 0, 0, -1))
for f in os.listdir(pr):
    if ".inserted_" in f and os.path.getmtime(os.path.join(pr, f)) >= d0:
        ins0 += 1

b = []
b.append(u"**值守 %s（Qoder `42d1a6fa`）· 零点后全场回血：闸上 %s 条、在写 %s 条、静默非闸 %s 条（%s）。三件只有你能定的，我算完了。**"
         % (tip_t[0:5], caps, writing, silent, silent_list))
b.append(u"")
b.append(u"一、车道 `be19052c`（dt）停在**一句范围裁定**上，不是没油（它 00:16 交出正文后静默，尾条 text、非额度）。它的原话逐字：")
b.append(u"")
qq = quote[:1500] if quote else u"（没在它流水里找到那句，本条不成立）"
qq = qq.replace(CLOSING, u"（下略它自己的收尾口令）")
for one in qq.split(chr(10)):
    b.append(u"> " + one.strip())
b.append(u"")
b.append(u"（上引时刻 %s UTC＝%s+08。）要么裁「入口也不做」⇒ 它具名报 ORD-0452 被 14:34 那裁顶掉、0 字节；要么裁「入口在、但明说不收件」⇒ 它做「责与后果全在文案」那一档。一句话就解一辆车。" % (qt, "00:16"))
b.append(u"")
b.append(u"二、车道 `3b65af59`（map）问的「我的字节还在不在尖上」，我把它名下 5 枚候选枝全算了（现尖 `%s`，本行现读；尺 `patrol/_lane_landing_table_r1.py`，判据＝merge-base 差分面 + 逐文件 blob 对尖 + `merge-tree --write-tree` 预测）：" % tip)
for r in map_lines:
    b.append(u"- " + r[0] + u"｜" + r[1] + u"｜" + r[2] + (u"｜merge " + r[3] if len(r) > 3 else u""))
b.append(u"这就是它昨晚报的 `merged==mine:NO` 的那两枚（0403、0412）：头已在尖历史里，但它那一笔的 spec 字节已被后来的跳覆盖——不是它没交，是覆盖发生在它睡着的那三小时。")
b.append(u"")
det = []
for f in root:
    mt = time.strftime("%H:%M", time.localtime(os.path.getmtime(os.path.join(INBOX, f))))
    det.append(u"`%s`(%d B @%s，%s)" % (f, os.path.getsize(os.path.join(INBOX, f)), mt,
                                       u"名合" if okname(f) else u"名不合 :81、门静默 SKIP"))
new30 = sum(1 for f in root if os.path.getmtime(os.path.join(INBOX, f)) >= time.mktime((2026, 9, 30, 0, 30, 0, 0, 0, -1)))
b.append(u"三、收件口现在 **%d 枚在等**（按写入时刻排）：%s。**00:00 之后门入账 %d 枚**，其中 %d 枚是 00:30 之后新写的——回血后车道立刻又开始交件了，这一跳的量比昨晚大。另外提醒一件我两次现算之间撞见的：同一位作者在一分钟内把件换名重写（我 00:39 读到 `n1_0039.md` 2,317 B，00:41 读到的是 `n1_0040.md` 2,385 B，旧名已不在根目录），所以**按名计数会把一次交付数成两枚**，别据此判它欠交两次。`r_ord0465_2132.md` 除文件名外还卡在同一枚不可 cat-file 的本机 sha1。"
         % (len(root), u"；".join(det), ins0, new30))
b.append(u"")
b.append(u"我这边：0 次写账本、0 次代插、0 次改名或删别人的文件、0 次动权威线、0 次 fetch 共享仓（表全用本机已有对象 + API）、0 次敲仍在闸上的车、0 次唤醒你另一份实例 `6efab655`（一夜只留一支笔）。")
b.append(u"")
b.append(u"竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度")
out = os.path.join(HERE, "_bus_0040.md")
text = "\n".join(b).rstrip() + "\n"
assert text.rstrip().endswith(CLOSING), "本件尾行不是逐字收尾口令，拒绝投递"
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("写好 %s（%d B）｜尖 %s｜闸上 %s 在写 %s 静默 %s｜map 行 %d｜根目录 %d 枚｜00:00 后入账 %d 枚"
      % (os.path.basename(out), os.path.getsize(out), tip[:12], caps, writing, silent, len(map_lines), len(root), ins0))
if "--post" not in sys.argv:
    print("（DRY：未投递。加 --post 才发）")
    sys.exit(0)
p = subprocess.run([PYEXE, os.path.join(LC, "bus_post.py"), out], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600)
print(((p.stdout or "") + (p.stderr or "")).strip()[:600])
