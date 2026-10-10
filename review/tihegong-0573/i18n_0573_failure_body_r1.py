#!/usr/bin/env python
"""ORD-0573 lane gate, the three plain quoted body arms moved onto lib.failureAttribution.* keys.

Nothing is hand-typed: each arm's Chinese and English bytes are cut out of the exact two lines read
off the authoritative tip with `git show`, then compared character-for-character against the two
dictionary entries this branch adds. A third arm proves the old arm bytes are gone from the product
file and that every line the branch touched belongs to a declared region.

Usage (cwd anywhere, paths derive from this file):
    python i18n_0573_failure_body_r1.py
    python i18n_0573_failure_body_r1.py --tip <40-hex>
    python i18n_0573_failure_body_r1.py --negative
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("CNX_LANE_ROOT") or os.path.dirname(os.path.dirname(HERE))
PRODUCT = "frontend/src/lib/failureAttribution.ts"
DICT = "frontend/src/i18n/LocaleContext.tsx"
TIP = "3085e1c05c54d4d9fdb55cfd01b7dd664b93c28c"

# (tip line of the Chinese arm, tip line of the English arm, key, tip lines this region may touch)
ITEMS = [
    (473, 474, "lib.failureAttribution.networkCopyStillReadable", {470, 471, 472, 473, 474, 475, 476, 477, 478}),
    (476, 477, "lib.failureAttribution.networkNoOfflineCopy", {470, 471, 472, 473, 474, 475, 476, 477, 478}),
    (588, 589, "lib.failureAttribution.readCauseNotClassified", {585, 586, 587, 588, 589, 590, 591, 592, 593}),
]

ZH_ARM = re.compile(r'^\? "(?P<v>.*)",?$')
EN_ARM = re.compile(r'^: "(?P<v>.*)",?$')
READS = re.compile(r'^titleOf\("(?P<key>[^"]*)"\),?$')
ENTRY = re.compile(r'^  "(?P<key>[^"]*)": "(?P<val>.*)",$')


def git_show(rev, path):
    out = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{path}"],
                         capture_output=True, check=True)
    return out.stdout.decode("utf-8").split("\n")


def tree_lines(rel):
    with open(os.path.join(ROOT, *rel.split("/")), "r", encoding="utf-8", newline="") as fh:
        return fh.read().split("\n")


def dict_entries(lines):
    block, found = None, {}
    for i, line in enumerate(lines):
        if line.startswith("const en: Dict = {"):
            block = "en"
        elif line.startswith("const zhCN: Dict = {"):
            block = "zh-CN"
        elif block and line.startswith("};"):
            block = None
        elif block:
            m = ENTRY.match(line)
            if m:
                found.setdefault(m.group("key"), {})[block] = (m.group("val"), i + 1)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tip", default=TIP)
    ap.add_argument("--negative", action="store_true")
    args = ap.parse_args()

    tip = git_show(args.tip, PRODUCT)
    now = tree_lines(PRODUCT)
    entries = dict_entries(tree_lines(DICT))

    fails, readings = [], []
    for zh_no, en_no, key, region in ITEMS:
        zh_m = ZH_ARM.match(tip[zh_no - 1].strip())
        en_m = EN_ARM.match(tip[en_no - 1].strip())
        if not zh_m or not en_m:
            fails.append(f"{key}: tip lines {zh_no}/{en_no} are not a quoted zh/en arm pair")
            continue
        want = {"zh-CN": zh_m.group("v"), "en": en_m.group("v")}
        got = entries.get(key)
        if not got:
            fails.append(f"{key}: no entry in {DICT}")
            continue
        for block in ("zh-CN", "en"):
            expect = want[block]
            if args.negative and block == "en":
                expect = expect[:-1] + "\u0000"
            if block not in got:
                fails.append(f"{key}: {block} side missing")
            elif got[block][0] != expect:
                fails.append(f"{key}: {block} side reads {got[block][0][:40]!r} at line {got[block][1]}, "
                             f"tip arm reads {expect[:40]!r}")
        hits = [i + 1 for i, line in enumerate(now)
                if 'titleOf("' in line and key in line]
        if len(hits) != 1:
            fails.append(f"{key}: read on {len(hits)} product line(s), expected exactly 1")
        for lineno in (zh_no, en_no):
            if tip[lineno - 1].strip() in [l.strip() for l in now]:
                fails.append(f"{key}: tip line {lineno} arm bytes still present in {PRODUCT}")
        readings.append(f"{key}: tip zh:{zh_no} en:{en_no} -> product:{hits[0] if hits else 0}, "
                        f"dict zh-CN:{got.get('zh-CN', (None, 0))[1]} en:{got.get('en', (None, 0))[1]}")

    allowed_tip = set()
    for _, _, _, region in ITEMS:
        allowed_tip |= region
    import difflib
    changed_tip, added_now = set(), set()
    for tag, a1, a2, b1, b2 in difflib.SequenceMatcher(None, tip, now).get_opcodes():
        if tag == "equal":
            continue
        changed_tip.update(range(a1 + 1, a2 + 1))
        added_now.update(range(b1 + 1, b2 + 1))
    outside = changed_tip - allowed_tip
    if outside:
        fails.append(f"tip lines changed outside the declared regions: {sorted(outside)[:8]}")
    reads_now = {i + 1 for i, line in enumerate(now) if 'titleOf("lib.failureAttribution' in line}
    if not (added_now & reads_now):
        fails.append("none of the new titleOf reads landed in this file")

    print(f"items={len(ITEMS)} changed_tip_lines={sorted(changed_tip)[:12]}")
    for r in readings:
        print("  " + r)
    if fails:
        print("RED")
        for f in fails:
            print("  - " + f)
        return 1
    if args.negative:
        print("GREEN under --negative -- the gate is blind")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
