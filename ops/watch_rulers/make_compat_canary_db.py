"""Make the compat-canary DB: consistent backup of the pinned preview DB, read-only source."""
import os
import sqlite3

SRC = r"D:\moodle\_qoder_cmdr_gate_20260921\backend\_live.db"
DST = r"D:\moodle\_qoder_cmdr_canary_0923\_compat.db"
os.makedirs(os.path.dirname(DST), exist_ok=True)
if os.path.exists(DST):
    raise SystemExit(f"REFUSE: destination already exists {DST}")

src = sqlite3.connect(f"file:{SRC}?mode=ro", uri=True)
src.execute("PRAGMA query_only=1")
dst = sqlite3.connect(DST)
src.backup(dst)
src.close()
dst.commit()

cur = dst.cursor()
counts = {}
for t in ("journeys", "travelers", "plan_versions", "places", "city_services"):
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    counts[t] = cur.fetchone()[0]
print("copy counts:", counts)
cur.execute("SELECT id, city_code, status FROM journeys ORDER BY updated_at DESC")
for r in cur.fetchall():
    print("  journey", r[0][:8], r[1], r[2])
print("dst bytes", os.path.getsize(DST))
dst.close()
