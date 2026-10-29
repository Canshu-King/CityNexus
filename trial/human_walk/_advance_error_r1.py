"""Ask the fixture run's advance once and print the server's own error body."""
from __future__ import annotations

import json
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request

WORK = r"D:/moodle/_codex_probe_1025"
BACKEND = r"D:/moodle/_codex_workers/citynexus-sandbox-security-20261025/backend"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
API = "http://127.0.0.1:60400"
DB = WORK + "/probe16_1025.db"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/advance-error-1.txt"
JOURNEY = "8ba03b8e-1461-4da4-9943-826cbea089fe"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def stop_backend() -> None:
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*--port 60400*' } | "
        "ForEach-Object { taskkill /PID $_.ProcessId /T /F }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)


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
            return error.code, {"raw": raw[:300]}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stop_backend()
    time.sleep(2)
    key = secrets.token_hex(24)
    env = {
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + DB,
        "CITYNEXUS_TRAVELER_AUTH_SECRET": "probe-isolated-5f3a9c1e7b2d4a6089f1c3e5d7b9a0f2",
        "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": "43200",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_DEMO_DATABASE_PATH": DB,
        "CITYNEXUS_SIMULATION_ENABLED": "true",
        "CITYNEXUS_DEMO_PRESENTER_KEY": key,
        "PYTHONPATH": BACKEND,
    }
    proc = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "60400", "--app-dir", BACKEND],
        cwd=BACKEND, env={**__import__("os").environ, **env},
        stdout=open(WORK + "/advance_error_backend.log", "wb"), stderr=subprocess.STDOUT,
    )
    receipt = {}
    try:
        for _ in range(60):
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
        receipt["current_status"] = status
        receipt["current"] = {k: current.get(k) for k in ("run_id", "sequence", "status", "virtual_now")}
        if current.get("run_id"):
            status, advanced = req("POST", base + "/runs/%s/advance" % current["run_id"],
                                   {"expected_sequence": current["sequence"]}, token=token,
                                   key="probe-one-" + secrets.token_hex(4))
            receipt["advance_status"] = status
            receipt["advance_body"] = advanced
        status, progress = req("GET", base + "/runs/%s/progress" % current["run_id"], token=token)
        receipt["progress_status"] = status
        receipt["progress"] = progress if status != 200 else {
            k: progress.get(k) for k in ("status", "sequence", "virtual_now", "readiness")}
        print(json.dumps(receipt, ensure_ascii=False)[:2500])
        return 0
    finally:
        with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        stop_backend()


if __name__ == "__main__":
    raise SystemExit(main())
