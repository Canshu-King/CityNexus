# -*- coding: utf-8 -*-
"""Produce the fourth-generation receipts by adapting the third-generation generators in place.

Every adaptation is a named substitution, printed as it is made, so the reader can see exactly what changed
between the two generations' instruments instead of trusting that a copy was faithful.
"""

import io
import os

SRC = r"D:/moodle/_ord0568_r3/r7"
DST = r"D:/moodle/_ord0568_r3/r8"
os.makedirs(DST, exist_ok=True)

NEW_TIP = "8996eee4fb9fb4e159588305223ef421728c4e72"
OLD_TIP = "aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f"
NEW_BRANCH = "review/cff87c64-ord0562-english-count-nouns-r7"
OLD_BRANCH = "review/cff87c64-ord0562-english-count-nouns-r6"

JOBS = [
    ("readiness_at_delivery_r7.py", "readiness_at_delivery_r8.py", [
        (OLD_TIP, NEW_TIP), (OLD_BRANCH, NEW_BRANCH),
        (r"D:/moodle/_ord0568_r3/r7/", r"D:/moodle/_ord0568_r3/r8/"),
        ("readiness_r7.json", "readiness_r8.json"),
    ]),
    ("make_preimage_r7.py", "make_preimage_r8.py", [
        (OLD_TIP, NEW_TIP), (OLD_BRANCH, NEW_BRANCH),
        ("preimage_on_tip_r7.txt", "preimage_on_tip_r8.txt"),
    ]),
    ("make_head_loop_r7.py", "make_head_loop_r8.py", [
        (OLD_BRANCH, NEW_BRANCH), ("readiness_r7.json", "readiness_r8.json"),
        ("head_loop_r7.txt", "head_loop_r8.txt"),
    ]),
    ("make_screen_note_r7.py", "make_screen_note_r8.py", [
        (r"D:/moodle/_ord0568_r3/r7", r"D:/moodle/_ord0568_r3/r8"),
        ("stack_ORD0562prv3-", "stack_ORD0562prv4-"),
        ("_onscreen_r3c.json", "_onscreen_r4.json"),
        ("budget_party%s_r3.json", "budget_party%s_r4.json"),
        ("shape_one_day_r3.json", "shape_one_day_r4.json"),
        ("preimage_on_tip_r7.txt", "preimage_on_tip_r8.txt"),
        ("screen_reads_r7.txt", "screen_reads_r8.txt"),
        ("hub_one_day_onscreen_r3c.json", "hub_one_day_onscreen_r4.json"),
        ("hub_two_days_onscreen_r3c.json", "hub_two_days_onscreen_r4.json"),
    ]),
]

for src, dst, subs in JOBS:
    text = io.open(os.path.join(SRC, src), encoding="utf-8").read()
    print("=== %s -> %s" % (src, dst))
    for old, new in subs:
        if old not in text:
            print("    MISS %r (not present; nothing changed for it)" % old)
            continue
        text = text.replace(old, new)
        print("    %r -> %r" % (old, new))
    io.open(os.path.join(DST, dst), "w", encoding="utf-8", newline="\n").write(text)
print("done")
