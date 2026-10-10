#!/usr/bin/env python
"""ORD-0557 lane gate, the lib.failureAttribution.* keys this lane moved off lib/failureAttribution.ts.

The screen text must not move, so nothing here is hand-typed: the zh and en arms are cut out of the
exact ternary line read off the authoritative tip with `git show`, and after the move the two
dictionary entries are re-read off the working tree and compared character-for-character against that
same cut. A fourth arm lists every line the branch moved in that file and refuses any line outside the
titles plus the declared wiring.

Usage (cwd anywhere, paths derive from this file):
    python i18n_0557_failure_attribution_r1.py
    python i18n_0557_failure_attribution_r1.py --tip <40-hex>   # cut the arms off another generation
    python i18n_0557_failure_attribution_r1.py --negative       # a moved byte must go red
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
TIP = "996f1b7588580a14fbbdec5301a6e4a7b70c93e4"  # the line this branch was cut from; --tip overrides

# (tip line number, draft key name) -- names copied from _cn10_fb557draft_1155.txt, lines read off TIP.
ITEMS = [(457, "lib.failureAttribution.tripNotOnServer"),
         (465, "lib.failureAttribution.networkUnavailable"),
         (478, "lib.failureAttribution.serviceUnavailable"),
         (485, "lib.failureAttribution.serverCouldNotRead"),
         (518, "lib.failureAttribution.slowDownRate"),
         (530, "lib.failureAttribution.slowDownRetry"),
         (538, "lib.failureAttribution.stateAlreadyMoved"),
         (565, "lib.failureAttribution.needsFreshSignIn"),
         (573, "lib.failureAttribution.stepNotAllowed")]

TERNARY = re.compile(r'^title: zh \? "(?P<zh>[^"]*)" : "(?P<en>[^"]*)",$')
READS = re.compile(r'^title: titleOf\("(?P<key>[^"]*)"\),$')
ENTRY = re.compile(r'^  "(?P<key>[^"]*)": "(?P<val>.*)",$')
KEYS = {key for _, key in ITEMS}
WIRING = [
    "/* ORD-0557: the attribution titles below read the shared dictionary. This module is a plain function,",
    "   not a component, so it uses the non-hook lookup the dictionary exports -- same reason the label",
    "   accessor above is imported here. */",
    'import { dictionaryCopy } from "../i18n/LocaleContext";',
    '  const titleOf = (key: string) => dictionaryCopy(zh ? "zh-CN" : "en", key);',
]


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
    """Each dictionary entry on the working tree, with the arm it carries and its line number."""
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
    ap.add_argument("--tip", default=TIP, help="40-hex generation to cut the before-arms off")
    ap.add_argument("--negative", action="store_true",
                    help="shift one expected dictionary byte and require this gate goes red")
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
        hit = [i + 1 for i, line in enumerate(now_product) if key_of_read(line.strip()) == key]
        if len(hit) != 1:
            fails.append(f"{key}: read on {len(hit)} product line(s), expected exactly 1")
        if old in [line.strip() for line in now_product]:
            fails.append(f"{key}: the tip ternary is still in {PRODUCT}")
        readings.append(f"{key}: tip:{lineno} -> product:{hit[0] if hit else 0}, "
                        f"dict zh-CN:{got.get('zh-CN', (None, 0))[1]} en:{got.get('en', (None, 0))[1]}")

    moved, added = set(), set()
    for tag, a1, a2, b1, b2 in difflib.SequenceMatcher(None, tip_product, now_product).get_opcodes():
        if tag == "equal":
            continue
        moved.update(range(a1 + 1, a2 + 1))
        added.update(range(b1 + 1, b2 + 1))
    titles = {lineno for lineno, _ in ITEMS}
    wiring_lines = {i + 1 for i, line in enumerate(now_product) if line in WIRING}
    read_lines = {i + 1 for i, line in enumerate(now_product) if key_of_read(line.strip()) in KEYS}
    if len(wiring_lines) != len(WIRING):
        fails.append(f"declared wiring lines found on {len(wiring_lines)} line(s), expected {len(WIRING)}")
    stray = (moved - titles) | (added - wiring_lines - read_lines)
    if stray:
        fails.append(f"product lines outside the titles plus the declared wiring moved: {sorted(stray)}")
    if not (moved & titles):
        fails.append("none of the title lines changed -- the move did not land")

    print(f"items={len(ITEMS)} moved_tip_lines={sorted(moved)} added_lines={sorted(added)}")
    for r in readings:
        print("  " + r)
    if fails:
        print("RED")
        for f in fails:
            print("  - " + f)
        return 1
    if args.negative:
        print("GREEN under --negative -- the gate is blind, it should have gone red")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
