"""Prove the AI switch stops Guardian before any work, on an isolated copy.

Creates a canary copy of the classroom DB, starts its own backend on 60410 with
CITYNEXUS_AI_ENABLED=false, drives run -> scene -> guardian over HTTP, and checks
that the switch answers fast, leaves the sequence alone and creates no guardian
run. The classroom stack on 60391/14492 is not touched.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
LIVE = r"D:/moodle/_cmdr_v3_live_1022"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SOURCE_DB = os.path.join(LIVE, "citynexus_v3_demo_1025.db")
CANARY_DB = os.path.join(LIVE, "canary_ai_off_1026.db")
LOG = os.path.join(LIVE, "uvicorn_ai_off_1026.log")
OUT = os.path.join(ROOT, "trial", "results", "20261022_v3_human_chrome", "ai-off-guardian-86.txt")
PORT = 60410
KEY = "ai-off-presenter-key-1026-0123456789abcdef0123456789abcdef"
SECRET = "ai-off-traveler-secret-1026-0123456789abcdef0123456789abcdef"

lines = []


def note(label, value):
    lines.append("%s %s" % (label, json.dumps(value, ensure_ascii=False, sort_keys=True)))
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def request(path, method="GET", body=None, headers=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    merged = {"Accept": "application/json"}
    if data is not None:
        merged["Content-Type"] = "application/json"
    merged.update(headers or {})
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), data=data, headers=merged, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as answer:
            raw = answer.read().decode("utf-8")
            return answer.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as caught:
        raw = caught.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else None
        except ValueError:
            parsed = {"raw": raw[:200]}
        return caught.code, parsed


def active_journey(db):
    conn = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
    try:
        row = conn.execute(
            "select id, current_activity_id from journeys where status='ACTIVE' order by rowid desc limit 1"
        ).fetchone()
        return (row[0], row[1]) if row else (None, None)
    finally:
        conn.close()


def main() -> int:
    for path in (OUT, CANARY_DB, CANARY_DB + "-wal", CANARY_DB + "-shm", LOG):
        if os.path.exists(path):
            os.remove(path)
    if not os.path.exists(SOURCE_DB):
        note("ERROR", {"missing": SOURCE_DB})
        return 1
    shutil.copy2(SOURCE_DB, CANARY_DB)
    journey_id, activity_id = active_journey(CANARY_DB)
    note("CANARY", {"db": os.path.basename(CANARY_DB), "journey_id": journey_id,
                    "activity_id": activity_id, "bytes": os.path.getsize(CANARY_DB)})
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + CANARY_DB.replace("\\", "/"),
        "CITYNEXUS_TRAVELER_AUTH_SECRET": SECRET,
        "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": "3600",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_DEMO_PRESENTER_KEY": KEY,
        "CITYNEXUS_DEMO_DATABASE_PATH": CANARY_DB,
        "CITYNEXUS_SIMULATION_ENABLED": "true",
        "CITYNEXUS_AI_ENABLED": "false",
        "PYTHONPATH": os.path.join(ROOT, "backend"),
    })
    handle = open(LOG, "wb")
    process = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT),
         "--app-dir", os.path.join(ROOT, "backend")],
        cwd=os.path.join(ROOT, "backend"), env=env, stdout=handle, stderr=subprocess.STDOUT,
    )
    try:
        ready = False
        for _ in range(120):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/api/v1/health" % PORT, timeout=3) as answer:
                    ready = answer.status == 200
            except Exception:
                ready = False
            if ready:
                break
            time.sleep(1)
        note("HEALTH", {"ready": ready})
        if not ready or not journey_id:
            return 1
        status, pairing = request("/api/v1/demo/pairing", "POST", {"journey_id": journey_id},
                                  {"X-CityNexus-Presenter-Key": KEY})
        note("PAIRING", {"status": status, "has_ticket": bool((pairing or {}).get("ticket")),
                         "error": (pairing or {}).get("error")})
        if status not in (200, 201):
            return 1
        status, redeemed = request("/api/v1/demo/pairing/redeem", "POST", {"ticket": pairing["ticket"]})
        note("REDEEM", {"status": status, "has_token": bool((redeemed or {}).get("access_token")),
                        "error": (redeemed or {}).get("error")})
        if status not in (200, 201):
            return 1
        token = redeemed["access_token"]
        auth = {"Authorization": "Bearer " + token, "Idempotency-Key": "ai-off-%d" % int(time.time())}
        base = "/api/v1/journeys/%s/simulation" % journey_id
        status, run = request(base + "/runs", "POST", {"seed": 17}, auth)
        note("START", {"status": status, "state": (run or {}).get("status"), "sequence": (run or {}).get("sequence"),
                       "error": (run or {}).get("error")})
        if status not in (200, 201):
            return 1
        run_id = run["run_id"]
        auth["Idempotency-Key"] = "ai-off-scene-%d" % int(time.time())
        status, scene = request(base + "/runs/%s/scenes" % run_id, "POST",
                                {"expected_sequence": run["sequence"], "scene_id": "closure-ai-off",
                                 "event_type": "CLOSURE", "activity_id": activity_id}, auth)
        note("SCENE", {"status": status, "state": (scene or {}).get("status"),
                       "sequence": (scene or {}).get("sequence"), "error": (scene or {}).get("error")})
        if status not in (200, 201):
            return 1
        before_sequence = scene["sequence"]
        auth["Idempotency-Key"] = "ai-off-guardian-%d" % int(time.time())
        began = time.time()
        status, guardian = request(base + "/runs/%s/guardian" % run_id, "POST",
                                   {"expected_sequence": before_sequence, "model_consent": True}, auth)
        guardian_http = status
        elapsed = round(time.time() - began, 2)
        note("GUARDIAN", {"status": status, "elapsed_s": elapsed,
                          "error_code": ((guardian or {}).get("error") or {}).get("code"),
                          "error_message": ((guardian or {}).get("error") or {}).get("message"),
                          "state": (guardian or {}).get("status") if status == 200 else None})
        status, current = request(base + "/runs/current", headers={"Authorization": "Bearer " + token})
        note("CURRENT_AFTER", {"status": status, "run_status": (current or {}).get("status"),
                               "sequence": (current or {}).get("sequence"),
                               "sequence_unchanged": (current or {}).get("sequence") == before_sequence})
        status, progress = request(base + "/runs/%s/progress" % run_id,
                                   headers={"Authorization": "Bearer " + token})
        readiness = (progress or {}).get("readiness") or {}
        note("PROGRESS", {"status": status, "ai_enabled": readiness.get("ai_enabled"),
                          "missing": readiness.get("missing"),
                          "guardian_runs": len((progress or {}).get("guardian_runs") or []),
                          "guardian_outcome": (progress or {}).get("guardian_outcome")})
        verdict = (
            status == 200
            and guardian is not None
            and ((guardian or {}).get("error") or {}).get("message") == "SIMULATION_AI_DISABLED"
            and (current or {}).get("sequence") == before_sequence
            and (current or {}).get("status") == "PAUSED_FOR_GUARDIAN"
            and len((progress or {}).get("guardian_runs") or []) == 0
            and readiness.get("ai_enabled") is False
            and "AI_DISABLED" in (readiness.get("missing") or [])
        )
        note("VERDICT", {"ai_switch_stops_guardian": bool(verdict),
                         "guardian_http": guardian_http})
        try:
            tail = open(LOG, "rb").read()[-4000:].decode("utf-8", errors="replace")
            tracebacks = tail.count("Traceback (most recent call last)")
        except OSError:
            tracebacks = -1
        note("SERVER_LOG", {"tracebacks": tracebacks})
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except Exception:
            process.kill()
        handle.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
