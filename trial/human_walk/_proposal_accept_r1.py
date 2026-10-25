"""Accept the launcher's PRESENTED proposal on a copy and read what actually moves.

No model is involved: the proposal already exists (prepare creates it).  This is the
`接受这份调整` branch of the quick card, measured rather than promised.
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
TARGET_DB = WORK + "/probe25_live.db"
JOURNEY = "2e9cd67d-10ca-4ecd-920b-76c81a350c71"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/proposal-accept-68.txt"
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
    log = open(WORK + "/proposal_backend.log", "wb")
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
        with OPENER.open(request, timeout=90) as answer:
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
        status, redeemed = req("POST", "/api/v1/demo/pairing/redeem", {"ticket": ticket["ticket"]})
        token = redeemed["access_token"]
        status, replans = req("GET", "/api/v1/journeys/%s/replans" % JOURNEY, token=token)
        items = replans if isinstance(replans, list) else (replans.get("items") or replans.get("replans") or [])
        presented = [item for item in items if str(item.get("status")) == "PRESENTED"]
        out["replans"] = {"http": status, "count": len(items), "presented": len(presented)}
        if not presented:
            out["accept"] = {"skipped": "no PRESENTED proposal"}
        else:
            proposal = presented[0]
            out["proposal"] = {"id": proposal.get("id"), "status": proposal.get("status"),
                               "proposed_plan_version_id": proposal.get("proposed_plan_version_id")}
            before = req("GET", "/api/v1/journeys/" + JOURNEY, token=token)[1]
            status, accepted = req("POST", "/api/v1/replans/%s/accept" % proposal["id"], {},
                                   token=token, key="accept-" + secrets.token_hex(4))
            out["accept"] = {"http": status,
                             "status": accepted.get("status"),
                             "error": None if status < 400 else code(accepted)}
            after = req("GET", "/api/v1/journeys/" + JOURNEY, token=token)[1]
            out["journey"] = {
                "before": {"plan": before.get("active_plan_version_id"), "status": before.get("status")},
                "after": {"plan": after.get("active_plan_version_id"), "status": after.get("status")},
            }
            status, replans_after = req("GET", "/api/v1/journeys/%s/replans" % JOURNEY, token=token)
            items_after = (replans_after if isinstance(replans_after, list)
                           else (replans_after.get("items") or replans_after.get("replans") or []))
            out["replans_after"] = {"http": status,
                                    "statuses": [str(item.get("status")) for item in items_after[:5]]}
        print(json.dumps(out, ensure_ascii=False)[:2000])
        return 0
    finally:
        with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        stop_backend()


if __name__ == "__main__":
    raise SystemExit(main())
