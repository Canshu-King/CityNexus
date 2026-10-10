# -*- coding: utf-8 -*-
"""按 `ledger_insert_after_r2.py:36-110` 的字面判据重放第二道闸（只读），用来核对我的副本有没有跑偏。

09-29 05:03 学到：现行闸口只扫 `\b[0-9a-f]{40}\b`，**短形（12 位）它根本不看**；
而我 `bolt_replica.py` 那一版按短形报了 abort —— 也就是说我对车道报的“第二道闸拒”可能是我副本的错。
这个脚本把现行判据逐字搬过来：同一份 _NON_RETRIEVABLE_PAT、同一段落锚范围、同一个 cat-file 通道。
"""
import glob
import io
import os
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
INBOX = r"D:\moodle\_qoder_ledger_inbox"
REPO = "D:/moodle/CityNexus"

HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
NON_RETRIEVABLE_PAT = re.compile(
    u"sha1\\s*[\\(（]?\\s*(over|of)\\s+bytes"
    u"|文件\\s*sha1|本机\\s*sha1|内容\\s*sha1"
    u"|本地字节重算|字节重算的\\s*sha"
    u"|从未入\\s*git|未入\\s*git|不在对象库"
    u"|非\\s*blob|不是\\s*blob|不可\\s*cat-file|故意不可取回",
    re.I)

# 先 fetch 全部分支（与闸口一致），否则今天的 lane 提交会被误报
subprocess.run(["git", "-C", REPO, "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--quiet"],
               capture_output=True, timeout=900)

files = [f for f in sorted(glob.glob(os.path.join(INBOX, "*.md")))]
res_cache = {}


def resolves(h):
    if h not in res_cache:
        p = subprocess.run(["git", "-C", REPO, "cat-file", "-t", h], capture_output=True, text=True, timeout=120)
        res_cache[h] = p.returncode == 0
    return res_cache[h]


for path in files:
    raw = io.open(path, encoding="utf-8", newline="\n").read()
    lines = raw.splitlines()
    all40 = sorted(set(HEX40.findall(raw)))
    for h in all40:
        resolves(h)
    unres = [h for h in all40 if not resolves(h)]
    verdict = "OK"
    hits = []
    for idx, text in enumerate(lines):
        for h in sorted(set(HEX40.findall(text))):
            if resolves(h):
                continue
            lo = hi = idx
            while lo > 0 and lines[lo - 1].strip():
                lo -= 1
            while hi < len(lines) - 1 and lines[hi + 1].strip():
                hi += 1
            para = "\n".join(lines[lo:hi + 1])
            declared = bool(NON_RETRIEVABLE_PAT.search(text))
            anchored = any(resolves(o) for o in set(HEX40.findall(para)) if o != h)
            hits.append((idx + 1, h, declared, anchored))
            if not (declared and anchored):
                verdict = "ABORT"
    age = (time.time() - os.path.getmtime(path)) / 60.0
    print("%-22s age=%5.1f 分  40位值 %d 枚（不可解析 %d）=> %s"
          % (os.path.basename(path), age, len(all40), len(unres), verdict))
    for ln, h, d, a in hits:
        print("      line %d  %s  declared=%s anchored=%s" % (ln, h[:16] + "…", d, a))
print("at", time.strftime("%H:%M:%S"), "（cat-file 只读，0 次写盘）")
