"""One guardian pulse on the demo stack, measured: latency, agent runtime, what the DB gained.

Read-only except the pulse itself (which is the product's own server-side cycle). No mock:
if the model is unavailable the receipt says so instead of pretending a run happened.
"""
import json
import sqlite3
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:60391/api/v1"
JOURNEY = "2e9cd67d-10ca-4ecd-920b-76c81a350c71"
DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_demo_1025.db"


def post(path, body, token=None, timeout=300):
    request = urllib.request.Request(
        API + path, data=json.dumps(body).encode("utf-8"), method="POST"
    )
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            return answer.status, json.loads(answer.read().decode("utf-8") or "{}"), time.time() - started
    except urllib.error.HTTPError as error:
        return error.code, {"raw": error.read().decode("utf-8")[:300]}, time.time() - started


def counts():
    db = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    try:
        return {
            "pulses": db.execute("select count(*) from guardian_pulses").fetchone()[0],
            "agent_runs": db.execute("select count(*) from agent_runs").fetchone()[0],
            "proposals": db.execute("select count(*) from replan_proposals").fetchone()[0],
        }
    finally:
        db.close()


session_status, session_body, _ = post("/demo/session", {}, timeout=30)
token = session_body.get("access_token")
before = counts()
pulse_code, body, seconds = post("/journeys/%s/guardian/pulse" % JOURNEY, {}, token)
after = counts()

db = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
db.row_factory = sqlite3.Row
latest = db.execute(
    "select status, started_at, completed_at, result_json from guardian_pulses order by started_at desc limit 1"
).fetchone()
proposal = db.execute(
    "select status, source_agent_run_id, created_at from replan_proposals order by created_at desc limit 1"
).fetchone()
db.close()

result = json.loads(latest["result_json"] or "{}") if latest else {}
agent_runtime = result.get("agent_runtime") or {}
print(json.dumps({
    "session_http": session_status,
    "pulse_http": pulse_code,
    "pulse_seconds": round(seconds, 1),
    "counts_before": before,
    "counts_after": after,
    "returned_keys": sorted(body.keys()),
    "returned_status": body.get("status") or body.get("pulse", {}).get("status"),
    "returned_decision": (body.get("guardian") or {}).get("decision"),
    "pulse_status": latest["status"] if latest else None,
    "pulse_agent_runtime": agent_runtime if agent_runtime else None,
    "pulse_result_keys": sorted(result.keys()),
    "latest_proposal": dict(proposal) if proposal else None,
}, ensure_ascii=False, indent=1))
