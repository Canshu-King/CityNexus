"""Read-only look at how the walking cap is actually stored for the walked journey.

The freeze leg resolves the cap in this order: a stored JourneyIntent capability wins over a re-read of the
traveller's words.  Whether an edited preference changes what the next freeze uses therefore depends on whether
a new intent row appears (and supersedes the old one).  This dumps exactly that, without writing anything.
"""
import json
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else r"D:/moodle/_cmdr_rescue_v3_1022/trial/.runtime/citynexus_v3_cap2_1024.db"
out = []
con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
con.row_factory = sqlite3.Row
tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
out.append("db=%s tables=%d" % (DB.split("/")[-1], len(tables)))
if "journey_intents" not in tables:
    out.append("NO journey_intents TABLE (tables present: %s)" % ",".join(sorted(tables)[:40]))
else:
    cols = [r[1] for r in con.execute("pragma table_info('journey_intents')")]
    out.append("journey_intents columns=%s" % ",".join(cols))
    rows = list(con.execute("select * from journey_intents order by id"))
    out.append("journey_intents rows=%d" % len(rows))
    for row in rows:
        d = dict(row)
        caps = d.get("capabilities_json")
        codes = []
        if caps:
            try:
                codes = ["%s=%s" % (c.get("code"), (c.get("params") or {}).get("max_m"))
                         for c in json.loads(caps) if isinstance(c, dict)]
            except Exception as exc:
                codes = ["UNPARSED:%s" % exc.__class__.__name__]
        text = str(d.get("source_text") or "").replace("\n", " ")[:90]
        out.append("  id=%s journey=%s superseded_at=%s codes=[%s] text=%s"
                   % (d.get("id"), str(d.get("journey_id"))[:8], d.get("superseded_at"),
                      ";".join(codes), text))

for name in ("journey_missions", "goal_tasks"):
    if name in tables:
        cols = [r[1] for r in con.execute("pragma table_info('%s')" % name)]
        cap_cols = [c for c in cols if "capabilit" in c or "intent" in c or "conversation" in c or "goal" in c]
        out.append("%s columns_of_interest=%s" % (name, ",".join(cap_cols)))
open(r"D:/moodle/_cmdr_v3_port_1022\cap_stored_read.txt", "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("rows_written=%d" % len(out))
