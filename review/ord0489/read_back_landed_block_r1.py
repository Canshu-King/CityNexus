"""ORD-0489 erratum support · read back the block that already landed and print what its anchors
actually point at, so the correction names the wrong lines from the artifact rather than memory.

Only anchors whose line cannot carry the claim are listed: the line is structural (`{`, `}`, `[`)
or is an unrelated statement (an import, an mtime) while the sentence asks for a count.
"""

import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WT = "D:/moodle/_qoder_seed_ord0489/wt"
OLD = Path("D:/moodle/_qoder_ledger_inbox/_processed/seed_1323.md.inserted_142228")
ANCHOR = re.compile(r"`(review/[^`]+|tools/[^`]+):(\d+)`")

CACHE: dict[str, list[str]] = {}


def lines_of(rel: str) -> list[str]:
    if rel not in CACHE:
        out = subprocess.run(["git", "-C", WT, "show", "HEAD:" + rel], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        CACHE[rel] = out.splitlines()
    return CACHE[rel]


structural = re.compile(r"^[\[\]{}(),]+\s*$")
rows = []
text = OLD.read_text(encoding="utf-8", errors="replace")
for number, line in enumerate(text.splitlines(), 1):
    for match in ANCHOR.finditer(line):
        rel, target = match.group(1), int(match.group(2))
        txt = lines_of(rel)
        if not (1 <= target <= len(txt)):
            rows.append((number, rel, target, "OUT_OF_RANGE", ""))
            continue
        row = txt[target - 1].strip()
        claim = re.findall(r"\d{2,6}", line.split(match.group(0))[0].split("`")[-1])
        if structural.match(row) or ("import " in row) or ("mtime_utc" in row and "7213056" not in row):
            rows.append((number, rel, target, "LINE_IS_STRUCTURAL_OR_UNRELATED", row[:60]))
        elif claim and not any(c in row for c in claim):
            rows.append((number, rel, target, "CLAIM_NOT_ON_LINE", row[:60]))
print("old_block_lines", len(text.splitlines()), "bad_anchors", len(rows))
for r in rows:
    print(" | ".join(str(x) for x in r))
