# -*- coding: utf-8 -*-
"""Pre-image on THIS generation: what the authoritative tip's own bytes say for the three counted lines.

The earlier blocks proved the pre-image by walking an old tree in a browser. That is no longer the honest
way to state it: the tip still carries all three inline templates, so the pre-image is read out of the tip
itself with `git show <tip>:<path>` and the grep hits are the receipt. The fixed forms are read out of the
shipped branch the same way, so both sides of the comparison come from published bytes rather than memory.
"""

import io
import os
import re
import subprocess

REPO = r"D:/moodle/CityNexus"
PATH = "frontend/src/app/V8Experience.tsx"
TIP = "aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f"
OUT = r"D:/moodle/_ord0568_r3/r7/preimage_on_tip_r7.txt"

env = dict(os.environ)
for gone in ("HTTP_PROXY", "HTTPS_PROXY"):
    env.pop(gone, None)


def remote_head(ref):
    row = subprocess.run(["git", "-C", REPO, "ls-remote", "--refs", "origin", ref],
                         capture_output=True, env=env).stdout.decode().split()
    assert row and len(row[0]) == 40, "no head read back for " + ref
    return row[0]


SHIP = remote_head("refs/heads/review/cff87c64-ord0562-english-count-nouns-r6")


def show(ref):
    proc = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, PATH)],
                          capture_output=True, env=env)
    assert proc.returncode == 0, "git show failed for " + ref
    return proc.stdout.decode("utf-8", "replace").split("\n")


TIP_PATTERNS = [
    ("budget advisory, one traveller reads `1 people`", re.compile(r"\$\{days\} days · \$\{people\} people")),
    ("hub day line, one day reads `1 days`", re.compile(r"\$\{tripDayCount\} days")),
    ("attention line, one change reads `1 change(s)`", re.compile(r"change\(s\)")),
]
MINE_PATTERNS = [
    ("budget advisory goes through the counted key", re.compile(r't\("hub\.budgetLine", \{ days, people, amount \}\)')),
    ("hub day line goes through the counted key", re.compile(r't\("hub\.todayDays", \{ n: tripDayCount \}\)')),
    ("attention line goes through the helper", re.compile(r'englishCountNoun\(disruptions\.length, "change"\)')),
]

lines = ["Pre-image and post-image read from published bytes of the same file, %s" % PATH]
for label, ref in (("TIP (pre-image)", TIP), ("SHIPPED BRANCH (post-image)", SHIP)):
    body = show(ref)
    patterns = TIP_PATTERNS if ref == TIP else MINE_PATTERNS
    lines.append("")
    lines.append("$ git -C D:/moodle/CityNexus show %s:%s" % (ref, PATH))
    for name, rx in patterns:
        hits = [i + 1 for i, line in enumerate(body) if rx.search(line)]
        assert len(hits) == 1, "%s: %r matched %d lines, wanted exactly 1" % (label, name, len(hits))
        lines.append("  %s -> line %d: %s" % (name, hits[0], body[hits[0] - 1].strip()))
        lines.append("    anchor: %s:%d" % (PATH, hits[0]))

text = "\n".join(lines) + "\n"
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)
print(text)
print("OK: every pattern matched exactly one line on its side")
