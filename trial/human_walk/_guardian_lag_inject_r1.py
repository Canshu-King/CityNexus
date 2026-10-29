"""Shape the 'failure recorded, run still GUARDIAN_RUNNING' window for a screen read.

inject: copies one mission / agent run / guardian run onto the run's pending event and sets
        the run to GUARDIAN_RUNNING.  restore: deletes exactly those copied rows and puts the
        run back to PAUSED_FOR_GUARDIAN.
This is a UI-branch fixture; it writes nothing outside the classroom demo database.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import uuid

DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_demo_1025.db"
JOURNEY = "2e9cd67d-10ca-4ecd-920b-76c81a350c71"
MARKER = "GUARDIAN_LAG_FIXTURE"


def columns(db, table):
    return [row[1] for row in db.execute("pragma table_info(%s)" % table)]


def copy_row(db, table, source, changes):
    names = columns(db, table)
    values = []
    for name in names:
        values.append(changes.get(name, source[name]))
    db.execute(
        "insert into %s (%s) values (%s)"
        % (table, ",".join(names), ",".join("?" for _ in names)),
        values,
    )


def inject(mode: str = "external") -> dict:
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    run = db.execute(
        "select id, state_json from simulation_runs where journey_id=? order by rowid desc limit 1",
        (JOURNEY,),
    ).fetchone()
    state = json.loads(run["state_json"])
    pending = state.get("pending_event_id")
    if not pending:
        raise SystemExit("run has no pending event")
    mission = db.execute(
        "select * from journey_missions where journey_id=? and trigger_event_id is not null "
        "and is_standing=0 order by rowid desc limit 1",
        (JOURNEY,),
    ).fetchone()
    agent = db.execute(
        "select * from agent_runs where mission_id=? order by rowid desc limit 1", (mission["id"],)
    ).fetchone()
    guardian = db.execute(
        "select * from guardian_runs where journey_id=? order by rowid desc limit 1", (JOURNEY,)
    ).fetchone()
    mission_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    guardian_id = str(uuid.uuid4())
    copy_row(db, "journey_missions", mission, {
        "id": mission_id, "trigger_event_id": pending, "is_standing": 0,
        "reasoning_summary": MARKER,
    })
    copy_row(db, "agent_runs", agent, {
        "id": agent_id, "mission_id": mission_id,
        "status": "PARTIAL" if mode == "unresolved" else "FAILED_EXTERNAL",
        "failure_reason": MARKER,
    })
    copy_row(db, "guardian_runs", guardian, {
        "id": guardian_id, "trigger_event_id": pending, "agent_run_id": agent_id,
        "proposal_id": None, "status": "PARTIAL", "action_status": "UNRESOLVED",
        "evidence_fingerprint": uuid.uuid4().hex,
        "reasoning_summary": MARKER,
    })
    db.execute("update simulation_runs set status='GUARDIAN_RUNNING' where id=?", (run["id"],))
    db.commit()
    db.close()
    return {"mission": mission_id, "agent": agent_id, "guardian": guardian_id, "pending": pending}


def restore(ids: dict) -> None:
    db = sqlite3.connect(DB)
    db.execute("delete from guardian_runs where id=?", (ids["guardian"],))
    db.execute("delete from agent_runs where id=?", (ids["agent"],))
    db.execute("delete from journey_missions where id=?", (ids["mission"],))
    db.execute(
        "update simulation_runs set status='PAUSED_FOR_GUARDIAN' where journey_id=? "
        "and state_json like ?",
        (JOURNEY, "%" + ids["pending"] + "%"),
    )
    db.commit()
    db.close()


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "inject"
    if action == "inject":
        print(json.dumps(inject(sys.argv[2] if len(sys.argv) > 2 else "external"), ensure_ascii=False))
    elif action == "restore":
        restore(json.loads(sys.argv[2]))
        print("RESTORED")
