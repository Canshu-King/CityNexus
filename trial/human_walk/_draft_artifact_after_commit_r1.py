"""Read-only: after a traveller commits a plan, what is left in the Agent task's draft artifact?

Why: the committed canary screen shows 「0 项安排 · 0 天」 in the day-by-day section while the departure
section below it says 「6 项正式安排」.  Either the draft really is gone (then the section must point at the
formal plan instead of counting nothing), or the screen stopped reading an artifact the server still holds.
"""
import json
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_variants_1022.db"
JOURNEY = sys.argv[1] if len(sys.argv) > 1 else "c1eb3edc-a9cc-40f5-ad8d-fd69b815cc80"

con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
con.row_factory = sqlite3.Row
tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
task_tables = [t for t in tables if "task" in t.lower()]
print("task-ish tables:", task_tables)
name = next((t for t in task_tables if "goal" in t), task_tables[0] if task_tables else None)
if not name:
    raise SystemExit("no task table")
cols = [r[1] for r in con.execute("pragma table_info(%s)" % name)]
print("columns:", ",".join(cols))
rows = list(con.execute("select * from %s where journey_id=?" % name, (JOURNEY,)))
print("tasks for journey:", len(rows))
for row in rows:
    artifact_column = next((c for c in cols if "draft" in c and "json" in c), None)
    raw = row[artifact_column] if artifact_column else None
    art = json.loads(raw) if raw else {}
    days = (art or {}).get("days") or []
    keys = row.keys()
    print(" | ".join([
        "task=" + str(row["id"])[:8],
        "status=" + str(row["status"]) if "status" in keys else "status=?",
        "type=" + (str(row["task_type"]) if "task_type" in keys else str(row["type"]) if "type" in keys else "?"),
        "artifact_column=" + str(artifact_column),
        "days=" + str(len(days)),
        "slots=" + str(sum(len(d.get("slots") or []) for d in days)),
        "updated=" + (str(row["updated_at"]) if "updated_at" in keys else str(row["created_at"])),
    ]))
    print("   keys:", json.dumps({k: (str(row[k])[:60] if k != artifact_column else "<%d B>" % len(raw or ""))
                                 for k in keys}, ensure_ascii=False))
