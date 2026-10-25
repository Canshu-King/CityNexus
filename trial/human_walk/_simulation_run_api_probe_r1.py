"""Read the real SimulationRun API shape from Codex's branch, on an isolated copy.

Starts the Codex worktree backend against `probe13_1025.db` (a copy of the classroom
database), redeems a one-use presenter ticket, then reads `/cities`, starts a run and
walks `advance` until it pauses or completes.  It never prints the presenter key and
never touches the live classroom stack (60391) or the shared demo database.
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
TARGET_DB = WORK + "/probe13_1025.db"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/simulation-run-api-1.txt"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def stop_backend() -> None:
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*--port 60400*' -and $_.CommandLine -like '*citynexus-sandbox-security-20261025*' } | "
        "ForEach-Object { taskkill /PID $_.ProcessId /T /F }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)


def copy_db(source_db: str, target_db: str) -> None:
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(target_db + suffix):
            os.remove(target_db + suffix)
    source = sqlite3.connect("file:" + source_db + "?mode=ro", uri=True)
    target = sqlite3.connect(target_db)
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
    log = open(WORK + "/sim_probe_backend.log", "wb")
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
            parsed = {"raw": raw[:200]}
        return error.code, parsed


def journey_in_db() -> str:
    con = sqlite3.connect("file:" + TARGET_DB + "?mode=ro", uri=True)
    try:
        row = con.execute("SELECT id, status FROM journeys ORDER BY created_at DESC LIMIT 1").fetchone()
        return row[0] if row else ""
    finally:
        con.close()


def summarize_run(body: dict) -> dict:
    return {
        "run_id": body.get("run_id"),
        "journey_id": body.get("journey_id"),
        "city_code": body.get("city_code"),
        "seed": body.get("seed"),
        "sequence": body.get("sequence"),
        "status": body.get("status"),
        "virtual_now": body.get("virtual_now"),
        "state_keys": sorted((body.get("state") or {}).keys()),
        "current_activity_id": ((body.get("state") or {}).get("current_activity_id")),
        "pending_event_id": ((body.get("state") or {}).get("pending_event_id")),
        "history_last": (body.get("history") or [{}])[-1] if body.get("history") else None,
    }


def dump(receipt: dict) -> None:
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stop_backend()
    time.sleep(2)
    copy_db(SOURCE_DB, TARGET_DB)
    presenter_key = secrets.token_hex(24)
    process = start_backend(presenter_key)
    receipt: dict = {"BACKEND": BACKEND}
    try:
        if not wait_healthy():
            print(json.dumps({"RAN": False, "reason": "backend not healthy"}))
            return 1
        journey = journey_in_db()
        receipt["journey"] = journey
        status, ticket = request("POST", "/api/v1/demo/pairing",
                                 {"journey_id": journey},
                                 headers={"X-CityNexus-Presenter-Key": presenter_key})
        receipt["pairing_status"] = status
        if status not in (200, 201):
            receipt["pairing_error"] = (ticket.get("error") or {}).get("code") or "PAIRING_REFUSED"
        else:
            status, redeemed = request("POST", "/api/v1/demo/pairing/redeem",
                                       {"ticket": ticket["ticket"]})
            receipt["redeem_status"] = status
            token = redeemed.get("access_token", "")
            journey = redeemed.get("journey_id", journey)
            receipt["redeem_journey"] = journey
            if not token:
                receipt["redeem_body"] = redeemed
            else:
                base = "/api/v1/journeys/%s/simulation" % journey
                status, cities = request("GET", base + "/cities?seed=17", token=token)
                receipt["cities_status"] = status
                receipt["cities"] = cities if status != 200 else {
                    "status": cities.get("status"),
                    "required_city_count": cities.get("required_city_count"),
                    "eligible_city_count": cities.get("eligible_city_count"),
                    "cities": [
                        {"city_code": city.get("city_code"), "status": city.get("status"),
                         "missing": city.get("missing"),
                         "poi": len(city.get("poi") or []), "routes": len(city.get("routes") or [])}
                        for city in cities.get("cities") or []
                    ],
                }
                status, run = request("POST", base + "/runs", {"seed": 17}, token=token,
                                      key="probe-start-" + secrets.token_hex(6))
                receipt["start_status"] = status
                receipt["start"] = summarize_run(run) if status in (200, 201) else run
                walk = []
                if status in (200, 201):
                    for step in range(12):
                        if run.get("status") != "RUNNING":
                            break
                        status, nxt = request("POST", base + "/runs/%s/advance" % run["run_id"],
                                              {"expected_sequence": run["sequence"]},
                                              token=token, key="probe-adv-%s-%d" % (run["run_id"][:8], step))
                        walk.append({"http": status, **((summarize_run(nxt)) if status == 200 else {"error": nxt})})
                        if status != 200:
                            break
                        run = nxt
                receipt["advance_walk"] = walk
                receipt["final"] = summarize_run(run) if run.get("run_id") else {}
                status, current = request("GET", base + "/runs/current", token=token)
                receipt["current_status"] = status
                receipt["current"] = summarize_run(current) if current.get("run_id") else current
                status, progress = (request("GET", base + "/runs/%s/progress" % run["run_id"], token=token)
                                    if run.get("run_id") else (0, {}))
                receipt["progress_status"] = status
                if status == 200:
                    receipt["progress"] = {
                        "status": progress.get("status"),
                        "sequence": progress.get("sequence"),
                        "virtual_now": progress.get("virtual_now"),
                        "readiness": progress.get("readiness"),
                        "guardian_runs": progress.get("guardian_runs"),
                        "proposals": progress.get("proposals"),
                    }
        with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(receipt, ensure_ascii=False)[:4000])
        return 0
    finally:
        dump(receipt)
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        stop_backend()


if __name__ == "__main__":
    raise SystemExit(main())
