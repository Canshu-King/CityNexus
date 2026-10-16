# -*- coding: utf-8 -*-
"""styles.css 加一条"中文词内不断行"的规则（四枚手机上被挤劈的读数标签）。

写法与位置都跟着仓库自己的先例：`cn-pulse.css` 的 `.v8-lede` 那一手（`anywhere` → `break-word` + `keep-all`）。
这一条只加不改：不动父层的 overflow-wrap，所以 ORD-0146 那道"长参考号不许把行撑爆"仍由原规则管。

规矩：锚必须逐字命中一次；命中不了就 ABORT 且不写一个字节。
"""
import io
import subprocess
import sys

REPO = r"D:/moodle/_cmdr_fe_rev_1016/tip"
REL = "frontend/src/styles.css"
PATH = REPO + "/frontend/src/styles.css"

ANCHOR = ".v9-evidence-drawer > .v8-route-row, .v9-evidence-drawer > small { margin-left: 20px; margin-right: 20px; }"
ADD = ANCHOR + "\n" + "\n".join([
    "/* 中文词内不断行。06:56 在 320/360/390/430 四档宽度上亲测：「证据」被挤成 证/据（320），",
    "   「路线证据」被劈成 路线证/据（四档全中），预订卡徽章「模拟承诺」被劈（360），",
    "   行程记忆里的「中途」被劈成 中/途（320）。同一手已用在 .v8-lede 上（cn-pulse.css 那一段注释）。",
    "   只加这一条、不动父层的 overflow-wrap：ORD-0146 那道长参考号仍可断。 */",
    ".v9-evidence-summary > span, .v9-evidence-drawer > .v8-aside-heading span,",
    ".v8-booking-card .v8-selected-label, .v13-2-memory-panel strong { word-break: keep-all; }",
])

head = subprocess.run(["git", "-C", REPO, "show", "HEAD:" + REL], capture_output=True, text=True, encoding="utf-8").stdout
n = head.count(ANCHOR)
print("锚命中 %d 次｜HEAD 行数 %d" % (n, head.count(chr(10)) + 1))
if n != 1:
    print("ABORT: 锚不唯一")
    sys.exit(2)
new = head.replace(ANCHOR, ADD, 1)
if new.count("word-break: keep-all") != head.count("word-break: keep-all") + 1:
    print("ABORT: 加进去的行数不对")
    sys.exit(3)
ob, cb = new.count("{"), new.count("}")
print("花括号 { %d } %d 配平=%s｜行数 %d -> %d" % (ob, cb, ob == cb, head.count(chr(10)) + 1, new.count(chr(10)) + 1))
if ob != cb:
    print("ABORT: 花括号不配平")
    sys.exit(4)
io.open(PATH, "w", encoding="utf-8", newline="\n").write(new)
print("written:", PATH)
