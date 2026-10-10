# -*- coding: utf-8 -*-
"""值守 03:1x · 「车道到底有没有在读它那张单」——按用户的话办：检查工人要在**他们的任务流水**里查。

为什么再建一枚：`_unclaimed_orders_r1.py` 现在能认出被点名的收件会话，但它那一格「收件会话已动」
只证明那条会话在派单块之后动过流水。全队 16 条在写的时候，这一路几乎必然为真 ⇒ 它只能证明「没弃单」，
证明不了「在看这张单」。这一枚加的是可归因的那一格：拿收件人自己的 jsonl 尾部窗口找该单号出现的最后时刻。

形制：
  ① 单号→收件人 只认紧配对（同 `_unclaimed_orders_r1.py`：`id`（ORD-N）半角全角都收 / 单头带 40 位 uuid /
     该行只有一枚 id 且句子含 派·→·@·给·收件）。
  ② 每条流水只读**尾部 WIN_MB**，窗口大小随读数一起印——「尾部窗口里没有」不等于「整条流水里没有」。
  ③ 判定分四档：自己写过这张单（该单号出现在它自己写的句子里、且在派单之后）／只在收到的正文里出现（它读到过、没写过）／窗口内没提到／取不到流水。

只读。身份只认 `projects/D--moodle/<uuid>.jsonl` 的文件名前 8 位。0 改产品、0 写账本、0 动任何进程。
"""
import glob
import io
import json
import os
import re
import sys
import time

INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROJ = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
WIN_MB = int(os.environ.get("WIN_MB", "4"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
now = time.time()


def cmdr_blocks(hours):
    out = []
    for pat in ("cmdr_*.md", "cmdr_*.md.inserted_*"):
        for f in glob.glob(os.path.join(INBOX, "_processed" if "inserted" in pat else "", pat)):
            if now - max(os.path.getmtime(f), os.path.getctime(f)) <= hours * 3600:
                out.append(f)
    return sorted(set(out), key=os.path.getmtime)


def tight_pairs(text):
    ids_universe = set(os.path.basename(x)[:8] for x in glob.glob(PROJ + "/*.jsonl"))
    res = {}
    for l in text.split(chr(10)):
        ids_all = [x for x in re.findall(r"\b([0-9a-f]{8})\b", l) if x in ids_universe]
        for m in re.finditer(r"ORD-0(\d{3})", l):
            num = "ORD-0" + m.group(1)
            got = []
            for d in re.finditer(r"`([0-9a-f]{8})`\s*[\(（]\s*" + num + r"\s*[\)）]", l):
                if d.group(1) in ids_universe:
                    got.append(d.group(1))
            mm = re.match(r"^### (ORD-0\d{3})\s+车道\s+([0-9a-f]{40})", l)
            if mm and mm.group(1) == num:
                got.append(mm.group(2)[:8])
            if not got and len(ids_all) == 1 and re.search(u"派|→|@|给|收件", l):
                got = ids_all
            if got:
                res.setdefault(num, set()).update(got)
    return res, ids_universe


def last_mentions(id8, num, win_bytes):
    """在该会话流水的尾部窗口里找该单号：返回（出现次数, 最后一次出现的记录时间戳, 窗口字节数, 文件末记录时间）。"""
    hits = glob.glob(os.path.join(PROJ, id8 + "*.jsonl"))
    if not hits:
        return None
    p = max(hits, key=os.path.getsize)
    size = os.path.getsize(p)
    fh = io.open(p, "rb")
    fh.seek(max(0, size - win_bytes))
    blob = fh.read().decode("utf-8", "replace")
    fh.close()
    n = blob.count(num)
    own_n = 0            # 车道自己写下的句子里出现该单号的次数（assistant 的 text 块）
    own_last = None      # 那一句的记录时间
    last_ts = None
    last_text = ""
    for line in blob.split(chr(10)):
        if num not in line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        m = r.get("message") or {}
        c = m.get("content")
        texts = []
        if isinstance(c, str):
            texts = [c]
        elif isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "text":
                    texts.append(x.get("text") or "")
        hit_here = any(num in t for t in texts)
        if hit_here:
            last_text = next(t for t in texts if num in t)[:70]
            last_ts = r.get("timestamp") or r.get("created_at")
            if m.get("role") == "assistant":
                own_n += 1
                own_last = last_ts
    return n, last_ts, min(size, win_bytes), os.path.getmtime(p), last_text, own_n, own_last


blocks = cmdr_blocks(HOURS)
pairs, univ = ({}, set())
for f in blocks:
    try:
        t = io.open(f, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    pp, univ = tight_pairs(t)
    wfm = max(os.path.getmtime(f), os.path.getctime(f))
    for num, ids in pp.items():
        for i8 in ids:
            pairs.setdefault(num, {}).setdefault(i8, wfm)
print("窗口 %g 小时｜号令者块 %d 枚｜尾部读数窗口 %d MB/条｜紧配对认出的「单号←收件会话」%d 对" % (
    HOURS, len(blocks), WIN_MB, sum(len(v) for v in pairs.values())))
tally = {"自己写过这张单": 0, "只在收到的正文里出现": 0, "窗口内没提到": 0, "取不到流水": 0}
rows = []
for num in sorted(pairs):
    for i8, t0 in sorted(pairs[num].items()):
        r = last_mentions(i8, num, WIN_MB * 1024 * 1024)
        if not r:
            verdict = "取不到流水"
            detail = "无 `<id8>*.jsonl`"
        else:
            n, last_ts, wb, mtime, snippet, own_n, own_last = r
            def to_ep(ts):
                if ts is None:
                    return None
                if isinstance(ts, (int, float)):
                    v = float(ts)
                    return v / 1000.0 if v > 1e11 else v
                if isinstance(ts, str) and ts.isdigit() and len(ts) >= 12:
                    v = float(ts)
                    return v / 1000.0 if v > 1e11 else v
                try:
                    return time.mktime(time.strptime(str(ts)[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
                except Exception:
                    return None
            oe = to_ep(own_last)
            re_ = to_ep(last_ts)
            if own_n and oe is not None and oe >= t0:
                verdict = "自己写过这张单"
                detail = "自述 %d 次｜最后一次 %s" % (own_n, time.strftime("%H:%M:%S", time.localtime(oe)))
            elif n:
                verdict = "只在收到的正文里出现"
                detail = "共 %d 次（自述 0 次）｜末次 %s" % (
                    n, time.strftime("%H:%M:%S", time.localtime(re_)) if re_ else "时间取不到")
            else:
                verdict = "窗口内没提到"
                detail = "0 次｜该条流水末记录 %s" % time.strftime("%H:%M:%S", time.localtime(mtime))
        tally[verdict] += 1
        rows.append((num, i8, verdict, detail))
        print("  %-9s ← `%s`  %-30s %s" % (num, i8, verdict, detail))
print("合计 %d 对：%s" % (len(rows), "｜".join("%s %d" % (k, v) for k, v in tally.items() if v)))
print("边界：「窗口内没提到」只说明最后 %d MB 里没有该单号，整条流水可能有（文件更大时靠这份窗口判定）；"
      "「自己写过」也只到字面提及为止，不判它做对了没有；「只在收到的正文里出现」= 这个单号只在它**读到**的东西里出现过，"
      "不等于没干活（读完直接改码不打单号是常见形制），它只说明这单号还没进它自己写下的句子里。" % WIN_MB)
