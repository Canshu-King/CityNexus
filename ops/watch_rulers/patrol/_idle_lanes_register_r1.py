# -*- coding: utf-8 -*-
"""值守 03:5x · 「静默的车道各自在等什么」登记表——只从它们自己的流水尾读，不猜。

为什么要这一枚：自动轮每拍印「静默非闸 N 条」，但 N 条里混着三种完全不同的事：
  ① 说完一句就停、那句是在**请号令者裁**（敲它没用，得有人给话）；
  ② 交完块就停、在等门那一跳（也不用敲）；
  ③ 停在一句和单无关的话上、名下还有没交的单（这一种才是真掉队）。
以前这三格只在名册里挤成同一个数字，号令者要点开一条条看。这里把分类做完，并给出**证据行**（尾句原文），
分类词只用于 grouping，判定仍以原文为准。

形制：
  · 会话全集从 `projects/D--moodle/*.jsonl` 推，不用静态花名表（09-30 的老规矩）。
  · 单号←收件人 用紧配对（同 `_unclaimed_orders_r1.py`），窗口默认 12 小时。
  · 「没交」= 远端没有含该单号的 review 枝 **且** 账本里没有车道块正文提到该单号——沿用那把尺的两路证据；
    这一路只看有没有交付痕迹，不判交付对不对。
  · 只读。0 改产品、0 写账本、0 动任何进程。
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

PROJ = r"C:/Users/仓鼠王/.qoder/projects/D--moodle"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ME = "42d1a6fa"
CMDR = "494abfd7"
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
SILENT_MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
# 静默上限：超过这个小时数的会话是历史遗留（09-18 那种），不是今晚的车道，列出来只会淹掉重点。
MAX_SILENT_H = float(sys.argv[3]) if len(sys.argv) > 3 else 12.0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
now = time.time()

ASK = [u"请裁", u"要你定", u"得你点头", u"二选一", u"该不该", u"要不要", u"请你判", u"等你一句", u"需要裁"]
DELIVERED = [u"已交", u"入账", u"落在收件口", u"块已落", u"过闸", u"PRECHECK=GREEN", u"交付坐标", u"已落地"]
DROP = [u"额度", u"usage limit", u"NetworkAttemptError", u"response_headers"]


def tail_of(path, want=6):
    """读流水尾部，返回（最后一条 assistant 文本, 尾记录角色/形制, 条数）。"""
    fh = io.open(path, "rb")
    size = os.path.getsize(path)
    fh.seek(max(0, size - 700000))
    lines = fh.read().decode("utf-8", "replace").split(chr(10))
    fh.close()
    last_role = last_kind = None
    n = 0
    texts = []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        m = r.get("message") or {}
        role = m.get("role")
        c = m.get("content")
        kinds = [x.get("type") for x in c] if isinstance(c, list) else (["str"] if isinstance(c, str) else [])
        if last_role is None:
            last_role, last_kind = role, ",".join(kinds) or "?"
        if role == "assistant" and isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("type") == "text" and (x.get("text") or "").strip():
                    texts.append(x["text"].strip())
                    break
        if len(texts) >= want:
            break
        n += 1
    return texts, last_role, last_kind


def tight_pairs(text):
    univ = set(os.path.basename(x)[:8] for x in glob.glob(PROJ + "/*.jsonl"))
    res = {}
    for l in text.split(chr(10)):
        ids_all = [x for x in re.findall(r"\b([0-9a-f]{8})\b", l) if x in univ]
        for m in re.finditer(r"ORD-0(\d{3})", l):
            num = "ORD-0" + m.group(1)
            got = []
            for d in re.finditer(r"`([0-9a-f]{8})`\s*[\(（]\s*" + num + r"\s*[\)）]", l):
                if d.group(1) in univ:
                    got.append(d.group(1))
            mm = re.match(r"^### " + num + r"\s+车道\s+([0-9a-f]{40})", l)
            if mm:
                got.append(mm.group(1)[:8])
            if not got and len(ids_all) == 1 and re.search(u"派|→|@|给|收件", l):
                got = ids_all
            if got:
                res.setdefault(num, set()).update(got)
    return res


def open_orders():
    """近 HOURS 小时号令者块里点过名的单号 → 收件人，去掉有交付痕迹的。"""
    blocks = []
    for pat in (os.path.join(INBOX, "_processed", "cmdr_*.inserted_*"), os.path.join(INBOX, "cmdr_*.md")):
        for f in glob.glob(pat):
            if now - max(os.path.getmtime(f), os.path.getctime(f)) <= HOURS * 3600:
                blocks.append(f)
    pairs = {}
    for f in blocks:
        try:
            t = io.open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for num, ids in tight_pairs(t).items():
            pairs.setdefault(num, set()).update(ids)
    blob = ""
    for f in glob.glob(os.path.join(INBOX, "_processed", "*.inserted_*")) + glob.glob(os.path.join(INBOX, "*.md")):
        if os.path.basename(f).startswith("cmdr_"):
            continue
        try:
            blob += io.open(f, encoding="utf-8", errors="replace").read()[-6000:]
        except Exception:
            pass
    blob += io.open(LEDGER, encoding="utf-8", errors="replace").read()[-400000:]
    try:
        r = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote",
                            "https://github.com/Canshu-King/CityNexus.git", "refs/heads/review/*"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        refs = (r.stdout or "").lower()
    except Exception:
        refs = ""
    pending = {}
    for num, ids in pairs.items():
        key = num.lower().replace("-", "")
        if key in refs or num in blob:
            continue
        for i8 in ids:
            pending.setdefault(i8, []).append(num)
    return pending, len(blocks), (u"枝可读（%d 行 review/*）" % len([x for x in refs.splitlines() if x.strip()])) if refs.strip() else u"枝取不到（不当结论）"


pending, nblk, refs_ok = open_orders()
rows = []
older = 0
# 一个会话可能有多份流水（fork 出来的），按 id8 取**最近动过**的那一份，否则同一条车道会被列三遍
latest = {}
for f in glob.glob(PROJ + "/*.jsonl"):
    id8 = os.path.basename(f)[:8]
    if id8 in (ME, CMDR):
        continue
    if id8 not in latest or os.path.getmtime(f) > os.path.getmtime(latest[id8]):
        latest[id8] = f
for id8, f in sorted(latest.items()):
    silent = (now - os.path.getmtime(f)) / 60.0
    if silent > MAX_SILENT_H * 60.0:
        older += 1
        continue
    if silent < SILENT_MIN:
        continue
    texts, role, kind = tail_of(f)
    last = texts[0] if texts else ""
    verdict = u"说不清（尾句里没有这三族的词）"
    if kind and "tool_use" in (kind or ""):
        verdict = u"停在一半（尾是工具块，没等到结果）"
    else:
        if any(w in last for w in ASK):
            verdict = u"在等裁语"
        elif any(w in last for w in DELIVERED):
            verdict = u"交完了在等门/等验收"
        elif any(w in last for w in DROP):
            verdict = u"像掉了（额度/链路字样）"
        elif id8 in pending:
            verdict = u"名下还有没交的单，却停在无关一句"
    rows.append((silent, id8, role, kind, verdict, u"、".join(pending.get(id8, [])), last[:150]))
rows.sort(reverse=True)
print("静默 %g 分—%g 小时的会话 %d 条（另有 %d 条静默超过上限＝历史遗留，不列）；"
      u"近 %g 小时号令者块 %d 枚里点过名、且没有交付痕迹的单，挂在收件人身上" % (
          SILENT_MIN, MAX_SILENT_H, len(rows), older, HOURS, nblk))
for silent, id8, role, kind, verdict, nums, last in rows:
    print("\n%-9s 静默 %6.1f 分｜尾=%s/%s｜%s%s" % (id8, silent, role, kind, verdict,
                                                  u"｜没交的单：" + nums if nums else u"｜没查到未交单"))
    print("          尾句：%s" % last.replace(chr(10), " ")[:150])
print("\n边界：分类词只用来分组，判定请以尾句原文为准；『没交』= 远端无该单号的 review 枝 且 没有车道块正文提到，"
      u"不判交付质量。ls-remote 这一路本次判语：%s。" % refs_ok)
