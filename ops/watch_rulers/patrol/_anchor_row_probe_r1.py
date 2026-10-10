# -*- coding: utf-8 -*-
"""现读权威账本，把我那两枚静默名单块的**当前行号**打出来（只读）。

为什么要有它：账本会被整文件重写，`path:line` 这类坐标一夜之间就漂（04 日 01:3x 实测：
昨夜报给号令者的行号现在指向空行）。所以行号必须**用的那一刻现取**，不能抄、不能凭记忆。
匹配用块里的 ASCII 锚（脚本名带行号那种），不拿 CJK 过命令行——那是本机老坑。
"""
import io
import os
import sys

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ANCHOR = "_idle_census_ledger_r1.py"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().splitlines()
hits = [(i + 1, l.strip()[:70]) for i, l in enumerate(lines) if ANCHOR in l]
print("ledger_lines=%d anchor=%s hits=%d" % (len(lines), ANCHOR, len(hits)))
for n, t in hits:
    print("  line %d | %s" % (n, t))
if not hits:
    print("  没数到 ⇒ 本枚不出行号，别拿旧行号顶")
    sys.exit(3)
