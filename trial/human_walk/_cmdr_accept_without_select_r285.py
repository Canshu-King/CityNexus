"""bw285: what does the accept door actually ask, and what does the shared door say instead?

Why this exists: section 14.21 listed sixteen places that can write a plan or journey into a
departure state, and only three of them visibly ask the shared authority blocker
(app/services.py plan_authority_blocker).  The trip-studio accept route is one of the three
that asks a door at all - but the door it asks, _trip_studio_authoritative_gate, reads only
frozen mobility evidence (backend/app/main.py:18642-18699): snapshot identity, integrity hash,
expiry, per-leg minutes, currency, times.  Nothing in it looks at a Place's opening or cost
facts.  Nobody had walked a real accept request to see which questions get asked.

This probe walks real HTTP routes on an isolated temporary database and records every answer of
three functions: the accept context resolver, its own authoritative gate, and the shared
authority blocker.  Then it asks the shared blocker and the accept gate directly, in this same
process, about the very same plan the walk produced - so a zero on the walk genuinely means
"nobody asked that door" rather than "the door is broken".

Disclosed setup: the journey, offers, stay option and plan below are produced by the product's
own POST routes inside a throwaway database this probe declares for itself.  Nothing is seeded
by hand, no DOM or API stub is used, and nothing here proves what a traveller sees on a screen.
"""

import io
import json
import os
import pathlib
import re
import sys
import tempfile
import threading
import uuid as uuidlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "tests"))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

if "CITYNEXUS_DATABASE_URL" in os.environ:
    print("ABORT this probe owns its database and refuses an inherited one")
    sys.exit(3)
TEMP_DIR = pathlib.Path(tempfile.mkdtemp(prefix="cnx_r285_"))
os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///%s" % (TEMP_DIR / "probe.db").as_posix()
os.environ.setdefault("CITYNEXUS_DEMO_RESET_TOKEN", uuidlib.uuid4().hex)
os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")

from demo_stage import demo_reset_headers  # noqa: E402
import app.main as main_module  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw285-accept-without-select.txt")
LOG = []
CALLS = []
_step_label = ["(unlabelled)"]

TARGETS = {
    "_trip_studio_context": "accept context",
    "_trip_studio_authoritative_gate": "accept's own gate",
    "plan_authority_blocker": "shared authority blocker",
}


def _trace(frame, event, arg):
    code = frame.f_code
    name = code.co_name
    if name not in TARGETS:
        return None
    if event != "call":
        return None

    def inner(frame, event, arg):
        if event == "return":
            result = arg[0] if isinstance(arg, tuple) else arg
            row = {"step": _step_label[0], "which": TARGETS[name],
                   "line": frame.f_lineno}
            if name == "plan_authority_blocker":
                row["verdict"] = "REFUSED" if isinstance(result, str) else "PASSED"
                row["detail"] = result if isinstance(result, str) else ""
                row["used_ids"] = len(frame.f_locals.get("used_unique") or [])
                row["content_places"] = len(frame.f_locals.get("used_content_places") or [])
            elif name == "_trip_studio_authoritative_gate":
                failures = []
                if isinstance(result, dict):
                    failures = list(result.get("failures") or [])
                row["verdict"] = "PASSED" if not failures else "FAILED"
                row["detail"] = ",".join(failures)[:220]
                row["used_ids"] = len(frame.f_locals.get("ordered") or [])
                row["content_places"] = 0
                row["fact_failure"] = any(
                    word in item for item in failures for word in ("OPENING", "COST_UNRESOLVED")
                )
            else:
                row["verdict"] = "returned"
                row["detail"] = ""
                row["used_ids"] = 0
                row["content_places"] = 0
            CALLS.append(row)
        return inner

    return inner


def _step(label):
    _step_label[0] = label


def _mask(text):
    return re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{28}", lambda m: m.group(0)[:8] + "…masked", str(text))


def _call(client, method, url, **kwargs):
    response = getattr(client, method)(url, **kwargs)
    LOG.append("%s %s -> http_status=%s" % (method.upper(), url, response.status_code))
    return response


def _make_journey(client, title):
    ids = _call(client, "post", "/api/v1/demo/reset", headers=demo_reset_headers()).json()
    create = _call(client, "post", "/api/v1/journeys", json={
        "traveler_id": ids["traveler_id"],
        "title": title,
        "city_code": "CN-TIANJIN",
        "timezone": "Asia/Shanghai",
        "start_at": "2026-10-09T18:00:00+08:00",
        "end_at": "2026-10-11T15:00:00+08:00",
        "budget": {"amount_minor": 120000, "currency": "CNY"},
        "stay_budget": {"amount_minor": 70000, "currency": "CNY"},
        "party_size": 2,
        "occupancy": {"adults": 2, "rooms": 1},
        "arrival_anchor": {"at": "2026-10-09T18:00:00+08:00", "location": "Tianjin West Station"},
        "departure_anchor": {"at": "2026-10-11T15:00:00+08:00", "location": "Tianjin Binhai Airport"},
    })
    if create.status_code != 201:
        LOG.append("BLOCKED at journey create: %s" % _mask(create.text[:300]))
        return None
    return create.json()["id"]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # threading.settrace arms threads created after this call, which is what the TestClient's
    # worker pool is; sys.settrace covers the calling thread.
    threading.settrace(_trace)
    sys.settrace(_trace)
    client = TestClient(main_module.app)

    # arm 1: a journey with no plan chosen at all - press accept anyway
    _step("arm1: accept on a journey with no active plan")
    j1 = _make_journey(client, "r285 arm1: accept without any selection")
    if j1 is None:
        return _finish()
    resp1 = _call(client, "post", f"/api/v1/journeys/{j1}/trip-studio/accept", json={
        "activity_ids": [str(uuidlib.uuid4()), str(uuidlib.uuid4())]})
    LOG.append("ARM1 http_status=%s body=%s" % (resp1.status_code, _mask(resp1.text[:400])))

    # arm 2: a real stay-materialised plan, then accept a swapped order
    _step("arm2: build a plan through the product's own routes")
    j2 = _make_journey(client, "r285 arm2: accept against a stay-materialised plan")
    if j2 is None:
        return _finish()
    _call(client, "post", f"/api/v1/journeys/{j2}/stays/offers/capture")
    generated = _call(client, "post", f"/api/v1/journeys/{j2}/stay-options/generate")
    if generated.status_code != 200 or not generated.json().get("top_k"):
        LOG.append("BLOCKED at stay-options generate: %s" % _mask(generated.text[:200]))
        return _finish()
    option_id = generated.json()["top_k"][0]["id"]
    _step("arm2: stay-option select")
    selected = _call(client, "post", f"/api/v1/journeys/{j2}/stay-options/{option_id}/select")
    if selected.status_code != 200:
        LOG.append("BLOCKED at stay select: %s" % _mask(selected.text[:300]))
        return _finish()
    plan_id = selected.json().get("plan_version_id")
    LOG.append("ARM2 JOURNEY_STATUS=%s plan_version_id=%s"
               % (selected.json().get("journey_status"), plan_id))

    from app.db.models import Activity, Journey, Place, PlanVersion
    from app.db.session import SessionLocal
    from app.services import plan_authority_blocker

    with SessionLocal() as session:
        rows = session.query(Activity).filter(
            Activity.plan_version_id == plan_id).order_by(Activity.sequence_no).all()
        order = [row.id for row in rows]
    LOG.append("ARM2 ACTIVITIES ON THE PLAN %d" % len(order))
    if len(order) < 2:
        LOG.append("BLOCKED: the accept payload needs at least two activities")
        return _finish()

    swapped = list(order)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    assert sorted(swapped) == sorted(order), "swap must not change the set"
    _step("arm2: accept with a swapped order")
    resp2 = _call(client, "post", f"/api/v1/journeys/{j2}/trip-studio/accept",
                  json={"activity_ids": swapped})
    LOG.append("ARM2 ACCEPT http_status=%s body=%s"
               % (resp2.status_code, _mask(resp2.text[:400])))

    # controls: ask each door directly, in this process, about the same rows
    control = {}
    _step("control: shared blocker asked directly")
    with SessionLocal() as session:
        plan = session.get(PlanVersion, plan_id)
        journey = session.get(Journey, j2)
        acts = session.query(Activity).filter(
            Activity.plan_version_id == plan_id).order_by(Activity.sequence_no).all()
        used = [str(a.place_id or "") for a in acts if a.place_id]
        places = {p.id: p for p in session.query(Place).filter(
            Place.city_code == journey.city_code).all()}
        before = len(CALLS)
        answer = plan_authority_blocker(plan, places, used_place_ids=used)
        control["shared_seen"] = len(CALLS) > before
        control["shared_answer"] = answer if isinstance(answer, str) else "PASSED"
        control["used_place_ids"] = len(used)

    _step("control: accept's own gate asked directly")
    from app.main import _trip_studio_authoritative_gate
    with SessionLocal() as session:
        plan = session.get(PlanVersion, plan_id)
        journey = session.get(Journey, j2)
        acts = list(session.query(Activity).filter(
            Activity.plan_version_id == plan_id).order_by(Activity.sequence_no).all())
        before = len(CALLS)
        evidence = json.loads(plan.mobility_evidence_json or "{}")
        gate = _trip_studio_authoritative_gate(session, journey, plan, acts, acts, evidence)
        control["own_seen"] = len(CALLS) > before
        failures = list(gate.get("failures") or [])
        control["own_answer"] = "PASSED" if not failures else ",".join(failures)[:220]
        control["own_mentions_place_facts"] = any(
            word in item for item in failures for word in ("OPENING", "PLACE_CLOSED", "COST_UNRESOLVED"))
        control["plan_status"] = plan.status
        control["journey_status"] = journey.status

    return _finish(control)


def _finish(control=None) -> int:
    sys.settrace(None)
    threading.settrace(None)
    control = control or {}
    by_which = {}
    for row in CALLS:
        by_which.setdefault(row["which"], []).append(row)
    lines = [
        "ACCEPT DOOR VERSUS THE SHARED AUTHORITY BLOCKER bw285",
        "DATABASE %s (temporary, produced only through the product's own POST routes)"
        % os.environ["CITYNEXUS_DATABASE_URL"],
        "GATE_ANSWERS_RECORDING %d rows (this is the denominator: refusals alone are not)"
        % len(CALLS),
    ]
    for which, rows in sorted(by_which.items()):
        refused = [r for r in rows if r["verdict"] in ("REFUSED", "FAILED")]
        lines.append("  %-26s asked=%d refused=%d" % (which, len(rows), len(refused)))
    lines.append("EVERY ANSWER BY STEP")
    for row in CALLS:
        lines.append("  %-34s %-26s line=%-6s used=%-3d content=%-3d %-8s %s"
                     % (row["step"], row["which"], row["line"], row["used_ids"],
                        row["content_places"], row["verdict"], _mask(row["detail"])[:120]))
    lines.append("STEPS")
    lines.extend("  %s" % entry for entry in LOG)
    lines.append("CONTROLS")
    for key in sorted(control):
        lines.append("  %s = %s" % (key, _mask(control[key])))
    asked_on_accept = [r for r in CALLS if r["step"].startswith("arm2: accept")
                        and r["which"] == "shared authority blocker"]
    lines.append("SHARED_BLOCKER_ASKED_DURING_ACCEPT %s (%d times)"
                 % ("YES" if asked_on_accept else "NO", len(asked_on_accept)))
    lines.append("SHARED_BLOCKER_REFUSES_THE_SAME_PLAN %s (answer=%s)"
                 % ("YES" if str(control.get("shared_answer", "")).startswith("UNRESOLVED")
                    or control.get("shared_answer") == "REFUSED" else "NO",
                    control.get("shared_answer")))
    if control and not (control.get("shared_seen") and control.get("own_seen")):
        print("ABORT a control call was not seen by the trace; the zeros above would be meaningless")
        verdict_rc = 9
    else:
        verdict_rc = 0
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return verdict_rc


if __name__ == "__main__":
    sys.exit(main())
