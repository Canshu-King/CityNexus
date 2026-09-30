"""ORD-0489 follow-up · audit every coordinate in the block that already landed.

The gate checks that a number and an anchor share a line; it cannot check that the line the anchor
names actually carries that number.  This does, by reading the object at HEAD and comparing.
"""

import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WT = "D:/moodle/_qoder_seed_ord0489/wt"
LEDGER = Path("D:/moodle/CITYNEXUS_AGENT_CONTROL.md")
HEAD = re.compile(r"^### ORD-0489 ", re.ASCII)
ANCHOR = re.compile(r"`(review/[^`]+|tools/[^`]+):(\d+)` blob `([0-9a-f]{40})`")

text = LEDGER.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()
start = next((i for i, l in enumerate(lines) if HEAD.match(l)), None)
if start is None:
    sys.exit("BLOCK_NOT_IN_LEDGER")
block = []
for line in lines[start:]:
    if block and line.startswith("### "):
        break
    block.append(line)

blob_cache: dict[str, tuple[str, list[str]]] = {}


def at(rel):
    if rel not in blob_cache:
        blob = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD:" + rel], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
        shown = subprocess.run(["git", "-C", WT, "show", "HEAD:" + rel], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        blob_cache[rel] = (blob, shown.splitlines())
    return blob_cache[rel]


problems = []
anchors = 0
for index, line in enumerate(block, 1):
    for match in ANCHOR.finditer(line):
        anchors += 1
        rel, number, blob = match.group(1), int(match.group(2)), match.group(3)
        real_blob, txt = at(rel)
        if real_blob != blob:
            problems.append(("BLOB", index, rel, number, blob[:10], real_blob[:10]))
            continue
        if not (1 <= number <= len(txt)):
            problems.append(("RANGE", index, rel, number, len(txt), ""))
            continue
        row = txt[number - 1]
        sentence = line.split("`" + rel)[0]
        wanted = [d for d in re.findall(r"\d+", sentence) if len(d) >= 1]
        # a number claimed in prose must be present on the line it is anchored to
        missing = [d for d in wanted if d not in row and d not in rel]
        if missing:
            problems.append(("NUMBER_NOT_ON_LINE", index, rel, number, ",".join(missing[:4]), row.strip()[:70]))

print(json_line := f"block_lines={len(block)} anchors={anchors} problems={len(problems)}")
for p in problems[:40]:
    print(" | ".join(str(x) for x in p))
