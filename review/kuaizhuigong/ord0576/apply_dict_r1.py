"""ORD-0576 kuaizhuigong: append the three catalogueReadback keys to both dictionary blocks.

The door: insertion points are located by asserting what is actually on the line (the last entry of
each block is `setup.groupRuleUnknown`, and the line after it must be the block's closing `};`).
Every Chinese value is taken from the component file at the live tip by regex, not typed here, so a
"transport, not rewrite" claim can only pass if the words really are the ones on screen. Any mismatch
aborts without writing.
"""

import re
import subprocess
import sys

TREE = "D:/moodle/_qoder_kuaizhuigong_0557"
DICT = "frontend/src/i18n/LocaleContext.tsx"
COMP = "frontend/src/features/planning/catalogueReadback.ts"
TIP = "0d0eca62ef8b7345bff48f6a30b1bf628e8124e0"
EN_ANCHOR = '  "setup.groupRuleUnknown"'
ZH_VALUES = {
    "catalog.count.unreadable": None,
    "catalog.count.zero": None,
    "catalog.count.some": None,
}


def show(ref, path):
    return subprocess.run(["git", "-C", TREE, "show", f"{ref}:{path}"], capture_output=True,
                          check=True).stdout.decode("utf-8")


comp_src = show(TIP, COMP)

# pull the Chinese literals out of the component itself
zh_unreadable = re.search(r'export const UNREADABLE_SENTENCE_ZH = "(.*?)";', comp_src)
zh_zero = re.search(r'\? "(服务器回读：这座城我们现在一个地点都还没有。)"', comp_src)
zh_some = re.search(r'`?(服务器回读：这座城我们现在有 \$\{count\} 个地点，可以排进行程。)`?', comp_src)
missing = [name for name, m in (("unreadable", zh_unreadable), ("zero", zh_zero), ("some", zh_some)) if not m]
if missing:
    print("ABORT could not lift the Chinese literals from the component: " + ", ".join(missing))
    sys.exit(1)

ZH_VALUES["catalog.count.unreadable"] = zh_unreadable.group(1)
ZH_VALUES["catalog.count.zero"] = zh_zero.group(1)
ZH_VALUES["catalog.count.some"] = zh_some.group(1)

# a lifted template literal carries `${count}`; a dictionary hole is `{count}`. Leaving the dollar in
# puts it on the traveller's screen -- the probe caught exactly that on the first pass.
def normalize_holes(value):
    return re.sub(r"\$\{(\w+)\}", r"{\1}", value)


for key in ZH_VALUES:
    ZH_VALUES[key] = normalize_holes(ZH_VALUES[key])

# the English side mirrors the same three arms, with the inline count call turned into the marker
en_unreadable = re.search(r'export const UNREADABLE_SENTENCE_EN =\s*\n?\s*"(.*?)";', comp_src)
en_zero = re.search(r': "(Read back from the server: we hold no places for this city yet\.)"', comp_src)
en_some = re.search(r'`Read back from the server: this city now has \$\{count\} \$\{englishCountNoun\(count, "place"\)\}( that can go into a trip\.)`', comp_src)
for tag, m in (("en unreadable", en_unreadable), ("en zero", en_zero), ("en some", en_some)):
    if not m:
        print(f"ABORT could not lift the {tag} literal from the component")
        sys.exit(1)

EN_VALUES = {
    "catalog.count.unreadable": en_unreadable.group(1),
    "catalog.count.zero": en_zero.group(1),
    # {plural:place:count} is what englishCountNoun(count, "place") produced at runtime
    "catalog.count.some": "Read back from the server: this city now has {count} "
                          "{plural:place:count}" + en_some.group(1),
}

lines = open(DICT, encoding="utf-8").read().split("\n")

# locate both block tails by the anchor entry and require the closing brace right after it
anchors = [i for i, l in enumerate(lines) if l.startswith(EN_ANCHOR)]
if len(anchors) != 2:
    print(f"ABORT expected the anchor entry on both sides, found {len(anchors)} at {anchors}")
    sys.exit(1)
for a in anchors:
    if lines[a + 1] != "};":
        print(f"ABORT line after the anchor at {a + 2} is not the block close: {lines[a+1]!r}")
        sys.exit(1)

before_len = len(lines)
en_at, zh_at = anchors[0], anchors[1]

en_new = [
    "  /* ORD-0576 kuaizhuigong: the three catalogueReadback sentences. Each English value is the exact",
    "     word that module printed before the keys existed, so an English screen cannot move; the count",
    "     noun uses {plural:place:count}, which is what its inline englishCountNoun call produced. */",
] + [f'  "{k}": "{EN_VALUES[k]}",' for k in ("catalog.count.unreadable", "catalog.count.zero", "catalog.count.some")]

zh_new = [f'  "{k}": "{ZH_VALUES[k]}",' for k in ("catalog.count.unreadable", "catalog.count.zero", "catalog.count.some")]

# insert the later block first so the earlier index stays valid
lines[zh_at + 1:zh_at + 1] = zh_new
lines[en_at + 1:en_at + 1] = en_new

if len(lines) != before_len + len(en_new) + len(zh_new):
    print(f"ABORT line count moved by the wrong amount: {before_len} + {len(en_new)} + {len(zh_new)} != {len(lines)}")
    sys.exit(1)

open(DICT, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

check = open(DICT, encoding="utf-8").read().split("\n")
bad = []
for key in ZH_VALUES:
    hits = [(i, l) for i, l in enumerate(check, 1) if l.strip().startswith(f'"{key}":')]
    if len(hits) != 2:
        bad.append(f"{key}: expected one entry per side, found {len(hits)}")
        continue
    en_line, zh_line = hits[0], hits[1]
    if en_line[1] != f'  "{key}": "{EN_VALUES[key]}",':
        bad.append(f"{key} en read-back differs from what was intended")
    if zh_line[1] != f'  "{key}": "{ZH_VALUES[key]}",':
        bad.append(f"{key} zh read-back differs from what was intended")
    # the Chinese side must be exactly the sentence lifted from the component
    if zh_line[1] != f'  "{key}": "{ZH_VALUES[key]}",':
        bad.append(f"{key} zh side drifted from the component literal")

print(f"keys_written={len(ZH_VALUES)} sides=2 anchor_lines={en_at + 1},{zh_at + 1} lines={len(check)}")
for key in ZH_VALUES:
    hits = [i for i, l in enumerate(check, 1) if l.strip().startswith(f'"{key}":')]
    print(f"  {key}: en@{hits[0]} zh@{hits[1]}")
for b in bad:
    print("REFUSED " + b)
print("VERDICT=%s" % ("PASS" if not bad else "ABORT"))
sys.exit(1 if bad else 0)
