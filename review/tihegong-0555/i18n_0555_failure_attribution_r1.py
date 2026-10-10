#!/usr/bin/env python
"""ORD-0555 lane gate, the failure.* keys of lib/failureAttribution.ts this lane moved (ITEMS).

The screen text must not move, so nothing here is hand-typed: the zh and en arms are cut out of the
exact ternary line read off the authoritative tip with `git show`, and after the move the two
dictionary entries are re-read off the working tree and compared character-for-character against
that same cut. A fourth arm lists every line the product branch moved in that file and refuses any
line outside the three titles plus the two wiring lines.

Usage (cwd anywhere, paths derive from this file):
    python i18n_0555_failure_attribution_r1.py
    python i18n_0555_failure_attribution_r1.py --tip <40-hex>   # cut the arms off another generation
    python i18n_0555_failure_attribution_r1.py --negative       # a moved byte must go red
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("CNX_LANE_ROOT") or os.path.dirname(os.path.dirname(HERE))
PRODUCT = "frontend/src/lib/failureAttribution.ts"
DICT = "frontend/src/i18n/LocaleContext.tsx"
TIP = "d435cff26df752908a8a3a58d5c61f9f5c23f40c"  # the line this branch was brought onto; --tip overrides

# (tip line number, new key) -- the line numbers are read off TIP, the names are the blessed ones.
ITEMS = [(454, "failure.thisTripIsNotOnThisServer"), (462, "failure.networkUnavailable"),
         (475, "failure.theServiceIsTemporarilyUnavailable"),
         (482, "failure.theServerCouldNotReadYourTrip")]

TERNARY = re.compile(r'^title: zh \? "(?P<zh>[^"]*)" : "(?P<en>[^"]*)",$')
READS = re.compile(r'^title: titleOf\("(?P<key>[^"]*)"\),$')
ENTRY = re.compile(r'^  "(?P<key>[^"]*)": "(?P<val>.*)",$')
KEYS = {key for _, key in ITEMS}
IMPORT_LINE = 'import { dictionaryCopy } from "../i18n/LocaleContext";'
HELPER_LINE = '  const titleOf = (key: string) => dictionaryCopy(zh ? "zh-CN" : "en", key);'


def key_of_read(stripped):
    m = READS.match(stripped)
    return m.group("key") if m else None


def git_show(rev, path):
    out = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{path}"],
                         capture_output=True, check=True)
    return out.stdout.decode("utf-8").split("\n")


def tree_lines(rel):
    path = os.path.join(ROOT, *rel.split("/"))
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read().split("\n")


def dict_entries(lines):
    """Each dictionary entry on the working tree, with the arms it carries and their line numbers."""
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
    ap.add_argument("--negative", action="store_true",
                    help="shift one expected dictionary byte and require this gate goes red")
    ap.add_argument("--tip", default=TIP, help="40-hex generation to cut the before-arms off")
    args = ap.parse_args()

    tip_product = git_show(args.tip, PRODUCT)
    now_product = tree_lines(PRODUCT)
    now_dict = dict_entries(tree_lines(DICT))

    fails, readings = [], []
    for lineno, key in ITEMS:
        old = tip_product[lineno - 1].strip()
        m = TERNARY.match(old)
        if not m:
            fails.append(f"{key}: tip line {lineno} is not a bilingual title ternary: {old[:70]!r}")
            continue
        arms = {"zh-CN": m.group("zh"), "en": m.group("en")}
        got = now_dict.get(key)
        if not got:
            fails.append(f"{key}: no entry in {DICT}")
            continue
        for block in ("zh-CN", "en"):
            want = arms[block]
            if args.negative and block == "en":
                want = want[:-1] + "\u0000"
            if block not in got:
                fails.append(f"{key}: {block} side missing from its dictionary")
            elif got[block][0] != want:
                fails.append(f"{key}: {block} side reads {got[block][0]!r} at line {got[block][1]}, "
                             f"tip ternary reads {want!r}")
        hit = [i + 1 for i, line in enumerate(now_product)
               if key_of_read(line.strip()) == key]
        if len(hit) != 1:
            fails.append(f"{key}: read on {len(hit)} product line(s), expected exactly 1")
        if old in [line.strip() for line in now_product]:
            fails.append(f"{key}: the tip ternary is still in {PRODUCT}")
        readings.append(f"{key}: tip:{lineno} -> product:{hit[0] if hit else 0}, "
                        f"dict zh-CN:{got.get('zh-CN', (None, 0))[1]} en:{got.get('en', (None, 0))[1]}")

    moved, added = set(), set()
    for op in difflib.SequenceMatcher(None, tip_product, now_product).get_opcodes():
        tag, a1, a2, b1, b2 = op
        if tag == "equal":
            continue
        moved.update(range(a1 + 1, a2 + 1))
        added.update(range(b1 + 1, b2 + 1))
    titles = {lineno for lineno, _ in ITEMS}
    wiring = {i + 1 for i, line in enumerate(now_product) if line in (IMPORT_LINE, HELPER_LINE)}
    reads = {i + 1 for i, line in enumerate(now_product) if key_of_read(line.strip()) in KEYS}
    stray = (moved - titles) | (added - wiring - reads)
    if stray:
        fails.append(f"product lines outside the three titles plus the wiring moved: {sorted(stray)}")
    if not (moved & titles):
        fails.append("none of the three title lines changed -- the move did not land")

    print(f"items={len(ITEMS)} moved_tip_lines={sorted(moved)} added_lines={sorted(added)}")
    for r in readings:
        print("  " + r)
    if fails:
        print("RED")
        for f in fails:
            print("  - " + f)
        return 1
    if args.negative:
        print("RED-EXPECTED? no -- negative control stayed GREEN, the gate is blind")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
