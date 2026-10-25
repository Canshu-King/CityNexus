"""Fixture stack: one ACTIVE journey on an isolated copy, driven from the 390 px UI.

The classroom DB's PLANNED journey is refused by `/start` (PLACE_UNAVAILABLE), so this
fixture flips that journey to ACTIVE in a copy (`probe16_1025.db`) and discloses it; every
simulation command afterwards is a real HTTP call issued by the browser's buttons.
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
FRONTEND = r"D:/moodle/_cmdr_rescue_v3_1022/frontend"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
API = "http://127.0.0.1:60400"
SOURCE_DB = WORK + "/probe6_1025.db"
TARGET_DB = WORK + "/probe16_1025.db"
JOURNEY = "8ba03b8e-1461-4da4-9943-826cbea089fe"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/clock-run-ui-1.txt"
PROBE = os.environ.get("CLOCK_PROBE") or r"D:/moodle/_cmdr_rescue_v3_1022/trial/human_walk/_clock_run_ui_r58.mjs"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def stop_backend() -> None:
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*--port 60400*' } | "
        "ForEach-Object { taskkill /PID $_.ProcessId /T /F }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)


def copy_and_activate() -> None:
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(TARGET_DB + suffix):
            os.remove(TARGET_DB + suffix)
    source = sqlite3.connect("file:" + SOURCE_DB + "?mode=ro", uri=True)
    target = sqlite3.connect(TARGET_DB)
    try:
        source.backup(target)
        target.execute("UPDATE journeys SET status='ACTIVE' WHERE id=?", (JOURNEY,))
        target.execute(
            "UPDATE plan_versions SET status='ACTIVE' WHERE id=(SELECT active_plan_version_id FROM journeys WHERE id=?)",
            (JOURNEY,),
        )
        first = target.execute(
            "SELECT id FROM activities WHERE plan_version_id=(SELECT active_plan_version_id FROM journeys WHERE id=?) "
            "ORDER BY start_at LIMIT 1", (JOURNEY,)).fetchone()
        if first:
            target.execute("UPDATE journeys SET current_activity_id=? WHERE id=?", (first[0], JOURNEY))
            target.execute("UPDATE activities SET status='ACTIVE' WHERE id=?", (first[0],))
        target.commit()
    finally:
        target.close()
        source.close()


def start_backend(presenter_key: str) -> subprocess.Popen:
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + TARGET_DB,
        "CITYNEXUS_TRAVELER_AUTH_SECRET": "probe-isolated-5f3a9c1e7b2d4a6089f1c3e5d7b9a0f2",
        "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": "43200",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_DEMO_DATABASE_PATH": TARGET_DB,
        "CITYNEXUS_SIMULATION_ENABLED": "true",
        "CITYNEXUS_DEMO_PRESENTER_KEY": presenter_key,
        "PYTHONPATH": BACKEND,
    })
    log = open(WORK + "/clock_run_backend.log", "wb")
    return subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "60400", "--app-dir", BACKEND],
        cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT,
    )


def wait_healthy(seconds: int = 90) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with OPENER.open(API + "/api/v1/health", timeout=3) as answer:
                if answer.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def post(path: str, body: dict, headers: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Accept": "application/json",
                                          "Content-Type": "application/json", **(headers or {})})
    try:
        with OPENER.open(req, timeout=30) as answer:
            raw = answer.read().decode()
            return answer.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        return error.code, {}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stop_backend()
    time.sleep(2)
    copy_and_activate()
    presenter_key = secrets.token_hex(24)
    backend = start_backend(presenter_key)
    frontend = None
    receipt: dict = {"fixture": "journey status set ACTIVE in isolated copy; real /start refused with PLACE_UNAVAILABLE"}
    try:
        if not wait_healthy():
            print(json.dumps({"RAN": False, "reason": "backend not healthy"}))
            return 1
        status, ticket = post("/api/v1/demo/pairing", {"journey_id": JOURNEY},
                              {"X-CityNexus-Presenter-Key": presenter_key})
        receipt["pairing_status"] = status
        if status not in (200, 201):
            print(json.dumps({"RAN": False, "reason": "pairing refused", "status": status}))
            return 1
        env = dict(os.environ)
        env["PAIR_TICKET"] = ticket["ticket"]
        env["PAIR_JOURNEY"] = JOURNEY
        env["PAIR_BASE"] = "http://127.0.0.1:14495"
        env["PAIR_OUT"] = OUT
        frontend = subprocess.Popen(
            [NODE, "node_modules/vite/bin/vite.js", "--port", "14495", "--strictPort", "--host", "0.0.0.0"],
            cwd=FRONTEND, env={**os.environ, "CITYNEXUS_BACKEND_PORT": "60400"},
            stdout=open(WORK + "/clock_run_frontend.log", "wb"), stderr=subprocess.STDOUT,
        )
        deadline = time.time() + 60
        ready = False
        while time.time() < deadline:
            try:
                with OPENER.open("http://127.0.0.1:14495/", timeout=3) as answer:
                    if answer.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(1)
        receipt["vite_ready"] = ready
        if not ready:
            print(json.dumps({"RAN": False, "reason": "vite not ready"}))
            return 1
        run = subprocess.run([NODE, PROBE], cwd=FRONTEND, env=env, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=300)
        receipt["probe_rc"] = run.returncode
        receipt["probe_stdout_tail"] = (run.stdout or "")[-1200:]
        receipt["probe_stderr_tail"] = (run.stderr or "")[-600:]
        print(json.dumps(receipt, ensure_ascii=False)[:2500])
        return run.returncode
    finally:
        if frontend is not None:
            subprocess.run(["taskkill", "/PID", str(frontend.pid), "/T", "/F"], capture_output=True)
        subprocess.run(["taskkill", "/PID", str(backend.pid), "/T", "/F"], capture_output=True)
        stop_backend()


if __name__ == "__main__":
    raise SystemExit(main())
