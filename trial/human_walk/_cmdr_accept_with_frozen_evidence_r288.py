"""bw288: with a frozen evidence set present, does accept land ACTIVE without ever asking the shared door?

bw285 walked the accept route on a plan that had no frozen mobility facts and got 503.  That is only
half the question: the 503 could be the reason nobody ever noticed that the accept path asks only its
own evidence gate.  If a journey DOES have capturable mobility facts, the same path can succeed - and
the shared authority blocker (app/services.py plan_authority_blocker), the one that vetoes plans whose
Places still carry unresolved opening/cost facts, would still never be consulted.

This probe therefore walks the real routes on a city whose OD matrix is complete, all the way to
preview (which freezes the evidence) and accept, and records every answer of the three functions.  It
then asks the shared blocker directly about the plan accept just promoted - a positive control for the
trace and a differential for the reader.

Disclosed setup: journey, offers, stay option, preview and accept are all produced by the product's
own POST routes against a throwaway database this probe declares for itself; the provider used is
whatever this deployment is configured with, and no snapshot row is written by hand.  Nothing here
proves what a traveller sees on a screen.
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
TEMP_DIR = pathlib.Path(tempfile.mkdtemp(prefix="cnx_r288_"))
os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///%s" % (TEMP_DIR / "probe.db").as_posix()
os.environ.setdefault("CITYNEXUS_DEMO_RESET_TOKEN", uuidlib.uuid4().hex)
os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")

CITY = os.getenv("CITYNEXUS_PROBE_CITY", "CN-BEIJING")

from demo_stage import demo_reset_headers  # noqa: E402
import app.main as main_module  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw288-accept-with-frozen-evidence.txt")
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
    if name not in TARGETS or event != "call":
        return None

    def inner(frame, event, arg):
        if event == "return":
            result = arg[0] if isinstance(arg, tuple) else arg
            row = {"step": _step_label[0], "which": TARGETS[name], "line": frame.f_lineno,
                   "verdict": "returned", "detail": "", "used_ids": 0, "content_places": 0,
                   "fact_failure": False}
            if name == "plan_authority_blocker":
                row["verdict"] = "REFUSED" if isinstance(result, str) else "PASSED"
                row["detail"] = result if isinstance(result, str) else ""
                row["used_ids"] = len(frame.f_locals.get("used_unique") or [])
                row["content_places"] = len(frame.f_locals.get("used_content_places") or [])
            elif name == "_trip_studio_authoritative_gate":
                failures = list(result.get("failures") or []) if isinstance(result, dict) else []
                row["verdict"] = "PASSED" if not failures else "FAILED"
                row["detail"] = ",".join(failures)[:220]
                row["used_ids"] = len(frame.f_locals.get("ordered") or [])
                row["fact_failure"] = any(
                    word in item for item in failures
                    for word in ("OPENING", "PLACE_CLOSED", "COST_UNRESOLVED"))
            CALLS.append(row)
        return inner

    return inner


def _step(label):
    _step_label[0] = label


def _mask(text):
    return re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{28}", lambda m: m.group(0)[:8] + "…masked", str(text))


def _call(client, method, url, **kwargs):
    response = getattr(client, method)(url, **kwargs)
    LOG.append("%s %s -> http_status=%s" % (method.upper(), url.split("/api/v1")[-1],
                                            response.status_code))
    return response


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    threading.settrace(_trace)
    sys.settrace(_trace)
    client = TestClient(main_module.app)

    _step("step:journey create")
    ids = _call(client, "post", "/api/v1/demo/reset", headers=demo_reset_headers())
    if ids.status_code != 200:
        LOG.append("BLOCKED at demo reset")
        return _finish({})
    traveler = ids.json()["traveler_id"]
    create = _call(client, "post", "/api/v1/journeys", json={
        "traveler_id": traveler,
        "title": "r288 probe: accept with frozen evidence",
        "city_code": CITY,
        "timezone": "Asia/Shanghai",
        "start_at": "2026-10-09T18:00:00+08:00",
        "end_at": "2026-10-11T15:00:00+08:00",
        "budget": {"amount_minor": 120000, "currency": "CNY"},
        "stay_budget": {"amount_minor": 70000, "currency": "CNY"},
        "party_size": 2,
        "occupancy": {"adults": 2, "rooms": 1},
        "arrival_anchor": {"at": "2026-10-09T18:00:00+08:00", "location": "Beijing South Station"},
        "departure_anchor": {"at": "2026-10-11T15:00:00+08:00", "location": "Beijing Capital Airport"},
    })
    if create.status_code != 201:
        LOG.append("BLOCKED at journey create: %s" % _mask(create.text[:300]))
        return _finish({})
    journey_id = create.json()["id"]

    _step("step:stay offers + options + select")
    _call(client, "post", f"/api/v1/journeys/{journey_id}/stays/offers/capture")
    generated = _call(client, "post", f"/api/v1/journeys/{journey_id}/stay-options/generate")
    if generated.status_code != 200 or not generated.json().get("top_k"):
        LOG.append("BLOCKED at stay-options generate: %s" % _mask(generated.text[:200]))
        return _finish({})
    option_id = generated.json()["top_k"][0]["id"]
    selected = _call(client, "post",
                     f"/api/v1/journeys/{journey_id}/stay-options/{option_id}/select")
    if selected.status_code != 200:
        LOG.append("BLOCKED at stay select: %s" % _mask(selected.text[:300]))
        return _finish({})
    plan_id = selected.json()["plan_version_id"]
    LOG.append("JOURNEY_STATUS_AFTER_STAY_SELECT %s" % selected.json().get("journey_status"))

    from app.db.models import Activity, Journey, Place, PlanVersion
    from app.db.session import SessionLocal
    from app.services import plan_authority_blocker

    with SessionLocal() as session:
        base_order = [row.id for row in session.query(Activity).filter(
            Activity.plan_version_id == plan_id).order_by(Activity.sequence_no).all()]
    LOG.append("ACTIVITIES ON THE PLAN %d" % len(base_order))
    if len(base_order) < 2:
        LOG.append("BLOCKED: accept needs at least two activities")
        return _finish({})
    swapped = list(base_order)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    assert sorted(swapped) == sorted(base_order), "swap must not change the set"

    _step("step:preview (freezes the evidence for this draft order)")
    preview = _call(client, "post", f"/api/v1/journeys/{journey_id}/trip-studio/preview",
                    json={"activity_ids": swapped})
    LOG.append("PREVIEW http_status=%s body=%s"
               % (preview.status_code, _mask(preview.text[:300])))
    preview_id = None
    if preview.status_code == 200:
        payload = preview.json()
        preview_id = payload.get("preview_id")
        LOG.append("PREVIEW can_accept=%s gate_status=%s failures=%s"
                   % (payload.get("can_accept"),
                      (payload.get("deterministic_gate") or {}).get("status"),
                      _mask((payload.get("deterministic_gate") or {}).get("failures"))[:200]))

    _step("step:accept")
    body = {"activity_ids": swapped}
    if preview_id:
        body["preview_id"] = preview_id
    accepted = _call(client, "post", f"/api/v1/journeys/{journey_id}/trip-studio/accept", json=body)
    LOG.append("ACCEPT http_status=%s body=%s"
               % (accepted.status_code, _mask(accepted.text[:420])))
    new_plan_id = None
    if accepted.status_code in (200, 201):
        new_plan_id = (accepted.json().get("plan") or {}).get("id")
        LOG.append("ACCEPT produced plan_version_id=%s status=%s"
                   % (new_plan_id, (accepted.json().get("plan") or {}).get("status")))

    target_id = new_plan_id or plan_id
    control = {"accept_http": accepted.status_code, "city": CITY,
               "preview_http": preview.status_code, "new_plan_id": new_plan_id,
               "plan_asked_about": target_id, "plan_was_produced_by_accept": bool(new_plan_id)}
    _step("control: shared blocker asked directly about the promoted plan")
    with SessionLocal() as session:
        plan = session.get(PlanVersion, target_id)
        journey = session.get(Journey, journey_id)
        acts = list(session.query(Activity).filter(
            Activity.plan_version_id == target_id).order_by(Activity.sequence_no).all())
        used = [str(a.place_id or "") for a in acts if a.place_id]
        places = {p.id: p for p in session.query(Place).filter(
            Place.city_code == journey.city_code).all()}
        before = len(CALLS)
        answer = plan_authority_blocker(plan, places, used_place_ids=used)
        control["shared_seen"] = len(CALLS) > before
        control["shared_answer"] = answer if isinstance(answer, str) else "PASSED"
        control["used_place_ids"] = len(used)
        control["promoted_plan_status"] = plan.status
        control["journey_status"] = journey.status
        control["journey_active_plan_is_promoted"] = (journey.active_plan_version_id == target_id)
        control["provider_keys"] = sorted({p.provider_key for p in places.values()
                                           if p.id in used})[:4]
    return _finish(control)


def _finish(control) -> int:
    sys.settrace(None)
    threading.settrace(None)
    by_which = {}
    for row in CALLS:
        by_which.setdefault(row["which"], []).append(row)
    walk_rows = [row for row in CALLS if not row["step"].startswith("control")]
    shared_on_walk = [row for row in walk_rows if row["which"] == "shared authority blocker"]
    lines = [
        "ACCEPT WITH FROZEN EVIDENCE AGAINST THE SHARED AUTHORITY BLOCKER bw288",
        "DATABASE %s (temporary, produced only through the product's own POST routes)"
        % os.environ["CITYNEXUS_DATABASE_URL"],
        "ANSWERS RECORDED %d rows during the walk (%d refusals) - refusals alone are not the denominator"
        % (len(walk_rows), len([r for r in walk_rows if r["verdict"] in ("REFUSED", "FAILED")])),
    ]
    for which, rows in sorted(by_which.items()):
        lines.append("  %-26s asked=%d (walk=%d)"
                     % (which, len(rows), len([r for r in rows if not r["step"].startswith("control")])))
    lines.append("EVERY ANSWER BY STEP")
    for row in CALLS:
        lines.append("  %-52s %-26s line=%-6s used=%-3d %-8s %s"
                     % (row["step"][:52], row["which"], row["line"], row["used_ids"],
                        row["verdict"], _mask(row["detail"])[:110]))
    lines.append("STEPS")
    lines.extend("  %s" % entry for entry in LOG)
    lines.append("CONTROLS")
    for key in sorted(control):
        lines.append("  %s = %s" % (key, _mask(control.get(key))))
    lines.append("SHARED_BLOCKER_ASKED_DURING_WALK %s (%d times)"
                 % ("YES" if shared_on_walk else "NO", len(shared_on_walk)))
    lines.append("SHARED_BLOCKER_REFUSES_THE_PROMOTED_PLAN %s (answer=%s)"
                 % ("YES" if str(control.get("shared_answer", "")).startswith("UNRESOLVED") else "NO",
                    control.get("shared_answer")))
    promoted_by_accept = bool(control.get("plan_was_produced_by_accept")) and str(
        control.get("promoted_plan_status")) in ("ACTIVE", "SELECTED")
    lines.append("ACCEPT_LANDED_A_NEW_PLAN_IN_A_DEPARTURE_STATE %s (accept produced plan=%s; "
                 "the plan this probe finally asked the shared door about had status=%s, "
                 "journey=%s, is the journey pointer=%s)"
                 % ("YES" if promoted_by_accept else "NO",
                    "yes" if control.get("plan_was_produced_by_accept") else "no",
                    control.get("promoted_plan_status"), control.get("journey_status"),
                    control.get("journey_active_plan_is_promoted")))
    lines.append("ACCEPT_GATE_LOOKED_AT_PLACE_FACTS %s"
                 % ("YES" if any(r["fact_failure"] for r in CALLS) else "NO"))
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    if control and not control.get("shared_seen"):
        print("ABORT the control call was not seen by the trace; the zeros above would be meaningless")
        return 9
    return 0


if __name__ == "__main__":
    sys.exit(main())
