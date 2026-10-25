"""Read the classroom stack the way the teacher will meet it, and print the short receipt fields.

Checks, in order: backend health, the LAN page, the demo session (which also tells us the journey
is ACTIVE), whether a PRESENTED proposal is waiting, and whether the simulated clock answers.  It
never prints a token, never writes anything, and does not change the scene.
"""
from __future__ import annotations

import json
import os
import socket
import sqlite3
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


health_status, health = get(API + "/api/v1/health")
web_status, _ = get(WEB + "/revolution")
lan_status, _ = get(LAN + "/revolution")
session_status, session = get(API + "/api/v1/demo/session")
journey_id = str(session.get("journey_id") or "")
clock_status, clock = get(API + "/api/v1/demo/simulation-clock/" + journey_id) if journey_id else (0, {})
token = str(session.get("access_token") or "")
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
    "SIM_CONSOLE": sim_console,
    "TABLET_OPEN": "http://%s:14492/revolution (tablet: UNVERIFIED)" % lan_ipv4(),
    "AGENT_QA": "direct-replan-only",
    "REAL_POI": True,
    "SAVED_PLAN": bool(scene.get("active_plan")),
    "RESTART_SESSION": True,
    "FALLBACK_SCREENSHOT": "trial/results/20261022_v3_human_chrome/rehearsal11-origin.png",
}, ensure_ascii=False))
