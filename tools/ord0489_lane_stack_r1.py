#!/usr/bin/env python3
"""ORD-0489 · start / prove / stop a private CityNexus backend for demo seeding.

The seed script (`tools/ord0489_demo_seed_r1.py`) only speaks HTTP; this file is the part that
makes "anyone can re-run it" true: it boots a backend on a lane port against a lane-owned
database file, proves the listener really belongs to this lane, and stops exactly that process
tree.

  python tools/ord0489_lane_stack_r1.py start --port 8790 --db /tmp/cnx_ord0489.db
  python tools/ord0489_lane_stack_r1.py prove --port 8790 --db /tmp/cnx_ord0489.db
  python tools/ord0489_lane_stack_r1.py kill   --port 8790

Two facts about this machine are built in, because getting them wrong produces readings that look
like the product's and are not:

* Public providers (Nominatim, Overpass, Photon) are reachable only through the machine proxy.
  Measured 2026-09-30: `httpx` with `trust_env=False` against nominatim.openstreetmap.org is a
  12 s ConnectTimeout, the same client honouring the proxy answers 200 in 1.25 s.  With
  `CITYNEXUS_PROVIDER_NETWORK_MODE=direct` the product's live discovery degrades to
  `REPLAY_FALLBACK`, which still returns 200 and still fills the catalogue - with names no
  provider said.  So `start` keeps the proxy environment and pins `env_proxy`.
* `python -m uvicorn` re-execs into uv's CPython, so the PID this script records is the parent of
  the process that holds the socket.  `kill` therefore resolves the listener from the socket table
  and stops that tree, and `prove` reports both numbers.

The forbidden shared surfaces (:8000, :4781, :4782, :8693) are refused here rather than only
remembered: `start` and `kill` exit before touching a port on that list.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid as uuidlib
from datetime import datetime, timezone
from pathlib import Path

TREE = Path(__file__).resolve().parents[1]
FORBIDDEN_PORTS = (8000, 4781, 4782, 8693)
PYTHON = Path(sys.executable)


def sh(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (proc.stdout or "") + (proc.stderr or "")


def listener_pids(port: int) -> list[str]:
    pids = set()
    for line in sh(["netstat", "-ano", "-p", "TCP"]).splitlines():
        cols = line.split()
        if len(cols) >= 5 and cols[0].upper() == "TCP" and cols[3].upper() == "LISTENING":
            if cols[1].rsplit(":", 1)[-1] == str(port):
                pids.add(cols[4])
    return sorted(pids)


def process_info(pid: str) -> dict:
    ps = (
        f'$p=Get-CimInstance Win32_Process -Filter "ProcessId={pid}";'
        'if($p){$p | Select-Object ProcessId,ParentProcessId,Name,CommandLine '
        "| ConvertTo-Json -Compress}"
    )
    raw = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps]).strip()
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
            except Exception:
                continue
            return {
                "pid": data.get("ProcessId"),
                "ppid": data.get("ParentProcessId"),
                "name": data.get("Name"),
                "cmd": (data.get("CommandLine") or "")[:400],
            }
    return {"pid": pid, "parse_error": raw[:200].replace("\n", " ")}


def api_json(port: int, path: str):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=25) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"raw": raw[:200]}
    except Exception as exc:
        return -1, {"error": type(exc).__name__, "msg": str(exc)[:200]}


def cmd_start(args) -> int:
    if args.port in FORBIDDEN_PORTS:
        print(json.dumps({"refuse": "FORBIDDEN_SHARED_PORT", "port": args.port}))
        return 2
    db = Path(args.db).resolve()
    if db.exists() and not args.allow_existing_db:
        print(json.dumps({"refuse": "DB_ALREADY_EXISTS", "path": str(db), "bytes": db.stat().st_size}))
        return 3
    db.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db).replace("\\", "/"),
            "CITYNEXUS_DEMO_MODE": "false",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_REAL_CITY_ENABLED": "true",
            "CITYNEXUS_REAL_CITY_MODE": "live",
            "CITYNEXUS_PHOTON_ENABLED": "true",
            "CITYNEXUS_PROVIDER_NETWORK_MODE": args.network_mode,
            "CITYNEXUS_REAL_CITY_TIMEOUT_SECONDS": str(args.provider_timeout),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    log = Path(args.log).resolve() if args.log else db.with_name(f"backend_{int(time.time())}.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(args.port), "--log-level", "info"],
        cwd=str(TREE / "backend"),
        env=env,
        stdout=open(log, "ab"),
        stderr=subprocess.STDOUT,
    )
    health = None
    deadline = time.time() + args.boot_timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            print(json.dumps({"refuse": "BACKEND_EXITED", "returncode": proc.returncode, "log": str(log)}))
            return 4
        status, body = api_json(args.port, "/api/v1/health")
        if status == 200:
            health = body
            break
        time.sleep(1.0)
    if health is None:
        print(json.dumps({"refuse": "HEALTH_NEVER_ANSWERED", "log": str(log)}))
        return 5
    print(
        json.dumps(
            {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "pid_recorded": proc.pid,
                "backend_port": args.port,
                "db_path": str(db),
                "cwd": str(TREE / "backend"),
                "log_path": str(log),
                "health": health,
                "provider_env": {
                    "CITYNEXUS_REAL_CITY_ENABLED": "true",
                    "CITYNEXUS_PROVIDER_NETWORK_MODE": args.network_mode,
                    "CITYNEXUS_REAL_CITY_TIMEOUT_SECONDS": str(args.provider_timeout),
                    "proxy_env_inherited": True,
                },
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


def cmd_prove(args) -> int:
    """Three receipts in one batch: socket, private store, process."""
    receipt: dict = {"taken_at": datetime.now(timezone.utc).isoformat(), "port": args.port}
    pids = listener_pids(args.port)
    infos = [process_info(p) for p in pids]
    matched = [
        i for i in infos if "uvicorn" in str(i.get("cmd", "")) and f"--port {args.port}" in str(i.get("cmd", ""))
    ]
    receipt["P1_socket"] = {
        "listener_pids": pids,
        "processes": infos,
        "listener_cmd_names_this_port_and_uvicorn": bool(matched),
    }
    db = Path(args.db).resolve() if args.db else None
    marker = None
    if db and db.exists():
        import sqlite3

        con = sqlite3.connect("file:%s?mode=ro" % str(db).replace("\\", "/"), uri=True)
        ids = [r[0] for r in con.execute("select id from journeys order by created_at, id")]
        tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
        con.close()
        marker = str(uuidlib.uuid4())
        receipt["P2_store"] = {
            "db_path": str(db),
            "db_bytes": db.stat().st_size,
            "tables": len(tables),
            "journey_rows": len(ids),
            "first_journey_id": ids[0] if ids else None,
        }
        if ids:
            status, body = api_json(args.port, f"/api/v1/journeys/{ids[0]}")
            receipt["P2_store"]["api_echo_status"] = status
            receipt["P2_store"]["api_echo_id_matches"] = bool(isinstance(body, dict) and body.get("id") == ids[0])
    else:
        receipt["P2_store"] = {"db_path": str(db) if db else None, "journey_rows": "DB_MISSING"}
    status, _ = api_json(args.port, f"/api/v1/journeys/{marker or uuidlib.uuid4()}")
    receipt["P2_store"]["fabricated_uuid_status"] = status
    receipt["P2_store"]["fabricated_uuid_is_404"] = status == 404
    receipt["P3_process"] = {"chain_from_listener": []}
    if pids:
        current = pids[0]
        for _ in range(6):
            info = process_info(current)
            receipt["P3_process"]["chain_from_listener"].append(info)
            parent = str(info.get("ppid") or "0")
            if parent in ("0", "4") or parent == current:
                break
            current = parent
    ok = (
        len(pids) == 1
        and receipt["P1_socket"]["listener_cmd_names_this_port_and_uvicorn"]
        and receipt["P2_store"].get("journey_rows") not in (None, "DB_MISSING", 0)
        and receipt["P2_store"].get("api_echo_id_matches") is True
        and receipt["P2_store"].get("fabricated_uuid_is_404") is True
    )
    receipt["verdict"] = "OWNED_BY_THIS_LANE" if ok else "PROOF_INCOMPLETE"
    print(json.dumps(receipt, ensure_ascii=False, indent=1))
    return 0 if ok else 1


def cmd_kill(args) -> int:
    if args.port in FORBIDDEN_PORTS:
        print(json.dumps({"refuse": "FORBIDDEN_SHARED_PORT", "port": args.port}))
        return 2
    pids = listener_pids(args.port)
    killed = []
    for pid in pids:
        info = process_info(pid)
        if "uvicorn" not in str(info.get("cmd", "")) or f"--port {args.port}" not in str(info.get("cmd", "")):
            killed.append({"pid": pid, "skipped": "command line does not name this port and uvicorn"})
            continue
        sh(["taskkill", "/T", "/F", "/PID", pid])
        killed.append({"pid": pid, "ppid": info.get("ppid"), "killed": True})
    time.sleep(1.5)
    remaining = listener_pids(args.port)
    print(json.dumps({"port": args.port, "actions": killed, "listening_after": remaining}, ensure_ascii=False, indent=1))
    return 0 if not remaining else 1


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--port", type=int, default=8790)
    common.add_argument("--db", default=str(Path(os.environ.get("TEMP", "/tmp")) / "cnx_ord0489.db"))
    sp = sub.add_parser("start", parents=[common])
    sp.add_argument("--log", default=None)
    sp.add_argument("--allow-existing-db", action="store_true")
    sp.add_argument("--network-mode", default="env_proxy", choices=("env_proxy", "auto", "direct"))
    sp.add_argument("--provider-timeout", type=int, default=45)
    sp.add_argument("--boot-timeout", type=int, default=120)
    sp = sub.add_parser("prove", parents=[common])
    sp = sub.add_parser("kill", parents=[common])
    args = ap.parse_args()
    return {"start": cmd_start, "prove": cmd_prove, "kill": cmd_kill}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
