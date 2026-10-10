# -*- coding: utf-8 -*-
"""路牌工甲: the ternary-with-one-CJK-literal counter, run against any repo I own.

The commander's ruler (`live_checks/_bilingual_count_r1.py`) executes inside his own integration
checkout, so a candidate branch that only exists in my repo cannot be measured with it without
writing into someone else's tree - which I don't do. This is the same judgment applied locally:
a ternary whose two arms are both string literals, exactly one of which contains CJK.

Calibration requirement: before any number from this file is quoted, it must reproduce the
commander's reading on the same generation. On tip ee8b9c6bb2 his ruler printed
`files=156 hits=318`; this one has to print the same two numbers or the delta is worthless.
"""

from __future__ import print_function

import re
import subprocess
import sys

REPO = sys.argv[1] if len(sys.argv) > 1 else "."
OLD = sys.argv[2]
NEW = sys.argv[3]

LIT = r'"(?:[^"\\]|\\.)*"'
TERN = re.compile(r"\?\s*" + LIT + r"\s*:\s*" + LIT, re.S)
CJK = re.compile(u"[㐀-䶿一-鿿豈-﫿]")
SUFFIX = (".ts", ".tsx")


def sh(args):
    p = subprocess.run(args, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        raise SystemExit("CODE_FAIL %s :: %s" % (args, p.stdout.decode("utf-8", "replace")[:200]))
    return p.stdout.decode("utf-8", "replace")


def count(sha):
    files = [f for f in sh(["git", "ls-tree", "-r", "--name-only", sha, "--", "frontend/src"]).splitlines()
             if f.endswith(SUFFIX)]
    if not files:
        raise SystemExit("NO_FILES at %s" % sha[:10])
    per = {}
    for f in files:
        blob = sh(["git", "show", "%s:%s" % (sha, f)])
        hits = 0
        for line in blob.splitlines():
            for m in TERN.finditer(line):
                arms = re.findall(LIT, m.group(0))
                if len(arms) == 2 and bool(CJK.search(arms[0])) != bool(CJK.search(arms[1])):
                    hits += 1
        if hits:
            per[f] = hits
    return per


old = count(sh(["git", "rev-parse", OLD]).strip())
new = count(sh(["git", "rev-parse", NEW]).strip())
fo, ho = len(old), sum(old.values())
fn, hn = len(new), sum(new.values())
if fo == 0 or fn == 0:
    raise SystemExit("ABORT 读数为零不可信：OLD 实读文件数 %d，NEW 实读文件数 %d" % (fo, fn))
print("OLD %s files=%d hits=%d" % (OLD[:10], fo, ho))
print("NEW %s files=%d hits=%d" % (NEW[:10], fn, hn))
print("DELTA %d (old-new)" % (ho - hn))
gone = [f for f in old if f not in new]
print("CLEARED_FILES %d" % len(gone))
for f in gone:
    print("CLEARED %d %s" % (old[f], f))
for f in sorted(new, key=lambda x: -new[x])[:6]:
    print("STILL %d %s" % (new[f], f))
