"""Activate the PLANNED classroom journey through the product's own `/start`, then drive a run.

Uses a copy of the classroom database and the Codex backend; nothing here writes the live
database, and the ticket/presenter key never reaches the receipt.  Every step is the endpoint
a real UI calls: pairing -> journey /start -> POST simulation/runs -> POST advance.
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
TARGET_DB = WORK + "/probe14_1025.db"
JOURNEY = "8ba03b8e-1461-4da4-9943-826cbea089fe"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/activate-and-run-1.txt"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def stop_backend() -> None:
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*--port 60400*' -and $_.CommandLine -like '*citynexus-sandbox-security-20261025*' } | "
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
    log = open(WORK + "/activate_backend.log", "wb")
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


def request(method: str, path: str, body: dict | None = None, token: str | None = None,
            key: str | None = None, headers: dict | None = None) -> tuple[int, dict]:
    merged = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        merged["Content-Type"] = "application/json"
    if token:
        merged["Authorization"] = "Bearer " + token
    if key:
        merged["Idempotency-Key"] = key
    req = urllib.request.Request(API + path, data=data, method=method, headers=merged)
    try:
        with OPENER.open(req, timeout=120) as answer:
            raw = answer.read().decode("utf-8", "replace")
            return answer.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = {"raw": raw[:300]}
        return error.code, parsed


def run_view(body: dict) -> dict:
    return {
        "run_id": body.get("run_id"),
        "sequence": body.get("sequence"),
        "status": body.get("status"),
        "virtual_now": body.get("virtual_now"),
        "city_code": body.get("city_code"),
        "history_tail": (body.get("history") or [{}])[-1] if body.get("history") else None,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stop_backend()
    time.sleep(2)
    copy_db()
    presenter_key = secrets.token_hex(24)
    process = start_backend(presenter_key)
    receipt: dict = {}
    try:
        if not wait_healthy():
            print(json.dumps({"RAN": False, "reason": "backend not healthy"}))
            return 1
        status, ticket = request("POST", "/api/v1/demo/pairing",
                                 {"journey_id": JOURNEY},
                                 headers={"X-CityNexus-Presenter-Key": presenter_key})
        receipt["pairing_status"] = status
        if status not in (200, 201):
            receipt["pairing_error"] = (ticket.get("error") or {}).get("code") or "PAIRING_REFUSED"
        else:
            status, redeemed = request("POST", "/api/v1/demo/pairing/redeem", {"ticket": ticket["ticket"]})
            receipt["redeem_status"] = status
            token = redeemed.get("access_token", "")
            receipt["redeem_journey"] = redeemed.get("journey_id")
            if not token:
                receipt["redeem_error"] = (redeemed.get("error") or {}).get("code") or "NO_TOKEN"
            else:
                status, journey = request("GET", "/api/v1/journeys/" + JOURNEY, token=token)
                receipt["journey_before"] = {"status": status, "journey_status": journey.get("status"),
                                             "plan": journey.get("active_plan_version_id")}
                status, started = request("POST", "/api/v1/journeys/" + JOURNEY + "/start",
                                          {}, token=token, key="probe-activate-1")
                receipt["start_status"] = status
                receipt["start"] = ({"status": started.get("status")} if status == 200 else
                                    {"code": (started.get("error") or {}).get("code"),
                                     "message": (started.get("error") or {}).get("message")})
                base = "/api/v1/journeys/%s/simulation" % JOURNEY
                status, run = request("POST", base + "/runs", {"seed": 17}, token=token,
                                      key="probe-run-1")
                receipt["run_status"] = status
                receipt["run"] = run_view(run) if status in (200, 201) else {
                    "code": (run.get("error") or {}).get("code")}
                walk = []
                if status in (200, 201):
                    for step in range(6):
                        if run.get("status") != "RUNNING":
                            break
                        status, nxt = request("POST", base + "/runs/%s/advance" % run["run_id"],
                                              {"expected_sequence": run["sequence"]}, token=token,
                                              key="probe-walk-%d" % step)
                        walk.append({"http": status, **((run_view(nxt)) if status == 200 else
                                                         {"code": (nxt.get("error") or {}).get("code")})})
                        if status != 200:
                            break
                        run = nxt
                receipt["advance_walk"] = walk
                status, current = request("GET", base + "/runs/current", token=token)
                receipt["current_status"] = status
                receipt["current"] = run_view(current) if current.get("run_id") else current
                status, clock = request("GET", "/api/v1/demo/simulation-clock/" + JOURNEY, token=token)
                receipt["legacy_clock"] = {"status": status,
                                           "version": clock.get("version"),
                                           "virtual_now": clock.get("virtual_now")}
        print(json.dumps(receipt, ensure_ascii=False)[:3000])
        return 0
    finally:
        with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        stop_backend()


if __name__ == "__main__":
    raise SystemExit(main())
