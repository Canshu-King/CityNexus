"""ORD-0541 lane -- a private database copy for one generation, plus the marker row that proves which
file a listener is reading.

The same five-step recipe this lane settled on for ORD-0528 (sqlite's backup API out of a `?mode=ro`
source, never a file copy; a marker `places` row that exists in no other store; counts printed rather
than implied), with the marker city taken as an argument so three generations can each name their own
store, and two readings the idempotency arms need before anything starts:

  * the journeys the copy holds that have an active plan with at least one activity -- the poster
    sheet only renders when one exists, so an arm that finds no 成长图并保存 bar has a supply problem
    and not a product red; and
  * how many `journey_share_grants` rows the copy carries, because "the roster is the size the first
    press left it" has to start from a count and not from a hope.

Refuses to run if the target already exists: reopening a database another stack wrote to is not a
fresh reading.
"""
import os
import sqlite3
import sys

SOURCE = "D:/moodle/_qoder_cmdr_gate_20260921/backend/_live.db"
TARGET = sys.argv[1]
MARKER_CITY = sys.argv[2] if len(sys.argv) > 2 else "CNX-ORD0541"

TABLES = ("journeys", "plan_versions", "activities", "places", "journey_share_grants")


def counts(conn):
    out = {}
    for table in TABLES:
        try:
            out[table] = conn.execute("select count(*) from %s" % table).fetchone()[0]
        except sqlite3.Error as error:
            out[table] = "unreadable:%s" % type(error).__name__
    return out


def main():
    if len(sys.argv) < 2:
        print("ABORT: usage is make_lane_db_r3.py <target.db> <marker-city>")
        return 1
    if os.path.exists(TARGET):
        print("ABORT: target exists, refusing to reopen %s" % TARGET)
        return 2
    if not os.path.exists(SOURCE):
        print("ABORT: no seed at %s" % SOURCE)
        return 3
    source = sqlite3.connect("file:%s?mode=ro" % SOURCE.replace("\\", "/"), uri=True)
    print("SOURCE_READONLY_OPEN %s" % SOURCE)
    print("source_counts %r" % (counts(source),))
    destination = sqlite3.connect(TARGET)
    source.backup(destination)
    destination.execute(
        "insert into places (id, provider_key, external_id, city_code, name, category, "
        "latitude, longitude, updated_at) values (?,?,?,?,?,?,?,?,?)",
        (
            "00000000-0000-4000-8000-00000000%04d" % (abs(hash(MARKER_CITY)) % 10000),
            "ord0541-lane",
            "ord0541-marker",
            MARKER_CITY,
            "ORD-0541 lane marker",
            "landmark",
            0.0,
            0.0,
            "2026-10-02T00:00:00+08:00",
        ),
    )
    destination.commit()
    print("copy_counts %r" % (counts(destination),))
    print("marker_rows_in_my_copy %d" % destination.execute(
        "select count(*) from places where city_code = ?", (MARKER_CITY,)).fetchone()[0])
    print("marker_rows_in_source %d" % source.execute(
        "select count(*) from places where city_code = ?", (MARKER_CITY,)).fetchone()[0])
    rows = destination.execute(
        "select j.id, j.title, j.city_code, j.traveler_id, "
        "(select count(*) from activities a where a.plan_version_id = j.active_plan_version_id) "
        "from journeys j where j.active_plan_version_id is not null"
    ).fetchall()
    print("journeys_with_active_plan %d" % len(rows))
    for row in rows[:6]:
        print("  journey %r" % (row,))
    print(
        "journeys_the_arms_use %d"
        % destination.execute(
            "select count(*) from journeys where id = ? and active_plan_version_id is not null",
            ("22222222-2222-4222-8222-222222222222",),
        ).fetchone()[0]
    )
    print("TARGET %s bytes=%d" % (TARGET.replace("\\", "/"), os.path.getsize(TARGET)))
    destination.close()
    source.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
