"""Read the goal-task statuses a run left behind, so a claim about "resumable" is grounded in a row."""
import os
import sqlite3
import sys

DB = sys.argv[1]
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
con.row_factory = sqlite3.Row
tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
print("db=%s tables=%d" % (os.path.basename(DB), len(tables)))
for name in ("goal_tasks", "agent_runs"):
    if name not in tables:
        print("  no table %s" % name)
        continue
    cols = [r[1] for r in con.execute("pragma table_info('%s')" % name)]
    print("  %s cols=%s rows=%d" % (name, ",".join(cols), con.execute("select count(*) from %s" % name).fetchone()[0]))
    if name == "goal_tasks":
        for row in con.execute("select * from goal_tasks order by rowid desc limit 8"):
            d = dict(row)
            print("    id=%s status=%s updated=%s" % (str(d.get("id"))[:8], d.get("status"), d.get("updated_at")))
    else:
        for row in con.execute("select * from agent_runs order by rowid desc limit 8"):
            d = dict(row)
            print("    run=%s status=%s code=%s started=%s" % (str(d.get("id"))[:8], d.get("status"),
                                                               d.get("error_code"), d.get("started_at")))
