"""Full text of the newest assistant messages for two lanes (map's suspicion + 道0370's live state)."""
import glob
import io
import json
import os
import sys

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
want = sys.argv[1] if len(sys.argv) > 1 else "3b65af59"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
p = sorted(glob.glob(os.path.join(BASE, want + "*.jsonl")), key=os.path.getmtime)[-1]
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
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        t = (" ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
             if isinstance(c, list) else (c if isinstance(c, str) else ""))
        if (t or "").strip():
            recs.append((d.get("timestamp") or "", t.strip()))
print("file=%s assistant-texts=%d  size=%d" % (os.path.basename(p), len(recs), os.path.getsize(p)))
for ts, t in recs[-n:]:
    print("\n--- %s (%d ch)" % (ts[:19], len(t)))
    print(t[:1600])
