"""ORD-0485 lane tool: make a private SQLite copy of the shared preview DB.

The shared file is opened with uri mode=ro only; the copy is written with
Connection.backup() so the commit point is well defined (a bare file copy
leaves the -wal half-written). Before and after, the shared file's size and
mtime are read back and compared, which is the proof that this lane did not
touch the user's stage.
"""
import json
import os
import sqlite3
import sys
import time

SHARED = r"D:\moodle\_qoder_preview_20260920\_preview.db"
MINE = r"D:\moodle\_qoder_phone_ord0485_20260930\run\phone_ord0485.db"

TABLES = [
    "journeys",
    "travelers",
    "plan_versions",
    "activities",
    "bookings",
    "commitments",
    "journey_checkins",
    "share_grants",
]


def stamp(path):
    st = os.stat(path)
    return {"bytes": st.st_size, "mtime_ns": st.st_mtime_ns,
            "mtime_local": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))}


def counts(db):
    out = {}
    con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
    try:
        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for t in TABLES:
            if t in have:
                out[t] = con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
            else:
                out[t] = "TABLE_ABSENT"
        out["journey_rows"] = [
            list(r) for r in con.execute(
                "SELECT id, city_code, title, status FROM journeys ORDER BY created_at")
        ] if "journeys" in have else []
    finally:
        con.close()
    return out


def main():
    if os.path.exists(MINE):
        os.remove(MINE)
    before = stamp(SHARED)
    src = sqlite3.connect("file:%s?mode=ro" % SHARED.replace("\\", "/"), uri=True)
    dst = sqlite3.connect(MINE)
    src.backup(dst)
    dst.commit()
    dst.close()
    src.close()
    after = stamp(SHARED)
    result = {
        "shared_before": before,
        "shared_after": after,
        "shared_untouched": before == after,
        "copy": stamp(MINE),
        "copy_counts": counts(MINE),
        "shared_counts_after": counts(SHARED),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["shared_untouched"] else 3


if __name__ == "__main__":
    sys.exit(main())
