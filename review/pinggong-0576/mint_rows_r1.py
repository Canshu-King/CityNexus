# -*- coding: utf-8 -*-
"""按键族把「现尖逐枚命中」与「CN 草稿表」铸成一份 rows JSON：
键名、中英文案全部取自草稿，逐字不改；行号与改前原文全部取自现尖 git 对象。
铸完即断言：每枚键在字典两侧都不存在（不抢注），每枚原文在现尖那一代命中期望次数。"""
import json
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
TREE = "D:/moodle/_qoder_pinggong_0576"
TIP = sys.argv[1]
FAMILY = sys.argv[2]
OUT = sys.argv[3]
PROD = "frontend/src/features/agent/CopilotDock.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
DRAFT = "E:/cn_0576/_cn_0578_2044.txt"
CJK = re.compile(r"[\u3400-\u9fff]")
LIT = r"(\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*')"
TERN = re.compile(r"\?\s*" + LIT + r"\s*:\s*" + LIT, re.S)

draft = {}
for line in open(DRAFT, encoding="utf-8").read().splitlines():
    if line.startswith("CopilotDock.tsx|"):
        parts = line.split("|")
        draft.setdefault(parts[2], {"key": parts[3], "en": parts[5], "dline": parts[1]})

prod_text = subprocess.check_output(
    ["git", "show", "%s:%s" % (TIP, PROD)], cwd=REPO).decode("utf-8", "replace")
dict_text = subprocess.check_output(
    ["git", "show", "%s:%s" % (TIP, DICT)], cwd=REPO).decode("utf-8", "replace")

rows = []
GUARD_STOP = set('{<>;,:()? \n')
for match in TERN.finditer(prod_text):
    left, right = match.group(1), match.group(2)
    if bool(CJK.search(left)) == bool(CJK.search(right)):
        continue
    tip_line = prod_text.count("\n", 0, match.start()) + 1
    if CJK.search(left):
        raw_zh, raw_en = left, right
    else:
        raw_zh, raw_en = right, left
    zh, en = raw_zh[1:-1], raw_en[1:-1]
    hit = draft.get(zh)
    if hit is None or not hit["key"].startswith(FAMILY + "."):
        continue

    # 语言条件臂一并收进「改前原文」：只替换 `? 串 : 串` 会留下光杆条件，那是语法破坏
    cursor = match.start() - 1
    while cursor >= 0 and prod_text[cursor] == " ":
        cursor -= 1
    guard_end = cursor + 1
    while cursor >= 0 and prod_text[cursor] not in GUARD_STOP:
        cursor -= 1
    guard = prod_text[cursor + 1:guard_end]
    if guard.count('"') % 2 or guard.count("'") % 2:
        raise SystemExit("ABORT guard %r at line %d has an unbalanced quote" % (guard, tip_line))
    whole = (guard + " " if guard else "") + match.group(0)

    rows.append({"tip_line": tip_line, "key": hit["key"], "zh": zh, "en": en,
                 "draft_line": hit["dline"], "guard": guard, "ternary": whole})

seen = []
for row in rows:
    if row["key"] not in seen:
        seen.append(row["key"])
for key in seen:
    if dict_text.count('"%s":' % key):
        raise SystemExit("ABORT key %s already on the tip dictionary" % key)

expect_once = {}
for row in rows:
    expect_once[row["ternary"]] = expect_once.get(row["ternary"], 0) + 1
for ternary, count in expect_once.items():
    actual = prod_text.count(ternary)
    if actual != count:
        raise SystemExit("ABORT ternary %r hits %d, expected %d" % (ternary[:50], actual, count))

with open(OUT, "w", encoding="utf-8") as handle:
    json.dump({"tip": TIP, "file": PROD, "family": FAMILY, "rows": rows},
              handle, ensure_ascii=False, indent=1)
print("MINTED rows %d keys %d family %s tip %s" % (len(rows), len(seen), FAMILY, TIP[:12]))
print("OUT %s" % OUT)
for row in rows:
    print("  %d\t%s\tdraft:%s\t%s" % (row["tip_line"], row["key"], row["draft_line"], row["zh"]))
