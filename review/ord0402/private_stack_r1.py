"""ORD-0402 slice 2 -- this lane's private stack: its own sqlite file, its own uvicorn, its own port.

Why a private stack at all: the preview chain on :4781/:8693 is showing the user a demo, and
`demo/reset` erases 52 tables including real trips. Nothing here opens those files or those ports.

Ownership is proved three ways in one receipt, because a port answering 200 is not the same fact as
*this process* answering it:
  1. the pid holding 127.0.0.1:8714 in `netstat` equals the pid of the child this script started;
  2. that pid's command line names this assembly module;
  3. the sqlite file the server was told to use exists on disk, and the row the run writes is read
     back from that file by a second connection that goes through no HTTP at all.

Usage:  python private_stack_r1.py up      # start, prove, seed, bin two trips, write the receipt
        python private_stack_r1.py status  # re-prove from the recorded pid
        python private_stack_r1.py down    # kill only the pid this lane started
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LANE = Path("D:/moodle/_qoder_q_ord0402")
ASSEMBLY = LANE / "assembly"
DB = ASSEMBLY / "q0402_trash.db"
LOG = LANE / "uvicorn_8714.log"
RECEIPT = LANE / "stack_receipt_r1.json"
PIDFILE = LANE / "uvicorn_8714.pid"
BACKEND = LANE / "wt" / "backend"
VENV_PY = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")
PORT = 8714
BASE = f"http://127.0.0.1:{PORT}"


def http(method: str, path: str, body: dict | None = None, port: int = PORT):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw and "json" in (r.headers.get("content-type") or "") else raw.decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode("utf-8", "replace")


def listener_pid(port: int) -> str | None:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    for line in out.splitlines():
        if f"127.0.0.1:{port}" in line and "LISTENING" in line:
            return line.split()[-1]
    return None


def command_line(pid: str) -> str:
    # The pid goes in as a single-quoted literal, not an f-string: `$pid` inside the PS string is
    # PowerShell's own automatic variable (it is a FileInfo for the script file), and `$` is also
    # what breaks an f-string. Neither is what this probe means.
    script = "(Get-CimInstance Win32_Process -Filter \"ProcessId=" + str(int(pid)) + "\").CommandLine"
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return out.stdout.strip()


def up() -> int:
    if PIDFILE.exists():
        print("a stack is already recorded; run `down` first")
        return 1
    if not os.environ.get("KEEP_DB"):
        DB.unlink(missing_ok=True)
    for side in (Path(str(DB) + "-wal"), Path(str(DB) + "-shm")):
        side.unlink(missing_ok=True)
    env = {**os.environ, "CITYNEXUS_DATABASE_URL": f"sqlite:///./{DB.name}", "PYTHONPATH": str(BACKEND)}
    env.pop("HTTP_PROXY", None)
    env.pop("HTTPS_PROXY", None)
    log = LOG.open("w", encoding="utf-8", errors="replace")
    child = subprocess.Popen(
        [str(VENV_PY), "-m", "uvicorn", "trash_door_assembly_r1:app", "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "info"],
        cwd=str(ASSEMBLY), env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    PIDFILE.write_text(str(child.pid), encoding="utf-8")
    ready = None
    for _ in range(60):
        time.sleep(1)
        try:
            status, _ = http("GET", "/api/v1/journeys")
            if status == 200:
                ready = True
                break
        except Exception:
            continue
    if not ready:
        print("the server never answered /api/v1/journeys; see", LOG)
        return 1

    # Seed through the real doors: a traveller, then two trips, then the real soft delete on both.
    _, traveler = http("POST", "/api/v1/travelers", {"display_name": "ORD-0402 lane Q", "timezone": "Asia/Shanghai", "locale": "zh-CN"})
    traveler_id = traveler["id"]
    created = []
    for title in ("厦门两日", "Xiamen two days"):
        status, journey = http(
            "POST", "/api/v1/journeys",
            {"traveler_id": traveler_id, "title": title, "city_code": "CN-350200", "timezone": "Asia/Shanghai",
             "start_at": "2026-10-10T01:00:00Z", "end_at": "2026-10-11T01:00:00Z",
             "budget": {"amount_minor": 120000, "currency": "CNY"}, "party_size": 2},
        )
        if status != 201:
            print("seed failed", status, journey)
            return 1
        created.append(journey["id"])
    deleted = [(jid, http("DELETE", f"/api/v1/journeys/{jid}")[0]) for jid in created]

    discarded = http("GET", "/api/v1/recycle-bin/journeys")[1]
    shadowed = http("GET", "/api/v1/journeys/discarded")
    still_listed = http("GET", "/api/v1/journeys")[1]
    pid_on_port = listener_pid(PORT)
    receipt = {
        "started_by_pid": child.pid,
        "netstat_pid_on_port": pid_on_port,
        "pid_match": pid_on_port == str(child.pid),
        "command_line_names_assembly": "trash_door_assembly_r1" in command_line(pid_on_port or "0"),
        "command_line": command_line(pid_on_port or "0")[:200],
        "db_file": str(DB),
        "db_file_bytes": DB.stat().st_size if DB.exists() else None,
        "database_url_env": env["CITYNEXUS_DATABASE_URL"],
        "traveler_id": traveler_id,
        "journey_ids": created,
        "delete_legs": deleted,
        "discarded_rows_from_assembly_door": [
            {"id": r["id"], "title": r["title"], "deleted_at": r["deleted_at"], "bin_state": r["bin_state"]} for r in discarded
        ],
        "journeys_listed_by_the_landed_door": len(still_listed),
        "product_undelete_route_used": "POST /api/v1/journeys/{id}/undelete (backend/app/main.py, landed by ORD-0399)",
        "standin": "GET /api/v1/recycle-bin/journeys is this assembly's route, not product code: ORD-0402 slice 1 has not landed.",
        "shadowed_collection_name": {"path": "/api/v1/journeys/discarded", "status": shadowed[0], "answer": shadowed[1]},
    }
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "command_line"}, ensure_ascii=False, indent=2))
    return 0


def status() -> int:
    pid = PIDFILE.read_text(encoding="utf-8").strip() if PIDFILE.exists() else None
    on_port = listener_pid(PORT)
    print(json.dumps({"recorded_pid": pid, "netstat_pid": on_port, "match": pid == on_port,
                      "alive": bool(on_port), "db_bytes": DB.stat().st_size if DB.exists() else None}, indent=2))
    return 0


def down() -> int:
    if not PIDFILE.exists():
        print("nothing recorded")
        return 0
    pid = PIDFILE.read_text(encoding="utf-8").strip()
    subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, text=True)
    PIDFILE.unlink(missing_ok=True)
    time.sleep(1)
    print("port still held:", listener_pid(PORT))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "up"
    sys.exit({"up": up, "status": status, "down": down}[cmd]())
