"""Restart the isolated SimulationRun stage with a presenter key and run one named probe.

The classroom stack (backend 60391, frontend 14492, live database) is untouched.  This reuses
the exported Codex backend in `_codex_probe_1025`, copies a chosen probe database to a new
file, mints one 120-second pairing ticket with a key that exists only in this process's
environment, and runs the probe with that ticket.  Nothing prints the key.

Examples:
  python _entry_banner_stack_r1.py                       # finished-trip entry banner probe
  python _entry_banner_stack_r1.py --source-db probe3_1025.db --target-db probe8_1025.db \
      --probe _classroom_run_resume_r34.mjs              # reload mid-run probe
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import time
import urllib.request

WORK = r"D:/moodle/_codex_probe_1025"
BACKEND = WORK + "/backend"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE = r"C:/Program Files/nodejs/node.exe"
PROBES = r"D:/moodle/_cmdr_rescue_v3_1022/trial/human_walk/"
JOURNEY = "2e9cd67d-10ca-4ecd-920b-76c81a350c71"
API = "http://127.0.0.1:60400"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def stop_isolated_backend() -> None:
    """Only the uvicorn that serves this exported tree on the spare port."""
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*--port 60400*' -and $_.CommandLine -like '*_codex_probe_1025*' } | "
        "ForEach-Object { taskkill /PID $_.ProcessId /T /F }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)


def copy_db(source_db: str, target_db: str) -> None:
    for suffix in ("", "-wal", "-shm"):
        stale = target_db + suffix
        if os.path.exists(stale):
            os.remove(stale)
    source = sqlite3.connect("file:" + source_db + "?mode=ro", uri=True)
    target = sqlite3.connect(target_db)
    try:
        source.backup(target)
        target.commit()
    finally:
        target.close()
        source.close()


def start_backend(database: str, presenter_key: str) -> subprocess.Popen:
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + database,
        "CITYNEXUS_TRAVELER_AUTH_SECRET": "probe-isolated-5f3a9c1e7b2d4a6089f1c3e5d7b9a0f2",
        "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": "43200",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_DEMO_DATABASE_PATH": database,
        "CITYNEXUS_SIMULATION_ENABLED": "true",
        "CITYNEXUS_DEMO_PRESENTER_KEY": presenter_key,
        "PYTHONPATH": BACKEND,
    })
    log = open(WORK + "/entry_banner_backend.log", "wb")
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


def issue_ticket(presenter_key: str, journey: str) -> str:
    body = json.dumps({"journey_id": journey}).encode()
    request = urllib.request.Request(
        API + "/api/v1/demo/pairing", data=body, method="POST",
        headers={"Content-Type": "application/json", "X-CityNexus-Presenter-Key": presenter_key},
    )
    with OPENER.open(request, timeout=15) as answer:
        return json.loads(answer.read().decode())["ticket"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-db", default="probe6_1025.db")
    parser.add_argument("--target-db", default="probe7_1025.db")
    parser.add_argument("--probe", default="_classroom_entry_banner_r33.mjs")
    parser.add_argument("--journey", default=JOURNEY)
    parser.add_argument("--tag", default="", help="suffix for the probe's own evidence files")
    args = parser.parse_args()

    source_db = os.path.join(WORK, args.source_db)
    target_db = os.path.join(WORK, args.target_db)
    probe = args.probe if os.path.isabs(args.probe) else PROBES + args.probe

    stop_isolated_backend()
    time.sleep(2)
    copy_db(source_db, target_db)
    presenter_key = secrets.token_hex(24)
    process = start_backend(target_db, presenter_key)
    if not wait_healthy():
        print(json.dumps({"STAGE_OK": False, "reason": "backend not healthy"}))
        process.terminate()
        return 1
    try:
        ticket = issue_ticket(presenter_key, args.journey)
    except Exception as error:  # noqa: BLE001
        print(json.dumps({"STAGE_OK": False, "reason": "pairing failed", "detail": str(error)[:120]}))
        return 1
    env = dict(os.environ)
    # The ticket rides only in the child's environment; it is not printed or written here.
    env["PAIR_TICKET"] = ticket
    env["SIM_BASE"] = "http://127.0.0.1:14494"
    env["PROBE_TAG"] = args.tag
    run = subprocess.run([NODE, probe], env=env, cwd=r"D:/moodle/_cmdr_rescue_v3_1022", capture_output=True, text=True, timeout=300)
    print(json.dumps({
        "STAGE_OK": run.returncode == 0,
        "backend_pid": process.pid,
        "ticket_issued": True,
        "db": target_db,
        "probe": os.path.basename(probe),
        "probe_rc": run.returncode,
        "probe_stdout": run.stdout.strip()[-400:],
        "probe_stderr": run.stderr.strip()[-400:],
    }, ensure_ascii=False))
    return run.returncode


if __name__ == "__main__":
    sys.exit(main())
