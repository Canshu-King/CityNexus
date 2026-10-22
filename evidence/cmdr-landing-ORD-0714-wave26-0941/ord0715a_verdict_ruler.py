# -*- coding: utf-8 -*-
"""ORD-0715 甲这一格的判词表：把被点名的 45 处逐枚读原文、分类、并写下"该不该让旅客读到"。

为什么要这张表：屏上文案那把尺判的是"这个词落在会被念出来的位置"，而它的位置轴不认识三种
机器形状——集合谓词（`[...].includes(x)`、`new Set([...])`）、data-* 属性、对象里的默认值。
把这 45 处一律当"要改的文案"去动产品，就是把记号删掉冒充修复；一律当"尺错了"不动，
又确实漏过按钮上写着 EN_ROUTE 那种真缺陷。所以逐枚判，判据写出来，谁都能反对我哪一行。

行号从尺自己的 JSON 取，原文从现尖 blob 读（不是工作树，不是记忆）。
"""
import json
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
TIP = "af8ad6a1c32021852ade9a7fa6d9f782f687879f"
SRC = json.loads(open(r"D:/moodle/_cmdr_fe_rev_1016/cmdr_codes_on_screen_tip_wave26.json",
                      encoding="utf-8").read())
MINE = ["frontend/src/app/V8Experience.tsx", "frontend/src/i18n/LocaleContext.tsx"]

RULES = [
    ("SET_OR_ARRAY_PREDICATE", re.compile(r"\.includes\(|new Set\("),
     "机器在用这个词做判断，不是把它念出来"),
    ("DATA_ATTRIBUTE", re.compile(r"data-[a-z-]+=\{"),
     "落在属性里，不是文本节点"),
    ("CODE_ELEMENT", re.compile(r"<code>"),
     "故意用等宽字体显示的原始值：这是给操作者看的字段，不是给旅客读的句子"),
    ("DICTIONARY_VALUE", re.compile(r'^[ \t]*"[^"]+":[ \t]*"'),
     "字典里的一枚值，两种语言各一行"),
    ("OBJECT_DEFAULT", re.compile(r'^[ \t]*[A-Za-z_][A-Za-z0-9_]*:[ \t]*"[A-Z][A-Z_]+"'),
     "对象字面量里的默认值"),
    ("CN_KEY_MAP", re.compile(r'[\u4e00-\u9fff]+:[ \t]*"[A-Z][A-Z_]+"'),
     "中文地名到服务器城市码的表"),
]


def line_of(sha, path, n):
    out = subprocess.run(["git", "show", "%s:%s" % (sha, path)], cwd=REPO,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if out.returncode != 0:
        raise SystemExit("SHOW_FAIL %s:%s" % (sha, path))
    lines = out.stdout.decode("utf-8", "replace").split("\n")
    if not (1 <= n <= len(lines)):
        raise SystemExit("LINE_OUT_OF_RANGE %s:%d (file has %d lines)" % (path, n, len(lines)))
    return lines[n - 1].strip()


def classify(text):
    for name, rx, why in RULES:
        if rx.search(text):
            return name, why
    return "UNCLASSIFIED", "得人读一遍才知道落点，别自动判"


rows = [p for p in SRC["problems"] if p["file"] in MINE]
if len(rows) != 45:
    print("NOTE 这一格的处数从 %d 变成 %d —— 尖动过，判词表要按现尖重跑" % (45, len(rows)))
counts = {}
for p in rows:
    text = line_of(TIP, p["file"], p["line"])
    cls, why = classify(text)
    counts[cls] = counts.get(cls, 0) + 1
    print("%s:%s | %-22s | %-24s | %s" % (p["file"].split("/")[-1], p["line"], p["token"], cls, text[:78]))
print()
print("CLASS TALLY (45 处这一格)")
for cls, n in sorted(counts.items(), key=lambda kv: -kv[1]):
    print("  %-24s %d" % (cls, n))
print("TOTAL", sum(counts.values()))
if counts.get("UNCLASSIFIED"):
    print("CHECK 有 %d 处没归类，判词不算完整" % counts["UNCLASSIFIED"])
    sys.exit(1)
