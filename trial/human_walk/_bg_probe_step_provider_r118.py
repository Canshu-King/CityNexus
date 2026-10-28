"""Read-only census of who answered for the AgentRunStep rows behind one journey.

Why this exists next to the screen arm: bl117 can only count disclosure lines it can see.  If the panel
shows none, the honest question is whether the server wrote no provider for those steps or the frontend
failed to render them -- and only the stored rows can tell those two apart.  Nothing here writes: the
database is opened with mode=ro and the instrument prints counts and field names, never row bodies.
"""
import glob
import json
import sqlite3
import sys

JOURNEY = sys.argv[1] if len(sys.argv) > 1 else ""
candidates = sorted(glob.glob(r"E:/_cmdr_tip_113_data/*.db"))
print("DATABASES", [p.replace("\\", "/").rsplit("/", 1)[-1] for p in candidates])
if not candidates:
    raise SystemExit("ABORT no tip-stack database found")
path = max(candidates, key=lambda p: __import__("os").path.getsize(p))
print("USING", path.replace("\\", "/"), "BYTES", __import__("os").path.getsize(path))

conn = sqlite3.connect("file:" + path.replace("\\", "/") + "?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
tables = {r["name"] for r in conn.execute("select name from sqlite_master where type='table'")}
for need in ("journey_missions", "agent_runs", "agent_run_steps"):
    if need not in tables:
        raise SystemExit("ABORT table missing: " + need)

runs = [r["id"] for r in conn.execute(
    "select r.id from agent_runs r join journey_missions m on m.id = r.mission_id where m.journey_id = ?",
    (JOURNEY,))]
print("RUNS", len(runs))
if not runs:
    raise SystemExit("ABORT this journey has no agent run yet")
marks = ",".join("?" * len(runs))
rows = list(conn.execute(
    "select tool_name, status, result_json from agent_run_steps where run_id in (%s)" % marks, runs))
print("STEPS", len(rows))
by_tool = {}
for r in rows:
    raw = r["result_json"] or ""
    has_provider = '"provider"' in raw
    has_provenance = '"provider_provenance"' in raw
    provider = ""
    if has_provider:
        try:
            provider = str(json.loads(raw).get("provider", ""))
        except Exception:
            provider = "(unparsable)"
    bucket = by_tool.setdefault(r["tool_name"], [0, 0, 0, {}])
    bucket[0] += 1
    bucket[1] += 1 if has_provider else 0
    bucket[2] += 1 if has_provenance else 0
    if provider:
        bucket[3][provider] = bucket[3].get(provider, 0) + 1
for tool in sorted(by_tool):
    total, prov, provenance, names = by_tool[tool]
    print("TOOL", tool, "steps=%d" % total, "with_provider=%d" % prov,
          "with_provenance=%d" % provenance, "providers=" + json.dumps(names, sort_keys=True))
conn.close()
