"""ORD-0410 lane: snapshot the preview DB read-only into a lane-private copy.

The source is opened `mode=ro` and only ever touched through sqlite's backup API, because
`_preview.db` is written continuously and a file copy can land mid-transaction.
"""
import json
import os
import sqlite3

SRC = "D:/moodle/_qoder_preview_20260920/_preview.db"
DST = "D:/moodle/_qoder_r_ord0410/run/_r_ord0410.db"

src = sqlite3.connect(f"file:{SRC}?mode=ro", uri=True)
dst = sqlite3.connect(DST)
src.backup(dst)
dst.commit()

cur = dst.cursor()
tables = [r[0] for r in cur.execute(
    "select name from sqlite_master where type='table' order by name")]
out = {"src_ro": True, "dst": DST, "dst_bytes": os.path.getsize(DST),
       "table_count": len(tables),
       "tables_like_leg_or_activity_or_journey": [
           t for t in tables
           if any(k in t.lower() for k in ("leg", "activity", "journey", "plan", "place"))]}
print(json.dumps(out, ensure_ascii=False, indent=1))
for t in out["tables_like_leg_or_activity_or_journey"]:
    print(f"{t} rows={cur.execute('select count(*) from ' + chr(34) + t + chr(34)).fetchone()[0]}")
dst.close()
src.close()
