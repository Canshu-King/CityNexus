import json
import sqlite3
import sys

DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_gozero_1026.db"
JOURNEY = "1acb10a6-c234-4765-a88a-4bd56f0985f7"

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
out = []

journeys = con.execute("select * from journeys where id = ?", (JOURNEY,)).fetchall()
for row in journeys:
    d = dict(row)
    out.append("JOURNEY_COLUMNS " + json.dumps(sorted(d), ensure_ascii=False))
    for key in ("goal_json", "intent_json", "metadata_json", "trip_context_json"):
        if isinstance(d.get(key), str) and len(d[key]) > 200:
            d[key] = d[key][:200] + "...TRUNC"
    out.append("JOURNEY " + json.dumps(d, ensure_ascii=False))

tables = {r["name"] for r in con.execute("select name from sqlite_master where type='table'")}
out.append("HAS_PLAN_VERSIONS " + str("plan_versions" in tables))

pv_cols = [r["name"] for r in con.execute("pragma table_info(plan_versions)")]
out.append("PLAN_VERSION_COLUMNS " + json.dumps(pv_cols, ensure_ascii=False))

plans = con.execute("select * from plan_versions where journey_id = ? order by version_no", (JOURNEY,)).fetchall()
out.append("PLAN_VERSION_ROWS " + str(len(plans)))
for row in plans:
    d = dict(row)
    for key in list(d):
        if isinstance(d[key], str) and len(d[key]) > 260:
            d[key] = d[key][:260] + "...TRUNC"
    out.append("PLAN " + json.dumps(d, ensure_ascii=False))

act_cols = [r["name"] for r in con.execute("pragma table_info(activities)")]
out.append("ACTIVITY_COLUMNS " + json.dumps(act_cols, ensure_ascii=False))
for row in plans:
    n = con.execute("select count(*) from activities where plan_version_id = ?", (row["id"],)).fetchone()[0]
    out.append(f"ACTIVITIES plan={row['id']} version={row['version_no']} count={n}")

sys.stdout.reconfigure(encoding="utf-8")
print("\n".join(out))
