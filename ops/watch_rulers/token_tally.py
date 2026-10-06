"""Sum real token usage out of Qoder transcript JSONL for the commander session (and the lanes).

The transcripts carry an assistant-message `usage` object with input / cache_creation /
cache_read / output tokens, so this is measured, not estimated. Lines are bucketed by their own
timestamp so a multi-day session only counts today.
"""
import glob
import io
import os
import re
from collections import defaultdict

DIR = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
USAGE = re.compile(r'"input_tokens":(\d+),"cache_creation_input_tokens":(\d+),'
                   r'"cache_read_input_tokens":(\d+),"output_tokens":(\d+)')
TS = re.compile(r'"timestamp":"(2026-\d\d-\d\d)')
CMD = "494abfd7-5a79-4cc1-8487-e873818a2db3"

per_day = defaultdict(lambda: [0, 0, 0, 0, 0])   # inp, cache_create, cache_read, out, records
per_file_today = defaultdict(lambda: [0, 0, 0, 0])
names = {
    CMD: "commander 包工头",
    "8c66aa92": "lane C backend",
    "e345b9d6": "lane D frontend",
    "dc19d662": "lane E red team",
    "8ccd71d8": "lane F gates",
    "c01d72a3": "lane B providers",
    "d291c9dc": "harness lane",
    "9baacb24": "hermes lane",
    "aad2d1f2": "HJ-P3",
    "1a986a24": "HJ-P1",
    "5ea3bedc": "AI scout",
    "848847ed": "reuse map",
    "6af4cf53": "misc",
    "f498474a": "unknown-large",
}

for path in glob.glob(os.path.join(DIR, "*.jsonl")):
    sid = os.path.basename(path)[:8]
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = USAGE.search(line)
            if not m:
                continue
            day = TS.search(line)
            day = day.group(1) if day else "??"
            vals = [int(x) for x in m.groups()]
            d = per_day[day]
            for i in range(4):
                d[i] += vals[i]
            d[4] += 1
            if day == "2026-09-21":
                p = per_file_today[sid]
                for i in range(4):
                    p[i] += vals[i]

def fmt(n):
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.2f} B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f} M"
    return f"{n:,}"

print("=== per day, all sessions in this project ===")
print(f"{'date':<12}{'input':>10}{'cache_write':>13}{'cache_read':>13}{'output':>10}{'records':>9}{'total ctx':>13}")
tot = [0, 0, 0, 0]
for day in sorted(per_day):
    a, b, c, o, r = per_day[day]
    print(f"{day:<12}{fmt(a):>10}{fmt(b):>13}{fmt(c):>13}{fmt(o):>10}{r:>9,}{fmt(a+b+c+o):>13}")
    if day == "2026-09-21":
        tot = [a, b, c, o]

print("\n=== today by session ===")
print(f"{'session':<10}{'who':<20}{'input':>10}{'cache_write':>13}{'cache_read':>13}{'output':>10}{'grand total':>13}")
rows = sorted(per_file_today.items(), key=lambda kv: -sum(kv[1]))
for sid, (a, b, c, o) in rows:
    if a + b + c + o == 0:
        continue
    print(f"{sid:<10}{names.get(sid,'') :<20}{fmt(a):>10}{fmt(b):>13}{fmt(c):>13}{fmt(o):>10}{fmt(a+b+c+o):>13}")

ca, cb, cc, co = per_file_today.get(CMD[:8], [0, 0, 0, 0])
print(f"\ncommander only: input {ca:,} + cache_write {cb:,} + cache_read {cc:,} = "
      f"prompt side {ca+cb+cc:,}; output {co:,}; grand {ca+cb+cc+co:,}")
print(f"share of today's project total: {(ca+cb+cc+co)/max(1,sum(tot)):.1%}")
