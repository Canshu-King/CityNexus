# -*- coding: utf-8 -*-
# 文字侧的 --v8-accent 换成 --cn-accent-text（厂内注释：那是"唯一一枚当文字用能过 AA 的强调色"）。
# 填充侧（background: var(--v8-accent) 配白字）一律不动——那是另一种形状。
# 用法：python _cmdr_accent_text_swap_r1.py [--apply]
import io, os, re, sys

TIP = r"D:/moodle/_cmdr_fe_rev_1016/tip/frontend/src"
APPLY = "--apply" in sys.argv
FILES = ("styles.css", "v10.css", "design-tokens.css", "cn-pulse.css")

hits = []
for f in FILES:
    p = os.path.join(TIP, f)
    ls = io.open(p, encoding="utf-8", newline="").read().split("\n")
    for i, s in enumerate(ls, 1):
        for m in re.finditer(r"color:\s*var\(--v8-accent\)", s):
            # 往前取这条声明所属的选择器（压缩行里可能有好几条规则）
            head = s[:m.start()]
            k = head.rfind("}")
            sel = head[k + 1:].strip() if k >= 0 else head.strip()
            sel = sel.split("{")[0].strip() or "(压缩行里，前一规则的尾部)"
            hits.append({"file": f, "line": i, "selector": sel[-70:], "col": m.start()})

print("文字侧 var(--v8-accent) 命中 %d 处" % len(hits))
for h in hits:
    print("   %s:%d  选择器=%s" % (h["file"], h["line"], h["selector"]))

if not APPLY:
    print("DRY：没 --apply 不写。")
    sys.exit(0)

for f in FILES:
    p = os.path.join(TIP, f)
    before = io.open(p, encoding="utf-8", newline="").read()
    n = before.count("color: var(--v8-accent)")
    if n == 0:
        continue
    after = before.replace("color: var(--v8-accent)", "color: var(--cn-accent-text)")
    assert after.count("color: var(--cn-accent-text)") == before.count("color: var(--cn-accent-text)") + n
    assert len(after) - len(before) == n * (len("--cn-accent-text") - len("--v8-accent"))
    io.open(p, "w", encoding="utf-8", newline="").write(after)
    print("写了 %s：%d 处，净字节 %+d" % (f, n, len(after) - len(before)))
