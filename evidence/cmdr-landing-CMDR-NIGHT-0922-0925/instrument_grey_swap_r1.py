# -*- coding: utf-8 -*-
# 三枚写死的浅灰 -> 配对好的 --cn-ink-secondary。逐枚断言"这一串在本文件里只出现一次"，
# 否则不动；改完打印每枚的字节差与总账，任何一枚没咬住就整体不写。
import io, os, sys

SRC = r"D:/moodle/_cmdr_fe_rev_1016/tip/frontend/src/styles.css"
APPLY = "--apply" in sys.argv

EDITS = [
    (".v8-agent-progress span { color: #8490a0; font-size: 10px; line-height: 1.4; }",
     ".v8-agent-progress span { color: var(--cn-ink-secondary); font-size: 10px; line-height: 1.4; }",
     "Copilot 进度块里的小字"),
    (".cn-agent-raw summary { color: #7e8ca1; cursor: pointer; font-size: 8px; }",
     ".cn-agent-raw summary { color: var(--cn-ink-secondary); cursor: pointer; font-size: 8px; }",
     "原始回执的折叠标题"),
    (".v8-advanced > summary { cursor: pointer; color: #7e8ca1; font-size: 11px; font-weight: 700; }",
     ".v8-advanced > summary { cursor: pointer; color: var(--cn-ink-secondary); font-size: 11px; font-weight: 700; }",
     "「我的」那屏高级详情"),
]

s = io.open(SRC, encoding="utf-8", newline="").read()
orig = s
plan = []
for old, new, note in EDITS:
    n = s.count(old)
    if n != 1:
        print("ABORT 这一串出现 %d 次（要 1 次），整批不写：%s" % (n, old[:70]))
        sys.exit(2)
    plan.append((old, new, note))
for old, new, note in plan:
    s = s.replace(old, new, 1)

removed = sum(len(o) - len(n) for o, n, _ in plan)
print("三枚断言全过｜文件净变化 %+d 字节（三枚 old 共 %d 字节换成 new 共 %d 字节）" % (
    len(s) - len(orig), sum(len(o) for o, _, _ in plan), sum(len(n) for _, n, _ in plan)))
for o, n, note in plan:
    print("   %-18s %+d 字节 | %s" % (note, len(n) - len(o), n[:78]))
assert s.count("#7e8ca1") == orig.count("#7e8ca1") - 2, "两枚 #7e8ca1 应各少一次"
assert s.count("#8490a0") == orig.count("#8490a0") - 1, "#8490a0 应少一次"
if not APPLY:
    print("DRY：没 --apply 就不写一个字节。")
    sys.exit(0)
io.open(SRC, "w", encoding="utf-8", newline="").write(s)
back = io.open(SRC, encoding="utf-8", newline="").read()
print("写回后读回长度 %d｜与内存串相等 %s" % (len(back), back == s))
