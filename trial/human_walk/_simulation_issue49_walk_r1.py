"""Walk Issue #49 end to end on an isolated stage: scene, real guardian, native accept, resume.

The walk uses the presenter ticket flow, the same run, and the native accept endpoint.
It prints status codes and counts only; the bearer, the presenter key and the ticket are
never printed.

Usage:
  python _simulation_issue49_walk_r1.py --base http://127.0.0.1:60398 \
      --key <presenter key> --db D:/moodle/_codex_probe_1025/probe4_1025.db
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


def call(base, method, path, body=None, token=None, key=None, presenter=None, timeout=120):
    request = urllib.request.Request(base + path, method=method)
    if body is not None:
        request.data = json.dumps(body).encode()
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    if key:
        request.add_header("Idempotency-Key", key)
    if presenter:
        request.add_header("X-CityNexus-Presenter-Key", presenter)
    try:
        with OPENER.open(request, timeout=timeout) as answer:
            raw = answer.read().decode()
            return answer.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:400]


def current_stop(database, plan):
    connection = sqlite3.connect(database)
    try:
        rows = connection.execute(
            "select id, title from activities where plan_version_id=? "
            "and status not in ('COMPLETED','SKIPPED','CANCELLED') order by start_at",
            (plan,),
        ).fetchall()
    finally:
        connection.close()
    return rows[0] if rows else (None, None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:60398")
    parser.add_argument("--key", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--timeout", type=float, default=480)
    args = parser.parse_args()

    status, session = call(args.base, "GET", "/api/v1/demo/session")
    print("SESSION_WITHOUT_TICKET http=%s" % status)

    status, pair = call(args.base, "POST", "/api/v1/demo/pairing",
                        {"journey_id": "2e9cd67d-10ca-4ecd-920b-76c81a350c71"}, presenter=args.key)
    if status != 201:
        print("PAIRING_FAILED", status, str(pair)[:300])
        return 1
    status, redeemed = call(args.base, "POST", "/api/v1/demo/pairing/redeem", {"ticket": pair["ticket"]})
    if status != 200:
        print("REDEEM_FAILED", status, str(redeemed)[:300])
        return 1
    token = redeemed["access_token"]
    journey = redeemed["journey_id"]
    print("PAIRING_OK journey=%s token_len=%d" % (journey, len(token)))

    status, current = call(args.base, "GET", "/api/v1/journeys/%s/simulation/runs/current" % journey, token=token)
    print("CURRENT http=%s status=%s" % (status, current.get("status") if isinstance(current, dict) else current))
    if current.get("status") == "NOT_STARTED":
        status, run = call(args.base, "POST", "/api/v1/journeys/%s/simulation/runs" % journey,
                           {"seed": 47}, token, "i49-start-" + uuid.uuid4().hex[:8])
        if status != 201:
            print("START_FAILED", status, str(run)[:300])
            return 1
    else:
        run = current
    print("RUN status=%s seq=%d" % (run.get("status"), run.get("sequence")))

    plan = (run.get("state") or {}).get("plan_version_id")
    activity_id, title = current_stop(args.db, plan)
    if not activity_id:
        print("NO_CURRENT_STOP")
        return 1
    status, scene = call(args.base, "POST", "/api/v1/journeys/%s/simulation/runs/%s/scenes" % (journey, run["run_id"]),
                         {"expected_sequence": run["sequence"], "scene_id": "i49-closure-" + uuid.uuid4().hex[:4],
                          "event_type": "CLOSURE", "activity_id": activity_id},
                         token, "i49-scene-" + uuid.uuid4().hex[:8])
    print("SCENE http=%s stop=%s status=%s" % (status, title, scene.get("status") if isinstance(scene, dict) else scene))
    if status != 200:
        return 1
    sequence = scene["sequence"]

    started = time.monotonic()
    status, guardian = call(args.base, "POST", "/api/v1/journeys/%s/simulation/runs/%s/guardian" % (journey, run["run_id"]),
                            {"expected_sequence": sequence, "model_consent": True},
                            token, "i49-guardian-" + uuid.uuid4().hex[:8], timeout=args.timeout)
    elapsed = time.monotonic() - started
    print("GUARDIAN http=%s elapsed=%.1fs status=%s" % (
        status, elapsed, guardian.get("status") if isinstance(guardian, dict) else str(guardian)[:200]))
    if status != 200:
        return 1
    sequence = guardian["sequence"]

    status, progress = call(args.base, "GET", "/api/v1/journeys/%s/simulation/runs/%s/progress" % (journey, run["run_id"]), token=token)
    if status == 200 and isinstance(progress, dict):
        proposals = progress.get("proposals") or []
        print("PROGRESS http=200 guardian_runs=%d agent_runs=%d steps=%d proposals=%d readiness=%s" % (
            len(progress.get("guardian_runs") or []), len(progress.get("agent_runs") or []),
            len(progress.get("steps") or []), len(proposals), json.dumps(progress.get("readiness") or {})[:160]))
        proposal_id = (proposals[0].get("id") or proposals[0].get("proposal_id")) if proposals else None
    else:
        print("PROGRESS_FAILED", status, str(progress)[:240])
        proposal_id = None
    if not proposal_id:
        print("NO_PROPOSAL — stop here, the guardian produced nothing to accept.")
        return 2

    status, accepted = call(args.base, "POST", "/api/v1/replans/%s/accept" % proposal_id,
                            None, token, "i49-accept-" + uuid.uuid4().hex[:8])
    print("ACCEPT http=%s" % status)
    if status not in (200, 201):
        print("ACCEPT_BODY", str(accepted)[:300])
        return 1

    status, progress = call(args.base, "GET", "/api/v1/journeys/%s/simulation/runs/%s/progress" % (journey, run["run_id"]), token=token)
    if status == 200 and isinstance(progress, dict):
        audit = [p.get("acceptance_audit_ids") for p in (progress.get("proposals") or [])]
        print("PROGRESS_AFTER_ACCEPT audits=%s" % json.dumps(audit)[:200])

    status, latest = call(args.base, "GET", "/api/v1/journeys/%s/simulation/runs/%s" % (journey, run["run_id"]), token=token)
    if status != 200:
        print("RUN_READ_FAILED", status, str(latest)[:200])
        return 1
    status, resumed = call(args.base, "POST", "/api/v1/journeys/%s/simulation/runs/%s/resume" % (journey, run["run_id"]),
                           {"expected_sequence": latest["sequence"]}, token, "i49-resume-" + uuid.uuid4().hex[:8])
    print("RESUME http=%s status=%s" % (status, resumed.get("status") if isinstance(resumed, dict) else str(resumed)[:200]))
    if status != 200:
        return 1

    sequence = resumed["sequence"]
    for step in range(1, 13):
        status, advanced = call(args.base, "POST", "/api/v1/journeys/%s/simulation/runs/%s/advance" % (journey, run["run_id"]),
                                {"expected_sequence": sequence}, token, "i49-adv-" + uuid.uuid4().hex[:8])
        if status != 200:
            print("ADVANCE_FAILED step=%d http=%s %s" % (step, status, str(advanced)[:200]))
            return 1
        sequence = advanced["sequence"]
        print("ADVANCE_%02d status=%s vnow=%s done=%d" % (
            step, advanced["status"], advanced["virtual_now"],
            len((advanced.get("state") or {}).get("completed_activity_ids") or [])))
        if advanced["status"] == "SIMULATED_COMPLETED":
            print("TWO_DAY_WALK_OK")
            return 0
    print("TWO_DAY_WALK_INCOMPLETE")
    return 1


if __name__ == "__main__":
    sys.exit(main())
