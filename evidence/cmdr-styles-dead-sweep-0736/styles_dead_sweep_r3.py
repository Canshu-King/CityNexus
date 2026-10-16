# -*- coding: utf-8 -*-
"""styles.css 死码清扫 v3 —— 从 HEAD 起重做一遍，并把手停在半路的 .v8-rain-button 收干净。

v2 只删了整条规则（6 行），没动混在压缩行里的 .v8-rain-button：
  :174 组合选择器里的一个 token + 它自己的整条规则（含 #fffaf4 浅底，是逃逸口分母的一员）
  :185 @media (max-width: 680px) 里 .v8-page-intro … 组合中的一个 token
  :281 @media (max-width: 680px) 里 44px 触达地板组合中的一个 token
这一版每处改动都带"预期次数"断言：任何一处对不上就 ABORT 且不写一个字节。
证据臂（_cmdr_deadcss_proof_r2.py 静态 + _cmdr_deadcss_dom_probe_r1.cjs 动态）已先证明
这三枚类名在产品源码 0 读者、六屏 0 命中，所以删规则与摘 token 都不可能改变渲染。
"""
import subprocess
import sys

REPO = r"D:/moodle/_cmdr_fe_rev_1016/tip"
PATH = r"D:/moodle/_cmdr_fe_rev_1016/tip/frontend/src/styles.css"
HEAD = "HEAD"

head_src = subprocess.run(["git", "-C", REPO, "show", "%s:frontend/src/styles.css" % HEAD],
                          capture_output=True, text=True, encoding="utf-8").stdout
if head_src.count("\n") < 1900:
    print("ABORT: HEAD 取回的内容不像 styles.css")
    sys.exit(2)

lines = head_src.split("\n")
before_lines = len(lines)
rain_before = head_src.count(".v8-rain-button")
copilot_runtime_before = head_src.count(".cn-copilot-runtime")
native_status_before = head_src.count(".cn-native-status")

# 甲 整条删除（v2 已证这 6 行是死规则）
DROP_EXACT = [
    ".v8-rain-button { color: #8a4f1d; }",
    ".cn-copilot-runtime { flex-wrap: wrap; padding: 8px var(--cn-s-10); border: 1px solid #e2e7ef; "
    "border-radius: var(--cn-r-8); color: #667489; background: #fff; font-size: 9px; }",
    ".cn-native-status { flex: none; padding: var(--cn-s-4) var(--cn-s-6); border-radius: var(--cn-r-4); "
    "color: #53627b; background: #e7edf5; font-size: 8px; font-weight: 800; letter-spacing: .04em; "
    "text-transform: uppercase; }",
    ".cn-native-status.active { color: #4c579d; background: #e9eaff; }",
    ".cn-native-status.terminal { color: #4c7d63; background: #e6f3eb; }",
]
EXPECT_DROPS = {DROP_EXACT[0]: 2, DROP_EXACT[1]: 1, DROP_EXACT[2]: 1, DROP_EXACT[3]: 1, DROP_EXACT[4]: 1}

kept, dropped = [], 0
for line in lines:
    hit = next((d for d in DROP_EXACT if line.strip() == d and EXPECT_DROPS[d] > 0), None)
    if line.strip() in DROP_EXACT:
        dropped += 1
        EXPECT_DROPS[line.strip()] -= 1
    else:
        kept.append(line)
if dropped != 6:
    print("ABORT: 整条删除期望 6 行，实到 %d 行" % dropped)
    sys.exit(3)

src = "\n".join(kept)

# 乙 组合选择器里摘 token（只摘这一枚，同一压缩行其余部分逐字保留）
TOKEN_EDITS = [
    # (原片段, 新片段, 期望命中次数)
    (".v8-quiet-button, .v8-text-button, .v8-rain-button { display: inline-flex;",
     ".v8-quiet-button, .v8-text-button { display: inline-flex;", 1),
    (".v8-quiet-button, .v8-primary, .v8-outline-button, .v8-rain-button, .v8-page-intro button,",
     ".v8-quiet-button, .v8-primary, .v8-outline-button, .v8-page-intro button,", 1),
    (".v8-page-intro .v8-primary, .v8-page-intro .v8-outline-button, .v8-page-intro .v8-rain-button { margin-top: 18px; }",
     ".v8-page-intro .v8-primary, .v8-page-intro .v8-outline-button { margin-top: 18px; }", 1),
    (".cn-copilot-head, .cn-copilot-runtime, .cn-copilot-form { display: flex; align-items: center; gap: var(--cn-s-10); }",
     ".cn-copilot-head, .cn-copilot-form { display: flex; align-items: center; gap: var(--cn-s-10); }", 1),
]
for old, new, n in TOKEN_EDITS:
    got = src.count(old)
    if got != n:
        print("ABORT: token 片段期望 %d 处，实到 %d 处 -> %s" % (n, got, old[:60]))
        sys.exit(4)
    src = src.replace(old, new)

# 丙 :174 那枚 .v8-rain-button 自己的整条规则（压缩行内，含 #fffaf4 浅底逃逸口）
RAINDROP = (".v8-rain-button { min-height: 40px; padding: 0 14px; border: 1px solid #f0d1b5; "
            "border-radius: var(--cn-r-8); color: var(--v8-amber); background: #fffaf4; "
            "font-size: 12px; font-weight: 750; }")
if src.count(RAINDROP) != 1:
    print("ABORT: .v8-rain-button 整条规则期望 1 处，实到 %d 处" % src.count(RAINDROP))
    sys.exit(5)
src = src.replace(RAINDROP, "")

after_lines = src.split("\n")
# 去掉因摘除整条规则而留下的空压缩行尾（不制造新空行）
cleaned = []
for ln in after_lines:
    cleaned.append(ln.rstrip() if ln.rstrip() != ln else ln)
src_out = "\n".join(cleaned)
if src_out.endswith("\n") is False:
    src_out += "\n"

rain_after = src_out.count(".v8-rain-button")
copilot_after = src_out.count(".cn-copilot-runtime")
native_after = src_out.count(".cn-native-status")
print("行数: %d -> %d" % (before_lines, src_out.rstrip("\n").count("\n") + 1))
print("token 计数 .v8-rain-button: %d -> %d" % (rain_before, rain_after))
print("token 计数 .cn-copilot-runtime: %d -> %d" % (copilot_runtime_before, copilot_after))
print("token 计数 .cn-native-status: %d -> %d" % (native_status_before, native_after))
if rain_after or copilot_after or native_after:
    print("ABORT: 还有残留 token，没清干净")
    sys.exit(6)

# 大括号配平自检：删规则不能把 { } 数带偏
ob, cb = src_out.count("{"), src_out.count("}")
print("花括号: { %d  } %d  配平=%s" % (ob, cb, ob == cb))
if ob != cb:
    print("ABORT: 花括号不配平")
    sys.exit(7)

open(PATH, "w", encoding="utf-8", newline="\n").write(src_out)
print("written:", PATH)
