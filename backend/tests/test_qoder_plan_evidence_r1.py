"""Freezing a hand-built candidate's own legs, so a real traveller round can actually be judged.

The door under test is one column-pair wide: it reads a plan version's own `activities` rows, asks the
capture domain the shipped generator already asks, and writes `mobility_snapshot_id` plus
`mobility_evidence_json`. Everything policed here is the temptation to make that step mean more than it
does -- to take minutes from the caller, to call the fixture's blanket constant a measurement, to overwrite
evidence under a round that is already answering, or to paper over a row that carries one of the two
columns alone.

The judgement cells do not restate the gate: they run the shipped functions (`validate_plan_feasibility`,
`capture_runtime_mobility_snapshot`, `app.services._snapshot_for_plan`) inside the test and compare, so a
door that disagreed with the domain it borrows would go red here rather than in a comment.

Profile pinned by `_offline_capture`: no Valhalla url and no Amap seam, which is what this machine is. The
arm that would reach a network is refused at the door level instead (cell on a provider that refuses a
leg), with the domain's own error type injected, so no test here spends a live call.
"""

from __future__ import annotations

import ast
import json
import re
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import (
    collective_consent,
    departure_read,
    plan_delta,
    plan_evidence,
    plan_from_slots,
    plan_submission,
    traveler_principal,
)
from app.core.config import settings
from app.db.models import (
    Activity,
    AuditLog,
    Base,
    IdempotencyKey,
    Journey,
    JourneyMember,
    Place,
    PlanVersion,
    ReplanProposal,
    Traveler,
)
from app.db.session import get_session
from app.integrations.mobility.runtime import capture_runtime_mobility_snapshot
from app.integrations.mobility.snapshot_capture import MobilitySnapshotCaptureError
from app.replanning.provider_snapshots import (
    EXPLICIT_FROZEN_FIXTURE,
    HARD_FEASIBLE_QUALITIES,
    SYNTHETIC_DEFAULT,
)
from app.services import validate_plan_feasibility

SECRET = uuid.uuid4().hex + uuid.uuid4().hex  # generated, never printed, never committed
CITY = "350825"
HOURS = {"open": "09:00", "close": "17:00"}
FREEZE = "/api/v1/journeys/{journey_id}/plans/{plan_version_id}/mobility-freeze"
SUBMIT = "/api/v1/journeys/{journey_id}/plans/{plan_version_id}/submission"


@pytest.fixture(autouse=True)
def _signing_secret(monkeypatch):
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))


@pytest.fixture(autouse=True)
def _offline_capture(monkeypatch):
    """Pin the profile this file measures: the server's own deterministic fixture provider.

    A machine that happens to export a live Valhalla url or an Amap key must not turn these cells into
    live-provider tests, and the pin has to be visible: `test_the_frozen_legs_carry_the_provider_this_run_configured`
    reads the provider word back off the answer, so a pin that did not land shows as red, not as silence.
    """
    from app.integrations.mobility import runtime as mobility_runtime

    monkeypatch.setattr(mobility_runtime, "settings", replace(settings, live_valhalla_url=None))
    monkeypatch.setattr(mobility_runtime, "routes_via_amap", lambda city_code: False)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _then(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def _traveler(session, key: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Traveler(id=ident, display_name=key, email=None, locale="zh-CN",
                         timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
    return ident


def _place(session, *, name: str, point: tuple[float, float] | None) -> str:
    ident = str(uuid.uuid4())
    session.add(Place(id=ident, provider_key="amap", external_id="x-" + ident[:8],
                      city_code=CITY, name=name, category="SIGHTSEE",
                      latitude=None if point is None else point[0],
                      longitude=None if point is None else point[1],
                      opening_hours_json=json.dumps(HOURS), tags_json="[]",
                      metadata_json="{}", updated_at=_now()))
    return ident


def _plan(session, journey_id: str, *, number: int, status: str) -> str:
    ident = str(uuid.uuid4())
    session.add(PlanVersion(id=ident, journey_id=journey_id, version_no=number,
                            planning_mode="balanced", status=status, source="MANUAL",
                            total_cost_minor=6000, currency="CNY",
                            estimated_duration_min=120, created_at=_now()))
    return ident


def _activity(session, plan_id: str, sequence_no: int, place_id: str | None, *,
              start: int, cost: int = 3000, length: int = 45, locked: bool = False) -> str:
    ident = str(uuid.uuid4())
    session.add(Activity(id=ident, plan_version_id=plan_id, sequence_no=sequence_no,
                         activity_type="SIGHTSEE", title="slot", place_id=place_id,
                         city_service_id=None, start_at=_then(start), end_at=_then(start + length),
                         travel_from_prev_min=10, estimated_cost_minor=cost, currency="CNY",
                         status="PLANNED", locked=locked, metadata_json="{}",
                         created_at=_now(), updated_at=_now()))
    return ident


@pytest.fixture()
def seeded():
    """One journey with an ACTIVE base and four CANDIDATEs that differ only in what they hold."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ids: dict[str, str] = {}
    with factory() as session:
        ids["owner"] = _traveler(session, "组织者")
        ids["stranger"] = _traveler(session, "陌生人")
        ids["journey"] = str(uuid.uuid4())
        ids["other_journey"] = str(uuid.uuid4())
        ids["base"] = _plan(session, ids["journey"], number=1, status="ACTIVE")
        ids["candidate"] = _plan(session, ids["journey"], number=2, status="CANDIDATE")
        ids["unfrozen"] = _plan(session, ids["journey"], number=3, status="CANDIDATE")
        ids["twice"] = _plan(session, ids["journey"], number=4, status="CANDIDATE")
        ids["blind"] = _plan(session, ids["journey"], number=5, status="CANDIDATE")
        ids["loop"] = _plan(session, ids["journey"], number=6, status="CANDIDATE")
        ids["foreign"] = _plan(session, ids["other_journey"], number=1, status="CANDIDATE")
        session.add(Journey(id=ids["journey"], traveler_id=ids["owner"], title="连城",
                            city_code=CITY, timezone="Asia/Shanghai", start_at=_then(30),
                            end_at=_then(60 * 48), budget_currency="CNY",
                            budget_amount_minor=500_00, status="PLANNED",
                            active_plan_version_id=ids["base"], created_at=_now(),
                            updated_at=_now()))
        session.add(Journey(id=ids["other_journey"], traveler_id=ids["stranger"], title="厦门",
                            city_code="350200", timezone="Asia/Shanghai", start_at=_then(30),
                            end_at=_then(60 * 48), budget_currency="CNY",
                            budget_amount_minor=500_00, status="PLANNED", created_at=_now(),
                            updated_at=_now()))
        session.add(JourneyMember(id=str(uuid.uuid4()), journey_id=ids["journey"],
                                  traveler_id=ids["owner"], role="OWNER", invited_by="self",
                                  created_at=_now(), updated_at=_now(), joined_at=_now(),
                                  expires_at=None, removed_at=None))
        ids["a"] = _place(session, name="冠豸山", point=(25.7, 116.75))
        ids["b"] = _place(session, name="天一塔", point=(25.71, 116.76))
        ids["c"] = _place(session, name="龙王滩", point=(25.72, 116.77))
        ids["blind_place"] = _place(session, name="只有名字的店", point=None)
        _activity(session, ids["base"], 1, ids["a"], start=60, locked=True)
        _activity(session, ids["base"], 2, ids["b"], start=150)
        for plan in ("candidate", "unfrozen", "twice"):
            _activity(session, ids[plan], 1, ids["a"], start=60)
            _activity(session, ids[plan], 2, ids["b"], start=150)
            _activity(session, ids[plan], 3, ids["c"], start=240)
        _activity(session, ids["blind"], 1, ids["blind_place"], start=60)
        _activity(session, ids["blind"], 2, ids["b"], start=150)
        _activity(session, ids["loop"], 1, ids["a"], start=60)
        _activity(session, ids["loop"], 2, ids["a"], start=150)
        _activity(session, ids["foreign"], 1, ids["b"], start=60)
        session.commit()
    return SimpleNamespace(engine=engine, factory=factory, ids=ids)


def _app():
    from app import main as main_module

    app = FastAPI()
    for route in (*plan_evidence.router.routes, *plan_submission.router.routes,
                  *plan_delta.router.routes, *collective_consent.router.routes,
                  *plan_from_slots.router.routes):
        app.add_api_route(route.path, route.endpoint, methods=sorted(route.methods),
                          name=route.name, status_code=route.status_code)
    app.add_exception_handler(StarletteHTTPException, main_module.http_error)
    return app


def _client(seeded, app=None):
    app = app or _app()

    def override_session():
        with seeded.factory() as inner:
            yield inner

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _header(traveler_id: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(traveler_id)}


def _freeze(seeded, plan_id: str, *, key="freeze-1", body=None, traveler_id=None):
    client = _client(seeded)
    return client.post(FREEZE.format(journey_id=seeded.ids["journey"], plan_version_id=plan_id),
                       json={} if body is None else body,
                       headers={"Idempotency-Key": key,
                                **_header(traveler_id or seeded.ids["owner"])})


def _submit(seeded, plan_id: str, *, key="submit-1"):
    return _client(seeded).post(SUBMIT.format(journey_id=seeded.ids["journey"],
                                              plan_version_id=plan_id),
                                json={}, headers={"Idempotency-Key": key,
                                                  **_header(seeded.ids["owner"])})


def _plan_row(seeded, plan_id: str) -> PlanVersion:
    with seeded.factory() as session:
        return session.get(PlanVersion, plan_id)


def _count(seeded, model) -> int:
    with seeded.factory() as session:
        return len(session.scalars(select(model)).all())


def test_freezing_writes_the_two_columns_the_gate_reads_and_nothing_else(seeded):
    ids = seeded.ids
    answer = _freeze(seeded, ids["candidate"])
    assert answer.status_code == 200, answer.text
    body = answer.json()
    row = _plan_row(seeded, ids["candidate"])
    evidence = json.loads(row.mobility_evidence_json)
    assert row.mobility_snapshot_id == body["mobility_snapshot_id"], row.mobility_snapshot_id
    assert row.mobility_snapshot_id == evidence["snapshot_id"], "the pair the gate compares"
    assert row.status == "CANDIDATE", "this door writes evidence, not a status"
    assert body["status"] == "CANDIDATE" and body["replaces_snapshot_id"] is None, body
    with seeded.factory() as session:
        journey = session.get(Journey, ids["journey"])
        assert journey.active_plan_version_id == ids["base"], "the shared plan did not move"
    assert _count(seeded, ReplanProposal) == 0, "freezing opened no round"
    audits = []
    with seeded.factory() as session:
        audits = session.scalars(select(AuditLog).where(
            AuditLog.action == plan_evidence.FREEZE_ACTION)).all()
    assert len(audits) == 1, audits
    assert json.loads(audits[0].after_json)["legs"] == body["counts"]["legs_frozen"], audits[0].after_json


def test_the_frozen_legs_are_the_ones_this_plan_s_own_slots_imply(seeded):
    """The pairs come from `activities`, not from the caller: derived here and compared."""
    ids = seeded.ids
    body = _freeze(seeded, ids["candidate"]).json()
    with seeded.factory() as session:
        keys = [str(row.place_id) for row in session.scalars(
            select(Activity).where(Activity.plan_version_id == ids["candidate"])
            .order_by(Activity.sequence_no)).all()]
    expected = sorted({(origin, destination) for origin in keys for destination in keys
                       if origin != destination})
    stored = json.loads(_plan_row(seeded, ids["candidate"]).mobility_evidence_json)
    frozen = sorted((str(item["origin_key"]), str(item["destination_key"]))
                    for item in stored["facts"])
    assert frozen == expected, (frozen, expected)
    assert body["counts"] == {"slots": len(keys), "distinct_places": len(set(keys)),
                              "legs_requested": len(expected), "legs_frozen": len(expected),
                              "hard_eligible_legs": 0, "fallback_legs": 0,
                              "slots_without_a_location_row": 0,
                              "same_place_consecutive_transitions": 0}, body["counts"]


def test_the_same_capture_the_generator_runs_produces_the_same_evidence_shape(seeded):
    """Re-run the domain the door borrows and compare its own answer, field by field."""
    ids = seeded.ids
    body = _freeze(seeded, ids["candidate"]).json()
    with seeded.factory() as session:
        journey = session.get(Journey, ids["journey"])
        keys = sorted({str(row.place_id) for row in session.scalars(
            select(Activity).where(Activity.plan_version_id == ids["candidate"])).all()})
        pairs = [(origin, destination) for origin in keys for destination in keys
                 if origin != destination]
        recomputed = capture_runtime_mobility_snapshot(
            session, journey, pairs, operation_key="recomputed-in-test").snapshot
    stored = json.loads(_plan_row(seeded, ids["candidate"]).mobility_evidence_json)
    assert sorted(stored) == sorted(recomputed.to_evidence()), (sorted(stored),
                                                                sorted(recomputed.to_evidence()))
    assert stored["operation_key"] == "plan.candidate_mobility_freeze:" + ids["candidate"], stored
    assert body["counts"]["legs_frozen"] == len(stored["facts"]) == len(recomputed.facts), body
    assert body["source_provider"] == recomputed.source_provider_key, body
    assert [(item["origin_key"], item["destination_key"], item["minutes"], item["provider"],
             item["fact_quality"]) for item in stored["facts"]] == [
        (item["origin_key"], item["destination_key"], item["minutes"], item["provider"],
         item["fact_quality"]) for item in recomputed.to_evidence()["facts"]
    ], "the door may not adjust a leg it borrowed"


def test_the_frozen_legs_carry_the_provider_this_run_configured(seeded):
    body = _freeze(seeded, seeded.ids["candidate"]).json()
    assert body["source_provider"] == "mock-mobility", body["source_provider"]
    assert body["provider_capabilities"] == {}, "the offline arm fills no capabilities, and says so"
    assert body["degraded"] is False, body["degraded"]


def test_a_constant_leg_is_counted_apart_from_a_measured_one(seeded):
    """The fixture's blanket default is not a measurement, and the answer cannot make it look like one."""
    ids = seeded.ids
    body = _freeze(seeded, ids["candidate"]).json()
    stored = json.loads(_plan_row(seeded, ids["candidate"]).mobility_evidence_json)
    words = [str(item["fact_quality"]) for item in stored["facts"]]
    assert set(words) == {SYNTHETIC_DEFAULT}, words
    assert body["fact_qualities"] == {SYNTHETIC_DEFAULT: len(words)}, body["fact_qualities"]
    assert body["counts"]["hard_eligible_legs"] == 0, body["counts"]
    assert SYNTHETIC_DEFAULT not in HARD_FEASIBLE_QUALITIES, "the word that decides this is the domain's"
    assert EXPLICIT_FROZEN_FIXTURE in HARD_FEASIBLE_QUALITIES


def test_a_frozen_candidate_reaches_a_verdict_and_an_unfrozen_one_does_not(seeded):
    """The inch this door exists for, measured as an A/B over two candidates in one journey."""
    ids = seeded.ids
    before = _submit(seeded, ids["unfrozen"], key="submit-unfrozen").json()
    assert before["gate"]["judged"] is False, before["gate"]
    assert before["evidence_gap"] is True, before["evidence_gap"]
    assert before["gate"]["refusal_code"] == "STALE_RECOMPOSE_REQUIRED", before["gate"]

    assert _freeze(seeded, ids["candidate"]).status_code == 200
    after = _submit(seeded, ids["candidate"], key="submit-frozen").json()
    assert after["gate"]["judged"] is True, after["gate"]
    assert after["evidence_gap"] is False, after["evidence_gap"]
    assert after["gate"]["refusal_code"] is None, after["gate"]
    with seeded.factory() as session:
        journey = session.get(Journey, ids["journey"])
        candidate = session.get(PlanVersion, ids["candidate"])
        gate = validate_plan_feasibility(session, journey, candidate)
    assert after["gate"]["passed"] is bool(gate.passed), (after["gate"], gate.failures)
    assert after["hard_constraints_passed"] is bool(gate.passed)


def test_the_door_never_takes_a_minute_from_the_caller(seeded):
    ids = seeded.ids
    refused = _freeze(seeded, ids["candidate"], body={"minutes": 12, "legs": [["a", "b"]]})
    assert refused.status_code == 422, refused.text
    detail = refused.json()["error"]
    assert detail["reason_code"] == plan_evidence.REASON_BODY, detail
    assert detail["details"]["received_fields"] == ["legs", "minutes"], detail["details"]
    assert detail["details"]["accepted_fields"] == [], detail["details"]
    row = _plan_row(seeded, ids["candidate"])
    assert row.mobility_snapshot_id is None and row.mobility_evidence_json is None


def test_a_plan_that_visits_one_place_twice_names_the_step_nothing_can_price(seeded):
    """Found by this door's own chain: the capture domain freezes no self-pair, so the gate cannot price it.

    The door does not invent a zero-minute measurement to make the plan pass, and it does not stay silent
    about a step it knows the gate will refuse. Which of the two shapes -- a named identity leg in the
    mobility domain, or a refusal at this door -- is the right fix belongs to that domain's owner, so this
    cell pins the disclosure and the shipped verdict, not a cure.
    """
    ids = seeded.ids
    answer = _freeze(seeded, ids["loop"]).json()
    assert answer["counts"]["same_place_consecutive_transitions"] == 1, answer["counts"]
    assert answer["same_place_consecutive_transitions"] == [
        {"from_sequence_no": 1, "to_sequence_no": 2, "place_id": ids["a"]}], answer
    assert answer["counts"]["distinct_places"] == 1 and answer["counts"]["legs_frozen"] == 0, (
        answer["counts"])
    assert any("zero-minute self leg" in line for line in answer["next_actions"]), (
        answer["next_actions"])
    verdict = _submit(seeded, ids["loop"], key="submit-loop").json()
    assert verdict["gate"]["judged"] is True, verdict["gate"]
    assert verdict["gate"]["passed"] is False, verdict["gate"]
    assert any(code.startswith("MOBILITY_DATA_UNAVAILABLE")
               for code in verdict["gate"]["failures"]), verdict["gate"]["failures"]
    stored = json.loads(_plan_row(seeded, ids["loop"]).mobility_evidence_json)
    assert stored["facts"] == [], "nothing was fabricated to fill the missing step"


def test_a_slot_whose_place_carries_no_point_is_named_and_nothing_is_written(seeded):
    ids = seeded.ids
    refused = _freeze(seeded, ids["blind"])
    assert refused.status_code == 409, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == plan_evidence.REASON_NO_POINT, error
    named = error["details"]["slots_without_coordinate"]
    assert named == [{"sequence_no": 1, "place_id": ids["blind_place"]}], named
    row = _plan_row(seeded, ids["blind"])
    assert row.mobility_snapshot_id is None and row.mobility_evidence_json is None, "half-written"
    assert _count(seeded, IdempotencyKey) == 0, "a refusal stores no receipt"


def test_a_provider_that_refuses_a_leg_leaves_the_row_exactly_as_it_was(seeded, monkeypatch):
    ids = seeded.ids
    captured = {"n": 0}
    original = plan_evidence.capture_runtime_mobility_snapshot

    def refusing(session, journey, pairs, **kwargs):
        captured["n"] += 1
        raise MobilitySnapshotCaptureError("mobility fact unavailable for x|y: TimeoutError")

    monkeypatch.setattr(plan_evidence, "capture_runtime_mobility_snapshot", refusing)
    refused = _freeze(seeded, ids["candidate"])
    assert refused.status_code == 503, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == plan_evidence.REASON_PROVIDER, error
    assert error["details"]["legs_requested"] == 6, error["details"]
    assert "TimeoutError" in error["details"]["detail"], error["details"]
    assert captured["n"] == 1, "the arm that refuses must be the arm that was asked"
    assert plan_evidence.capture_runtime_mobility_snapshot is refusing
    monkeypatch.setattr(plan_evidence, "capture_runtime_mobility_snapshot", original)
    row = _plan_row(seeded, ids["candidate"])
    assert row.mobility_snapshot_id is None and row.mobility_evidence_json is None
    assert _count(seeded, AuditLog) == 0, "a refused capture writes no audit either"


def test_the_same_key_replays_even_after_the_candidate_has_been_submitted(seeded):
    """The receipt is checked before the state guards: a retry must not be refused by its own write."""
    ids = seeded.ids
    first = _freeze(seeded, ids["candidate"], key="freeze-retry")
    assert first.status_code == 200, first.text
    assert _submit(seeded, ids["candidate"]).status_code == 201
    again = _freeze(seeded, ids["candidate"], key="freeze-retry")
    assert again.status_code == 200, again.text
    body = again.json()
    assert body["idempotency_replay"] is True, body
    assert body["mobility_snapshot_id"] == first.json()["mobility_snapshot_id"], body
    with seeded.factory() as session:
        freezes = session.scalars(select(AuditLog).where(
            AuditLog.action == plan_evidence.FREEZE_ACTION)).all()
    assert len(freezes) == 1, "the replay captured nothing a second time"


def test_a_new_key_under_an_open_round_is_refused_by_name(seeded):
    ids = seeded.ids
    assert _freeze(seeded, ids["candidate"]).status_code == 200
    assert _submit(seeded, ids["candidate"]).status_code == 201
    refused = _freeze(seeded, ids["candidate"], key="freeze-second")
    assert refused.status_code == 409, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == plan_evidence.REASON_ROUND_IN_FLIGHT, error
    proposals = error["details"]["proposal_ids"]
    assert len(proposals) == 1 and error["details"]["proposal_statuses"] == ["PRESENTED"], error["details"]
    with seeded.factory() as session:
        row = session.get(ReplanProposal, proposals[0])
    assert row.proposed_plan_version_id == ids["candidate"], vars(row)


def test_a_candidate_with_no_round_may_be_frozen_again_and_says_what_it_replaced(seeded):
    ids = seeded.ids
    first = _freeze(seeded, ids["twice"], key="freeze-1").json()
    assert first["replaces_snapshot_id"] is None, first
    second = _freeze(seeded, ids["twice"], key="freeze-2").json()
    assert second["replaces_snapshot_id"] == first["mobility_snapshot_id"], second
    assert second["mobility_snapshot_id"] != first["mobility_snapshot_id"], "a new capture, a new id"
    assert _count(seeded, AuditLog) == 2, "both writes are on the record"
    with seeded.factory() as session:
        before = session.scalars(select(AuditLog).where(
            AuditLog.action == plan_evidence.FREEZE_ACTION).order_by(AuditLog.created_at)).all()
    assert json.loads(before[1].before_json)["mobility_snapshot_id"] == (
        first["mobility_snapshot_id"]), before[1].before_json


def test_one_of_the_two_columns_alone_is_named_not_repaired(seeded):
    ids = seeded.ids
    with seeded.factory() as session:
        row = session.get(PlanVersion, ids["unfrozen"])
        row.mobility_snapshot_id = "a-column-pair-this-door-did-not-write"
        session.commit()
    refused = _freeze(seeded, ids["unfrozen"])
    assert refused.status_code == 409, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == plan_evidence.REASON_HALF_FROZEN, error
    assert error["details"]["mobility_snapshot_id_present"] is True, error["details"]
    assert error["details"]["mobility_evidence_json_present"] is False, error["details"]
    stored = _plan_row(seeded, ids["unfrozen"])
    assert stored.mobility_snapshot_id == "a-column-pair-this-door-did-not-write", "left as found"
    assert stored.mobility_evidence_json is None


def test_who_may_not_ask_for_this(seeded):
    ids = seeded.ids
    client = _client(seeded)
    anonymous = client.post(FREEZE.format(journey_id=ids["journey"], plan_version_id=ids["candidate"]),
                            json={}, headers={"Idempotency-Key": "k"})
    assert anonymous.status_code == 401, anonymous.text
    outsider = client.post(FREEZE.format(journey_id=ids["journey"], plan_version_id=ids["candidate"]),
                           json={}, headers={"Idempotency-Key": "k", **_header(ids["stranger"])})
    assert outsider.status_code == 403, outsider.text
    assert outsider.json()["error"]["reason_code"] == departure_read.REASON_MEMBER_REQUIRED
    no_key = client.post(FREEZE.format(journey_id=ids["journey"], plan_version_id=ids["candidate"]),
                         json={}, headers=_header(ids["owner"]))
    assert no_key.status_code == 422, no_key.text
    assert no_key.json()["error"]["reason_code"] == plan_evidence.REASON_KEY_REQUIRED
    active = _freeze(seeded, ids["base"])
    assert active.status_code == 409, active.text
    assert active.json()["error"]["reason_code"] == plan_evidence.REASON_NOT_CANDIDATE
    foreign = _freeze(seeded, ids["foreign"])
    assert foreign.status_code == 404, foreign.text
    assert foreign.json()["error"]["reason_code"] == "PLAN_NOT_IN_JOURNEY"


def test_the_same_key_over_another_candidate_is_a_conflict(seeded):
    ids = seeded.ids
    assert _freeze(seeded, ids["candidate"], key="shared-key").status_code == 200
    refused = _freeze(seeded, ids["twice"], key="shared-key")
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["reason_code"] == plan_evidence.REASON_KEY_CONFLICT
    assert _plan_row(seeded, ids["twice"]).mobility_snapshot_id is None, "the conflict wrote nothing"


def test_the_answer_says_which_store_it_wrote_and_which_door_reads_it(seeded):
    body = _freeze(seeded, seeded.ids["candidate"]).json()
    assert body["read_from"] == {
        "capture": "app.integrations.mobility.runtime.capture_runtime_mobility_snapshot",
        "columns": "app.db.models.PlanVersion.mobility_snapshot_id",
        "consumed_by": "app.services._snapshot_for_plan",
    }, body["read_from"]
    assert body["evidence_columns"] == ["mobility_snapshot_id", "mobility_evidence_json"]
    assert body["expires_at"] is None, "neither shipped arm writes an expiry; naming it beats claiming it"
    joined = " ".join(body["next_actions"])
    assert joined.count("/api/v1/") == len(body["next_actions"]), body["next_actions"]
    assert "submission" in joined and "plans/delta" in joined, body["next_actions"]


def test_no_provider_client_is_reachable_from_the_draft_door_it_freezes_for(seeded):
    """The ban that made this second door necessary is still policed, on the other module's tree."""
    tree = ast.parse(Path("app/plan_from_slots.py").read_text(encoding="utf-8"), filename="plan_from_slots")
    modules = {str(node.module) for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not [name for name in modules if "integrations" in name], modules
    assert "app.agent" not in modules, "no agent runtime import"
    this = ast.parse(Path("app/plan_evidence.py").read_text(encoding="utf-8"), filename="plan_evidence")
    reach = {str(node.module) for node in ast.walk(this) if isinstance(node, ast.ImportFrom)}
    assert "app.integrations.mobility.runtime" in reach, sorted(reach)


def test_the_shipped_ddl_already_holds_both_columns_as_nullable_text(seeded):
    """`no migration` is a claim, so it is read off the schema file, not asserted."""
    ddl = Path("db/schema.sql").read_text(encoding="utf-8")
    start = ddl.index("CREATE TABLE IF NOT EXISTS plan_versions")
    body = ddl[start:ddl.index(");", start)]
    for column in ("mobility_snapshot_id", "mobility_evidence_json"):
        line = next(row for row in body.splitlines() if row.strip().startswith(column))
        assert "TEXT" in line, line
        assert "NOT NULL" not in line, line
    assert "ALTER TABLE" not in body, "this door needs no schema change and did not add one"


def test_no_response_description_in_the_contract_is_cut_at_a_comma():
    """An inline `{description: a, b}` flow scalar ends at the first comma: the rest becomes extra keys.

    Fifteen entries in this file were in that shape when this cell went in, and every reason-code list
    they carried was invisible to anything reading the parsed contract -- a generated client included.
    The rule is repo-wide, so the next inline entry with a comma goes red here instead of quietly
    truncating.
    """
    contract = yaml.safe_load(Path("../contracts/openapi.yaml").read_text(encoding="utf-8"))
    allowed = {"description", "content", "headers"}
    broken = []
    for path, item in contract["paths"].items():
        for verb, door in item.items():
            if not isinstance(door, dict) or verb == "parameters":
                continue
            for status, response in (door.get("responses") or {}).items():
                if not isinstance(response, dict):
                    continue
                junk = [key for key in response if key not in allowed and key != "$ref"]
                if junk:
                    broken.append((path, verb, status, junk[0]))
    assert broken == [], f"truncated descriptions: {broken[:5]}"
    named = [
        door["responses"][status]["description"]
        for path, item in contract["paths"].items() if "mobility-freeze" in path
        for verb, door in item.items() if isinstance(door, dict) and verb == "post"
        for status in door["responses"]
    ]
    assert any("FREEZE_PROPOSAL_ALREADY_ASKING" in text for text in named), named
    assert sum("error.reason_code" in text for text in named) >= 5, named


def test_the_contract_promises_exactly_the_keys_this_door_emits(seeded):
    contract = yaml.safe_load(Path("../contracts/openapi.yaml").read_text(encoding="utf-8"))
    path = contract["paths"]["/journeys/{journey_id}/plans/{plan_version_id}/mobility-freeze"]
    door = path["post"]
    assert door["operationId"] == "postJourneyPlanMobilityFreeze", door["operationId"]
    assert door["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PlanCandidateMobilityFreeze"}, door["responses"]["200"]
    schema = contract["components"]["schemas"]["PlanCandidateMobilityFreeze"]

    body = _freeze(seeded, seeded.ids["candidate"]).json()
    replay = _freeze(seeded, seeded.ids["candidate"]).json()
    assert replay["idempotency_replay"] is True, replay
    assert sorted(schema["required"]) == sorted(body), sorted(set(schema["required"]) ^ set(body))
    assert sorted(schema["properties"]) == sorted(set(body) | set(replay)), (
        sorted(set(schema["properties"]) ^ (set(body) | set(replay))))

    keys = [item["name"] for item in door["parameters"]]
    assert keys == ["Idempotency-Key"], keys
    assert door["parameters"][0]["required"] is True, door["parameters"]
    request = door["requestBody"]["content"]["application/json"]["schema"]
    assert request["additionalProperties"] is False, request
    assert "required" not in request or request["required"] == [], request

    promised = set()
    for response in door["responses"].values():
        text = str(response.get("description", ""))
        tail = text.split("error.reason_code")[-1] if "error.reason_code" in text else ""
        promised |= {word for word in re.findall(r"[A-Z][A-Z_0-9]+", tail)}
    mine = {value for name, value in vars(plan_evidence).items()
            if name.startswith("REASON_") and isinstance(value, str)}
    named_elsewhere = {"TRAVELER_CREDENTIALS_MISSING", "JOURNEY_MEMBER_REQUIRED", "PLAN_NOT_IN_JOURNEY"}
    assert mine <= promised, sorted(mine - promised)
    assert promised - mine <= named_elsewhere, sorted(promised - mine - named_elsewhere)
    counts = schema["properties"]["counts"]
    assert sorted(counts["required"]) == sorted(body["counts"]), (
        sorted(set(counts["required"]) ^ set(body["counts"])))
    assert sorted(schema["properties"]["read_from"]["required"]) == sorted(body["read_from"])
