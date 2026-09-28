"""ORD-0436 -- stand up this lane's own stack, read the 成员与权限 screen in both languages.

The point of this file is not the screenshots; it is that every number in the readout can be
attributed. Three proofs are taken before a single page is opened, in the shape the shared-port
lesson demands (a 200 on a port can be another lane's backend):

1. the process holding the backend port is one this script spawned, or its direct child;
2. that process' command line names ``app.main:app`` and this port;
3. the database file it opened is one this script created, and it is not any of the shared stores.

The screen is served by `vite preview` against the production bundle, with `CITYNEXUS_BACKEND_PORT`
pointed at proof 1 -- `vite preview` does not inherit the dev proxy, so leaving that variable unset
would quietly send the reading to port 8000 and report on somebody else's product.

Three of the activity rows come from the product's own doors, in this order: POST /journeys writes
`journey.created`, DELETE writes `journey.deleted`, and 找回 writes `journey.undeleted`. The other
two go in through the product's own audit writer against this lane's private database: one member
action, because the door that would write it is ORD-0434's and does not exist yet, and one action
name nothing knows, which is the case the screen must refuse to dress up. Both are marked `fixture`
in the readout.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parents[1]
WORK = pathlib.Path("D:/moodle/_qoder_ord0436_build")
DIST = WORK / "frontend" / "dist"
OUT = REPO / "review" / "ord0436-access"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
BACKEND_PORT = 4731
FRONTEND_PORT = 4802
DB = pathlib.Path("D:/moodle/_qoder_ord0436_stack/cnx.db")
FORBIDDEN_STORES = ("_preview.db", "_live.db")

READER = REPO / "live_checks" / "ord0436_two_arms_r1.mjs"


def clean_env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if "PROXY" not in k.upper()}
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(name, None)
    env.update(extra)
    return env


def listener_pid(port: int) -> int | None:
    # netstat writes this box's ANSI code page, not UTF-8; reading it as UTF-8 is how the first
    # cut of this instrument died (a decode error inside a reader thread, then a None stdout).
    raw = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"], capture_output=True, check=False
    ).stdout or b""
    out = raw.decode("utf-8", "replace") or raw.decode("gbk", "replace")
    for line in out.splitlines():
        if f":{port}" in line and "LISTENING" in line.upper():
            fields = line.split()
            return int(fields[-1]) if fields[-1].isdigit() else None
    return None


def process_info(pid: int) -> dict[str, object]:
    """This process' own command line and parent, read from the operating system.

    One joined line rather than `Format-List`: that formatter wraps a long command line across
    console rows, which is what made the first cut of this proof report `command_names_this_app_and_port
    = False` for a process whose command line did name the app and the port.
    """

    out = subprocess.run(
        [
            "powershell", "-NoProfile", "-Command",
            "$p = Get-CimInstance Win32_Process -Filter \"ProcessId=%d\"; "
            "'{0}|{1}|{2}' -f $p.ProcessId, $p.ParentProcessId, $p.CommandLine" % pid,
        ],
        capture_output=True,
        check=False,
    ).stdout or b""
    line = next((l for l in out.decode("utf-8", "replace").splitlines() if "|" in l), "")
    fields = line.split("|", 2)
    return {
        "pid": pid,
        "ProcessId": int(fields[0]) if len(fields) > 0 and fields[0].strip().isdigit() else None,
        "ParentProcessId": int(fields[1]) if len(fields) > 1 and fields[1].strip().isdigit() else None,
        "CommandLine": fields[2].strip() if len(fields) > 2 else "",
    }


def wait_for_port(port: int, timeout: float = 60.0) -> int | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        pid = listener_pid(port)
        if pid:
            return pid
        time.sleep(0.5)
    return None


def seed(created_journey_id: str) -> dict[str, object]:
    """Three rows from the product's own doors, two written by its own audit writer, all in this
    lane's private database."""

    import httpx

    base = f"http://127.0.0.1:{BACKEND_PORT}/api/v1"
    now = datetime.now(timezone.utc).isoformat()
    with httpx.Client(base_url=base, trust_env=False, timeout=30) as client:
        traveler = client.post(
            "/travelers",
            json={
                "display_name": "ORD-0436 probe",
                "email": None,
                "locale": "zh-CN",
                "timezone": "Asia/Shanghai",
            },
        )
        if traveler.status_code >= 400:
            raise SystemExit(f"the traveller door answered {traveler.status_code}: {traveler.text[:200]}")
        journey = client.post(
            "/journeys",
            json={
                "traveler_id": traveler.json()["id"],
                "title": "ORD-0436 access probe",
                "city_code": "CN-XIAMEN",
                "timezone": "Asia/Shanghai",
                "start_at": "2026-11-03T09:00:00+08:00",
                "end_at": "2026-11-05T17:00:00+08:00",
                "budget": {"amount_minor": 90000, "currency": "CNY"},
                "planning_mode": "balanced",
            },
        )
        journey.raise_for_status()
        journey_id = journey.json()["id"]
        deleted = client.delete(f"/journeys/{journey_id}")
        undeleted = client.post(f"/journeys/{journey_id}/undelete")
    # The two fixture rows go in through the product's own audit writer, in this process, against
    # this lane's database: `audit_logs.trace_id` is NOT NULL and the writer owns that value, so
    # hand-written SQL would have been testing my guess at the schema rather than the screen.
    os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
        sys.path.insert(0, str(REPO / "backend"))
    from app.core.audit import record_audit  # noqa: E402  (needs the database URL set above)
    from app.db.session import SessionLocal  # noqa: E402

    with SessionLocal() as session:
        record_audit(
            session,
            action="journey.member_added",
            entity_type="Journey",
            entity_id="ord0436-fixture-member",
            journey_id=journey_id,
            actor_type="traveller",
            actor_id="ord0436-probe",
            after={"member": "fixture"},
        )
        record_audit(
            session,
            action="journey.unlisted_share_change",
            entity_type="Journey",
            entity_id="ord0436-fixture-unknown",
            journey_id=journey_id,
            actor_type="traveller",
            actor_id="ord0436-probe",
            after={"note": "no sentence exists for this action"},
        )
        session.commit()

    import sqlite3

    with sqlite3.connect(DB) as connection:
        feed = [
            row[0]
            for row in connection.execute(
                "SELECT action FROM audit_logs WHERE journey_id = ? ORDER BY created_at, id",
                (journey_id,),
            )
        ]
    return {
        "journey_id": journey_id,
        "delete_door_status": deleted.status_code,
        "undelete_door_status": undeleted.status_code,
        "actions_in_this_lane_database": feed,
        "fixture_rows_written_by": "app.core.audit.record_audit (the product's own writer)",
        "fixture_rows": [
            {"action": "journey.member_added", "why": "ORD-0434 has no writer for it yet; the screen's sentence for it is what is being read"},
            {"action": "journey.unlisted_share_change", "why": "an action no sentence exists for, to prove the screen says so instead of inventing one"},
        ],
    }


def main() -> None:
    if not (DIST / "index.html").is_file():
        raise SystemExit(f"no production bundle at {DIST}; run vite build before this reading")
    OUT.mkdir(parents=True, exist_ok=True)
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()

    backend = subprocess.Popen(
        [PY, "-X", "utf8", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(BACKEND_PORT), "--log-level", "warning"],
        cwd=str(REPO / "backend"),
        env=clean_env(
            PYTHONPATH=f"{REPO}:{REPO / 'backend'}",
            CITYNEXUS_DATABASE_URL=f"sqlite:///{DB.as_posix()}",
            CITYNEXUS_DEMO_MODE="true",
        ),
        stdout=(WORK / "backend.out").open("w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
    )
    frontend = None
    report: dict[str, object] = {"started_at": datetime.now().astimezone().isoformat(timespec="seconds")}
    try:
        pid = wait_for_port(BACKEND_PORT)
        assert pid is not None, "the backend never took the port"
        info = process_info(pid)
        report["backend_identity"] = {
            "listener_pid": pid,
            "listener_is_spawned_or_its_child": info.get("ProcessId") == backend.pid
            or info.get("ParentProcessId") == backend.pid,
            "listener_command": str(info.get("CommandLine", ""))[:200],
            "command_names_this_app_and_port": (
                "app.main:app" in str(info.get("CommandLine", "")) and f"--port {BACKEND_PORT}" in str(info.get("CommandLine", ""))
            ),
            "database_file": str(DB),
            "database_exists": DB.exists(),
            "shared_stores_named_by_this_run": [
                name for name in FORBIDDEN_STORES if name in str(DB)
            ],
        }
        assert report["backend_identity"]["listener_is_spawned_or_its_child"], report["backend_identity"]
        assert report["backend_identity"]["command_names_this_app_and_port"], report["backend_identity"]
        assert not report["backend_identity"]["shared_stores_named_by_this_run"]

        seeded = seed("")
        report["seed"] = seeded

        vite_cli = WORK / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
        assert vite_cli.is_file(), f"no vite cli at {vite_cli}"
        frontend = subprocess.Popen(
            ["node", str(vite_cli), "preview", "--host", "127.0.0.1", "--port",
             str(FRONTEND_PORT), "--strictPort"],
            cwd=str(WORK / "frontend"),
            env=clean_env(CITYNEXUS_BACKEND_PORT=str(BACKEND_PORT)),
            stdout=(WORK / "frontend.out").open("w", encoding="utf-8"),
            stderr=subprocess.STDOUT,
        )
        assert wait_for_port(FRONTEND_PORT, 90.0), "vite preview never took its port"
        # Node resolves a bare package name from the importing file's own directory upward, so the
        # reader has to sit next to the tree that has `node_modules`; running it out of the repo's
        # `live_checks/` gave `Cannot find package 'playwright'` with nothing else wrong.
        reader_copy = WORK / "frontend" / READER.name
        # The reader imports one sibling module (the contract-domain parser), and a missing import
        # would kill the reading with a node error rather than a product red -- so both files travel.
        for helper in sorted((REPO / "live_checks").glob("ord0436_*.mjs")):
            shutil.copyfile(helper, WORK / "frontend" / helper.name)
        reading = subprocess.run(
            ["node", str(reader_copy)],
            cwd=str(WORK / "frontend"),
            env=clean_env(
                CNX_BASE=f"http://127.0.0.1:{FRONTEND_PORT}",
                CNX_JOURNEY=seeded["journey_id"],
                CNX_OUT=str(OUT),
                # The seam arm reads the contract from the lane tree: the bundle this reading runs
                # against lives in a separate export directory that holds no `contracts/`.
                CNX_REPO=str(REPO),
            ),
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, timeout=420,
        )
        report["reader_exit_code"] = reading.returncode
        try:
            report["reading"] = json.loads(reading.stdout[reading.stdout.index("{"): reading.stdout.rindex("}") + 1])
        except ValueError:
            report["reading_unparsed"] = reading.stdout[-4000:]
            report["reader_stderr"] = reading.stderr[-2000:]
        (OUT / "TWO_ARMS_R1.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8", newline="\n")
        checks = (report.get("reading") or {}).get("checks", [])
        for check in checks:
            print(f"{check['verdict']:5s} {check['name']} :: {str(check['detail'])[:150]}")
        print("all_pass:", (report.get("reading") or {}).get("all_pass"), "| readout:", OUT / "TWO_ARMS_R1.json")
    finally:
        for process in (frontend, backend):
            if process is None:
                continue
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        time.sleep(1.0)
        report["stopped"] = {
            "backend_port_release": listener_pid(BACKEND_PORT) is None,
            "frontend_port_release": listener_pid(FRONTEND_PORT) is None,
        }
        print(json.dumps(report["stopped"], indent=2))
        shutil.rmtree(DB.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
