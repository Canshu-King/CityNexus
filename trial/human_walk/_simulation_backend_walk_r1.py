"""Walk the Codex SimulationRun API against an isolated stage backend.

The backend is a throwaway copy of the classroom database on a spare port with
no model keys, so this probe can show what the contract does without touching
the running classroom stack.  It never prints the bearer.

Usage:
  python _simulation_backend_walk_r1.py --base http://127.0.0.1:60396 \
      --db D:/moodle/_codex_probe_1025/probe2_1025.db [--seed 23]
"""

import argparse
import json
import sqlite3
import sys
import urllib.error
import urllib.request
import uuid

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(base, method, path, body=None, token=None, key=None):
    request = urllib.request.Request(base + path, method=method)
    if body is not None:
        request.data = json.dumps(body).encode()
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    if key:
        request.add_header("Idempotency-Key", key)
    try:
        with OPENER.open(request, timeout=90) as answer:
            raw = answer.read().decode()
            return answer.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:600]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:60396")
    parser.add_argument("--db", required=True)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    status, session = call(args.base, "GET", "/api/v1/demo/session")
    if status != 200 or not isinstance(session, dict):
        print("SESSION_FAILED", status, str(session)[:300])
        return 1
    token = session["access_token"]
    journey = session["journey_id"]
    print("SESSION journey=%s title=%s" % (journey, session.get("journey_title")))

    status, cities = call(args.base, "GET", "/api/v1/journeys/%s/simulation/cities?seed=%d" % (journey, args.seed), token=token)
    if status == 200 and isinstance(cities, dict):
        print("CITIES status=%s eligible=%s required=%s blocked=%d" % (
            cities.get("status"), cities.get("eligible_city_count"),
            cities.get("required_city_count"), len(cities.get("cities") or [])))
        for item in cities.get("cities") or []:
            print("  CITY %s %s missing=%s" % (item.get("city_code"), item.get("status"), ",".join(item.get("missing") or [])))
    else:
        print("CITIES_FAILED", status, str(cities)[:300])

    status, current = call(args.base, "GET", "/api/v1/journeys/%s/simulation/runs/current" % journey, token=token)
    current_status = current.get("status") if isinstance(current, dict) else None
    print("CURRENT http=%s status=%s" % (status, current_status))
    if current_status == "NOT_STARTED":
        status, run = call(args.base, "POST", "/api/v1/journeys/%s/simulation/runs" % journey, {"seed": args.seed}, token, "walk-start-" + uuid.uuid4().hex[:8])
        if status != 201 or not isinstance(run, dict):
            print("START_FAILED", status, str(run)[:400])
            return 1
        print("START http=201 status=%s seq=%d city=%s vnow=%s" % (run["status"], run["sequence"], run["city_code"], run["virtual_now"]))
    else:
        status, run = call(args.base, "GET", "/api/v1/journeys/%s/simulation/runs/%s" % (journey, current["run_id"]), token=token)
        if status != 200 or not isinstance(run, dict):
            print("RUN_READ_FAILED", status, str(run)[:400])
            return 1
        print("RUN_REUSED status=%s seq=%d vnow=%s" % (run["status"], run["sequence"], run["virtual_now"]))
    run_id, sequence = run["run_id"], run["sequence"]

    database = sqlite3.connect(args.db)
    plan = database.execute("select active_plan_version_id from journeys where id=?", (journey,)).fetchone()[0]
    rows = database.execute(
        "select id, title from activities where plan_version_id=? "
        "and status not in ('COMPLETED','SKIPPED','CANCELLED') order by start_at limit 1", (plan,)
    ).fetchall()
    database.close()
    if not rows:
        print("NO_ACTIVITY for plan", plan)
        return 1
    activity_id, activity_title = rows[0]
    print("ACTIVITY %s %s" % (activity_id, activity_title))

    status, scene = call(args.base, "POST", "/api/v1/journeys/%s/simulation/runs/%s/scenes" % (journey, run_id),
                         {"expected_sequence": sequence, "scene_id": "walk-closure-" + uuid.uuid4().hex[:4], "event_type": "CLOSURE",
                          "activity_id": activity_id}, token, "walk-scene-" + uuid.uuid4().hex[:8])
    if status != 200 or not isinstance(scene, dict):
        print("SCENE_FAILED", status, str(scene)[:400])
        return 1
    sequence = scene["sequence"]
    print("SCENE http=200 status=%s seq=%d vnow=%s" % (scene["status"], sequence, scene["virtual_now"]))
    print("  HISTORY %s" % json.dumps((scene.get("history") or [])[-2:], ensure_ascii=False)[:400])

    status, guardian = call(args.base, "POST", "/api/v1/journeys/%s/simulation/runs/%s/guardian" % (journey, run_id),
                            {"expected_sequence": sequence, "model_consent": True}, token, "walk-guardian-" + uuid.uuid4().hex[:8])
    print("GUARDIAN http=%s %s" % (status, json.dumps(guardian, ensure_ascii=False)[:700] if isinstance(guardian, (dict, list)) else str(guardian)[:400]))
    if status == 200 and isinstance(guardian, dict):
        print("  GUARDIAN status=%s seq=%s model_execution=%s" % (
            guardian.get("status"), guardian.get("sequence"), guardian.get("model_execution")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
