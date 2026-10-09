"""Third pass at reading token usage - parse JSON properly, one usage per assistant message, deduped by uuid.

Both earlier passes are untrustworthy and this file says why:
  pass 1 summed a fixed 4-key regex over whole lines and got identical totals for two unrelated
         sessions (0 shared uuids) - impossible unless each line replays history and every replay
         was added again;
  pass 2 found zero matches in the lane files, so their `usage` objects are not in that key order.
So: load each line as JSON, walk its objects, take `usage` only where the record carries one,
key on the message uuid so a replayed history counts once, and bucket by that message's timestamp.
"""
import io
import json
import os
from collections import defaultdict

DIR = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
FILES = {
    "494abfd7": "commander 包工头",
    "f498474a": "sibling session",
    "8c66aa92": "lane C", "e345b9d6": "lane D", "dc19d662": "lane E",
    "8ccd71d8": "lane F", "c01d72a3": "lane B", "d291c9dc": "harness",
    "9baacb24": "hermes", "aad2d1f2": "HJ-P3", "1a986a24": "HJ-P1",
}
DAY = "2026-09-21"


def walk(obj, out):
    if isinstance(obj, dict):
        u = obj.get("usage")
        if isinstance(u, dict) and any(k.endswith("_tokens") for k in u):
            out.append((obj.get("uuid") or obj.get("id"),
                        obj.get("timestamp") or obj.get("createdAt") or obj.get("created_at"),
                        u, obj.get("role") or obj.get("type")))
        for v in obj.values():
            walk(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, out)


seen = set()
rows = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0, 0]))
keys_seen = defaultdict(int)
dupes = defaultdict(int)
noparent = defaultdict(int)
lines_wo_usage = defaultdict(int)

for sid, who in FILES.items():
    cand = [n for n in os.listdir(DIR) if n.startswith(sid) and n.endswith(".jsonl")]
    if not cand:
        print(f"!! no jsonl for {sid}")
        continue
    with io.open(os.path.join(DIR, cand[0]), encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or '"input_tokens"' not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                noparent[sid] += 1
                continue
            found = []
            walk(rec, found)
            if not found:
                lines_wo_usage[sid] += 1
            for uuid, ts, usage, role in found:
                keys_seen[",".join(sorted(k for k in usage if k.endswith("_tokens")))] += 1
                d = ts[:10] if isinstance(ts, str) and len(ts) >= 10 else "nodate"
                k = (sid, uuid, d)
                if k in seen:
                    dupes[sid] += 1
                    continue
                seen.add(k)
                r = rows[sid][d]
                r[0] += int(usage.get("input_tokens") or 0)
                r[1] += int(usage.get("cache_creation_input_tokens") or 0)
                r[2] += int(usage.get("cache_read_input_tokens") or 0)
                r[3] += int(usage.get("output_tokens") or 0)
                r[4] += 1


def fmt(n):
    return f"{n/1e6:.1f}M" if n >= 1e6 else f"{n:,}"


print("=== usage-object shapes encountered ===")
for k, v in sorted(keys_seen.items(), key=lambda kv: -kv[1])[:5]:
    print(f"  {v:>6,}x  {k}")
print("unparseable lines:", dict(noparent) or 0, "| lines with the key but no usage obj:",
      dict(lines_wo_usage) or 0, "| dedup hits:", dict(dupes) or 0)

print(f"\n=== per session, {DAY} (and neighbours) ===")
print(f"{'session':<10}{'who':<18}{'date':<12}{'calls':>7}{'input':>9}{'cache_wrt':>10}"
      f"{'cache_read':>11}{'output':>10}{'total':>9}{'avg/call':>10}")
today = {}
for sid in FILES:
    for d in sorted(rows.get(sid, {})):
        a, b, c, o, r = rows[sid][d]
        if d not in (DAY, "2026-09-20"):
            continue
        print(f"{sid:<10}{FILES[sid]:<18}{d:<12}{r:>7,}{fmt(a):>9}{fmt(b):>10}{fmt(c):>11}"
              f"{o:>10,}{fmt(a+b+c+o):>9}{(a+b+c+o)//max(1,r):>10,}")
        if d == DAY:
            today[sid] = (a, b, c, o, r)

ta = sum(v[0] for v in today.values())
tb = sum(v[1] for v in today.values())
tc = sum(v[2] for v in today.values())
to = sum(v[3] for v in today.values())
tr = sum(v[4] for v in today.values())
print(f"\nALL listed sessions today: calls {tr:,}  input {fmt(ta)}  cache_write {fmt(tb)}  "
      f"cache_read {fmt(tc)}  output {to:,}  total {fmt(ta+tb+tc+to)}")
c = today.get("494abfd7")
if c:
    print(f"commander today: calls {c[4]:,} | fresh input {fmt(c[0])} | cache read {fmt(c[2])} | "
          f"output {c[3]:,} | total {fmt(c[0]+c[1]+c[2]+c[3])} | avg/call "
          f"{(c[0]+c[1]+c[2]+c[3])//max(1,c[4]):,}")
    print(f"commander share of listed sessions today: "
          f"{(c[0]+c[1]+c[2]+c[3])/max(1,ta+tb+tc+to):.1%}")
