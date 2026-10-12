# -*- coding: utf-8 -*-
"""批二起的铸规格器（改进处）：
  · 「改前原文」取成从语言条件臂起、到英文臂止的整段切片，排版（含跨行）逐字保留；
    切片起点落在条件臂那一行的第一个非空白字符上，所以缩进不受影响；
  · 每枚带 offset 与起止行；相同切片去重后记次数；
  · 可选第 4 参限定本批枚数（一轮最多八处），按起始行升序取前 N。
用法：python mint2.py <那一代的 sha> <键族> <out.json> [最多几处]"""
import json
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
GEN = sys.argv[1]
FAMILY = sys.argv[2]
OUT = sys.argv[3]
LIMIT = int(sys.argv[4]) if len(sys.argv) > 4 else 0
PROD = "frontend/src/features/agent/CopilotDock.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
DRAFT = "E:/cn_0576/_cn_0578_2044.txt"
CJK = re.compile(r"[\u3400-\u9fff]")
LIT = r"(\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*')"
TERN = re.compile(r"\?\s*" + LIT + r"\s*:\s*" + LIT, re.S)
GUARD_STOP = set('{<>;,:()?')


def die(msg):
    raise SystemExit("ABORT " + msg)


draft = {}
for line in open(DRAFT, encoding="utf-8").read().splitlines():
    if line.startswith("CopilotDock.tsx|"):
        parts = line.split("|")
        draft.setdefault(parts[2], {"key": parts[3], "en": parts[5], "dline": parts[1]})

prod_text = subprocess.check_output(
    ["git", "show", "%s:%s" % (GEN, PROD)], cwd=REPO).decode("utf-8", "replace")
dict_text = subprocess.check_output(
    ["git", "show", "%s:%s" % (GEN, DICT)], cwd=REPO).decode("utf-8", "replace")

found = []
for match in TERN.finditer(prod_text):
    left, right = match.group(1), match.group(2)
    if bool(CJK.search(left)) == bool(CJK.search(right)):
        continue
    if CJK.search(left):
        raw_zh, raw_en = left, right
    else:
        raw_zh, raw_en = right, left
    zh, en = raw_zh[1:-1], raw_en[1:-1]
    hit = draft.get(zh)
    if hit is None or not hit["key"].startswith(FAMILY + "."):
        continue

    cursor = match.start() - 1
    while cursor >= 0 and prod_text[cursor] in " \t\n\r":
        cursor -= 1
    guard_end = cursor + 1
    while cursor >= 0 and prod_text[cursor] not in GUARD_STOP:
        cursor -= 1
    token_start = cursor + 1
    while prod_text[token_start] in " \t\n\r":
        token_start += 1
    guard = prod_text[token_start:guard_end]
    line_no = prod_text.count("\n", 0, match.start()) + 1
    if not guard:
        die("no language guard before line %d —— 这形制不是 `条件 ? 中 : 英`" % line_no)
    if guard.count('"') % 2 or guard.count("'") % 2:
        die("guard %r unbalanced quote near line %d" % (guard, line_no))
    whole = prod_text[token_start:match.end()]
    if not whole.startswith(guard) or "?" not in whole:
        die("slice %r does not start at the guard of line %d" % (whole[:60], line_no))

    found.append({
        "start": token_start,
        "start_line": prod_text.count("\n", 0, token_start) + 1,
        "end_line": prod_text.count("\n", 0, match.end()) + 1,
        "key": hit["key"], "zh": zh, "en": en, "draft_line": hit["dline"],
        "guard": guard, "ternary": whole,
    })

found.sort(key=lambda row: row["start"])
if LIMIT:
    found = found[:LIMIT]

keys = []
for row in found:
    if row["key"] not in keys:
        keys.append(row["key"])
for key in keys:
    if dict_text.count('"%s":' % key):
        die("key %s already defined in that generation's dictionary" % key)

slices = {}
for row in found:
    slices[row["ternary"]] = slices.get(row["ternary"], 0) + 1
for ternary, count in slices.items():
    if prod_text.count(ternary) != count:
        die("slice %r hits %d, expected %d" % (ternary[:60], prod_text.count(ternary), count))

json.dump({"gen": GEN, "file": PROD, "family": FAMILY, "rows": found},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("MINTED gen %s family %s rows %d keys %d limit %d out %s"
      % (GEN[:12], FAMILY, len(found), len(keys), LIMIT, OUT))
for row in found:
    print("  %d-%d\t%s\tdraft:%s\tguard=%r" % (row["start_line"], row["end_line"],
                                               row["key"], row["draft_line"], row["guard"]))
