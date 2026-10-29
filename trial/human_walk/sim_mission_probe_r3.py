"""Second cut, retry after the request_replan fix: reset + re-inject the closure, pulse, follow the
run, and read the proposal the agent actually produced."""
from __future__ import annotations

import io
import json
import sqlite3
import time
import urllib.error
import urllib.request

DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_play_1024.db"
API = "http://127.0.0.1:60361"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/sim-mission-3.txt"
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
journey_id = journey["id"]
note("JOURNEY " + journey_id)
plan = connection.execute("select active_plan_version_id as p from journeys where id=?", (journey_id,)).fetchone()["p"]
activities = list(connection.execute(
    "select sequence_no,title,place_id,status from activities where plan_version_id=? order by sequence_no", (plan,)
))
current = next((a for a in activities if a["status"] in {"ACTIVE", "EN_ROUTE", "ARRIVED", "IN_PROGRESS"}), None)
# A different affected place produces a different incident fingerprint, so the Guardian cannot
# reuse the earlier PROPOSAL_PRESENTED run; the earlier target is already consumed.
place_id = current["place_id"]
note("TARGET " + json.dumps({"title": current["title"], "place_id": place_id}, ensure_ascii=False))

status, normal = call("POST", f"/api/v1/journeys/{journey_id}/guardian/provider-fixture",
                      {"state": "NORMAL", "payload": {}})
note("RESET " + json.dumps({"status": status, "revision": normal.get("revision")}, ensure_ascii=False))
status, fixture = call("POST", f"/api/v1/journeys/{journey_id}/guardian/provider-fixture",
                       {"state": "DISRUPTED", "payload": {"target_place_id": place_id, "cause": "SCENARIO_INJECTED_CLOSURE"}})
note("FIXTURE " + json.dumps({"status": status, "revision": fixture.get("revision"), "state": fixture.get("state")}, ensure_ascii=False))

started = time.time()
status, pulse = call("POST", f"/api/v1/journeys/{journey_id}/guardian/pulse")
guardian = pulse.get("guardian") or {}
note("PULSE " + json.dumps({"status": status, "decision": guardian.get("decision"),
                            "action_status": guardian.get("action_status"),
                            "agent_run_id": guardian.get("agent_run_id"),
                            "proposal_id": guardian.get("proposal_id")}, ensure_ascii=False))

deadline = time.time() + 420
last = None
while time.time() < deadline:
    connection = db()
    run = connection.execute(
        "select id,status,outcome,failure_reason,provider_key,model_key,started_at,completed_at "
        "from agent_runs where journey_id=? and id != 'c186a76f-9afa-42b9-8bd5-dc597a9af5f0' "
        "order by created_at desc limit 1", (journey_id,)
    ).fetchone()
    current_run = dict(run) if run else None
    if current_run != last:
        note("RUN " + json.dumps(current_run, ensure_ascii=False))
        last = current_run
    if current_run and current_run["status"] not in {"RUNNING", "PENDING"}:
        break
    time.sleep(15)
note("ELAPSED_S " + str(int(time.time() - started)))

connection = db()
for row in connection.execute(
    "select id,status,decision,action_status,agent_run_id,proposal_id,active_plan_before_id,active_plan_after_id,reasoning_summary "
    "from guardian_runs where journey_id=? order by created_at desc limit 1", (journey_id,)
):
    note("GUARDIAN_RUN " + json.dumps(dict(row), ensure_ascii=False, default=str)[:1400])
for row in connection.execute(
    "select id,base_plan_version_id,proposed_plan_version_id,status,hard_constraints_passed,locked_commitments_preserved,"
    "utility_score,diff_json,explanation_json from replan_proposals where journey_id=? order by created_at desc limit 2",
    (journey_id,),
):
    item = dict(row)
    note("PROPOSAL " + json.dumps({k: item[k] for k in ("id", "base_plan_version_id", "proposed_plan_version_id",
        "status", "hard_constraints_passed", "locked_commitments_preserved", "utility_score")}, ensure_ascii=False))
    note("PROPOSAL_DIFF " + str(item.get("diff_json") or "")[:1200])
    note("PROPOSAL_EXPL " + str(item.get("explanation_json") or "")[:800])
run_id = (last or {}).get("id")
if run_id:
    for row in connection.execute(
        "select sequence_no,tool_name,status,result_json,arguments_json from agent_run_steps where run_id=? order by sequence_no",
        (run_id,),
    ):
        item = dict(row)
        note("STEP " + json.dumps({"n": item["sequence_no"], "tool": item["tool_name"], "status": item["status"],
                                   "args": str(item.get("arguments_json") or "")[:200],
                                   "result": str(item.get("result_json") or "")[:600]}, ensure_ascii=False))
print("\n".join(lines))
