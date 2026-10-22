"""Make a private phone-chain store from the shared preview database, read-only on the source side.

The preview database is somebody else's running demo; the walk writes (imports, check-ins), so it can only
ever run against a copy.  The copy is taken with sqlite3's backup API over a `mode=ro` connection, and the
source's size and mtime are re-statted afterwards: if the read-only open somehow wrote, this refuses.
"""
import os
import sqlite3
import sys

SRC = r"D:/moodle/_qoder_preview_20260920/_preview.db"


def main():
    dst = sys.argv[1]
    for suffix in ("", "-wal", "-shm"):
        p = dst + suffix
        if os.path.exists(p):
            os.remove(p)
    before = os.stat(SRC)
    src = sqlite3.connect("file:" + SRC.replace(os.sep, "/") + "?mode=ro", uri=True)
    dst_conn = sqlite3.connect(dst)
    src.backup(dst_conn)
    dst_conn.commit()
    dst_conn.close()
    src.close()
    after = os.stat(SRC)
    if (before.st_size, int(before.st_mtime)) != (after.st_size, int(after.st_mtime)):
        raise SystemExit("ABORT_SOURCE_MOVED size=%s->%s mtime=%s->%s"
                         % (before.st_size, after.st_size, before.st_mtime, after.st_mtime))
    rows = {}
    c = sqlite3.connect("file:" + dst.replace(os.sep, "/") + "?mode=ro", uri=True)
    for table, col in (("places", "city_code"), ("journeys", "city_code")):
        try:
            rows[table] = sorted({r[0] for r in c.execute("select %s from %s" % (col, table))})
        except Exception as e:
            rows[table] = "QUERY_FAILED " + str(e)[:60]
    n = list(c.execute("select count(*) from places"))[0][0]
    c.close()
    print("copy_bytes=%d source_bytes=%d source_mtime_unchanged=True places=%d codes=%s"
          % (os.path.getsize(dst), after.st_size, n, rows))


if __name__ == "__main__":
    main()
