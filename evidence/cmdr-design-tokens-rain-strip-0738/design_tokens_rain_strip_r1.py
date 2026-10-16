# -*- coding: utf-8 -*-
"""把最后一枚 .v8-rain-button 从暗档覆盖组里摘掉（design-tokens.css:815）。

上一刀清了 styles.css，但暗档那条组里还留着 `:root[data-theme="dark"] .v8-page .v8-rain-button`。
类名死证已在上一刀的静态臂里量过（157 枚 .tsx/.ts 零字面读者，模板串插值片段无一能拼出它），
所以这一处也只是"改名之后没人再画"的残留。

规矩：从压缩的组合选择器里只摘这一枚 token，其余八枚与声明块逐字不动；
预期次数对不上就 ABORT 且不写一个字节；改完比花括号配平与文件字节。
"""
import subprocess
import sys

REPO = r"D:/moodle/_cmdr_fe_rev_1016/tip"
REL = "frontend/src/design-tokens.css"
PATH = REPO + r"\frontend\src\design-tokens.css"
TOK = ", :root[data-theme=\"dark\"] .v8-page .v8-rain-button"

head = subprocess.run(["git", "-C", REPO, "show", "HEAD:" + REL],
                      capture_output=True, text=True, encoding="utf-8").stdout
if len(head) < 50000:
    print("ABORT: HEAD 取回的 design-tokens.css 不像本尊（%d 字符）" % len(head))
    sys.exit(2)

n = head.count(TOK)
print("摘前：token 片段命中 %d 处｜文件字符 %d" % (n, len(head)))
if n != 1:
    print("ABORT: 预期一处，实到 %d 处" % n)
    sys.exit(3)
if head.count(".v8-rain-button") != 1:
    print("ABORT: 文件里 .v8-rain-button 不止一处（实到 %d），本脚本只处理一处" % head.count(".v8-rain-button"))
    sys.exit(4)

new = head.replace(TOK, "", 1)
if new.count(".v8-rain-button") != 0:
    print("ABORT: 摘完还有残留")
    sys.exit(5)
for keep in [".v8-compare-button", ".v8-map-panel", ".v8-comparison", ".v8-next-card",
             ".v8-mode-chooser", ".v8-live-now", ".v8-day-detail", ".v8-day-card"]:
    if new.count(keep) < head.count(keep):
        print("ABORT: 顺手伤了活的选择器 %s（摘前 %d 摘后 %d）" % (keep, head.count(keep), new.count(keep)))
        sys.exit(6)
ob, cb = new.count("{"), new.count("}")
print("摘后：花括号 { %d } %d 配平=%s｜行 %d -> %d" % (ob, cb, ob == cb, head.count("\n") + 1, new.count("\n") + 1))
if ob != cb:
    print("ABORT: 花括号不配平")
    sys.exit(7)

open(PATH, "w", encoding="utf-8", newline="\n").write(new)
print("written:", PATH)
