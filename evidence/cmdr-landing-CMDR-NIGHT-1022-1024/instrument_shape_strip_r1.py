# -*- coding: utf-8 -*-
# 七处异形死选择器的剥离（三臂已证：甲 0 读者 / 乙 0 拼装 / 丙 0 上屏，见账本 CMDR-NIGHT-0926 与 -1015）。
# 只做"整枚选择器从组里摘掉"这一种动作；压缩行里那 29 处不在本工具范围内（另建工单给车道）。
# 每处断言"这一串在本文件只出现一次"，任何一处不成立就整批不写。
import io, os, sys

TIP = r"D:/moodle/_cmdr_fe_rev_1016/tip/frontend/src"
APPLY = "--apply" in sys.argv
NL = "\n"

EDITS = [
    ("design-tokens.css",
     ".v8-page button:not(.cn-no-motion)," + NL + ".v8-page a.v8-cta," + NL + ".v8-page .v8-card {",
     ".v8-page button:not(.cn-no-motion)," + NL + ".v8-page .v8-card {",
     "v8-cta 在过渡那一组的整行"),
    ("design-tokens.css",
     "  .v8-page button, .v8-page a.v8-cta, .v8-page .v8-card {",
     "  .v8-page button, .v8-page .v8-card {",
     "v8-cta 在 reduced-motion 那组里的中段"),
    ("design-tokens.css",
     ".v9-language," + NL + ".v8-home-language {" + NL + "  border-color: var(--cn-control-border);" + NL + "}",
     ".v9-language {" + NL + "  border-color: var(--cn-control-border);" + NL + "}",
     "v8-home-language 作为组尾（要把 { 挪回上一行）"),
    ("cn-pulse.css",
     ".plan-ranking," + NL + ".collections-panel," + NL + ".poi-import-panel {",
     ".plan-ranking {",
     "collections-panel 与 poi-import-panel 同组两枚（组里只剩 plan-ranking）"),
    ("cn-pulse.css",
     ".v8-user small," + NL + ".v8-user-meta," + NL,
     ".v8-user small," + NL,
     "v8-user-meta 在组中段"),
    ("cn-pulse.css",
     ".cn-pending-empty-next," + NL + ".v8-empty-hint {",
     ".cn-pending-empty-next {",
     "v8-empty-hint 作为组尾"),
]

cache = {}
for f, old, new, note in EDITS:
    if f not in cache:
        cache[f] = io.open(os.path.join(TIP, f), encoding="utf-8", newline="").read()
    n = cache[f].count(old)
    if n != 1:
        print("ABORT %s 里这一串出现 %d 次（要 1 次）⇒ 整批不写：%s" % (f, n, note))
        sys.exit(2)
    cache[f] = cache[f].replace(old, new, 1)
    print("咬住 %-46s 净字节 %+d" % (note, len(new) - len(old)))

# 结构自检：摘完不许留下空选择器、双逗号、"逗号直接跟 {"、或整行只剩 "{"
for f, s in cache.items():
    problems = []
    for i, line in enumerate(s.split(NL), 1):
        st = line.strip()
        if st.startswith(",") or ",," in st or st == "{":
            problems.append((i, line[:60]))
        elif st.endswith(",") and "{" in st:
            problems.append((i, line[:60]))
    print("%s 结构自检：%s" % (f, "干净" if not problems else problems[:4]))
    if problems:
        sys.exit(3)

if not APPLY:
    print("DRY：没 --apply 不写一个字节。")
    sys.exit(0)
for f, s in cache.items():
    p = os.path.join(TIP, f)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print("写了 %s（读回 %d 字节）" % (f, os.path.getsize(p)))
