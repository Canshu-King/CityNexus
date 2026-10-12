# -*- coding: utf-8 -*-
"""成对尺：把 LocaleContext 的 en 与 zh-CN 两块键名各数一遍，报两侧总数与两个方向的差集。
差集非空不等于本车道造的（现尖上本来就有单侧键），所以本尺同时数现尖那一代做对照。"""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
TIP = sys.argv[1]
PATH = "frontend/src/i18n/LocaleContext.tsx"
KEYL = re.compile(r'^\s*"([a-z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)+)"\s*:')


def sides(text):
    en_head = text.index("const en: Dict = {")
    en_end = text.index("\n};", en_head)
    zh_head = text.index("const zhCN: Dict = {")
    zh_end = text.index("\n};", zh_head)
    en, zh = [], []
    for index, line in enumerate(text[:en_end].split("\n")):
        hit = KEYL.match(line)
        if hit:
            en.append(hit.group(1))
    for line in text[zh_head:zh_end].split("\n"):
        hit = KEYL.match(line)
        if hit:
            zh.append(hit.group(1))
    return en, zh


tip_text = subprocess.check_output(["git", "show", "%s:%s" % (TIP, PATH)],
                                   cwd=REPO).decode("utf-8", "replace")
with open("D:/moodle/_qoder_pinggong_0576/" + PATH, encoding="utf-8") as handle:
    cand_text = handle.read()

for tag, text in (("TIP", tip_text), ("CAND", cand_text)):
    en, zh = sides(text)
    only_en = sorted(set(en) - set(zh))
    only_zh = sorted(set(zh) - set(en))
    print("%s en=%d zh=%d only_en=%d only_zh=%d" % (tag, len(en), len(zh), len(only_en), len(only_zh)))
    for key in only_en:
        print("   ONLY_EN %s" % key)
    for key in only_zh:
        print("   ONLY_ZH %s" % key)
    if len(en) != len(set(en)):
        print("   DUP_IN_EN present")
    if len(zh) != len(set(zh)):
        print("   DUP_IN_ZH present")

tip_en, tip_zh = sides(tip_text)
cand_en, cand_zh = sides(cand_text)
new_en = sorted(set(cand_en) - set(tip_en))
new_zh = sorted(set(cand_zh) - set(tip_zh))
print("NEW_EN %d NEW_ZH %d same_set=%s" % (len(new_en), len(new_zh), new_en == new_zh))
for key in new_en:
    print("   NEW %s" % key)
