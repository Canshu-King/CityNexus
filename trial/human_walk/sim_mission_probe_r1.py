"""Second cut: give the ACTIVE journey a standing mission, pulse again, and follow the run to a
proposal (or to a named failure).  Read-only after the two POSTs except for the server's own work."""
from __future__ import annotations

import io
import json
import sqlite3
import time
import urllib.error
import urllib.request

DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_play_1024.db"
API = "http://127.0.0.1:60361"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/sim-mission-1.txt"
lines: list[str] = []


def note(value: str) -> None:
    lines.append(value)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def call(method: str, path: str, body: dict | None = None, timeout: int = 300) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(API + path, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            raw = answer.read().decode("utf-8")
            return answer.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except ValueError:
            payload = {"raw": raw[:300]}
        return error.code, payload


def db() -> sqlite3.Connection:
    connection = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


connection = db()
journey = connection.execute(
    "select id from journeys where status='ACTIVE' order by updated_at desc limit 1"
).fetchone()
if journey is None:
    note("NO_ACTIVE_JOURNEY")
    print("\n".join(lines))
    raise SystemExit(0)
journey_id = journey["id"]
note("JOURNEY " + journey_id)

status, mission = call("PUT", f"/api/v1/journeys/{journey_id}/guardian/mission", {
    "command": "这趟旅行由你守护：遇到景点临时关闭、交通延误或时间不够时，先给我一个可执行的替代安排，改动前等我确认。",
    "requested_autonomy": "EXECUTE_WITHIN_BOUNDS",
})
note("MISSION " + json.dumps({"status": status, "id": mission.get("id"), "state": mission.get("status"),
                              "autonomy": mission.get("requested_autonomy")}, ensure_ascii=False))

status, pulse = call("POST", f"/api/v1/journeys/{journey_id}/guardian/pulse")
guardian = pulse.get("guardian") or {}
note("PULSE " + json.dumps({"status": status, "decision": guardian.get("decision"),
                            "action_status": guardian.get("action_status"),
                            "agent_run_id": guardian.get("agent_run_id"),
                            "proposal_id": guardian.get("proposal_id")}, ensure_ascii=False))

deadline = time.time() + 360
last = None
while time.time() < deadline:
    connection = db()
    run = connection.execute(
        "select id,status,outcome,failure_reason,provider_key,model_key,started_at,completed_at "
        "from agent_runs where journey_id=? order by created_at desc limit 1",
        (journey_id,),
    ).fetchone()
    current = dict(run) if run else None
    if current != last:
        note("RUN " + json.dumps(current, ensure_ascii=False))
        last = current
    if current and current["status"] not in {"RUNNING", "PENDING"}:
        break
    time.sleep(15)

connection = db()
note("GUARDIAN_RUNS " + json.dumps([dict(row) for row in connection.execute(
    "select id,status,decision,action_status,agent_run_id,trigger_event_id,completed_at "
    "from guardian_runs where journey_id=? order by started_at desc limit 2", (journey_id,)
)], ensure_ascii=False, default=str)[:1800])
try:
    proposals = [dict(row) for row in connection.execute(
        "select * from replan_proposals where journey_id=? order by created_at desc limit 2", (journey_id,)
    )]
    note("PROPOSALS " + json.dumps(proposals, ensure_ascii=False, default=str)[:1600])
except sqlite3.Error as error:
    note("PROPOSALS_ERR " + str(error))
try:
    steps = [dict(row) for row in connection.execute(
        "select sequence_no,tool_name,status,result_json from agent_run_steps "
        "where run_id in (select id from agent_runs where journey_id=?) order by sequence_no limit 12",
        (journey_id,),
    )]
    note("STEPS " + json.dumps(steps, ensure_ascii=False, default=str)[:2000])
except sqlite3.Error as error:
    note("STEPS_ERR " + str(error))
print("\n".join(lines))
