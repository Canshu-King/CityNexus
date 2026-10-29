"""Replay a pairing ticket on an isolated copy: the second redeem must be refused."""
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
TARGET_DB = WORK + "/probe22_live.db"
JOURNEY = "2e9cd67d-10ca-4ecd-920b-76c81a350c71"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/pairing-replay-66.txt"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def stop_backend() -> None:
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*--port 60400*' } | "
        "ForEach-Object { taskkill /PID $_.ProcessId /T /F }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)


def copy_db() -> None:
    import os
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
    import os
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
    log = open(WORK + "/pairing_backend.log", "wb")
    return subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "60400", "--app-dir", BACKEND],
        cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT,
    )


def req(method, path, body=None, headers=None):
    merged = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        merged["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=data, method=method, headers=merged)
    try:
        with OPENER.open(request, timeout=30) as answer:
            raw = answer.read().decode()
            return answer.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        raw = error.read().decode()
        try:
            return error.code, json.loads(raw)
        except ValueError:
            return error.code, {"raw": raw[:160]}


def short(body: dict) -> dict:
    return {"error": ((body.get("error") or {}).get("message")
                      or (body.get("error") or {}).get("code") or ""),
            "has_token": bool(body.get("access_token"))}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stop_backend()
    time.sleep(2)
    copy_db()
    key = secrets.token_hex(24)
    proc = start_backend(key)
    out: dict = {"source": "read-only copy of the live classroom DB"}
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
        out["issue"] = {"http": status, "has_ticket": bool(ticket.get("ticket"))}
        status, first = req("POST", "/api/v1/demo/pairing/redeem", {"ticket": ticket["ticket"]})
        out["first_redeem"] = {"http": status, **short(first)}
        status, again = req("POST", "/api/v1/demo/pairing/redeem", {"ticket": ticket["ticket"]})
        out["second_redeem"] = {"http": status, **short(again)}
        status, bogus = req("POST", "/api/v1/demo/pairing/redeem", {"ticket": "A" * 43})
        out["bogus_ticket"] = {"http": status, **short(bogus)}
        status, pair_nokey = req("POST", "/api/v1/demo/pairing", {"journey_id": JOURNEY})
        out["pairing_without_key"] = {"http": status, **short(pair_nokey)}
        print(json.dumps(out, ensure_ascii=False))
        return 0
    finally:
        with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        stop_backend()


if __name__ == "__main__":
    raise SystemExit(main())
