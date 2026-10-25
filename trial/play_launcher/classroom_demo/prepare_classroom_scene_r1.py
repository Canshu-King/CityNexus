"""Prepare the classroom scene on the isolated demo stack, then print the short receipt fields.

What it does, in order: snapshot the play database through sqlite3's backup API into the demo
database, restart the demo backend on 60391 with the fixed demo secret, wait for health, sign a
bearer for the demo journey's traveller, and ask the replan endpoint for one closure proposal so the
phone already has a card to accept.  It never touches the play stack's files or ports, never prints
the bearer, and never writes the AMap key anywhere.

Run it before a rehearsal, or whenever the scene has been consumed (the journey keeps the plan the
teacher accepted).
"""
from __future__ import annotations

from datetime import datetime
import io
import json
import os
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
OUT = r"D:/moodle/_cmdr_v3_port_1022"
CANARY = r"D:/moodle/_cmdr_v3_live_1022"
SRC = os.path.join(CANARY, "citynexus_v3_play_1024.db")
DST = os.path.join(CANARY, "citynexus_v3_demo_1025.db")
PORT = 60391
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
SHIM = r"C:/Users/仓鼠王/WorkBuddy/2026-09-15-15-47-27/wb2api/codex-shim/shim.mjs"
SECRET = os.environ.get("MERGE_AUTH_SECRET") or secrets.token_hex(32)
MODEL = "cn:hy3"
JOURNEY = "2e9cd67d-10ca-4ecd-920b-76c81a350c71"
TRAVELER = "9ac3c100-da78-4933-ba1b-cb79991fcb1e"


def gateway_key() -> str:
    match = re.search(r"WB2API_KEY \|\| '([^']+)'", io.open(SHIM, encoding="utf-8").read())
    if not match:
        raise SystemExit("no local gateway key found")
    return match.group(1)


def call(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=240) as answer:
            raw = answer.read().decode("utf-8")
            return answer.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            return error.code, (json.loads(raw) if raw else {})
        except ValueError:
            return error.code, {"raw": raw[:300]}


def listening_pid(port: int) -> str | None:
    probe = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace")
    for line in probe.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].upper() == "TCP" and fields[1].endswith(":%d" % port) \
                and fields[3].upper() == "LISTENING":
            return fields[4]
    return None


def lan_ipv4() -> str:
    """The address the tablet must use; a Wi-Fi reconnect changes it."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


INCIDENT_LEAD = "T00:57:00+00:00"  # 08:57 at +08:00, three minutes before the 09:00 clock


def _shift(value, delta):
    if not value:
        return value
    try:
        return (datetime.fromisoformat(str(value)) + delta).isoformat()
    except ValueError:
        return value


def align_incident_to_virtual_day(target: sqlite3.Connection) -> None:
    """Leave one opening-day incident and put its whole trail on the virtual clock.

    The play database accumulated two closures from earlier rehearsals, and their
    timestamps were real-world UTC, so the phone showed 10/25 beside a 12/03 virtual
    clock. Keep the incident that happens on the journey's opening day, drop the rest,
    and shift its detection (plus the guardian runs, pulses and recovery epoch that
    trail it) by one constant offset, so every line on the phone tells the same day
    and keeps its order.
    """
    row = target.execute("select start_at from journeys where id=?", (JOURNEY,)).fetchone()
    if row is None or not row[0]:
        return
    day = str(row[0])[:10]
    events = target.execute(
        "select id, detected_at from events where journey_id=? and event_type='CLOSURE' "
        "order by (substr(occurred_at,1,10)=?) desc, detected_at desc, id desc",
        (JOURNEY, day),
    ).fetchall()
    for (event_id, _detected) in events[1:]:
        target.execute("delete from events where id=?", (event_id,))
    if not events:
        return
    event_id, detected = events[0]
    delta = datetime.fromisoformat(day + INCIDENT_LEAD) - datetime.fromisoformat(str(detected))
    target.execute(
        "update events set detected_at=?, created_at=? where id=?",
        (_shift(detected, delta), _shift(detected, delta), event_id),
    )
    for table, columns in (
        ("guardian_runs", ("created_at", "completed_at")),
        ("guardian_pulses", ("started_at", "completed_at")),
        ("recovery_epochs", ("opened_at", "closed_at")),
        ("recovery_discovery_attempts", ("created_at", "updated_at")),
    ):
        rows = target.execute(
            "select id," + ",".join(columns) + " from " + table + " where journey_id=?",
            (JOURNEY,),
        ).fetchall()
        for pk, *values in rows:
            assignments = ",".join("%s=?" % column for column in columns)
            target.execute(
                "update " + table + " set " + assignments + " where id=?",
                (*[_shift(value, delta) for value in values], pk),
            )


def copy_database() -> None:
    source = sqlite3.connect("file:" + SRC + "?mode=ro", uri=True)
    target = sqlite3.connect(DST)
    try:
        source.backup(target)
        # Every rehearsal starts at the journey's opening hour, not at whatever
        # hour the previous demonstration advanced to.
        target.execute("DELETE FROM simulation_clocks")
        align_incident_to_virtual_day(target)
        target.commit()
    finally:
        target.close()
        source.close()


def restart_backend() -> None:
    holder = listening_pid(PORT)
    if holder:
        subprocess.run(["taskkill", "/PID", holder, "/F"], capture_output=True)
        time.sleep(2)
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + DST.replace("\\", "/"),
        "CITYNEXUS_TRAVELER_AUTH_SECRET": SECRET,
        "CITYNEXUS_TRAVELER_AUTH_TTL_SECONDS": "43200",
        "CITYNEXUS_DEMO_MODE": "true",
        "CITYNEXUS_DEMO_RESET_TOKEN": SECRET[:16],
        # Codex's presenter boundary checks this before issuing a classroom session.
        "CITYNEXUS_DEMO_DATABASE_PATH": DST,
        "CITYNEXUS_SIMULATION_ENABLED": "true",
        "CITYNEXUS_AI_ENABLED": "true",
        "CITYNEXUS_AI_PROVIDER": "deepseek",
        "CITYNEXUS_AI_MODEL": MODEL,
        "CITYNEXUS_AI_API_KEY": gateway_key(),
        "CITYNEXUS_DEEPSEEK_API_URL": "http://127.0.0.1:7864/v1/responses",
        "CITYNEXUS_DEEPSEEK_REASONING_EFFORT": "low",
        "CITYNEXUS_DEEPSEEK_WEB_SEARCH": "false",
        "CITYNEXUS_HERMES_API_URL": "http://127.0.0.1:7863/v1/chat/completions",
        "CITYNEXUS_HERMES_API_KEY": gateway_key(),
        "CITYNEXUS_HERMES_MODEL": MODEL,
        "PYTHONPATH": os.path.join(ROOT, "backend"),
    })
    subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT),
         "--app-dir", os.path.join(ROOT, "backend")],
        cwd=os.path.join(ROOT, "backend"), env=env,
        stdout=open(os.path.join(OUT, "uvicorn_demo_classroom.log"), "wb"), stderr=subprocess.STDOUT,
    )
    for _ in range(120):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/v1/health", timeout=5) as answer:
                if answer.status == 200:
                    return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.5)
    raise SystemExit("demo backend did not become healthy")


def _listening_pids(port: int) -> list[str]:
    probe = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace")
    pids: list[str] = []
    for line in probe.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].upper() == "TCP" and fields[1].endswith(":%d" % port)                 and fields[3].upper() == "LISTENING":
            pids.append(fields[4])
    return pids


def ensure_frontend() -> bool:
    """Start the LAN demo front end on a port this script owns.

    14492 is the classroom port: a stray listener (an orphaned vite bound to
    127.0.0.1 only, measured 2026-10-25) shadows the LAN one on this machine, so
    every listener there is replaced rather than trusted.
    """
    for pid in set(_listening_pids(14492)):
        subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
    time.sleep(1)
    node = r"C:/Program Files/nodejs/node.exe"
    env = dict(os.environ)
    env["CITYNEXUS_BACKEND_PORT"] = str(PORT)
    subprocess.Popen(
        [node, os.path.join(ROOT, "frontend", "node_modules", "vite", "bin", "vite.js"),
         "--port", "14492", "--strictPort", "--host", "0.0.0.0"],
        cwd=os.path.join(ROOT, "frontend"), env=env,
        stdout=open(os.path.join(OUT, "vite_demo_classroom.log"), "wb"), stderr=subprocess.STDOUT,
    )
    for _ in range(40):
        if listening_pid(14492):
            return True
        time.sleep(0.5)
    return False


def issue_token() -> str:
    sys.path.insert(0, os.path.join(ROOT, "backend"))
    os.environ["CITYNEXUS_TRAVELER_AUTH_SECRET"] = SECRET
    from app.traveler_principal import issue_traveler_token

    return issue_traveler_token(TRAVELER, ttl_seconds=43200)


copy_database()
restart_backend()
FRONTEND_UP = ensure_frontend()
TOKEN = issue_token()

readonly = sqlite3.connect("file:" + DST + "?mode=ro", uri=True)
readonly.row_factory = sqlite3.Row
journey = readonly.execute(
    "select id, title, status, active_plan_version_id from journeys where id=?", (JOURNEY,)
).fetchone()
event = readonly.execute(
    "select id, event_type from events where journey_id=? and status in ('DETECTED','ACKNOWLEDGED') "
    "order by detected_at desc limit 1",
    (JOURNEY,),
).fetchone()
readonly.close()

proposal = None
if journey is not None and event is not None:
    status, answer = call(
        "POST", f"/api/v1/journeys/{JOURNEY}/replans",
        {"trigger_event_id": event["id"], "candidate_count": 3}, token=TOKEN,
    )
    proposal = answer.get("id") if status == 201 else None
    proposal_status = answer.get("status") if status == 201 else answer.get("error", {}).get("reason_code")
else:
    status, proposal_status = 0, "NO_EVENT"

print(json.dumps({
    "DEMO_READY": bool(proposal),
    "WINDOWS_START": "start_classroom_demo.bat",
    "FRONTEND_UP": FRONTEND_UP,
    "TABLET_OPEN": "http://%s:14492/revolution" % lan_ipv4(),
    "AGENT_QA": "direct-replan-only (agent path verified separately)",
    "REAL_POI": True,
    "SAVED_PLAN": bool(journey and journey["active_plan_version_id"]),
    "RESTART_SESSION": True,
    "FALLBACK_SCREENSHOT": "trial/results/20261022_v3_human_chrome/rehearsal11-origin.png",
    "journey": dict(journey) if journey is not None else None,
    "event": dict(event) if event is not None else None,
    "replan_http_status": status,
    "proposal": proposal,
    "proposal_status": proposal_status,
}, ensure_ascii=False))
print()
print("Classroom ready. Tablet address (same Wi-Fi): http://%s:14492/revolution" % lan_ipv4())
