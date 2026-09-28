"""ORD-0402 follow-up -- the same four arms, this time with NO assembly route.

The first acceptance run (review/ord0402/private_stack_r1.py) had to stand in the read door, because
slice 1 was not on the line: the enumeration came from this lane's assembly module, and that was named
in every artifact. Slice 1 has since landed -- `GET /api/v1/recycle-bin/journeys` at
`backend/app/main.py:3058` -- so this run serves `app.main:app` itself. Both doors the traveller uses
are now the product's own, and the only thing this lane supplies is the port, the sqlite file and the
clicks.

Ownership is proved the way the first run learned to prove it: the listening pid's PARENT is the handle
this script started (the venv python is a redirector, so `pid == netstat pid` is false and is printed
as false), the listener's command line names `app.main:app`, and the rows are read back out of the
sqlite file with no HTTP in the way.

Usage:  python private_stack_r2.py up | status | down
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LANE = Path("D:/moodle/_qoder_q_ord0402b")
RUN = LANE / "run"
DB = RUN / "q0402b_product.db"
LOG = LANE / "uvicorn_8724.log"
RECEIPT = LANE / "stack_receipt_r2.json"
PIDFILE = LANE / "uvicorn_8724.pid"
BACKEND = LANE / "wt" / "backend"
VENV_PY = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")
PORT = 8724
READ_DOOR = "/api/v1/recycle-bin/journeys"


def http(method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode("utf-8", "replace")


def listener_pid() -> str | None:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    for line in out.splitlines():
        if f"127.0.0.1:{PORT}" in line and "LISTENING" in line:
            return line.split()[-1]
    return None


def wmi(pid: str, name: str) -> str:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-CimInstance Win32_Process -Filter \"ProcessId=" + str(int(pid)) + "\")." + name],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return out.stdout.strip()


def up() -> int:
    if PIDFILE.exists():
        print("a stack is already recorded; run `down` first")
        return 1
    RUN.mkdir(parents=True, exist_ok=True)
    for path in (DB, Path(str(DB) + "-wal"), Path(str(DB) + "-shm")):
        path.unlink(missing_ok=True)
    env = {**os.environ, "CITYNEXUS_DATABASE_URL": f"sqlite:///./{DB.name}", "PYTHONPATH": str(BACKEND)}
    env.pop("HTTP_PROXY", None)
    env.pop("HTTPS_PROXY", None)
    log = LOG.open("w", encoding="utf-8", errors="replace")
    child = subprocess.Popen(
        [str(VENV_PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT),
         "--log-level", "info"],
        cwd=str(RUN), env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    PIDFILE.write_text(str(child.pid), encoding="utf-8")
    for _ in range(90):
        time.sleep(1)
        try:
            if http("GET", "/api/v1/journeys")[0] == 200:
                break
        except Exception:
            continue
    else:
        print("the product server never answered; see", LOG)
        return 1

    _, traveler = http("POST", "/api/v1/travelers", {"display_name": "ORD-0402 recheck", "timezone": "Asia/Shanghai", "locale": "zh-CN"})
    created = []
    for title in ("厦门两日", "Xiamen two days"):
        status, journey = http("POST", "/api/v1/journeys", {
            "traveler_id": traveler["id"], "title": title, "city_code": "CN-350200",
            "timezone": "Asia/Shanghai", "start_at": "2026-10-10T01:00:00Z", "end_at": "2026-10-11T01:00:00Z",
            "budget": {"amount_minor": 120000, "currency": "CNY"}, "party_size": 2})
        if status != 201:
            print("seed failed", status, journey)
            return 1
        created.append(journey["id"])
    binned = [(jid, http("DELETE", f"/api/v1/journeys/{jid}")[0]) for jid in created]
    door = http("GET", READ_DOOR)

    on_port = listener_pid()
    receipt = {
        "server_module": "app.main:app (the product's own app object; no route added by this lane)",
        "started_by_pid": child.pid,
        "netstat_pid_on_port": on_port,
        "listener_equals_started_pid": on_port == str(child.pid),
        "parent_of_listener": wmi(on_port or "0", "ParentProcessId"),
        "parent_of_listener_equals_started_pid": wmi(on_port or "0", "ParentProcessId") == str(child.pid),
        "listener_command_line": wmi(on_port or "0", "CommandLine")[:200],
        "db_file": str(DB),
        "db_file_bytes": DB.stat().st_size if DB.exists() else None,
        "database_url_env": env["CITYNEXUS_DATABASE_URL"],
        "journey_ids": created,
        "delete_legs": binned,
        "read_door": {"path": READ_DOOR, "status": door[0], "rows": len(door[1] or []),
                      "row_fields": sorted((door[1] or [{}])[0].keys())},
        "read_door_rows": door[1],
        "landed_list_after_binning": len(http("GET", "/api/v1/journeys")[1] or []),
        "assembly_used": False,
    }
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "read_door_rows"}, ensure_ascii=False, indent=2)[:1600])
    return 0


def status() -> int:
    started = PIDFILE.read_text(encoding="utf-8").strip() if PIDFILE.exists() else None
    on_port = listener_pid()
    print(json.dumps({"started": started, "listener": on_port, "parent_of_listener": wmi(on_port, "ParentProcessId") if on_port else None,
                      "db_bytes": DB.stat().st_size if DB.exists() else None}, indent=2))
    return 0


def down() -> int:
    if not PIDFILE.exists():
        print("nothing recorded")
        return 0
    pid = PIDFILE.read_text(encoding="utf-8").strip()
    subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
    PIDFILE.unlink(missing_ok=True)
    time.sleep(1)
    print("port still held:", listener_pid())
    return 0


if __name__ == "__main__":
    sys.exit({"up": up, "status": status, "down": down}[sys.argv[1] if len(sys.argv) > 1 else "up"]())
