"""Accept the proposal the isolated backend just presented, and read the Journey back.

The second half of the sandbox cut: a presented recovery proposal becomes the active PlanVersion on
the same Journey only when the traveller agrees.  Runnable evidence, not a request log: it prints the
proposal status, the Journey's active plan before and after, and every plan version's status.
"""
from __future__ import annotations

import io
import json
import sqlite3
import urllib.error
import urllib.request

DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_simmerge_1025.db"
API = "http://127.0.0.1:60391"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/sim-replan-accept-1.txt"
lines: list[str] = []


def note(value: str) -> None:
    lines.append(value)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def call(method: str, path: str, body: dict | None = None, headers: dict | None = None,
         timeout: int = 120) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(API + path, data=data, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
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
proposal = connection.execute(
    "select id, proposed_plan_version_id, status from replan_proposals "
    "where journey_id=? order by created_at desc limit 1",
    (journey_id,),
).fetchone()
note("JOURNEY " + journey_id)
note("BEFORE_ACTIVE " + str(journey["plan"]))
note("PROPOSAL " + json.dumps(dict(proposal), ensure_ascii=False))

status, answer = call(
    "POST",
    f"/api/v1/replans/{proposal['id']}/accept",
    body=None,
    headers={"Idempotency-Key": "sim-accept-probe-" + proposal["id"][:8]},
)
note("ACCEPT status=%s" % status)
note("BODY " + json.dumps(answer, ensure_ascii=False)[:1500])

after = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
after.row_factory = sqlite3.Row
journey_after = after.execute(
    "select active_plan_version_id as plan from journeys where id=?", (journey_id,)
).fetchone()
note("AFTER_ACTIVE " + str(journey_after["plan"]))
note("PROPOSAL_STATUS " + str(after.execute(
    "select status from replan_proposals where id=?", (proposal["id"],)
).fetchone()["status"]))
for row in after.execute(
    "select id, status, version_no from plan_versions where journey_id=? order by created_at",
    (journey_id,),
):
    note("PLAN " + json.dumps(dict(row), ensure_ascii=False))
note("ACTIVE_MOVED " + json.dumps({
    "before": journey["plan"],
    "after": journey_after["plan"],
    "proposed": proposal["proposed_plan_version_id"],
    "is_expected": journey_after["plan"] == proposal["proposed_plan_version_id"],
}, ensure_ascii=False))
