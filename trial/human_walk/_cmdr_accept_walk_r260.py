"""bw260: does the traveller's own "accept this version" key reach the shared authority gate?

Section 14.21 put backend/app/main.py:19038 (the accept implementation writes a new plan
straight to ACTIVE when the journey is already ACTIVE) into the column where this ruler
cannot see the gate in the same function.  Reading the code further, the accept door runs
its own _trip_studio_authoritative_gate, which only checks frozen evidence identity,
integrity, expiry and mobility costs - it says nothing about a Place's opening or price
facts.  Whether a real accept walk ever asks the shared gate has never been measured.

This probe reuses the stay walk from bw250 (which leaves the journey ACTIVE with nine
activities) and then posts the product's own accept route with two of those activities.
Disclosed setup: the journey is built by this probe through the product's POST routes on a
temporary database.  It is not a screen the operator touched, and nothing is seeded by hand.
"""

import io
import json
import os
import pathlib
import sys
import tempfile
import threading
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "tests"))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

if "CITYNEXUS_DATABASE_URL" in os.environ:
    print("ABORT this probe owns its database and refuses an inherited one")
    sys.exit(3)
TEMP_DIR = pathlib.Path(tempfile.mkdtemp(prefix="cnx_r260_"))
os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///%s" % (TEMP_DIR / "probe.db").as_posix()
os.environ.setdefault("CITYNEXUS_DEMO_RESET_TOKEN", uuid.uuid4().hex)
os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")

from demo_stage import demo_reset_headers  # noqa: E402
import app.main as main_module  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw260-accept-walk-against-the-gate.txt")
LOG = []
TARGET_FILE = os.path.join("app", "services.py")
TARGET_FUNC = "plan_authority_blocker"
CALLS = []
_step_label = ["(unlabelled)"]


def _trace(frame, event, arg):
    code = frame.f_code
    if code.co_name != TARGET_FUNC or not code.co_filename.endswith(TARGET_FILE):
        return None
    if event != "call":
        return None

    def inner(frame, event, arg):
        if event == "return":
            result = arg[0] if isinstance(arg, tuple) else arg
            CALLS.append({"step": _step_label[0], "line": frame.f_lineno,
                          "content_places": len(frame.f_locals.get("used_content_places") or []),
                          "verdict": "REFUSED" if isinstance(result, str) else "PASSED"})
        return inner

    return inner


def _step(label):
    _step_label[0] = label


def _call(client, method, url, **kwargs):
    response = getattr(client, method)(url, **kwargs)
    LOG.append("%s %s -> http_status=%s" % (method.upper(), url, response.status_code))
    return response


def _activity_ids(plan_id):
    from app.db.models import Activity
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        return [row.id for row in session.query(Activity).filter(
            Activity.plan_version_id == plan_id
        ).order_by(Activity.sequence_no).all()]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = TestClient(main_module.app)

    _step("step:demo/reset")
    reset = _call(client, "post", "/api/v1/demo/reset", headers=demo_reset_headers())
    if reset.status_code != 200:
        LOG.append("BLOCKED at demo reset: %s" % reset.text[:250])
        return _finish(None)
    ids = reset.json()
    _step("step:journey create")
    create = _call(client, "post", "/api/v1/journeys", json={
        "traveler_id": ids["traveler_id"],
        "title": "r260 probe: accept this version against the shared gate",
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
        LOG.append("BLOCKED at journey create: %s" % create.text[:250])
        return _finish(None)
    journey_id = create.json()["id"]

    _step("step:offers capture")
    _call(client, "post", f"/api/v1/journeys/{journey_id}/stays/offers/capture")
    _step("step:stay-options generate")
    generated = _call(client, "post", f"/api/v1/journeys/{journey_id}/stay-options/generate")
    if generated.status_code != 200 or not generated.json()["top_k"]:
        LOG.append("BLOCKED at stay-options generate: %s" % generated.text[:250])
        return _finish(journey_id)
    option_id = generated.json()["top_k"][0]["id"]

    _step("step:stay-options select")
    selected = _call(client, "post",
                     f"/api/v1/journeys/{journey_id}/stay-options/{option_id}/select")
    if selected.status_code != 200:
        LOG.append("BLOCKED at stay select: %s" % selected.text[:250])
        return _finish(journey_id)
    base_plan_id = selected.json().get("plan_version_id")
    LOG.append("JOURNEY_STATUS_RIGHT_AFTER_STAY_SELECT %s"
               % selected.json().get("journey_status"))

    # The accept door refuses a partial order (TRIP_STUDIO_REQUIRES_FULL_ACTIVE_PLAN_ORDER),
    # so it gets every activity of the active plan.  Any swap creates a leg the frozen matrix
    # may not contain, and that answers 503 before the door is reached - so every adjacent
    # pair is tried until one walk gets far enough to be asked.  This is the shape of a
    # traveller dragging one card in "按天调整行程", tried once per neighbour.
    base_order = _activity_ids(base_plan_id)
    if len(base_order) < 2:
        LOG.append("BLOCKED: the accept route needs at least two activities")
        return _finish(journey_id)

    LOG.append("ACTIVITY_IDS_TAKEN_TO_ACCEPT %d (from plan %s)"
               % (len(base_order), base_plan_id))
    for index in range(1, len(base_order)):
        order = list(base_order)
        order[index - 1], order[index] = order[index], order[index - 1]
        assert sorted(order) == sorted(base_order), "the swap must only reorder, never edit"
        _step("step:trip-studio accept swap %d" % index)
        accept = _call(client, "post", f"/api/v1/journeys/{journey_id}/trip-studio/accept",
                       json={"activity_ids": order})
        LOG.append("ACCEPT_SWAP %d http_status=%s body=%s"
                   % (index, accept.status_code, accept.text[:260]))
        if any(row["step"].startswith("step:trip-studio accept") for row in CALLS):
            LOG.append("STOP_CONDITION the shared gate was asked during swap %d" % index)
            break
        if accept.status_code == 201:
            LOG.append("STOP_CONDITION swap %d produced a plan (http_status=201)" % index)
            break
    new_plan_id = None
    if accept.status_code == 201:
        new_plan_id = (accept.json().get("plan") or {}).get("id") or accept.json().get("plan_id")
        LOG.append("ACCEPT_PLAN_ID %s" % new_plan_id)
        if new_plan_id:
            from app.db.models import PlanVersion
            from app.db.session import SessionLocal
            with SessionLocal() as session:
                row = session.get(PlanVersion, new_plan_id)
                LOG.append("ACCEPT_PLAN_STATUS %s" % (row.status if row else "<not found>"))
    return _finish(journey_id)


def _finish(journey_id) -> int:
    from app.db.models import Activity, Journey, Place, PlanVersion
    from app.db.session import SessionLocal
    from app.services import plan_authority_blocker

    control = {"asked": False, "answer": None, "seen_by_trace": False}
    plan_rows = {}
    opening_words = {}
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id) if journey_id else None
        if journey:
            for plan in session.query(PlanVersion).filter(
                PlanVersion.journey_id == journey_id).all():
                plan_rows[plan.status] = plan_rows.get(plan.status, 0) + 1
            active = session.get(PlanVersion, journey.active_plan_version_id) \
                if journey.active_plan_version_id else None
            if active:
                used_ids = []
                for activity in session.query(Activity).filter(
                    Activity.plan_version_id == active.id
                ).order_by(Activity.sequence_no).all():
                    if not activity.place_id:
                        continue
                    used_ids.append(str(activity.place_id))
                    place = session.get(Place, activity.place_id)
                    if place is not None:
                        word = str(json.loads(place.opening_hours_json or "{}").get("status"))
                        key = "%s | opening=%s" % (place.provider_key, word)
                        opening_words[key] = opening_words.get(key, 0) + 1
                places = {place.id: place for place in session.query(Place).filter(
                    Place.city_code == journey.city_code).all()}
                control["asked"] = True
                before = len(CALLS)
                _step("control: ask the shared gate directly")
                answer = plan_authority_blocker(active, places, used_place_ids=used_ids)
                control["answer"] = answer if isinstance(answer, str) else "PASSED"
                control["seen_by_trace"] = len(CALLS) > before

    refused = [row for row in CALLS if row["verdict"] == "REFUSED"]
    blocked = any("BLOCKED" in entry for entry in LOG)
    lines = [
        "ACCEPT WALK AGAINST THE SHARED AUTHORITY GATE bw260",
        "DATABASE %s (temporary, reached only through the product's own POST routes)"
        % os.environ["CITYNEXUS_DATABASE_URL"],
        "GATE_ANSWERS_RECORDED %d (refused %d, passed %d)"
        % (len(CALLS), len(refused), len(CALLS) - len(refused)),
        "MEASURED %s" % ("NO - the walk stopped before the door" if blocked else "YES"),
        "POSITIVE_CONTROL asked=%s seen_by_trace=%s direct_answer=%s"
        % (control["asked"], control["seen_by_trace"], control["answer"]),
        "PLAN STATUSES ON THIS JOURNEY %s" % json.dumps(plan_rows, sort_keys=True,
                                                        ensure_ascii=False),
        "OPENING WORDS ON THE ACTIVE PLAN %s" % json.dumps(opening_words, sort_keys=False,
                                                           ensure_ascii=False),
        "EVERY ANSWER BY STEP",
    ]
    for row in CALLS:
        lines.append("  %-44s line=%-4s content_places=%-3d %s"
                     % (row["step"], row["line"], row["content_places"], row["verdict"]))
    lines.append("STEPS")
    lines.extend("  %s" % entry for entry in LOG)
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    if control["asked"] and not control["seen_by_trace"]:
        print("ABORT the trace never saw the control call, so a zero here would be "
              "a false negative rather than a reading")
        return 9
    return 0


if __name__ == "__main__":
    threading.settrace(_trace)
    sys.settrace(_trace)
    try:
        code = main()
    finally:
        sys.settrace(None)
        threading.settrace(None)
    sys.exit(code)
