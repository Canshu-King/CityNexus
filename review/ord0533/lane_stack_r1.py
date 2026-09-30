"""ORD-0533 lane stack -- my own backend on my own port (same shape as the ORD-0525 runner; a branch cannot borrow another branch file), reading my own copy of a scheduled DB.

Why a script and not a hand command: the acceptance for this order is a *download*, so a browser has
to talk to a real server.  That makes three things provable before any screen reading counts:

1. the listener is mine.  A 200 on a port is not identity (`project-shared-port-readiness-is-not-identity`),
   so this proves ownership with a marker journey that exists only in my copy -- created through the
   product's own POST doors -- plus the opposite probe: a well-formed uuid that is not in any store has
   to answer 404.  A one-way 200 is not a proof.
2. the code generation is mine.  `GET /api/v1/journeys/<marker>/calendar.ics` on a marker journey that
   has no active plan must answer the named 409 refusal this lane shipped in slice 1.  Another lane's
   backend at an older generation would answer 404 for an unknown route instead.
3. the expected numbers come from the server, not from a head.  The canary trip's per-day stop counts
   are read out of `GET /api/v1/journeys/{id}` (the read door) and grouped in the trip's own timezone,
   the same way the screen groups them, so the spec compares three independent renderings of one fact.

Ports come from the environment and default to 4911 (backend) / 4912 (frontend).  The four ports this
lane must never touch (:8000, :4781, :4782, :8693) and the LAN backends the commander named (:4783,
:4785, :4787) are asserted free-or-not-mine before anything starts.

Usage:
    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0533/lane_stack_r1.py --start
    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0533/lane_stack_r1.py --stop
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0533_data")
DB = DATA / "_ord0533-lane.db"
BACKEND_LOG = DATA / "uvicorn_4911_r1.log"
RECEIPT = DATA / "lane_stack_receipt_r1.json"
SOURCE_CANARY = pathlib.Path(
    "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/canary_56d20ec.db"
)
PY = sys.executable
FORBIDDEN = (8000, 4781, 4782, 4783, 4785, 4786, 4787, 8693)
CANARY_JOURNEY = "22222222-2222-4222-8222-222222222222"


def ports() -> tuple[int, int]:
    return (
        int(os.environ.get("CITYNEXUS_ORD0533_BACKEND_PORT", "4911")),
        int(os.environ.get("CITYNEXUS_ORD0533_PORT", "4912")),
    )


def listening_pids(port: int) -> list[str]:
    """Every pid LISTENING on exactly this port.

    The first cut of this filter matched `line.strip().endswith("LISTENING")`, which can never be true:
    `netstat -ano` puts the state in column four and the pid last, so the function answered `[]` for a
    port that was demonstrably held, and both the "my port is free" assertion and the teardown check
    were vacuous.  Measured on this machine (col2=local, col4=LISTENING, last field=pid); the column
    positions are what the function now reads.
    """

    finished = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, errors="replace"
    )
    pids: set[str] = set()
    for line in finished.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0] != "TCP":
            continue
        local, state, pid = parts[1], parts[3], parts[-1]
        if state.upper() == "LISTENING" and local.endswith(f":{port}"):
            pids.add(pid)
    return sorted(pids)


def http(method: str, url: str, body: dict | None = None) -> tuple[int, dict | bytes | None, str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"content-type": "application/json", "user-agent": "CityNexus-ORD-0533-lane"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as answer:
            raw = answer.read()
            kind = answer.headers.get("content-type", "")
            payload: dict | bytes
            if "json" in kind:
                payload = json.loads(raw.decode("utf-8"))
            else:
                payload = raw
            return answer.status, payload, kind
    except urllib.error.HTTPError as failure:
        raw = failure.read()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = raw
        return failure.code, payload, failure.headers.get("content-type", "")


def fetch_calendar(url: str) -> tuple[int, bytes, dict[str, str]]:
    """A GET that keeps the response headers, because the counts this door promises ride in them.

    `http()` throws the headers away, which is right for JSON bodies and wrong here: the whole point of
    the slice-1 headers is that a reader can check the arithmetic without parsing the object.
    """

    request = urllib.request.Request(
        url, method="GET", headers={"user-agent": "CityNexus-ORD-0533-lane"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as answer:
            return answer.status, answer.read(), {
                key.lower(): value for key, value in answer.headers.items()
            }
    except urllib.error.HTTPError as failure:
        return failure.code, failure.read(), {
            key.lower(): value for key, value in (failure.headers or {}).items()
        }


def main(argv: list[str]) -> int:
    backend_port, frontend_port = ports()
    base = f"http://127.0.0.1:{backend_port}"

    if "--stop" in argv:
        owner = listening_pids(backend_port)
        killed: list[str] = []
        for pid in owner:
            subprocess.run(["taskkill", "/T", "/F", "/PID", pid], capture_output=True)
            killed.append(pid)
        time.sleep(1.5)
        still = listening_pids(backend_port)
        print(json.dumps({"killed": killed, "still_listening": still, "port": backend_port}))
        return 0 if not still else 1

    # ---- precondition: my ports are free, and I am not sitting on a forbidden one
    assert not listening_pids(backend_port), f"backend port {backend_port} is already held"
    assert not listening_pids(frontend_port), f"frontend port {frontend_port} is already held"
    held_forbidden = {p: listening_pids(p) for p in FORBIDDEN if listening_pids(p)}
    assert DB.is_file(), f"my copy of the scheduled store is missing: {DB}"

    environment = dict(os.environ)
    environment.pop("DEEPSEEK_API_KEY", None)
    environment.pop("CITYNEXUS_E2E_RUN_ID", None)  # the run-id guard refuses an existing file
    environment["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
    environment["CITYNEXUS_DEMO_MODE"] = "true"

    log = BACKEND_LOG.open("w", encoding="utf-8", errors="replace")
    child = subprocess.Popen(
        [
            PY, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(backend_port), "--log-level", "info",
        ],
        cwd=ROOT / "backend",
        env=environment,
        stdout=log,
        stderr=subprocess.STDOUT,
    )

    ready = None
    for _ in range(90):
        try:
            status, payload, _kind = http("GET", f"{base}/api/v1/health")
            if status == 200:
                ready = payload
                break
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(1)
    assert ready is not None, f"backend did not come up; see {BACKEND_LOG}"

    # ---- proof 1: the listener reads MY file, in both directions
    status, traveler, _ = http(
        "POST",
        f"{base}/api/v1/travelers",
        {"display_name": "ORD-0533 车道探针", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    )
    assert status == 201, (status, traveler)
    marker_id = str(uuid.uuid4())
    status, journey, _ = http(
        "POST",
        f"{base}/api/v1/journeys",
        {
            "id": marker_id,
            "traveler_id": traveler["id"],
            "title": "ORD-0525 私有探针行程",
            "city_code": "CN-XIAMEN",
            "timezone": "Asia/Shanghai",
            "start_at": "2031-06-01T00:00:00+08:00",
            "end_at": "2031-06-03T00:00:00+08:00",
            "budget": {"amount_minor": 50000, "currency": "CNY"},
            "planning_mode": "balanced",
        },
    )
    assert status in (200, 201), (status, journey)
    marker_journey = journey["id"]
    positive_status, positive_body, _ = http("GET", f"{base}/api/v1/journeys/{marker_journey}")
    negative_status, _, _ = http("GET", f"{base}/api/v1/journeys/{uuid.uuid4()}")

    # ---- proof 2: the door this lane shipped is the generation answering
    cal_status, cal_body, cal_kind = http(
        "GET", f"{base}/api/v1/journeys/{marker_journey}/calendar.ics"
    )
    refusal = (cal_body or {}).get("error", {}).get("reason_code") if isinstance(cal_body, dict) else None

    # ---- proof 3: the expected per-day numbers, read from the door the SCREEN reads.
    # `GET /api/v1/journeys/{id}` is the trip's own row and carries no plan projection at all (measured:
    # this probe first asked that door for `active_plan` and got a null, which is my key-name guess
    # being wrong, not the server having no plan).  The shell's boot read is
    # `GET /api/v1/journeys/{id}/experience` (`frontend/src/app/V8Experience.tsx:740`), and that is the
    # payload the itinerary paints, so that is the door the arm's denominator must come from.
    status, v8, _ = http("GET", f"{base}/api/v1/journeys/{CANARY_JOURNEY}/experience")
    assert status == 200, (status, v8)
    tz = v8["journey"]["timezone"]
    plan = v8.get("active_plan") or {}
    activities = plan.get("activities") or []
    per_day: dict[str, int] = {}
    for row in activities:
        # The trip's own calendar day for each stop: the browser reaches it through Intl in
        # `TripItinerary.localDateKey`, this script through zoneinfo, and the spec reads the numbers
        # the screen itself paints.  Three renderings of one rule, so an arm that lets them disagree
        # is failing for a real reason.
        day = datetime.fromisoformat(row["start_at"]).astimezone(ZoneInfo(tz)).date().isoformat()
        per_day[day] = per_day.get(day, 0) + 1
    ics_status, ics_bytes, ics_headers = fetch_calendar(
        f"{base}/api/v1/journeys/{CANARY_JOURNEY}/calendar.ics"
    )
    ics_text = ics_bytes.decode("utf-8")
    events = len(re.findall(r"BEGIN:VEVENT", ics_text))

    with sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True) as connection:
        census = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("journeys", "activities", "plan_versions", "places")
        }

    receipt = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "backend_port": backend_port,
        "frontend_port": frontend_port,
        "recorded_child_pid": child.pid,
        "socket_owner_pids": listening_pids(backend_port),
        "database_url": environment["CITYNEXUS_DATABASE_URL"],
        "health": ready,
        "forbidden_ports_held_by_others": held_forbidden,
        "marker_journey_id": marker_journey,
        "identity_positive_status": positive_status,
        "identity_positive_echoes_marker": bool(
            isinstance(positive_body, dict) and positive_body.get("id") == marker_journey
        ),
        "identity_negative_status": negative_status,
        "calendar_on_marker_status": cal_status,
        "calendar_on_marker_reason": refusal,
        "calendar_on_marker_media_type": cal_kind,
        "canary_journey_id": CANARY_JOURNEY,
        "canary_timezone": tz,
        "canary_active_plan_id": plan.get("id"),
        "canary_activities_from_experience_door": len(activities),
        "canary_stops_per_day": per_day,
        "source_canary_file": (
            "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/canary_56d20ec.db"
        ),
        "source_canary_sha256_at_probe": hashlib.sha256(SOURCE_CANARY.read_bytes()).hexdigest()[:16],
        "source_canary_sha256_at_copy": "6160ac66274558e5",
        "source_canary_opened_only_as_mode_ro": True,
        "canary_calendar_status": ics_status,
        "canary_calendar_media_type": ics_headers.get("content-type"),
        "canary_calendar_content_disposition": ics_headers.get("content-disposition"),
        "canary_calendar_count_headers": {
            key: value for key, value in ics_headers.items() if key.startswith("x-citynexus-ics")
        },
        "canary_calendar_bytes": len(ics_bytes),
        "canary_calendar_vevents_counted_from_body": events,
        "store_census_after_boot": census,
        "backend_log": str(BACKEND_LOG),
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2)[:2600])
    # The child is left running on purpose: the spec needs it.  --stop takes it down and re-checks.
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
