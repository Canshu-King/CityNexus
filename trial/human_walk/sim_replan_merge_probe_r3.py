"""Does replan still call the selected plan's measured leg ineligible after the baseline reuse?

Runs against the isolated copy of the play database on port 60391.  The journey's active plan froze two
live AMap legs; the closure event targets one stop and offers a newly discovered museum as the
replacement.  Before the fix the gap named a *baseline* pair as SYNTHETIC_DEFAULT; the reading here is
which pairs the endpoint still refuses.
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import urllib.error
import urllib.request

DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_simmerge_1025.db"
API = "http://127.0.0.1:60391"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/sim-replan-merge-3.txt"
lines: list[str] = []


def note(value: str) -> None:
    lines.append(value)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def call(method: str, path: str, body: dict | None = None, timeout: int = 240) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(API + path, data=data, method=method)
    if os.environ.get("SIM_TOKEN"):
        request.add_header("Authorization", "Bearer " + os.environ["SIM_TOKEN"])
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
            payload = {"raw": raw[:500]}
        return error.code, payload


connection = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
connection.row_factory = sqlite3.Row
journey = connection.execute(
    "select id, active_plan_version_id as plan from journeys where status='ACTIVE' order by updated_at desc limit 1"
).fetchone()
journey_id = journey["id"]
note("JOURNEY " + journey_id)
activities = list(connection.execute(
    "select sequence_no,title,place_id,status from activities where plan_version_id=? order by sequence_no",
    (journey["plan"],),
))
for activity in activities:
    note("ACTIVITY " + json.dumps(dict(activity), ensure_ascii=False))
events = list(connection.execute(
    "select id,event_type,affected_activity_id,detected_at from events where journey_id=? order by detected_at desc limit 6",
    (journey_id,),
))
for event in events:
    note("EVENT " + json.dumps(dict(event), ensure_ascii=False))
closure = next((row for row in events if row["event_type"] == "CLOSURE"), None)
if closure is None:
    note("NO_CLOSURE_EVENT")
    raise SystemExit(1)
plan_evidence = json.loads(connection.execute(
    "select mobility_evidence_json from plan_versions where id=?", (journey["plan"],)
).fetchone()[0] or "{}")
baseline_pairs = {
    (str(fact.get("origin_key")), str(fact.get("destination_key")))
    for fact in plan_evidence.get("facts") or []
    if isinstance(fact, dict)
}
note("BASELINE_PAIRS " + json.dumps(sorted(baseline_pairs)))
note("BASELINE_QUALITIES " + json.dumps(sorted({
    str(fact.get("fact_quality")) for fact in plan_evidence.get("facts") or [] if isinstance(fact, dict)
})))
attempt = connection.execute(
    "select deep_candidate_ids_json, materialized_place_ids_json from recovery_discovery_attempts "
    "where journey_id=? order by created_at desc limit 1",
    (journey_id,),
).fetchone()
if attempt is not None:
    for raw in attempt:
        try:
            candidates = json.loads(raw or "[]")
        except ValueError:
            candidates = []
        if candidates:
            break
note("CANDIDATES " + json.dumps(candidates[:6]))
place_ids = candidates[:3] if candidates else ["real-place-1c83a042cf4c732762837c63"]

status, answer = call("POST", f"/api/v1/journeys/{journey_id}/replans", {
    "trigger_event_id": closure["id"],
    "candidate_count": 3,
    "place_ids": place_ids,
})
note("REPLAN status=%s" % status)
note("BODY " + json.dumps(answer, ensure_ascii=False)[:4000])
gaps = ((answer.get("error") or {}).get("details") or {}).get("gaps") if isinstance(answer, dict) else None
if gaps:
    pairs = [(gap.get("from_place_id"), gap.get("to_place_id")) for gap in gaps]
    note("GAP_PAIRS " + json.dumps(pairs))
    note("GAP_QUALITIES " + json.dumps([gap.get("fact_quality") for gap in gaps]))
    note("BASELINE_PAIR_STILL_REFUSED " + json.dumps(
        str(any(pair in baseline_pairs for pair in pairs))
    ))
note("VERDICT " + json.dumps({
    "status": status,
    "gaps_total": ((answer.get("error") or {}).get("details") or {}).get("gaps_total"),
    "proposal_id": answer.get("id") if status == 201 else None,
}, ensure_ascii=False))
