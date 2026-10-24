"""Follow the walking cap through the walked journey's own rows: which task carries the sentence, and what the frozen hops say.

The code resolves the cap from the last twelve user messages of a task's conversation plus the intent source texts.
So the question "does a replan still honour the cap" is answerable from the database: does the task produced for the
replan still carry that sentence, and do its frozen hops say public transport?  Read-only.
"""
import json
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_cap2_1024.db"
out = []
con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
con.row_factory = sqlite3.Row
tables = sorted(r[0] for r in con.execute("select name from sqlite_master where type='table'"))
cand = [t for t in tables if "goal" in t or "task" in t or t == "plan_versions" or "mission" in t]
out.append("candidate tables=%s" % ",".join(cand))

for name in cand:
    cols = [r[1] for r in con.execute("pragma table_info('%s')" % name)]
    n = con.execute("select count(*) from %s" % name).fetchone()[0]
    out.append("%s rows=%d cols=%s" % (name, n, ",".join(cols)))

for name, textcol in [(t, c) for t in cand for c in [r[1] for r in con.execute("pragma table_info('%s')" % t)]
                      if c in ("conversation_json", "intent_json", "payload_json", "result_json", "goal_text")]:
    rows = list(con.execute("select rowid, %s from %s order by rowid limit 40" % (textcol, name)))
    for row in rows:
        blob = row[1]
        if not blob:
            continue
        has_cap = "公里" in str(blob) and "步行" in str(blob)
        out.append("  %s rowid=%s col=%s len=%d mentions_walking_km=%s"
                   % (name, row[0], textcol, len(str(blob)), "YES" if has_cap else "no"))

if "plan_versions" in tables:
    cols = [r[1] for r in con.execute("pragma table_info('plan_versions')")]
    ev = [c for c in cols if "mobility" in c or "evidence" in c]
    out.append("plan_versions evidence columns=%s" % ",".join(ev))
    for row in con.execute("select id, journey_id, %s from plan_versions order by id desc limit 6" % (ev[0] if ev else "null as x")):
        d = dict(row)
        raw = d.get(ev[0]) if ev else None
        modes = {}
        if raw:
            try:
                data = json.loads(raw)
                items = data if isinstance(data, list) else (data.get("legs") or data.get("transitions") or [])
                for it in items:
                    if isinstance(it, dict):
                        key = str(it.get("mode") or it.get("frozen_mode") or "?")
                        modes[key] = modes.get(key, 0) + 1
            except Exception as exc:
                modes = {"UNPARSED": exc.__class__.__name__}
        out.append("  plan_version %s journey=%s len=%s modes=%s"
                   % (str(d.get("id"))[:8], str(d.get("journey_id"))[:8], len(raw or ""), modes))

open(r"D:/moodle/_cmdr_v3_port_1022/cap_replan_read.txt", "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("rows_written=%d" % len(out))
