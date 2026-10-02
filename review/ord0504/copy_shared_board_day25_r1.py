"""ORD-0504 shared-recipe hand -- take a consistent copy of the day25 shared board into THIS lane.

The order asks whether the trip the shared stack shows also renders only server-true money. Answering
it must not write the shared store, and that store is being written right now (its -wal carries a
04:38 timestamp), so this follows the line's own recipe (`live_checks/make_compat_canary_db.py`):
open the source `mode=ro` with `PRAGMA query_only=1`, then use the sqlite online-backup API to produce
one consistent file inside this lane. The source is never opened read-write and never copied mid-page.

If a read-only open of a live WAL database cannot produce a consistent snapshot, this script says so
and stops -- it does not fall back to a plain file copy, which would grab a torn state.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

SRC = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_cmdr_canary_day25.db")
DST = Path("D:/moodle/_qoder_r_ord0465_20260929/run/ord0504_shared_day25_copy.db")

if DST.exists():
    raise SystemExit("REFUSE: destination already exists %s" % DST)
if not SRC.is_file():
    raise SystemExit("SOURCE-ABSENT %s" % SRC)

src = sqlite3.connect("file:%s?mode=ro" % SRC.as_posix(), uri=True)
src.execute("PRAGMA query_only=1")
# a read-only connection must be able to read the journal it is paired with, or the snapshot it
# produces is not the state the shared stack is actually serving
journal = src.execute("PRAGMA journal_mode").fetchone()[0]
print("source journal_mode as seen by the read-only connection:", journal)

dst = sqlite3.connect(str(DST))
src.backup(dst)
src.close()
dst.commit()

cur = dst.cursor()
counts = {}
for table in ("journeys", "travelers", "plan_versions", "journey_legs", "places", "bookings",
              "transport_reservations", "commitments", "activities"):
    try:
        cur.execute("SELECT COUNT(*) FROM %s" % table)
        counts[table] = cur.fetchone()[0]
    except sqlite3.Error as error:
        counts[table] = "NO-SUCH-TABLE %s" % error
print("copy counts:", counts)

cur.execute("SELECT id, city_code, status, title FROM journeys ORDER BY updated_at DESC")
rows = cur.fetchall()
money = {}
for journey_id, city, status, title in rows:
    one = {"city": city, "status": status, "title": (title or "")[:40]}
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN cost_amount_minor IS NULL THEN 1 ELSE 0 END),"
                " COUNT(cost_amount_minor), SUM(cost_amount_minor), GROUP_CONCAT(DISTINCT cost_status)"
                " FROM journey_legs l JOIN plan_versions p ON l.plan_version_id = p.id"
                " WHERE p.journey_id = ?", (journey_id,))
    one["legs"] = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM bookings b JOIN plan_stops s ON b.plan_stop_id = s.id"
                " JOIN plan_versions p ON s.plan_version_id = p.id WHERE p.journey_id = ?", (journey_id,))
    one["bookings"] = cur.fetchone()[0]
    money[journey_id] = one
for journey_id, one in list(money.items())[:12]:
    print("  journey", journey_id[:8], one)
dst.close()
print("dst bytes", os.path.getsize(DST))
print("source still read-only: opened with mode=ro and PRAGMA query_only=1; no write was attempted")
sys.exit(0)
