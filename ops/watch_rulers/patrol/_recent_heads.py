import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
L = io.open(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md", encoding="utf-8", errors="replace").read().split("\n")
pat = re.compile(r"^#{2,3}\s+(CMDR|ORD-\d+)?\s*(2026-\d\d-\d\d)\s*(\d\d)[:：]?(\d\d)?")
rows = []
for i, l in enumerate(L):
    if not l.startswith("### "):
        continue
    m = re.search(r"2026-(\d\d)-(\d\d)", l)
    t = re.search(r"\b(\d\d)[:：]?(\d\d)(?:\+08)?\b", l)
    if not m or not t:
        continue
    d = "%s-%s" % (m.group(1), m.group(2))
    hm = "%s:%s" % (t.group(1), t.group(2))
    if d == "09-29" and hm >= "02:00":
        rows.append((d + " " + hm, i + 1, l.strip()[:190]))
rows.sort()
print("09-29 02:00 之后的块头 %d 枚（按块头时间排）:" % len(rows))
for k, ln, h in rows:
    print("  [%s] :%d %s" % (k, ln, h))
