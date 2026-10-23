"""Measure how many times each ledger heading was entered and how many of those are word-for-word identical.

Why: the relay block for one refused branch appeared 13 times in the shared ledger.  The live door (r2) has a
verbatim-duplicate guard, so either the copies were written by the older door, or they differ by a few
characters and slipped past a hash of the whole text.  Which of those it is decides the fix.
"""
import hashlib
import io
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
NEEDLE = sys.argv[1] if len(sys.argv) > 1 else "落地这一侧没回音"

lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").split("\n")
blocks = []          # (line_number, heading, [body lines])
current = None
for index, line in enumerate(lines, start=1):
    if line.startswith("### "):
        current = [index, line.strip(), []]
        blocks.append(current)
    elif current is not None and line.strip():
        current[2].append(line.strip())

by_heading = defaultdict(list)
for line_no, heading, body in blocks:
    if NEEDLE in heading:
        by_heading[heading].append((line_no, "\n".join(body)))

print("relay headings:", len(by_heading), "| relay blocks:", sum(len(v) for v in by_heading.values()))
for heading, copies in sorted(by_heading.items(), key=lambda kv: -len(kv[1]))[:6]:
    hashes = Counter(hashlib.sha256(body.encode("utf-8")).hexdigest()[:12] for _, body in copies)
    diffs = sorted({len(body) for _, body in copies})
    print("- copies=%d distinct_bodies=%d body_sizes=%s | %s" % (
        len(copies), len(hashes), diffs[:4], heading[:78]))
    print("    lines:", ",".join(str(n) for n, _ in copies[:14]))

# Also: the total block count and how many headings repeat at all.
head_count = Counter(h for _, h, _ in blocks)
repeat = [(h, c) for h, c in head_count.items() if c > 1]
print("ALL blocks:", len(blocks), "| headings seen more than once:", len(repeat))
for h, c in sorted(repeat, key=lambda kv: -kv[1])[:8]:
    print("   x%d  %s" % (c, h[:90]))
