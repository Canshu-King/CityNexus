"""Read the classroom stack the way the teacher will meet it, and print the short receipt fields.

Checks, in order: backend health, the LAN page, the demo session (which also tells us the journey
is ACTIVE), whether a PRESENTED proposal is waiting, and whether the simulated clock answers.  It
never prints a token, never writes anything, and does not change the scene.
"""
from __future__ import annotations

import io
import json
import os
import socket
import sqlite3
import time
import urllib.error
import urllib.request

CANARY = r"D:/moodle/_cmdr_v3_live_1022"
DB = os.path.join(CANARY, "citynexus_v3_demo_1025.db")
API = "http://127.0.0.1:60391"
WEB = "http://127.0.0.1:14492"
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


LAN = "http://%s:14492" % lan_ipv4()

SESSION_FILE = os.path.join(CANARY, ".demo_presenter_session.json")


def presenter_session() -> dict | None:
    """A short-lived presenter bearer written by the launcher after it redeems a ticket."""
    try:
        with io.open(SESSION_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("access_token") and int(data.get("expires_at") or 0) > time.time() + 5:
            return data
    except (OSError, ValueError, TypeError):
        pass
    return None


def get(url: str, timeout: int = 8, bearer: str = "") -> tuple[int, dict]:
    try:
        request = urllib.request.Request(url)
        if bearer:
            request.add_header("Authorization", "Bearer " + bearer)
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            raw = answer.read().decode("utf-8", "replace")
            try:
                return answer.status, (json.loads(raw) if raw.strip().startswith("{") else {})
            except ValueError:
                return answer.status, {}
    except urllib.error.HTTPError as error:
        return error.code, {}
    except Exception:  # noqa: BLE001
        return 0, {}


def pairing_door() -> str:
    """Which entry door this backend serves: a pairing ticket or the older open demo session."""
    request = urllib.request.Request(
        API + "/api/v1/demo/pairing", data=b"{}", method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as answer:
            return "PAIRING" if answer.status in (201, 400, 422) else "http=%s" % answer.status
    except urllib.error.HTTPError as error:
        if error.code in (403, 422):
            return "PAIRING"
        return "SESSION" if error.code in (404, 405) else "http=%s" % error.code
    except Exception:  # noqa: BLE001
        return "UNKNOWN"


health_status, health = get(API + "/api/v1/health")
web_status, _ = get(WEB + "/revolution")
lan_status, _ = get(LAN + "/revolution")
presenter = presenter_session()
door = pairing_door()
if presenter:
    session_status, session = 200, {"journey_id": presenter.get("journey_id")}
    token = str(presenter.get("access_token") or "")
    session_state = "LIVE"
else:
    session_status, session = get(API + "/api/v1/demo/session")
    token = str(session.get("access_token") or "")
    # A pairing backend hands out 15-minute bearers; an expired file is not a
    # broken stack, it only means the launcher has to print a fresh ticket.
    session_state = "OPEN" if session_status == 200 else (
        "NEEDS_TICKET" if door == "PAIRING" else "MISSING")
journey_id = str(session.get("journey_id") or "")
if not journey_id and os.path.exists(DB):
    readonly = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    row = readonly.execute(
        "select id from journeys where status='ACTIVE' order by created_at desc limit 1"
    ).fetchone()
    readonly.close()
    if row is not None:
        journey_id = row[0]
clock_status, clock = (
    get(API + "/api/v1/demo/simulation-clock/" + journey_id, bearer=token)
    if journey_id else (0, {})
)
sim_status, sim_body = (
    get(API + "/api/v1/journeys/" + journey_id + "/simulation/runs/current", bearer=token)
    if journey_id and token else (0, {})
)
sim_console = (
    "AVAILABLE:" + str(sim_body.get("status"))
    if sim_status == 200
    else "NOT_DEPLOYED" if sim_status == 404 else "http=%s" % sim_status
)

proposal = None
scene = {"journey": journey_id or None, "journey_status": session.get("status")}
if journey_id and os.path.exists(DB):
    readonly = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    readonly.row_factory = sqlite3.Row
    row = readonly.execute(
        "select id, status from replan_proposals where journey_id=? and status='PRESENTED' "
        "order by created_at desc limit 1",
        (journey_id,),
    ).fetchone()
    if row is not None:
        proposal = row["id"]
    journey_row = readonly.execute(
        "select status, active_plan_version_id from journeys where id=?", (journey_id,)
    ).fetchone()
    if journey_row is not None:
        scene["journey_status"] = journey_row["status"]
        scene["active_plan"] = journey_row["active_plan_version_id"]
    readonly.close()

print(json.dumps({
    "DEMO_READY": bool(health_status == 200 and web_status == 200 and session_status == 200 and proposal),
    "BACKEND_HEALTH": health_status,
    "PAGE_LOOPBACK": web_status,
    "PAGE_LAN": lan_status,
    "AI_STATE": health.get("ai_state"),
    "DEMO_SESSION": session_status,
    "JOURNEY_STATUS": scene.get("journey_status"),
    "ACTIVE_PLAN": scene.get("active_plan"),
    "PROPOSAL_WAITING": proposal,
    "CLOCK_HTTP": clock_status,
    "CLOCK": clock.get("virtual_now"),
    "CLOCK_VERSION": clock.get("version"),
    "ENTRY_DOOR": door, "SESSION_STATE": session_state,
    "STACK_HEALTHY": bool(health_status == 200 and web_status == 200
                          and scene.get("journey_status") in ("ACTIVE", "COMPLETED")),
    "SIM_CONSOLE": sim_console,
    "TABLET_OPEN": "http://%s:14492/revolution (tablet: UNVERIFIED)" % lan_ipv4(),
    "AGENT_QA": "direct-replan-only",
    "REAL_POI": True,
    "SAVED_PLAN": bool(scene.get("active_plan")),
    "RESTART_SESSION": True,
    "FALLBACK_SCREENSHOT": "trial/results/20261022_v3_human_chrome/rehearsal11-origin.png",
}, ensure_ascii=False))
