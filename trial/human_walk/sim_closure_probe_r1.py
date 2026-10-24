"""Second cut, first half: inject a simulated closure at the next stop of the ACTIVE journey,
run one real Guardian pulse, and read what the server actually did (events, runs, proposals)."""
from __future__ import annotations

import io
import json
import sqlite3
import urllib.error
import urllib.request

DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_play_1024.db"
API = "http://127.0.0.1:60361"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/sim-closure-1.txt"
lines: list[str] = []


def note(value: str) -> None:
    lines.append(value)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def call(method: str, path: str, body: dict | None = None, timeout: int = 240) -> tuple[int, dict]:
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


connection = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
connection.row_factory = sqlite3.Row
journey = connection.execute(
    "select id from journeys where status='ACTIVE' order by updated_at desc limit 1"
).fetchone()
if journey is None:
    note("NO_ACTIVE_JOURNEY")
    print("\n".join(lines))
    raise SystemExit(0)
journey_id = journey["id"]
note("JOURNEY " + journey_id)

plan = connection.execute(
    "select active_plan_version_id from journeys where id=?", (journey_id,)
).fetchone()["active_plan_version_id"]
activities = list(connection.execute(
    "select sequence_no, title, place_id, status from activities where plan_version_id=? order by sequence_no",
    (plan,),
))
for item in activities:
    note("ACTIVITY " + json.dumps(dict(item), ensure_ascii=False))
current = next((a for a in activities if a["status"] in {"ACTIVE", "EN_ROUTE", "ARRIVED", "IN_PROGRESS"}), activities[0] if activities else None)
target = next((a for a in activities if current and a["sequence_no"] > current["sequence_no"] and a["place_id"]), None)
place_id = (target or current)["place_id"] if (target or current) else None
note("TARGET " + json.dumps({"title": (target or current)["title"] if (target or current) else None,
                             "place_id": place_id}, ensure_ascii=False))

status, fixture = call("POST", f"/api/v1/journeys/{journey_id}/guardian/provider-fixture",
                       {"state": "DISRUPTED", "payload": {"target_place_id": place_id, "cause": "SCENARIO_INJECTED_CLOSURE"}})
note("FIXTURE " + json.dumps({"status": status, "fixture": fixture}, ensure_ascii=False)[:600])

status, pulse = call("POST", f"/api/v1/journeys/{journey_id}/guardian/pulse")
note("PULSE " + json.dumps({"status": status, "summary_keys": sorted(pulse.keys())}, ensure_ascii=False))
note("PULSE_BODY " + json.dumps(pulse, ensure_ascii=False)[:3000])

for query, label in [
    ("select id,status,started_at,finished_at,result_json from guardian_pulses where journey_id=? order by started_at desc limit 2", "PULSE_ROW"),
    ("select id,event_type,severity,status,occurred_at,payload_json from events where journey_id=? order by occurred_at desc limit 4", "EVENT"),
    ("select id,status,started_at,finished_at,intent_json from agent_runs where journey_id=? order by started_at desc limit 2", "RUN"),
    ("select id,status,plan_version_id,reason_code,created_at from replan_proposals where journey_id=? order by created_at desc limit 3", "PROPOSAL"),
]:
    try:
        rows = list(connection.execute(query, (journey_id,)))
    except sqlite3.Error as error:
        note(label + "_ERR " + str(error))
        continue
    for row in rows:
        note(label + " " + json.dumps(dict(row), ensure_ascii=False)[:900])
print("\n".join(lines))
