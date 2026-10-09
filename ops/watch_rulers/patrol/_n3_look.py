"""Print what actually landed in N3's transcript at 12:13 (17405 chars, no closing line)."""
import glob
import io
import json
import os

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
MARK = "relay_49fe0d7b_2008"
for p in sorted(glob.glob(os.path.join(BASE, "49fe0d7b*.jsonl"))):
    with io.open(p, encoding="utf-8", errors="replace") as f:
        for i, rec in enumerate(f):
            if MARK not in rec:
                continue
            try:
                d = json.loads(rec.strip())
            except Exception:
                print("line %d: unparseable record with marker" % i)
                continue
            m = d.get("message") or {}
            c = m.get("content")
            if isinstance(c, list):
                parts = [(x.get("type"), (x.get("text") or "")[:0]) for x in c if isinstance(x, dict)]
                t = " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
            else:
                parts = [(type(c).__name__, "")]
                t = c or ""
            print("file=%s line=%d role=%s ts=%s types=%s" % (
                os.path.basename(p)[:8], i, m.get("role"), d.get("timestamp"), parts[:6]))
            print("   chars=%d" % len(t))
            print("   HEAD>>> %s" % t[:260].replace("\n", " | "))
            print("   MARKER CONTEXT>>> %s" % t[max(0, t.find(MARK) - 300):t.find(MARK) + 300].replace("\n", " | "))
            print("   TAIL>>> %s" % t[-260:].replace("\n", " | "))
