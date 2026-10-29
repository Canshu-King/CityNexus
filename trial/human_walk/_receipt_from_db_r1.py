"""Read one journey's product truth straight from the isolated canary DB.

No credentials are printed: the bearer token never enters SQLite, and this script only reads
journey/mission/plan rows. Usage: python _receipt_from_db_r1.py <db> [journey-prefix]
"""
import json
import sqlite3
import sys

db = sys.argv[1] if len(sys.argv) > 1 else r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_gozero_1026.db"
prefix = sys.argv[2] if len(sys.argv) > 2 else ""
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

where, args = "", []
if prefix:
    where, args = " where id like ?", [prefix + "%"]
journeys = conn.execute("select id,status,title,city_code,start_at,end_at,active_plan_version_id,current_activity_id,created_at from journeys" + where, args).fetchall()
for journey in journeys:
    print("JOURNEY", json.dumps(dict(journey), ensure_ascii=False))
    missions = conn.execute(
        "select id,status,user_text,failure_reason,created_at,completed_at,intent_json from journey_missions where journey_id=?",
        [journey["id"]],
    ).fetchall()
    for mission in missions:
        task = (json.loads(mission["intent_json"] or "{}").get("goal_task") or {})
        draft = task.get("draft_artifact") or {}
        slots = sum(len(day.get("slots") or []) for day in draft.get("days") or [])
        print("  MISSION", json.dumps({
            "id": mission["id"], "status": mission["status"], "failure": mission["failure_reason"],
            "created_at": mission["created_at"], "completed_at": mission["completed_at"],
        }, ensure_ascii=False))
        print("  TASK", json.dumps({
            "status": task.get("status"), "failure_code": task.get("failure_code"),
            "mode": task.get("interaction_mode"), "usage": task.get("usage"),
            "draft_revision": draft.get("revision"), "days": len(draft.get("days") or []), "slots": slots,
            "pending_question": bool(task.get("pending_question")),
            "pending_options": [o.get("label") for o in (task.get("pending_question") or {}).get("options") or []],
            "conversation": len(task.get("conversation") or []),
            "research_places": len(task.get("research_places") or []),
        }, ensure_ascii=False))
        steps = conn.execute(
            "select tool_name,status from agent_run_steps where run_id in (select id from agent_runs where mission_id=?)",
            [mission["id"]],
        ).fetchall()
        counts = {}
        for step in steps:
            counts[step["tool_name"]] = counts.get(step["tool_name"], 0) + 1
        print("  TOOLS", json.dumps(counts, ensure_ascii=False), "steps", len(steps))
    plans = conn.execute(
        "select id,version_no,status,lifecycle,source,total_cost_minor,currency,mobility_snapshot_id,created_at,explanation_json "
        "from plan_versions where journey_id=? order by version_no", [journey["id"]],
    ).fetchall()
    for plan in plans:
        explanation = json.loads(plan["explanation_json"] or "{}")
        print("  PLAN", json.dumps({
            "id": plan["id"], "version_no": plan["version_no"], "status": plan["status"],
            "lifecycle": plan["lifecycle"], "source": plan["source"], "cost_minor": plan["total_cost_minor"],
            "currency": plan["currency"], "mobility_snapshot": plan["mobility_snapshot_id"],
            "unresolved": len(explanation.get("unresolved_facts") or []), "created_at": plan["created_at"],
        }, ensure_ascii=False))
        activities = conn.execute(
            "select count(*) from plan_activities where plan_version_id=?", [plan["id"]]
        ).fetchone()[0] if conn.execute(
            "select count(*) from sqlite_master where type='table' and name='plan_activities'"
        ).fetchone()[0] else -1
        print("    ACTIVITIES", activities)
