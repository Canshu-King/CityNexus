"""Drive the SimulationRun guardian path on an isolated stage, with a real model.

Starts (or reuses) a run, injects a closure on the current stop, hands the
event to the guardian, and prints what the contract records: the run status,
the guardian outcome fields, the history tail, and how long the model path took.
The bearer is never printed.

Usage:
  python _simulation_guardian_model_r1.py --base http://127.0.0.1:60396 \
      --db D:/moodle/_codex_probe_1025/probe2_1025.db [--timeout 480]
"""

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(base, method, path, body=None, token=None, key=None, timeout=120):
    request = urllib.request.Request(base + path, method=method)
    if body is not None:
        request.data = json.dumps(body).encode()
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    if key:
        request.add_header("Idempotency-Key", key)
    try:
        with OPENER.open(request, timeout=timeout) as answer:
            raw = answer.read().decode()
            return answer.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:500]


def current_stop(database, journey, state):
    completed = set((state or {}).get("completed_activity_ids") or [])
    plan = (state or {}).get("plan_version_id")
    connection = sqlite3.connect(database)
    try:
        rows = connection.execute(
            "select id, title from activities where plan_version_id=? "
            "and status not in ('COMPLETED','SKIPPED','CANCELLED') order by start_at",
            (plan,),
        ).fetchall()
    finally:
        connection.close()
    for activity_id, title in rows:
        if activity_id not in completed:
            return activity_id, title
    return None, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:60396")
    parser.add_argument("--db", required=True)
    parser.add_argument("--timeout", type=float, default=480)
    args = parser.parse_args()

    status, session = call(args.base, "GET", "/api/v1/demo/session")
    if status != 200 or not isinstance(session, dict):
        print("SESSION_FAILED", status, str(session)[:300])
        return 1
    token = session["access_token"]
    journey = session["journey_id"]
    print("SESSION journey=%s" % journey)

    status, current = call(args.base, "GET", "/api/v1/journeys/%s/simulation/runs/current" % journey, token=token)
    if status != 200 or not isinstance(current, dict):
        print("CURRENT_FAILED", status, str(current)[:300])
        return 1
    if current.get("status") == "NOT_STARTED":
        status, run = call(args.base, "POST", "/api/v1/journeys/%s/simulation/runs" % journey,
                           {"seed": 41}, token, "model-start-" + uuid.uuid4().hex[:8])
        if status != 201:
            print("START_FAILED", status, str(run)[:400])
            return 1
        print("START status=%s seq=%d" % (run["status"], run["sequence"]))
    else:
        run = current
        print("RUN_REUSED status=%s seq=%d" % (run["status"], run["sequence"]))

    if run["status"] == "RUNNING":
        stop_id, stop_title = current_stop(args.db, journey, run.get("state"))
        if not stop_id:
            print("NO_CURRENT_STOP")
            return 1
        status, run = call(args.base, "POST", "/api/v1/journeys/%s/simulation/runs/%s/scenes" % (journey, run["run_id"]),
                           {"expected_sequence": run["sequence"], "scene_id": "model-closure-" + uuid.uuid4().hex[:4],
                            "event_type": "CLOSURE", "activity_id": stop_id},
                           token, "model-scene-" + uuid.uuid4().hex[:8])
        if status != 200:
            print("SCENE_FAILED", status, str(run)[:400])
            return 1
        print("SCENE stop=%s status=%s seq=%d" % (stop_title, run["status"], run["sequence"]))

    print("GUARDIAN_CALL status_before=%s seq=%d timeout=%ds" % (run["status"], run["sequence"], args.timeout))
    started = time.monotonic()
    status, guardian = call(args.base, "POST", "/api/v1/journeys/%s/simulation/runs/%s/guardian" % (journey, run["run_id"]),
                            {"expected_sequence": run["sequence"], "model_consent": True},
                            token, "model-guardian-" + uuid.uuid4().hex[:8], timeout=args.timeout)
    elapsed = time.monotonic() - started
    print("GUARDIAN_HTTP http=%s elapsed=%.1fs" % (status, elapsed))
    if status != 200 or not isinstance(guardian, dict):
        print("GUARDIAN_FAILED", str(guardian)[:500])
        return 1
    print("GUARDIAN_RUN status=%s seq=%d" % (guardian.get("status"), guardian.get("sequence")))
    for step in (guardian.get("history") or [])[-3:]:
        print("HISTORY %s" % json.dumps(step, ensure_ascii=False)[:600])
    state = guardian.get("state") or {}
    for field in ("suggested_scene", "pending_event_id", "guardian_lease_expires_at"):
        if field in state:
            print("STATE %s=%s" % (field, state[field]))
    execution = (guardian.get("execution_truth") or {})
    print("EXECUTION_TRUTH %s" % json.dumps(execution, ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
