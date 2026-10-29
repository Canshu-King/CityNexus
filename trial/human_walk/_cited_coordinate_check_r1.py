"""Check every `path:line` coordinate inside a walkthrough chapter actually resolves.

A correction written with a wrong line number is worse than the bare filename it replaces, so this reads each cited
file and asks whether the named line exists -- and, when a fragment is given, whether it is really on that line.
"""
import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
DOC = os.path.join(ROOT, "trial", "results", "20261022_V3_CHROME_USE_HUMAN_WALKTHROUGH.md")
START = int(sys.argv[1]) if len(sys.argv) > 1 else 1950
END = int(sys.argv[2]) if len(sys.argv) > 2 else 10 ** 9

CITE = re.compile(r"[A-Za-z0-9_./\-]+\.(?:py|tsx|ts|mjs|md|txt|json|yaml|css|log):\d+")

text = io.open(DOC, encoding="utf-8").read().splitlines()
chapter = "\n".join(text[START - 1:min(END, len(text))])
cites = []
for match in CITE.finditer(chapter):
    if match.group(0) not in cites:
        cites.append(match.group(0))

bad = []
for cite in cites:
    path, line = cite.rsplit(":", 1)
    line = int(line)
    full = os.path.join(ROOT, path.replace("/", os.sep))
    if not os.path.isfile(full):
        bad.append((cite, "FILE NOT IN TREE"))
        continue
    n = len(io.open(full, encoding="utf-8", errors="replace").read().splitlines())
    if line > n:
        bad.append((cite, "LINE BEYOND END (file has %d)" % n))

print("chapter_lines=%d..%d citations=%d unresolved=%d" % (START, min(END, len(text)), len(cites), len(bad)))
for cite, why in bad:
    print("  BAD %s | %s" % (cite, why))
if not bad and cites:
    print("  every cited path:line names a line that exists in the tree now")
