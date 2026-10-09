# -*- coding: utf-8 -*-
"""账本「同一块头入过两次」扫描（只读）。

为什么要单开：门自己的 `dedupe()` 只对**当下共存**的文件分组（`sorted(group)[-1]`），
一份块插完就搬进 `_processed` 了，车道若拿**逐字相同的块头**（连 `@HH:MM+08` 都没变）再投一次，
门看不见前一份，于是账本里出现两块同名同戳、正文不同的块——读的人无从判哪份作数。
2026-09-29 实测到两对，都出自车道 `8ac89982`（账本行 17083/17234、20646/20867）。

判据分两层，都不靠猜：
  层一：账本里 `^### ` 行逐字相同的组（含正文前 40 行是否也相同，用来分辨「纯重复」与「同头不同文」）。
  层二：`_processed` 里同一枚文件被插过 >1 次的族，比两份的**首行**是否逐字相同——
        首行不同＝同名不同块（正常换日/换用途），首行相同＝真重复投递。
噪声遮除：块内小节头（如 `### ④ 现场`）字数很短，不是投递块；本件只报**长度 >= 30** 的同头组，
          并把被遮掉的短头组数一并打印，不当「没有问题」。
"""
import collections
import hashlib
import io
import os
import re
import sys
import time

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
PROCESSED = r"D:\moodle\_qoder_ledger_inbox\_processed"
MIN_TITLE_LEN = 30


def scan_ledger():
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split(chr(10))
    heads = [(i + 1, l.rstrip()) for i, l in enumerate(lines) if l.startswith("### ")]
    by = collections.defaultdict(list)
    for ln, h in heads:
        by[h].append(ln)
    dups = {h: v for h, v in by.items() if len(v) > 1}
    short = {h: v for h, v in dups.items() if len(h) - 4 < MIN_TITLE_LEN}
    real = {h: v for h, v in dups.items() if len(h) - 4 >= MIN_TITLE_LEN}
    print("账本 `### ` 头共 %d 枚；逐字同头的组 %d 个" % (len(heads), len(dups)))
    print("  其中短小节头（%d 个，本件不判为投递重复，只计数不隐藏）：%s"
          % (len(short), ", ".join(sorted(k[:14] + "…" for k in list(short)[:6]))))
    print("  投递块级的同头重复：%d 个" % len(real))
    for h, v in sorted(real.items(), key=lambda kv: -len(kv[1])):
        bodies = []
        for n in v:
            i = n - 1
            seg = []
            while i < len(lines) and len(seg) < 40:
                if len(seg) > 0 and lines[i].startswith("### "):
                    break
                seg.append(lines[i])
                i += 1
            bodies.append(hashlib.sha1(chr(10).join(seg).encode("utf-8")).hexdigest()[:12])
        same_body = len(set(bodies)) == 1
        print("     x%d 行 %s｜正文sha1 %s｜%s" % (len(v), v, bodies, "完全相同（纯重复）" if same_body else "不同（同头两文，读的人无法判哪份作数）"))
        print("        " + h[:110])
    return real


def scan_processed():
    g = collections.defaultdict(list)
    for f in os.listdir(PROCESSED):
        m = re.match(r"^(.*)\.md\.inserted_(\d+)$", f)
        if m:
            g[m.group(1)].append((m.group(2), f))
    multi = {k: v for k, v in g.items() if len(v) > 1}
    true_dup, name_reuse = [], []
    for k, v in multi.items():
        firsts = []
        for st, f in sorted(v):
            try:
                t = io.open(os.path.join(PROCESSED, f), encoding="utf-8", errors="replace").read()
                firsts.append(t.splitlines()[0].strip() if t.strip() else "")
            except Exception:
                firsts.append("?")
        (true_dup if len(set(firsts)) == 1 else name_reuse).append((k, v, firsts))
    print()
    print("`_processed` 同名被插 >1 次的族：%d 个（共 %d 族）" % (len(multi), len(g)))
    print("  首行逐字相同＝真重复投递：%d 个" % len(true_dup))
    for k, v, firsts in true_dup:
        print("     %-18s x%d 插于 %s｜%s" % (k, len(v), ", ".join(x[0] for x in sorted(v)), firsts[0][:80]))
    print("  首行不同＝同名不同块（正常改名复用）：%d 个" % len(name_reuse))
    for k, v, firsts in name_reuse[:6]:
        print("     %-18s x%d｜两首行不同：%s / %s" % (k, len(v), firsts[0][:34], firsts[1][:34]))
    if len(name_reuse) > 6:
        print("     …另 %d 个未打印" % (len(name_reuse) - 6))
    return true_dup


def main():
    print("=== 账本同头重复扫描 %s ===" % time.strftime("%m-%d %H:%M:%S"))
    real = scan_ledger()
    td = scan_processed()
    print()
    print("小结：账本投递块级同头重复 %d 组｜_processed 真重复投递 %d 族。" % (len(real), len(td)))
    print("边界：只读账本与 _processed，0 改动、0 删除、0 代插。判据是逐字块头 + 正文 sha1，不是文件名；")
    print("      短小节头那一档是**计数后排除**，不是没看。")


main()
