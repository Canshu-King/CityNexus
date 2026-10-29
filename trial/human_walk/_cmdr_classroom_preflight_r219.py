"""Read-only pre-flight for the classroom stack the operator will walk tomorrow.

The tablet acceptance is the one thing only the operator can do, so the useful service is to state,
before they sit down, what the classroom database can and cannot show.  This opens the canary database
in SQLite read-only mode (no writes are possible on that URI, and the run refuses unless the path is
the classroom canary, so the real databases are out of reach by construction) and reports the
journey/plan state and whether any route evidence exists at all.
"""

import io
import os
import sqlite3
import sys

DB = r"E:\_cmdr_clean_1028_data\citynexus_v3_clean_1028.db"
MUST_CONTAIN = "_cmdr_clean_1028_data"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw219-classroom-preflight.txt")

EVIDENCE_TABLES = ("mobility_facts", "route_acquisition_operations")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if MUST_CONTAIN not in DB:
        print("ABORT refusing to read a database that is not the classroom canary")
        return 4
    if not os.path.exists(DB):
        print("ABORT classroom database missing at %s" % DB)
        return 3

    connection = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    cursor = connection.cursor()
    lines = [
        "CLASSROOM PRE-FLIGHT bw219",
        "DATABASE %s (opened with mode=ro; no write is possible on this URI)" % DB,
        "JOURNEYS_BY_STATUS %s" % cursor.execute(
            "select status, count(*) from journeys group by status order by status"
        ).fetchall(),
        "PLAN_VERSIONS_BY_STATUS %s" % cursor.execute(
            "select status, count(*) from plan_versions group by status order by status"
        ).fetchall(),
    ]

    planned = cursor.execute(
        "select id, city_code, start_at, end_at, active_plan_version_id from journeys"
        " where status = 'PLANNED' order by created_at desc limit 3"
    ).fetchall()
    lines.append("PLANNED_JOURNEYS %d listed below" % len(planned))
    for journey_id, city, start_at, end_at, plan_id in planned:
        plan_status = cursor.execute(
            "select status from plan_versions where id = ?", (plan_id,)
        ).fetchone() if plan_id else None
        lines.append(
            "  journey=%s city=%s window=%s..%s active_plan=%s plan_status=%s"
            % (str(journey_id)[:8], city, start_at, end_at, str(plan_id)[:8] if plan_id else None,
               plan_status[0] if plan_status else None)
        )

    for table in EVIDENCE_TABLES:
        present = cursor.execute(
            "select count(*) from sqlite_master where type='table' and name=?", (table,)
        ).fetchone()[0]
        if not present:
            lines.append("EVIDENCE_TABLE %s absent" % table)
            continue
        total = cursor.execute("select count(*) from %s" % table).fetchone()[0]
        scoped = "n/a"
        if any(row[1] == "journey_id" for row in cursor.execute("pragma table_info(%s)" % table)):
            if planned:
                scoped = cursor.execute(
                    "select count(*) from %s where journey_id = ?" % table, (planned[0][0],)
                ).fetchone()[0]
        lines.append("EVIDENCE_TABLE %s rows_total=%s rows_for_planned_journey=%s" % (table, total, scoped))

    connection.close()
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
