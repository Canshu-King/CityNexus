# -*- coding: utf-8 -*-
"""把 ORD-0715 乙那六枚文件也先判一遍——不是替接单人改，是把"每枚要读什么"准备好。

同甲那把尺：行号从尺的 JSON 取，原文从现尖 blob 现读，再按落点归类。
输出两件事：每枚文件的类别计数，以及**可能被念出来**的那几行的原文（其余的机器落点只报数）。
"""
import collections
import json
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
TIP = "af8ad6a1c32021852ade9a7fa6d9f782f687879f"
SRC = json.loads(open(r"D:/moodle/_cmdr_fe_rev_1016/cmdr_codes_on_screen_tip_wave26.json",
                      encoding="utf-8").read())

TARGETS = [
    "frontend/src/features/simulation/SimulationPanel.tsx",
    "frontend/src/features/trip/spendFacts.ts",
    "frontend/src/features/pending/pendingPlaceWrites.ts",
    "frontend/src/features/poster/posterShare.ts",
    "frontend/src/features/inbox/shareGrantRead.ts",
    "frontend/src/features/inbox/JourneyInboxWorkbench.tsx",
]

RULES = [
    ("SET_OR_ARRAY_PREDICATE", re.compile(r"\.includes\(|new Set\(|\bcase\b|\b===|\b!=="),
     "机器在比这个词"),
    ("DATA_ATTRIBUTE", re.compile(r"data-[a-z-]+=\{|attributes\[|\bsetAttribute\("), "落在属性里"),
    ("TYPE_OR_KEY_POSITION", re.compile(r'^[ \t]*(export )?(type|const [A-Z_]+ =|interface)|:\s*"[A-Z][A-Z_ ]+"\s*[;|]'),
     "类型联合或表键位"),
    ("OBJECT_DEFAULT", re.compile(r'^[ \t]*[A-Za-z_][A-Za-z0-9_]*:[ \t]*"[A-Z][A-Z_ ]+"[,}]?$', ),
     "对象字面量里的值（要看它最终流向哪儿才知道）"),
    ("CODE_ELEMENT", re.compile(r"<code>|<pre>|font-mono"), "等宽显示的技术字段"),
    ("DICTIONARY_VALUE", re.compile(r'^[ \t]*"[^"]+":[ \t]*"'), "字典值"),
    ("JSX_OR_COPY_STRING", re.compile(r'return |textContent|innerText|\bt\('), "像是要被念出来的"),
]

# 会被念出来的类别——这些需要人判断，其余是机器落点
SPOKEN = {"CODE_ELEMENT", "DICTIONARY_VALUE", "JSX_OR_COPY_STRING"}


def line_of(path, n):
    out = subprocess.run(["git", "show", "%s:%s" % (TIP, path)], cwd=REPO,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if out.returncode != 0:
        raise SystemExit("SHOW_FAIL %s" % path)
    lines = out.stdout.decode("utf-8", "replace").split("\n")
    if not (1 <= n <= len(lines)):
        raise SystemExit("LINE_OUT_OF_RANGE %s:%d" % (path, n))
    return lines[n - 1].strip()


def classify(text):
    for name, rx, why in RULES:
        if rx.search(text):
            return name
    return "UNCLASSIFIED"


grand = collections.Counter()
spoken_rows = []
for path in TARGETS:
    rows = [p for p in SRC["problems"] if p["file"] == path]
    if not rows:
        raise SystemExit("NO_FINDINGS for %s —— 清单里没这枚，别当成「它干净」" % path)
    counts = collections.Counter()
    for p in rows:
        text = line_of(path, p["line"])
        cls = classify(text)
        counts[cls] += 1
        grand[cls] += 1
        if cls in SPOKEN or cls == "UNCLASSIFIED":
            spoken_rows.append((path, p["line"], p["token"], cls, text))
    print("==== %s  共 %d 处" % (path.split("/")[-1], len(rows)))
    for cls, n in counts.most_common():
        print("     %-24s %d" % (cls, n))

print()
print("TOTAL over the six files: %d 处，其中需要人判的（可能被念出或未归类）：%d"
      % (sum(grand.values()), len(spoken_rows)))
print("CLASS TALLY overall")
for cls, n in grand.most_common():
    print("  %-24s %d" % (cls, n))
print()
print("---- 需要人判的那几行（原文现读） ----")
for path, n, token, cls, text in spoken_rows:
    print("%s:%s | %s | %s" % (path.split("/")[-1], n, token, text[:96]))
