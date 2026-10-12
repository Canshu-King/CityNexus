# -*- coding: utf-8 -*-
"""并代后的字典对账：本枝那代键集 ∪ 线上那代键集 必须与现在树上的键集逐字相等，
任一侧内不得有重键，两侧之间不得多出单侧键。sha 一律由命令行给，不手写。"""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MINE = sys.argv[1]
THEIRS = sys.argv[2]
PATH = "D:/moodle/_qoder_pinggong_0576/frontend/src/i18n/LocaleContext.tsx"
REPO = "D:/moodle/_qoder_integration_20260919"
KEYL = re.compile(r'^\s*"([a-z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)+)"\s*:')
SIDES = {"en": "const en: Dict = {", "zh": "const zhCN: Dict = {"}


def key_lines(body, marker):
    head = body.index(marker)
    tail = body.index("\n};", head)
    out = []
    for line in body[head:tail].split("\n"):
        hit = KEYL.match(line)
        if hit:
            out.append(hit.group(1))
    return out


def from_ref(sha, marker):
    body = subprocess.check_output(
        ["git", "show", "%s:frontend/src/i18n/LocaleContext.tsx" % sha],
        cwd=REPO).decode("utf-8", "replace")
    return key_lines(body, marker)


now = open(PATH, encoding="utf-8").read()
counts = {}
problems = []
for side, marker in SIDES.items():
    mine = from_ref(MINE, marker)
    theirs = from_ref(THEIRS, marker)
    got = key_lines(now, marker)
    want = set(mine) | set(theirs)
    lost = sorted(want - set(got))
    extra = sorted(set(got) - want)
    dupes = sorted({k for k in got if got.count(k) > 1})
    counts[side] = (len(got), len(mine), len(theirs))
    if lost or extra or dupes:
        problems.append("%s lost=%s extra=%s dupes=%s" % (side, lost[:4], extra[:4], dupes[:4]))

only_en = sorted(set(key_lines(now, SIDES["en"])) - set(key_lines(now, SIDES["zh"])))
only_zh = sorted(set(key_lines(now, SIDES["zh"])) - set(key_lines(now, SIDES["en"])))
copilot_en = [k for k in key_lines(now, SIDES["en"]) if k.startswith("copilot.")]
copilot_zh = [k for k in key_lines(now, SIDES["zh"]) if k.startswith("copilot.")]
print("EN total=%d mine=%d theirs=%d   ZH total=%d mine=%d theirs=%d"
      % (counts["en"][0], counts["en"][1], counts["en"][2],
         counts["zh"][0], counts["zh"][1], counts["zh"][2]))
print("COPILOT en=%d zh=%d  ONE_SIDED en=%d zh=%d"
      % (len(copilot_en), len(copilot_zh), len(only_en), len(only_zh)))
for key in (only_en + only_zh)[:6]:
    print("  ONE_SIDED %s" % key)
for problem in problems:
    print("PROBLEM " + problem)
if problems or only_en or only_zh:
    raise SystemExit(1)
print("VERDICT merge_keys_balanced")
