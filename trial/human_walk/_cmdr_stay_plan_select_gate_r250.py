"""bw250: does the v9 stay-materialiser's own Place rows ever meet the selection gate?

Why this exists: section 14.19 found the product writing opening status "NORMALIZED"
through app/operations/v9.py, a provider key that the selection gate does NOT treat as
structural.  That is only a defect if a real route actually reaches the gate with those
rows.  Nobody has measured it, because no test asks the plan-selection door about a plan
that came from /stay-options/{id}/select.

This probe walks the real HTTP routes in order (reset -> create -> offers capture ->
stay-options generate -> stay-options select -> plan select) on an isolated temporary
database, and records which arm of plan_authority_blocker answered, if any.

Disclosed setup: the journey below is created by this probe through the product's own
POST routes; nothing is seeded into a database by hand and no DOM/API stub is used.
Nothing here proves what a traveller sees on a screen.
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
TEMP_DIR = pathlib.Path(tempfile.mkdtemp(prefix="cnx_r250_"))
os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///%s" % (TEMP_DIR / "probe.db").as_posix()
os.environ.setdefault("CITYNEXUS_DEMO_RESET_TOKEN", uuid.uuid4().hex)
# The reset door answers DEMO_MODE_REQUIRED without this, and this probe only ever resets
# the temporary database it declared for itself two lines above.
os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")

from demo_stage import demo_reset_headers  # noqa: E402
import app.main as main_module  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw250-stay-plan-against-select-gate.txt")
LOG = []
TARGET_FILE = os.path.join("app", "services.py")
TARGET_FUNC = "plan_authority_blocker"
CALLS = []


def _trace(frame, event, arg):
    """Count every answer, not only refusals.

    A probe that records only refusals cannot tell "the door was asked and let the plan
    through" apart from "nobody ever asked the door".
    """

    code = frame.f_code
    if code.co_name != TARGET_FUNC or not code.co_filename.endswith(TARGET_FILE):
        return None
    if event != "call":
        return None

    def inner(frame, event, arg):
        if event == "return":
            result = arg[0] if isinstance(arg, tuple) else arg
            CALLS.append({"step": _step_label[0],
                          "line": frame.f_lineno,
                          "content_places": len(frame.f_locals.get("used_content_places") or []),
                          "used_ids": len(frame.f_locals.get("used_unique") or []),
                          "verdict": "REFUSED" if isinstance(result, str) else "PASSED"})
        return inner

    return inner


_step_label = ["(unlabelled)"]


def _step(label):
    _step_label[0] = label


def _call(client, method, url, **kwargs):
    response = getattr(client, method)(url, **kwargs)
    LOG.append("%s %s -> http_status=%s" % (method.upper(), url, response.status_code))
    return response


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = TestClient(main_module.app)

    _step("step:demo/reset")
    reset = _call(client, "post", "/api/v1/demo/reset", headers=demo_reset_headers())
    if reset.status_code != 200:
        LOG.append("BLOCKED at demo reset: %s" % reset.text[:300])
        return _finish(None)
    ids = reset.json()
    _step("step:journey create")
    create = _call(client, "post", "/api/v1/journeys", json={
        "traveler_id": ids["traveler_id"],
        "title": "r250 probe: stay plan against the selection gate",
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
        LOG.append("BLOCKED at journey create: %s" % create.text[:300])
        return _finish(None)
    journey_id = create.json()["id"]

    _step("step:offers capture")
    _call(client, "post", f"/api/v1/journeys/{journey_id}/stays/offers/capture")
    _step("step:stay-options generate")
    generated = _call(client, "post", f"/api/v1/journeys/{journey_id}/stay-options/generate")
    if generated.status_code != 200:
        LOG.append("BLOCKED at stay-options generate: %s" % generated.text[:300])
        return _finish(journey_id)
    options = generated.json()["top_k"]
    if not options:
        LOG.append("BLOCKED: no stay option was produced")
        return _finish(journey_id)

    _step("step:stay-options select")
    selected = _call(client, "post",
                     f"/api/v1/journeys/{journey_id}/stay-options/{options[0]['id']}/select")
    plan_id = None if selected.status_code != 200 else selected.json().get("plan_version_id")
    if plan_id is None:
        LOG.append("BLOCKED at stay select: %s" % selected.text[:300])
        return _finish(journey_id)
    LOG.append("JOURNEY_STATUS_RIGHT_AFTER_STAY_SELECT %s"
               % selected.json().get("journey_status"))

    # Now the door that section 14.19 attributes the fixture reds to.
    _step("step:plan select on the stay-materialised plan")
    gate = _call(client, "post", f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select")
    LOG.append("PLAN_SELECT http_status=%s body=%s" % (gate.status_code, gate.text[:400]))

    # That door answers by plan state first, so the walk keeps going to the traveller's
    # departure door, which asks the same shared authority blocker about the same rows.
    _step("step:departure door on the stay-materialised plan")
    start = _call(client, "post", f"/api/v1/journeys/{journey_id}/start")
    LOG.append("START http_status=%s body=%s" % (start.status_code, start.text[:400]))
    return _finish(journey_id)


def _finish(journey_id) -> int:
    from app.db.models import Activity, Journey, Place, PlanVersion
    from app.db.session import SessionLocal
    from app.services import plan_authority_blocker

    providers = {}
    plan_ids = []
    plan_statuses = {}
    control = {"asked": False, "answer": None, "seen_by_trace": False}
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id) if journey_id else None
        if journey:
            plan_ids = [plan.id for plan in session.query(PlanVersion).filter(
                PlanVersion.journey_id == journey_id).all()]
        for plan_id in plan_ids:
            row = session.get(PlanVersion, plan_id)
            plan_statuses[row.status] = plan_statuses.get(row.status, 0) + 1
            for activity in session.query(Activity).filter(
                Activity.plan_version_id == plan_id
            ).order_by(Activity.sequence_no).all():
                place = session.get(Place, activity.place_id) if activity.place_id else None
                bucket = "<no place row>" if place is None else "%s | opening=%s" % (
                    place.provider_key,
                    json.loads(place.opening_hours_json or "{}").get("status"))
                providers.setdefault(bucket, 0)
                providers[bucket] += 1

        # Positive control for this probe: ask the very same door directly, in this same
        # process, about the very same rows the walk just produced.  If the trace sees this
        # call, a zero above genuinely means "nobody asked the door".
        if journey and plan_ids:
            plan = session.get(PlanVersion, journey.active_plan_version_id
                               or plan_ids[0])
            activities = session.query(Activity).filter(
                Activity.plan_version_id == plan.id).order_by(Activity.sequence_no).all()
            used_ids = [str(activity.place_id or "") for activity in activities
                        if activity.place_id]
            places = {place.id: place for place in session.query(Place).filter(
                Place.city_code == journey.city_code).all()}
            control["asked"] = True
            before = len(CALLS)
            _step("control: ask the shared gate directly")
            answer = plan_authority_blocker(plan, places, used_place_ids=used_ids)
            control["answer"] = answer if isinstance(answer, str) else "PASSED"
            control["seen_by_trace"] = len(CALLS) > before

    sealed = [row for row in CALLS if row["verdict"] == "REFUSED"]
    lines = [
        "STAY-MATERIALIZED PLAN AGAINST THE SELECTION GATE bw250",
        "DATABASE %s (temporary, reached only through the product's own POST routes)"
        % os.environ["CITYNEXUS_DATABASE_URL"],
        "GATE_ANSWERS_RECORDED %d (refused %d, passed %d)"
        % (len(CALLS), len(sealed), len(CALLS) - len(sealed)),
        "PLAN VERSIONS ON THIS JOURNEY %d" % len(plan_ids),
        "PLAN STATUSES %s" % json.dumps(plan_statuses, sort_keys=True, ensure_ascii=False),
        "ACTIVITY PLACE ROWS BY PROVIDER AND OPENING WORD",
    ]
    for key, count in sorted(providers.items()):
        lines.append("  %3d x %s" % (count, key))
    lines.append("EVERY ANSWER BY STEP (this is the denominator, refusals alone are not)")
    for row in CALLS:
        lines.append("  %-46s line=%-4s used_ids=%-3d content_places=%-3d %s"
                     % (row["step"], row["line"], row["used_ids"],
                        row["content_places"], row["verdict"]))
    lines.append("STEPS")
    lines.extend("  %s" % entry for entry in LOG)
    v9 = [key for key in providers if "citynexus-v9-domain" in key]
    blocked = any("BLOCKED" in entry for entry in LOG)
    # A blocked walk must never read as "the gate was asked and said nothing".
    lines.append("MEASURED %s" % ("NO - the walk stopped before the door" if blocked else "YES"))
    lines.append("POSITIVE_CONTROL asked=%s seen_by_trace=%s direct_answer=%s"
                 % (control["asked"], control["seen_by_trace"], control["answer"]))
    lines.append("V9_DOMAIN_ROWS_PRESENT %s" % ("YES" if v9 else "NO"))
    lines.append("V9_DOMAIN_ROWS_REFUSED_BY_THE_GATE %s"
                 % ("YES" if any(row["step"].startswith("step:plan select")
                                 or row["step"].startswith("step:departure door")
                                 for row in sealed) else "NO"))
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    if control["asked"] and not control["seen_by_trace"]:
        print("ABORT the trace never saw the control call, so a zero above would be "
              "a false negative rather than a reading")
        return 9
    return 0


if __name__ == "__main__":
    # threading.settrace arms threads created after this call, which is what the
    # TestClient's worker pool is; sys.settrace covers the calling thread.
    threading.settrace(_trace)
    sys.settrace(_trace)
    try:
        code = main()
    finally:
        sys.settrace(None)
        threading.settrace(None)
    sys.exit(code)
