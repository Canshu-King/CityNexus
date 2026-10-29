"""Does the Guardian pause the run honestly when no model is configured?

Read-only copy of the live classroom DB; a standing mission is created, one CLOSURE
scene is injected, then the Guardian endpoint is called. No model key is passed to
the isolated backend, so the expected answer is a pause, not a fabricated proposal.
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

WORK = r"D:/moodle/_codex_probe_1025"
BACKEND = r"D:/moodle/_cmdr_rescue_v3_1022/backend"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
API = "http://127.0.0.1:60400"
SOURCE_DB = r"D:/moodle/_cmdr_v3_live_1022/citynexus_v3_demo_1025.db"
TARGET_DB = WORK + "/probe23_live.db"
JOURNEY = "2e9cd67d-10ca-4ecd-920b-76c81a350c71"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/guardian-unavailable-67.txt"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def stop_backend() -> None:
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*--port 60400*' } | "
        "ForEach-Object { taskkill /PID $_.ProcessId /T /F }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)


def copy_db() -> None:
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(TARGET_DB + suffix):
            os.remove(TARGET_DB + suffix)
    source = sqlite3.connect("file:" + SOURCE_DB + "?mode=ro", uri=True)
    target = sqlite3.connect(TARGET_DB)
    try:
        source.backup(target)
        target.commit()
    finally:
        target.close()
        source.close()


def start_backend(presenter_key: str) -> subprocess.Popen:
    env = dict(os.environ)
    for name in ("CITYNEXUS_AI_API_KEY", "CITYNEXUS_HERMES_API_KEY", "CITYNEXUS_DEEPSEEK_API_KEY"):
        env.pop(name, None)
    env.update({
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + TARGET_DB,
        "CITYNEXUS_TRAVELER_AUTH_SECRET": "probe-isolated-5f3a9c1e7b2d4a6089f1c3e5d7b9a0f2",
        "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": "43200",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_DEMO_DATABASE_PATH": TARGET_DB,
        "CITYNEXUS_SIMULATION_ENABLED": "true",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_DEMO_PRESENTER_KEY": presenter_key,
        "PYTHONPATH": BACKEND,
    })
    log = open(WORK + "/guardian_backend.log", "wb")
    return subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "60400", "--app-dir", BACKEND],
        cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT,
    )


def req(method, path, body=None, token=None, key=None, headers=None):
    merged = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        merged["Content-Type"] = "application/json"
    if token:
        merged["Authorization"] = "Bearer " + token
    if key:
        merged["Idempotency-Key"] = key
    request = urllib.request.Request(API + path, data=data, method=method, headers=merged)
    try:
        with OPENER.open(request, timeout=120) as answer:
            raw = answer.read().decode()
            return answer.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        raw = error.read().decode()
        try:
            return error.code, json.loads(raw)
        except ValueError:
            return error.code, {"raw": raw[:200]}


def code(body: dict) -> str:
    err = body.get("error") or {}
    return str(err.get("message") or err.get("code") or "")


def first_open_activity() -> str:
    con = sqlite3.connect("file:" + TARGET_DB + "?mode=ro", uri=True)
    try:
        row = con.execute(
            "select a.id from activities a join journeys j on j.active_plan_version_id=a.plan_version_id "
            "where j.id=? and a.status not in ('COMPLETED','SKIPPED','CANCELLED') order by a.start_at limit 1",
            (JOURNEY,)).fetchone()
        return row[0] if row else ""
    finally:
        con.close()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stop_backend()
    time.sleep(2)
    copy_db()
    activity = first_open_activity()
    key = secrets.token_hex(24)
    proc = start_backend(key)
    out: dict = {"source": "read-only copy of the live classroom DB",
                 "activity": activity, "ai_enabled": False}
    try:
        for _ in range(90):
            try:
                with OPENER.open(API + "/api/v1/health", timeout=2) as answer:
                    if answer.status == 200:
                        break
            except Exception:
                time.sleep(1)
        status, ticket = req("POST", "/api/v1/demo/pairing", {"journey_id": JOURNEY},
                             headers={"X-CityNexus-Presenter-Key": key})
        status, redeemed = req("POST", "/api/v1/demo/pairing/redeem", {"ticket": ticket["ticket"]})
        token = redeemed["access_token"]
        base = "/api/v1/journeys/%s/simulation" % JOURNEY
        status, mission = req("PUT", "/api/v1/journeys/%s/guardian/mission" % JOURNEY,
                              {"command": "闭馆时给我一份替代安排，先确认。",
                               "requested_autonomy": "PLAN_ONLY"}, token=token)
        out["mission"] = {"http": status, "status": (mission.get("mission") or {}).get("status"),
                          "error": None if status < 400 else code(mission)}
        status, current = req("GET", base + "/runs/current", token=token)
        run = current
        out["before"] = {"sequence": run.get("sequence"), "status": run.get("status")}
        status, scene = req("POST", base + "/runs/%s/scenes" % run["run_id"],
                            {"expected_sequence": run["sequence"], "scene_id": "probe-closure-67",
                             "event_type": "CLOSURE", "activity_id": activity},
                            token=token, key="guard-scene-" + secrets.token_hex(4))
        out["scene"] = {"http": status,
                        "status": scene.get("status"),
                        "error": None if status == 200 else code(scene)}
        if status == 200:
            run = scene
        status, guardian = req("POST", base + "/runs/%s/guardian" % run["run_id"],
                               {"expected_sequence": run["sequence"], "model_consent": True},
                               token=token, key="guard-run-" + secrets.token_hex(4))
        out["guardian"] = {"http": status,
                           "status": guardian.get("status"),
                           "error": None if status == 200 else code(guardian)}
        status, after = req("GET", base + "/runs/current", token=token)
        out["after"] = {"sequence": after.get("sequence"), "status": after.get("status")}
        status, progress = req("GET", base + "/runs/%s/progress" % after["run_id"], token=token)
        out["progress"] = progress if status != 200 else {
            "status": progress.get("status"),
            "guardian_runs": progress.get("guardian_runs"),
            "proposals": progress.get("proposals"),
            "readiness": progress.get("readiness")}
        print(json.dumps(out, ensure_ascii=False)[:2500])
        return 0
    finally:
        with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        stop_backend()


if __name__ == "__main__":
    raise SystemExit(main())
