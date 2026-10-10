"""Commander-only token tally, plus a duplicate check on the suspicious sibling file.

Why: the first pass reported identical totals for 494abfd7 and f498474a, which is either a fork
sharing history (=> must not be summed twice) or a measurement artifact. Lane files also came out
of the "today" bucket empty, so the date key next to `usage` is not uniform across files - probe
the real shape instead of assuming one.
"""
import io
import json
import os
import re
from collections import Counter

DIR = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
USAGE = re.compile(r'"input_tokens":(\d+),"cache_creation_input_tokens":(\d+),'
                   r'"cache_read_input_tokens":(\d+),"output_tokens":(\d+)')
DATE = re.compile(r'"(timestamp|createdAt|created_at|time|ts)":"?(2026-\d\d-\d\d)')

FILES = {
    "494abfd7": "commander 包工头",
    "f498474a": "sibling (suspected fork)",
    "8c66aa92": "lane C", "e345b9d6": "lane D", "dc19d662": "lane E",
    "8ccd71d8": "lane F", "c01d72a3": "lane B", "d291c9dc": "harness",
    "9baacb24": "hermes", "6af4cf53": "misc",
}

stats = {}
msgids = {}
for sid, who in FILES.items():
    path = next((os.path.join(DIR, n) for n in os.listdir(DIR)
                 if n.startswith(sid) and n.endswith(".jsonl")), None)
    if not path:
        continue
    day_tot = {}
    ids = set()
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"input_tokens"' not in line:
                continue
            m = DATE.search(line)
            day = m.group(2) if m else "nodate"
            d = day_tot.setdefault(day, [0, 0, 0, 0, 0])
            for g, i in zip(USAGE.finditer(line), range(4)):
                pass
            us = USAGE.findall(line)
            for u in us:
                v = [int(x) for x in u]
                d[0] += v[0]; d[1] += v[1]; d[2] += v[2]; d[3] += v[3]
                d[4] += 1
            mid = re.search(r'"(uuid|id|messageId)":"([0-9a-f-]{20,})"', line)
            if mid:
                ids.add(mid.group(2))
    stats[sid] = (who, day_tot)
    msgids[sid] = ids

def fmt(n):
    return f"{n/1e6:.1f}M" if n >= 1e6 else f"{n:,}"

for sid, (who, dt) in stats.items():
    print(f"\n=== {sid} ({who}) ===")
    for day in sorted(dt):
        a, b, c, o, r = dt[day]
        print(f"  {day}  calls={r:>6,}  input={fmt(a):>7}  cache_read={fmt(c):>7} "
              f"output={o:>8,}  total={fmt(a+b+c+o):>7}  avg_call={(a+b+c+o)//max(1,r):,}")

base = stats.get("494abfd7", (None, {}))
sib = stats.get("f498474a", (None, {}))
print("\n=== duplicate check commander vs sibling ===")
print("shared message uuids:", len(msgids["494abfd7"] & msgids["f498474a"]),
      "| commander only:", len(msgids["494abfd7"] - msgids["f498474a"]),
      "| sibling only:", len(msgids["f498474a"] - msgids["494abfd7"]))
print("today rows identical?", base[1].get("2026-09-21") == sib[1].get("2026-09-21"))
