"""ORD-0555 PlanComparison word-by-word ruler.

For each of the six sites the order names, read the OLD tip's source line, pull
the two literals out of `zh ? "A" : "B"`, then read the NEW key's value on both
sides of the dictionary and compare them character for character.
"""
import re
import subprocess
import sys

TREE = "D:/moodle/_qoder_bijiagong_0555"
OLD_TIP = "8bc584613cc5fb047453f497b2152f8ab5102ca9"
COMPONENT = "frontend/src/features/planning/PlanComparison.tsx"
LOCALE = "frontend/src/i18n/LocaleContext.tsx"

# (old tip line number, new key) — the six sites the order lists
SITES = [
    (108, "planning.thisPlanCouldNotBeChosen"),
    (115, "planning.couldNotReachTheServerTryAgain"),
    (124, "planning.chooseYourPlan"),
    (202, "planning.totalCost"),
    (216, "planning.stops"),
    (221, "planning.walking"),
]

PAIR = re.compile(r'zh\s*\?\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"')
KEYLINE = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')


def git_show(path, rev=OLD_TIP):
    out = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "show", f"{rev}:{path}"],
                         capture_output=True)
    if out.returncode != 0:
        sys.exit("git show failed for %s at %s: %s" % (path, rev, out.stderr.decode("utf-8", "replace")))
    return out.stdout.decode("utf-8").split("\n")


def dict_values(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    starts = {}
    for n, line in enumerate(lines, 1):
        if line.startswith("const en: Dict"):
            starts["en"] = n
        if line.startswith("const zhCN: Dict"):
            starts["zh"] = n
        if line.startswith("const dictionaries"):
            starts["end"] = n
    sides = {"en": {}, "zh": {}}
    where = None
    for n, line in enumerate(lines, 1):
        if n == starts["en"]:
            where = "en"
        elif n == starts["zh"]:
            where = "zh"
        elif n == starts["end"]:
            where = None
        if where is None:
            continue
        m = KEYLINE.match(line)
        if m:
            sides[where].setdefault(m.group(1), []).append((n, m.group(2)))
    return sides


def main():
    old_component = git_show(COMPONENT)
    sides = dict_values(TREE + "/" + LOCALE)
    print("old tip %s" % OLD_TIP)
    print("sites checked: %d" % len(SITES))
    fails = 0
    for lineno, key in SITES:
        src_line = old_component[lineno - 1]
        m = PAIR.search(src_line)
        if not m:
            print("line %d: no `zh ? \"\" : \"\"` pair found -> FAIL" % lineno)
            fails += 1
            continue
        old_zh, old_en = m.group(1), m.group(2)
        en_hits = sides["en"].get(key, [])
        zh_hits = sides["zh"].get(key, [])
        if len(en_hits) != 1 or len(zh_hits) != 1:
            print("%s: expected one en and one zh entry, got en=%d zh=%d -> FAIL"
                  % (key, len(en_hits), len(zh_hits)))
            fails += 1
            continue
        (en_line, en_val) = en_hits[0]
        (zh_line, zh_val) = zh_hits[0]
        ok_en = en_val == old_en
        ok_zh = zh_val == old_zh
        print("%s" % key)
        print("  old line %d pair: zh=%r en=%r" % (lineno, old_zh, old_en))
        print("  en dict line %d identical=%s" % (en_line, ok_en))
        print("  zh dict line %d identical=%s" % (zh_line, ok_zh))
        if not (ok_en and ok_zh):
            fails += 1
    # nothing of the six may remain inline in the component any more
    component_now = open(TREE + "/" + COMPONENT, encoding="utf-8").read()
    moved = sum(1 for _, key in SITES if key in component_now)
    ternary = component_now.count('zh ? "')
    print("keys referenced from the component: %d of %d" % (moved, len(SITES)))
    print('remaining `zh ? "` hits in the component: %d' % ternary)
    print("RESULT: %s" % ("WORDING_VERBATIM_PASS" if fails == 0 and moved == len(SITES)
                          else "FAIL count=%d" % fails))
    return 0 if fails == 0 and moved == len(SITES) else 1


if __name__ == "__main__":
    sys.exit(main())
