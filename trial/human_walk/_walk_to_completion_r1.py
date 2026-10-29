"""Walk the fixture run to the end through `/advance`, recording every pause.

Read-only copy of the classroom DB; journey/plan/first-stop are only flipped ACTIVE
so `/simulation/runs` can start (the real `/start` is refused, see activate-and-run-1.txt).
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
BACKEND = r"D:/moodle/_codex_workers/citynexus-sandbox-security-20261025/backend"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
API = "http://127.0.0.1:60400"
SOURCE_DB = WORK + "/probe6_1025.db"
TARGET_DB = WORK + "/probe18_1025.db"
JOURNEY = "8ba03b8e-1461-4da4-9943-826cbea089fe"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/walk-to-completion-1.txt"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def stop_backend() -> None:
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*--port 60400*' } | "
        "ForEach-Object { taskkill /PID $_.ProcessId /T /F }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)


def prepare() -> None:
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(TARGET_DB + suffix):
            os.remove(TARGET_DB + suffix)
    source = sqlite3.connect("file:" + SOURCE_DB + "?mode=ro", uri=True)
    target = sqlite3.connect(TARGET_DB)
    try:
        source.backup(target)
        target.execute("UPDATE journeys SET status='ACTIVE' WHERE id=?", (JOURNEY,))
        target.execute("UPDATE plan_versions SET status='ACTIVE' WHERE id=(SELECT active_plan_version_id FROM journeys WHERE id=?)", (JOURNEY,))
        first = target.execute(
            "SELECT id FROM activities WHERE plan_version_id=(SELECT active_plan_version_id FROM journeys WHERE id=?) ORDER BY start_at LIMIT 1",
            (JOURNEY,)).fetchone()
        if first:
            target.execute("UPDATE journeys SET current_activity_id=? WHERE id=?", (first[0], JOURNEY))
            target.execute("UPDATE activities SET status='ACTIVE' WHERE id=?", (first[0],))
        target.commit()
    finally:
        target.close()
        source.close()


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
            return error.code, {"raw": raw[:300]}


def view(body: dict) -> dict:
    return {"sequence": body.get("sequence"), "status": body.get("status"),
            "virtual_now": body.get("virtual_now"),
            "event": ((body.get("history") or [{}])[-1] or {}).get("event")}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stop_backend()
    time.sleep(2)
    prepare()
    key = secrets.token_hex(24)
    env = {
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + TARGET_DB,
        "CITYNEXUS_TRAVELER_AUTH_SECRET": "probe-isolated-5f3a9c1e7b2d4a6089f1c3e5d7b9a0f2",
        "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": "43200",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_DEMO_DATABASE_PATH": TARGET_DB,
        "CITYNEXUS_SIMULATION_ENABLED": "true",
        "CITYNEXUS_DEMO_PRESENTER_KEY": key,
        "PYTHONPATH": BACKEND,
    }
    proc = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "60400", "--app-dir", BACKEND],
        cwd=BACKEND, env={**os.environ, **env},
        stdout=open(WORK + "/walk_backend.log", "wb"), stderr=subprocess.STDOUT,
    )
    receipt: dict = {"fixture": "journey/plan/first stop ACTIVE in a copy"}
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
        status, run = req("POST", base + "/runs", {"seed": 17}, token=token, key="walk-start")
        receipt["start"] = view(run) if status in (200, 201) else run
        steps = []
        for index in range(30):
            if run.get("status") != "RUNNING":
                break
            status, nxt = req("POST", base + "/runs/%s/advance" % run["run_id"],
                              {"expected_sequence": run["sequence"]}, token=token,
                              key="walk-%02d" % index)
            steps.append({"http": status, **((view(nxt)) if status == 200 else
                                             {"code": (nxt.get("error") or {}).get("code"),
                                              "message": (nxt.get("error") or {}).get("message")})})
            if status != 200:
                break
            run = nxt
        receipt["steps"] = steps
        receipt["final"] = view(run)
        status, progress = req("GET", base + "/runs/%s/progress" % run["run_id"], token=token)
        receipt["progress"] = progress if status != 200 else {
            "status": progress.get("status"), "readiness": progress.get("readiness")}
        print(json.dumps(receipt, ensure_ascii=False)[:3000])
        return 0
    finally:
        with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        stop_backend()


if __name__ == "__main__":
    raise SystemExit(main())
