# -*- coding: utf-8 -*-
"""Count the one-CJK-arm ternaries in one file at two commits, same instrument both sides."""

import re
import subprocess
import sys

PATH = "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx"
LIT = r'"(?:[^"\\]|\\.)*"'
TERN = re.compile(r"\?[ \t]*" + LIT + r"[ \t]*:[ \t]*" + LIT)
CJK = re.compile(u"[　-〿一-鿿豈-﫿]")
REPO = "D:/moodle/CityNexus"


def hits(sha):
    out = subprocess.run(["git", "show", "%s:%s" % (sha, PATH)], cwd=REPO,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    text = out.stdout.decode("utf-8", "replace")
    found = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in TERN.finditer(line):
            arms = re.findall(LIT, m.group(0))
            if len(arms) == 2 and bool(CJK.search(arms[0])) != bool(CJK.search(arms[1])):
                found.append((i, line.strip()[:70]))
    return found


before = hits(sys.argv[1])
after = hits(sys.argv[2])
print("instrument regex arms=%d, one-CJK rule" % 2)
print("BEFORE %s 命中 %d 处: %s" % (sys.argv[1][:10], len(before), before))
print("AFTER  %s 命中 %d 处: %s" % (sys.argv[2][:10], len(after), after))
print("both_arms_produced_readings: %s" % (len(before) > 0))
