"""ORD-0417 snap stack: make a private, writable copy of the shared preview database.

The shared `D:/moodle/_qoder_preview_20260920/_preview.db` is the user's; this opens it read-only and
uses the online-backup API so the copy is a consistent snapshot rather than a file copy of a live
WAL.  Nothing here writes to the source.
"""
import sqlite3
import sys

SRC = r"D:/moodle/_qoder_preview_20260920/_preview.db"
DST = sys.argv[1]

src = sqlite3.connect(f"file:{SRC}?mode=ro", uri=True, timeout=30)
try:
    n = src.execute("select count(*) from journeys").fetchone()[0]
    ids = [r[0] for r in src.execute("select id from journeys order by id").fetchall()]
    dst = sqlite3.connect(DST)
    src.backup(dst)
    dst.commit()
    got = dst.execute("select count(*) from journeys").fetchone()[0]
    mtime = src.execute("pragma data_version").fetchone()[0]
    print(f"source journeys={n} copied={got} data_version={mtime}")
    print("journey ids:", ids[:6])
    dst.close()
finally:
    src.close()
