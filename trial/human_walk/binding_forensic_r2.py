"""Read-only forensics for ticket #314: what did the Agent actually do before it saved a
place-less draft?

walk-110 (2026-10-24 07:2x) saved 6 slots and every one of them said 「具体地点：让 Agent 找这一处」,
so freeze answered NO_PLACED_STOPS and the travel-gaps door had no pair to measure.  Before writing a
fix we want the recorded fact: which research tools ran in that round, what each one answered, and
whether any of them handed back a place id the draft could have carried.

Nothing here writes: the sqlite URL opens with mode=ro, and the only things printed are tool names,
statuses, reason codes, counts and id *prefixes* -- never a receipt body, never a credential.
"""

import json
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_cmdr_v3_live_1022/citynexus_v3_bound_1024.db"
JOURNEY = sys.argv[2] if len(sys.argv) > 2 else "9ef9cb8f-c522-4da3-9ef5-bd1b0e5bf3ad"

conn = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
conn.row_factory = sqlite3.Row

tables = [r[0] for r in conn.execute("select name from sqlite_master where type='table'")]
print(f"TABLES_HAVE={sorted(t for t in tables if 'mission' in t or 'step' in t or 'plan' in t)}")

rows = list(conn.execute("select id, intent_json, status from journey_missions where journey_id=? "
                         "and intent_json like '%goal_task%' order by rowid", (JOURNEY,)))
print(f"MISSIONS_ON_JOURNEY={len(rows)}")
for mission in rows:
    intent = json.loads(mission["intent_json"] or "{}")
    task = intent.get("goal_task") or {}
    draft = task.get("draft_artifact") or {}
    slots = [(day.get("date"), [(s.get("title"), s.get("place_id")) for s in day.get("slots") or []])
             for day in draft.get("days") or []]
    bound = sum(1 for _, items in slots for _, pid in items if pid)
    total = sum(len(items) for _, items in slots)
    print(f"TASK {mission['id'][:8]} status={mission['status']} draft_rev={draft.get('revision')} "
          f"slots={total} bound={bound} "
          f"research_places={len(task.get('research_places') or [])} "
          f"candidate_place_ids={len(task.get('candidate_place_ids') or [])} "
          f"research_routes={len(task.get('research_routes') or [])}")
    for date, items in slots:
        for title, pid in items:
            print(f"  SLOT {date} place_id={'YES ' + str(pid)[:18] if pid else 'NONE'} :: {title[:28]}")
    leads = [f"{str(p.get('id'))[:20]}|canon={str(p.get('canonical_place_id') or '')[:12]}|{p.get('region_status')}"
             for p in (task.get("research_places") or [])]
    print(f"  LEADS={leads[:8]}")
    print(f"  CANDIDATE_IDS={[str(x)[:20] for x in (task.get('candidate_place_ids') or [])][:8]}")

steps_table = next((t for t in ("agent_run_steps", "goal_task_steps", "journey_mission_steps") if t in tables), None)
if steps_table is None:
    print(f"NO_STEPS_TABLE among {sorted(t for t in tables if 'step' in t or 'run' in t)}")
else:
    cols = [r[1] for r in conn.execute(f"pragma table_info({steps_table})")]
    print(f"STEPS_TABLE={steps_table} COLS={cols}")
    name_col = next((c for c in ("tool_name", "tool", "name") if c in cols), None)
    res_col = next((c for c in ("result_json", "output_json", "observation_json", "payload_json") if c in cols), None)
    arg_col = next((c for c in ("args_json", "arguments_json", "input_json") if c in cols), None)
    time_col = next((c for c in ("created_at", "started_at", "occurred_at") if c in cols), None)
    where = "" if "journey_id" in cols else "1=1"
    steps = list(conn.execute(f"select * from {steps_table} where {where} order by rowid"))
    print(f"RUN_STEPS={len(steps)}")
    for step in steps:
        body = {}
        try:
            body = json.loads((step[res_col] if res_col else "{}") or "{}")
        except Exception:
            pass
        args = {}
        try:
            args = json.loads((step[arg_col] if arg_col else "{}") or "{}")
        except Exception:
            pass
        if not isinstance(body, dict):
            body = {}
        brief = {k: (len(v) if isinstance(v, list) else v) for k, v in body.items()
                 if k in ("status", "reason_code", "places", "place_count", "observations",
                          "candidate_count", "needs", "decision", "options", "message")}
        abrief = {k: str(v)[:22] for k, v in args.items() if isinstance(v, (str, int)) or v is None}
        print(f"  {step[time_col] if time_col else ''} {str(step[name_col] if name_col else '?'):<26} "
              + json.dumps(brief, ensure_ascii=False)[:200] + " args=" + json.dumps(abrief, ensure_ascii=False)[:110])
conn.close()
