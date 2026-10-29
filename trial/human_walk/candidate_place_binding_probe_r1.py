"""Read what the candidate this walk saved actually binds: which rows have a place, which do not.

Why: the phone said 「这版方案里没有相邻两站之间的转场要核实」 while six arrangements had just been saved
(trial/results/20261022_v3_human_chrome/replan-probe-2-log.txt, the FREEZE_ROUND lines).  That sentence is
produced when `used_edges` finds no pair of *placed* consecutive activities, so the question is whether the
saved rows carry a `place_id` at all.  Read-only against this walk's own canary file.
"""
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_replan_1024.db"
connection = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
connection.row_factory = sqlite3.Row
plans = connection.execute("select id, status, created_at, mobility_snapshot_id, journey_id from plan_versions"
                           " order by created_at").fetchall()
print(f"PLAN_VERSIONS {len(plans)}")
for plan in plans[-4:]:
    rows = connection.execute("select sequence_no, title, place_id, start_at, end_at from activities"
                              " where plan_version_id = ? order by sequence_no", (plan["id"],)).fetchall()
    placed = [row for row in rows if row["place_id"]]
    print(f"PLAN {plan['id'][:8]} status={plan['status']} snapshot={str(plan['mobility_snapshot_id'])[:8]}"
          f" rows={len(rows)} placed={len(placed)} created={plan['created_at']}")
    for row in rows:
        print(f"   SEQ {row['sequence_no']} place={'YES' if row['place_id'] else 'NO '} window={row['start_at'][11:16]}"
              f"-{row['end_at'][11:16]} title={row['title'][:34]}")
for name in ("places", "journeys"):
    print(f"TABLE {name} rows={connection.execute(f'select count(*) from {name}').fetchone()[0]}")
connection.close()
