"""Fix the day attribution and settle the sibling-session question.

Pass 3 found 18,900 usage objects but bucketed every one as "nodate": the `usage` object sits on the
message, while `timestamp` sits on the enclosing JSONL record. So key the day off the record, count
each usage once.

The sibling (f498474a) reported near-identical totals to the commander with ZERO shared message
uuids. Two candidates: a fork that inherited the same history (=> its tokens are a copy, not extra
spend), or a genuinely parallel session that happens to be similar. Distinguish them by comparing the
user-turn text between the two files, since a fork replays the same sentences.
"""
import hashlib
import io
import json
import os
from collections import defaultdict

DIR = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
DAY = "2026-09-21"
FILES = {
    "494abfd7": "commander 包工头", "f498474a": "sibling",
    "8c66aa92": "lane C", "e345b9d6": "lane D", "dc19d662": "lane E",
    "8ccd71d8": "lane F", "c01d72a3": "lane B", "d291c9dc": "harness",
    "9baacb24": "hermes", "aad2d1f2": "HJ-P3", "1a986a24": "HJ-P1",
    "5ea3bedc": "AI scout", "848847ed": "reuse map", "d4b04a0f": "HJ-P2",
}


def usages(obj, out):
    if isinstance(obj, dict):
        u = obj.get("usage")
        if isinstance(u, dict) and any(k.endswith("_tokens") for k in u):
            out.append(u)
        for v in obj.values():
            usages(v, out)
    elif isinstance(obj, list):
        for v in obj:
            usages(v, out)


def texts(obj, role, out):
    if isinstance(obj, dict):
        if (obj.get("role") or obj.get("type")) == role:
            t = obj.get("text") or obj.get("content")
            if isinstance(t, str) and t.strip():
                out.append(t.strip()[:200])
        for v in obj.values():
            texts(v, role, out)
    elif isinstance(obj, list):
        for v in obj:
            texts(v, role, out)


per_day = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0, 0]))
user_turns = defaultdict(set)
rec_ts_field = defaultdict(int)
for sid, who in FILES.items():
    cand = [n for n in os.listdir(DIR) if n.startswith(sid) and n.endswith(".jsonl")]
    if not cand:
        continue
    with io.open(os.path.join(DIR, cand[0]), encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            us, ut = [], []
            usages(rec, us)
            texts(rec, "user", ut)
            for t in ut:
                user_turns[sid].add(hashlib.sha1(t.encode("utf-8")).hexdigest())
            if not us:
                continue
            # record-level timestamp is the day key
            ts = rec.get("timestamp") if isinstance(rec, dict) else None
            if isinstance(ts, str) and len(ts) >= 10:
                day = ts[:10]
                rec_ts_field["record-level"] += 1
            else:
                m = [t for t in (rec.get("time"), rec.get("createdAt"), rec.get("ts"))
                     if isinstance(t, str)]
                day = m[0][:10] if m else "nodate"
                rec_ts_field["fallback:" + ("found" if m else "none")] += 1
            for u in us:
                r = per_day[sid][day]
                r[0] += int(u.get("input_tokens") or 0)
                r[1] += int(u.get("cache_creation_input_tokens") or 0)
                r[2] += int(u.get("cache_read_input_tokens") or 0)
                r[3] += int(u.get("output_tokens") or 0)
                r[4] += 1


def fmt(n):
    return f"{n/1e6:.1f}M" if n >= 1e6 else f"{n/1e3:.1f}k" if n >= 1e3 else f"{n:,}"


print("timestamp sources:", dict(rec_ts_field))
print(f"\n=== {DAY} by session ===")
print(f"{'session':<10}{'who':<17}{'calls':>7}{'fresh input':>12}{'cache write':>12}"
      f"{'cache read':>11}{'output':>9}{'total':>9}{'avg/call':>10}")
tot = [0, 0, 0, 0, 0]
for sid, who in FILES.items():
    d = per_day.get(sid, {}).get(DAY)
    if not d:
        continue
    a, b, c, o, r = d
    print(f"{sid:<10}{who:<17}{r:>7,}{fmt(a):>12}{fmt(b):>12}{fmt(c):>11}{fmt(o):>9}"
          f"{fmt(a+b+c+o):>9}{(a+b+c+o)//max(1,r):>10,}")
    for i, v in enumerate(d):
        tot[i] += v
print(f"{'TOTAL':<10}{'':<16}{tot[4]:>7,}{fmt(tot[0]):>12}{fmt(tot[1]):>12}"
      f"{fmt(tot[2]):>11}{fmt(tot[3]):>9}{fmt(sum(tot[:4])):>9}")

cm, sb = user_turns["494abfd7"], user_turns["f498474a"]
inter = cm & sb
print("\n=== is the sibling a fork of the commander? ===")
print(f"commander user-turns {len(cm)} | sibling {len(sb)} | shared {len(inter)} "
      f"({len(inter)/max(1,len(sb)):.0%} of sibling, {len(inter)/max(1,len(cm)):.0%} of commander)")
for sid in ("8c66aa92", "e345b9d6"):
    s = user_turns[sid]
    print(f"  lane {sid}: {len(s & cm)} shared with commander of {len(s)}")
print("\nhistory span (all days, commander):")
for day in sorted(per_day.get("494abfd7", {})):
    a, b, c, o, r = per_day["494abfd7"][day]
    print(f"  {day}  calls {r:>6,}  total {fmt(a+b+c+o):>8}")
