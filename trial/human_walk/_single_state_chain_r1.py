"""Probe the single-state chain on a copy of the live classroom DB.

Uses the existing RUNNING run (no data is deleted or created): one advance with the
current sequence, one replay with the stale sequence, and one write through the retired
`/demo/simulation-clock` door. Expected: 200, 409 stale, 409 use-run.
"""
from __future__ import annotations

import json
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
TARGET_DB = WORK + "/probe21_live.db"
JOURNEY = "2e9cd67d-10ca-4ecd-920b-76c81a350c71"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/single-state-chain-65.txt"
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
        if __import__("os").path.exists(TARGET_DB + suffix):
            __import__("os").remove(TARGET_DB + suffix)
    source = sqlite3.connect("file:" + SOURCE_DB + "?mode=ro", uri=True)
    target = sqlite3.connect(TARGET_DB)
    try:
        source.backup(target)
        target.commit()
    finally:
        target.close()
        source.close()


def start_backend(presenter_key: str) -> subprocess.Popen:
    env = dict(__import__("os").environ)
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
    log = open(WORK + "/chain_backend.log", "wb")
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
        with OPENER.open(request, timeout=60) as answer:
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


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stop_backend()
    time.sleep(2)
    copy_db()
    key = secrets.token_hex(24)
    proc = start_backend(key)
    out: dict = {"source": "read-only copy of the live classroom DB", "journey": JOURNEY}
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
        status, current = req("GET", base + "/runs/current", token=token)
        run = {"sequence": current.get("sequence"), "status": current.get("status"),
               "virtual_now": current.get("virtual_now")}
        out["current"] = run
        status, advanced = req("POST", base + "/runs/%s/advance" % current["run_id"],
                               {"expected_sequence": current["sequence"]}, token=token,
                               key="chain-live-" + secrets.token_hex(4))
        out["advance_current"] = {"http": status,
                                  "sequence": advanced.get("sequence"),
                                  "status": advanced.get("status"),
                                  "error": None if status == 200 else code(advanced)}
        status, stale = req("POST", base + "/runs/%s/advance" % current["run_id"],
                            {"expected_sequence": current["sequence"]}, token=token,
                            key="chain-stale-" + secrets.token_hex(4))
        out["advance_stale_sequence"] = {"http": status, "error": code(stale)}
        clock_status, clock = req("GET", "/api/v1/demo/simulation-clock/" + JOURNEY, token=token)
        out["legacy_clock"] = {"http": clock_status, "version": clock.get("version"),
                               "virtual_now": clock.get("virtual_now")}
        status, legacy = req("POST", "/api/v1/demo/simulation-clock/%s/advance" % JOURNEY,
                             {"minutes": 30, "expected_version": clock.get("version")},
                             token=token, key="chain-legacy-" + secrets.token_hex(4))
        out["legacy_advance"] = {"http": status, "error": code(legacy)}
        status, after = req("GET", base + "/runs/current", token=token)
        out["run_unchanged_by_legacy"] = {"sequence": after.get("sequence"),
                                          "virtual_now": after.get("virtual_now")}
        print(json.dumps(out, ensure_ascii=False)[:2500])
        return 0
    finally:
        with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        stop_backend()


if __name__ == "__main__":
    raise SystemExit(main())
