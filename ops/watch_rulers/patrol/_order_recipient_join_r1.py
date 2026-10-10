# -*- coding: utf-8 -*-
"""值守 02:36 · 把「无人接」那 12 张拆开看：到底是无主单，还是已点名只是还没交。

为什么要这一把：`_unclaimed_orders_r1.py` 的判据是「远端没有该单的枝 且 账本没有该单的块」，
它量的是**还没交付**，不是**没派给人**。09-30 已经栽过一次：号令者一行十四张的批量写法被漏读，
把已点名的单报成无主，我若照那个名单去敲车道就是错敲（记忆条目 relay-addressing / 批量派单漏读）。
所以这里不新判据，只把同一批单号的**派单原文行**摘出来，认里面写明的收件会话，再逐条读那条会话的流水尾。

只读。身份只认反引号里的 8 位会话 id 与 `projects/D--moodle/<uuid>.jsonl` 的文件名前缀，不认标题。
"""
import glob
import io
import os
import re
import sys
import time

LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
WANT = sys.argv[2:] if len(sys.argv) > 2 else []

now = time.time()
blocks = []
for f in glob.glob(os.path.join(INBOX, "_processed", "cmdr_*.md.inserted_*")):
    if now - os.path.getmtime(f) <= HOURS * 3600:
        m = re.search(r"cmdr_(\d{4})\.md\.inserted_(\d{6})$", os.path.basename(f))
        blocks.append((m.group(2), os.path.basename(f), f))
blocks.sort()

ORD = re.compile(r"ORD-(0\d{2,3})")
ID = re.compile(r"`([0-9a-f]{8})`")


def lane_tail(id8):
    hits = glob.glob(os.path.join(BASE, id8 + "*.jsonl"))
    if not hits:
        return None
    p = max(hits, key=os.path.getsize)
    n = os.path.getsize(p)
    fh = io.open(p, "rb")
    fh.seek(max(0, n - 400000))
    tail = fh.read().decode("utf-8", "replace").splitlines()
    role = kind = None
    cnt = 0
    for line in reversed(tail):
        cnt += 1
        if '"role":"assistant"' in line or '"role":"user"' in line:
            role = "assistant" if '"role":"assistant"' in line else "user"
            kind = "tool_use" if '"type":"tool_use"' in line else (
                "tool_result" if '"type":"tool_result"' in line else ("text" if '"type":"text"' in line else "?"))
            break
    mt = max((os.path.getmtime(h) for h in hits))
    return os.path.basename(hits[0])[:36], role, kind, (now - mt) / 60.0, len(tail)


rows = {}
for ins, nm, path in blocks:
    ls = io.open(path, encoding="utf-8", errors="replace", newline="").read().splitlines()
    for i, l in enumerate(ls):
        if "ORD-0" not in l:
            continue
        # 只认「紧配对」：一行里既有多个单号又有多个 id 时，宽配对会把整行名单挂到每张单上
        # （02:37 实测错过一次：叫醒名单那行让 12 张单每都挂上 16 条收件）。三种紧配对形制：
        #   A `id`(ORD-N)   B ORD-N …… 派/→/收 `id`（该行只有 1 枚 id 才用）   C ### ORD-N 车道 <40 位>
        ids_all = ID.findall(l)
        ords_all = ORD.findall(l)
        for m in ORD.finditer(l):
            oid = "ORD-" + m.group(1)
            if WANT and oid not in WANT:
                continue
            ids = []
            for d in re.finditer(u"`([0-9a-f]{8})`\s*[\(（]\s*" + oid + u"\s*[\)）]", l):
                ids.append(d.group(1))
            for d in re.finditer(u"^### " + oid + u"\s+车道\s+([0-9a-f]{40})", l, re.M):
                ids.append(d.group(1)[:8])
            if not ids and len(ids_all) == 1:
                if re.search(u"派|→|@|给|收件", l):
                    ids = ids_all
            ids = sorted(set(ids))
            cur = rows.setdefault(oid, {"ids": set(), "src": []})
            cur["ids"].update(ids)
            if len(cur["src"]) < 2:
                cur["src"].append((nm, i + 1, int(ins[:2]) * 60 + int(ins[2:4]), l[:110]))

print("窗口：%s 小时内的号令者块 %d 枚；下面只列 %s 的单号" % (
    ("%g" % HOURS), len(blocks), "全列" if not WANT else " ".join(WANT)))
for oid in sorted(rows):
    r = rows[oid]
    ids = sorted(r["ids"])
    print("\n%s  点名收件：%s" % (oid, "、".join("`%s`" % x for x in ids) if ids else "（这一行里没有 8 位会话 id）"))
    for nm, ln, _, txt in r["src"]:
        print("     原文 %s 第 %d 行：%s" % (nm, ln, txt))
    for i8 in ids:
        t = lane_tail(i8)
        if not t:
            print("     尾：`%s` 无流水文件 ⇒ 不可寻址" % i8)
        else:
            fn, role, kind, silent, nrec = t
            print("     尾：`%s`(%s…) recs+%d role=%s kinds=%s 静默 %.1f 分" % (i8, fn[:8], nrec, role, kind, silent))
if not rows:
    print("读数不全：窗口内没扫到任何 ORD 行")
