"""What are the last user records in map's and 道0370's transcripts?

The 20:01 knocks to these two returned messageSent but do not appear as user records, while the knocks to the
cold lanes (S4/N3/0388) do. This prints the tail of each transcript's user turns (timestamp, first 90 chars,
whether the closing line is present) so "queued vs delivered vs lost" is read from the file, not assumed.
"""
import glob
import io
import json
import os
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
CLOSING = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read().decode("utf-8").strip()

for id8, nm in (("3b65af59", "map"), ("e4f3490f", "道0370"), ("904a042d", "Q")):
    g = sorted(glob.glob(os.path.join(BASE, id8 + "*.jsonl")), key=os.path.getmtime)
    p = g[-1]
    recs = []
    with io.open(p, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            m = d.get("message") or {}
            role = m.get("role")
            c = m.get("content")
            t = (" ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
                 if isinstance(c, list) else (c if isinstance(c, str) else ""))
            if role in ("user", "assistant") and (t or "").strip():
                recs.append((d.get("timestamp") or "", role, t.strip()))
    print("== %s %s  file=%s  size=%d  mtime=%s  text-records=%d" % (
        nm, id8, os.path.basename(p)[:12], os.path.getsize(p),
        time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(p))), len(recs)))
    for ts, role, t in recs[-6:]:
        mark = "CLOSING-OK" if CLOSING in t else ""
        print("   %s %-9s %5d ch  %s  %s" % (ts[:19], role, len(t), mark, t[:90].replace("\n", " ")))
    print()
