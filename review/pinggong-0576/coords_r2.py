# -*- coding: utf-8 -*-
"""交件坐标清册：从推上去那枚枝尖的对象里现读——
每枚 copilot.* 键的两侧定义行、组件里每处取词行、以及该文件残留的内联双语行数。
sha 由命令行给，绝不手打。"""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CAND = sys.argv[1]
REPO = "D:/moodle/_qoder_integration_20260919"
DICT = "frontend/src/i18n/LocaleContext.tsx"
PROD = "frontend/src/features/agent/CopilotDock.tsx"


def show(rel):
    return subprocess.check_output(["git", "show", "%s:%s" % (CAND, rel)],
                                   cwd=REPO).decode("utf-8", "replace")


dict_text = show(DICT)
prod_text = show(PROD)
en_head = dict_text.index("const en: Dict = {")
en_end = dict_text.index("\n};", en_head)
zh_head = dict_text.index("const zhCN: Dict = {")
zh_end = dict_text.index("\n};", zh_head)


def numbered(body, start, end):
    out = []
    for index, line in enumerate(body[start:end].split("\n"), start=body[:start].count("\n") + 1):
        out.append((index, line))
    return out


en_keys, zh_keys = {}, {}
for index, line in numbered(dict_text, en_head, en_end):
    hit = re.match(r'\s*"((?:copilot\.[^"]+))"\s*:', line)
    if hit:
        en_keys[hit.group(1)] = index
for index, line in numbered(dict_text, zh_head, zh_end):
    hit = re.match(r'\s*"((?:copilot\.[^"]+))"\s*:', line)
    if hit:
        zh_keys[hit.group(1)] = index

calls = {}
for index, line in enumerate(prod_text.split("\n"), start=1):
    for hit in re.findall(r't\("(copilot\.[^"]+)"\)', line):
        calls.setdefault(hit, []).append(index)

CJK = re.compile(r"[\u3400-\u9fff]")
LIT = r"(\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*')"
TERN = re.compile(r"\?\s*" + LIT + r"\s*:\s*" + LIT, re.S)
left = sum(1 for m in TERN.finditer(prod_text)
           if bool(CJK.search(m.group(1))) != bool(CJK.search(m.group(2))))

print("CAND %s" % CAND)
print("KEY_DEFINITIONS %d" % len(en_keys))
for key in sorted(en_keys):
    where = calls.get(key, [])
    print("  %s en=%d zh=%d calls=%s" % (key, en_keys[key], zh_keys.get(key, -1),
                                         ",".join(str(w) for w in where)))
print("UNIQUE_KEYS_CALLED %d CALL_SITES %d" % (len(calls), sum(len(v) for v in calls.values())))
print("INLINE_BILINGUAL_LEFT_IN_FILE %d" % left)
