"""Offering a hand-built CANDIDATE to the members, without applying it to anybody.

The V3 order's third item asks for "submit-without-applying candidates". This file is mostly about the
things a write door is tempted to invent and must not: a utility score it computed itself, a hard-
constraint claim it assumed, an event that triggered nothing, a sentence destined for a screen. Every
stored judgement here is re-run independently from the shipped function that owns it, and the difference
this proposal carries is compared against the delta read door's own answer -- one writer per judgement,
proved by running both.

Seeded on `create_all` with the same shapes the delta spec uses; the package DDL's own refusals
(`IdempotencyKey.expires_at`, the `base <> proposed` CHECK) are re-run over the shipped socket in
`_live_submission_1020ee.py`, so nothing in this file relies on the ORM being looser than the schema.
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
from app.replanning.verified_scoring import score_replan_candidate
from app.services import validate_plan_feasibility

SECRET = uuid.uuid4().hex + uuid.uuid4().hex  # generated, never printed, never committed
CITY = "350825"
HOURS = {"open": "09:00", "close": "17:00"}


@pytest.fixture(autouse=True)
def _signing_secret(monkeypatch):
    """The traveller principal verifier refuses to mint tokens with no secret configured (503), so the
    arms sign against one generated here rather than against anything on this machine."""
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _then(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def _traveler(session, key: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Traveler(id=ident, display_name=key, email=None, locale="zh-CN",
                         timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
    return ident


def _place(session, *, name: str, point: tuple[float, float] | None = None) -> str:
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


def _activity(session, plan_id: str, sequence_no: int, place_id: str | None, *, title: str,
              cost: int = 3000, start: int | None = None, length: int = 45, locked: bool = False,
              travel: int = 10, currency: str = "CNY", at: str | None = None) -> str:
    """One slot. `at` pins the start verbatim -- see the mirror candidate in the fixture, where two
    rows are meant to carry the same instant down to the microsecond; `start` asks for one from now."""
    if (start is None) == (at is None):
        raise AssertionError("a slot takes a minute offset or a pinned instant, not both")
    ident = str(uuid.uuid4())
    start_at = _then(int(start)) if at is None else at
    end_at = (datetime.fromisoformat(start_at) + timedelta(minutes=length)).isoformat()
    session.add(Activity(id=ident, plan_version_id=plan_id, sequence_no=sequence_no,
                         activity_type="SIGHTSEE", title=title, place_id=place_id,
                         city_service_id=None, start_at=start_at, end_at=end_at,
                         travel_from_prev_min=travel, estimated_cost_minor=cost, currency=currency,
                         status="PLANNED", locked=locked, metadata_json="{}",
                         created_at=_now(), updated_at=_now()))
    return ident


@pytest.fixture()
def seeded():
    """A journey on an ACTIVE base, plus one CANDIDATE that drops a place and adds another."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ids: dict[str, str] = {}
    with factory() as session:
        ids["owner"] = _traveler(session, "组织者")
        ids["xiaoyu"] = _traveler(session, "小雨")
        ids["stranger"] = _traveler(session, "陌生人")
        ids["journey"] = str(uuid.uuid4())
        ids["other_journey"] = str(uuid.uuid4())
        ids["base"] = _plan(session, ids["journey"], number=1, status="ACTIVE")
        ids["candidate"] = _plan(session, ids["journey"], number=2, status="CANDIDATE")
        ids["active_other"] = _plan(session, ids["journey"], number=3, status="ACTIVE")
        ids["other_candidate"] = _plan(session, ids["journey"], number=4, status="CANDIDATE")
        ids["mirror"] = _plan(session, ids["journey"], number=5, status="CANDIDATE")
        ids["foreign"] = _plan(session, ids["other_journey"], number=1, status="CANDIDATE")
        session.add(Journey(id=ids["journey"], traveler_id=ids["owner"], title="连城",
                            city_code=CITY, timezone="Asia/Shanghai", start_at=_then(60),
                            end_at=_then(60 * 24), budget_currency="CNY",
                            budget_amount_minor=500_00, status="ACTIVE",
                            active_plan_version_id=ids["base"], created_at=_now(),
                            updated_at=_now()))
        session.add(Journey(id=ids["other_journey"], traveler_id=ids["stranger"], title="厦门",
                            city_code="350200", timezone="Asia/Shanghai", start_at=_then(60),
                            end_at=_then(60 * 24), budget_currency="CNY",
                            budget_amount_minor=500_00, status="PLANNED", created_at=_now(),
                            updated_at=_now()))
        session.add(JourneyMember(id=str(uuid.uuid4()), journey_id=ids["journey"],
                                  traveler_id=ids["owner"], role="OWNER", invited_by="self",
                                  created_at=_now(), updated_at=_now(), joined_at=_now(),
                                  expires_at=None, removed_at=None))
        ids["a"] = _place(session, name="冠豸山", point=(25.7, 116.75))
        ids["b"] = _place(session, name="天一塔", point=(25.71, 116.76))
        ids["c"] = _place(session, name="龙王滩", point=(25.72, 116.77))
        #: One clock taken once, so the mirror candidate below carries the base's instants verbatim:
        #: two separate `_then` calls differ by microseconds, and that would make a "same plan"
        #: candidate differ in a way no traveller ever typed.
        at = {1: _then(60), 2: _then(120), 3: _then(180)}
        _activity(session, ids["base"], 1, ids["a"], title="冠豸山", at=at[1], locked=True)
        _activity(session, ids["base"], 2, ids["b"], title="天一塔", at=at[2])
        _activity(session, ids["base"], 3, ids["c"], title="龙王滩", at=at[3])
        # The mirror: the same three places, the same instants, the same money, the same lock. Only the
        # version row is new -- which is exactly what `POST .../plans/from-slots` writes when a
        # traveller presses the plan already in force back at the server.
        _activity(session, ids["mirror"], 1, ids["a"], title="冠豸山", at=at[1], locked=True)
        _activity(session, ids["mirror"], 2, ids["b"], title="天一塔", at=at[2])
        _activity(session, ids["mirror"], 3, ids["c"], title="龙王滩", at=at[3])
        _activity(session, ids["candidate"], 1, ids["a"], title="冠豸山", start=60, locked=True)
        _activity(session, ids["candidate"], 2, ids["c"], title="龙王滩", start=120)
        _activity(session, ids["active_other"], 1, ids["a"], title="冠豸山", start=60)
        _activity(session, ids["foreign"], 1, ids["b"], title="天一塔", start=60)
        session.commit()
    return SimpleNamespace(engine=engine, factory=factory, ids=ids)


def _app(seeded):
    from app import main as main_module

    app = FastAPI()
    for route in (*plan_submission.router.routes, *plan_delta.router.routes,
                  *collective_consent.router.routes, *plan_from_slots.router.routes):
        app.add_api_route(route.path, route.endpoint, methods=sorted(route.methods),
                          name=route.name, status_code=route.status_code)
    app.add_exception_handler(StarletteHTTPException, main_module.http_error)

    def override_session():
        with seeded.factory() as inner:
            yield inner

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _header(traveler_id: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(traveler_id)}


def _submit(client, ids, traveler_id=None, *, plan=None, key="submit-1", body=None,
            header=None):
    return client.post(SUBMIT.format(journey_id=ids["journey"],
                                     plan_version_id=plan or ids["candidate"]),
                       json={} if body is None else body,
                       headers={"Idempotency-Key": key,
                                **_header(traveler_id or ids["owner"])},
                       )


SUBMIT = "/api/v1/journeys/{journey_id}/plans/{plan_version_id}/submission"


def _rows(seeded, model):
    with seeded.factory() as session:
        return list(session.scalars(select(model)).all())


def _proposal(seeded, proposal_id: str):
    with seeded.factory() as session:
        return session.get(ReplanProposal, proposal_id)


def test_a_submitted_candidate_becomes_a_presented_proposal_and_nothing_else_moves(seeded):
    client = _app(seeded)
    ids = seeded.ids
    answer = _submit(client, ids)
    assert answer.status_code == 201, answer.text
    body = answer.json()
    assert body["status"] == plan_submission.STATUS_PRESENTED, body["status"]
    assert body["applied"] is False and body["shared_plan_updated"] is False, body
    assert body["journey_active_plan_version_id"] == ids["base"], body
    stored = _proposal(seeded, body["proposal_id"])
    assert stored.status == "PRESENTED" and stored.base_plan_version_id == ids["base"], vars(stored)
    assert stored.proposed_plan_version_id == ids["candidate"], stored.proposed_plan_version_id
    rows = _rows(seeded, PlanVersion)
    assert {row.id: row.status for row in rows}[ids["candidate"]] == "CANDIDATE", rows
    with seeded.factory() as session:
        assert session.get(Journey, ids["journey"]).active_plan_version_id == ids["base"]


def test_every_stored_judgement_is_the_shipped_function_s_own_answer(seeded):
    """Re-run gate, lock rule and scorer in the test and compare -- the door may not add its own."""
    client = _app(seeded)
    ids = seeded.ids
    body = _submit(client, ids).json()
    with seeded.factory() as session:
        journey = session.get(Journey, ids["journey"])
        base = session.get(PlanVersion, ids["base"])
        candidate = session.get(PlanVersion, ids["candidate"])
        try:
            gate = validate_plan_feasibility(session, journey, candidate)
            refusal = None
        except (ValueError, TypeError) as refused:
            gate, refusal = None, str(refused)
    stored = _proposal(seeded, body["proposal_id"])
    expected_passed = bool(gate.passed) if refusal is None else False
    assert stored.hard_constraints_passed is expected_passed, (
        stored.hard_constraints_passed, expected_passed, refusal)
    assert body["gate"]["passed"] is expected_passed, body["gate"]
    assert body["gate"]["judged"] is (refusal is None), body["gate"]
    assert body["hard_constraints_passed"] is stored.hard_constraints_passed, body
    assert stored.locked_commitments_preserved is True, stored.locked_commitments_preserved
    assert body["locked_slots_dropped"] == [], body["locked_slots_dropped"]

    recomputed = score_replan_candidate(
        base_activity_count=body["delta"]["counts"]["from_slots"],
        moved_count=body["delta"]["counts"]["moved"],
        removed_count=body["delta"]["counts"]["removed"],
        added_count=body["delta"]["counts"]["added"],
        travel_delta_min=_travel_delta(seeded, base.id, candidate.id),
        budget_amount_minor=journey.budget_amount_minor,
        after_envelope=body["envelope"],
        commitments_preserved=True,
    )
    assert stored.utility_score == recomputed.total, (stored.utility_score, recomputed.total)
    assert json.loads(stored.score_breakdown_json) == dict(recomputed.breakdown), stored
    assert 0.0 <= stored.utility_score <= 1.0, stored.utility_score


def test_a_candidate_the_gate_refuses_to_judge_is_stored_as_not_judged_not_passed(seeded):
    """The shipped wall for a hand-built plan, stated rather than smoothed over.

    `validate_plan_feasibility` raises `STALE_RECOMPOSE_REQUIRED` for a version with no frozen mobility
    evidence -- the same sentence the select door and the consent round already hit. The column this
    feeds is 0/1 with no null, so the honest encoding is not-passed **plus** the gate's own code and
    `judged: false`; a screen reading it can say "not judged", and nothing in this door may write the
    word "passed" for it.
    """
    client = _app(seeded)
    body = _submit(client, seeded.ids).json()
    assert body["gate"] == {
        "judged": False, "passed": False, "failures": [],
        "refusal_code": "STALE_RECOMPOSE_REQUIRED",
        "refusal_detail": ("STALE_RECOMPOSE_REQUIRED: PlanVersion frozen mobility evidence is missing "
                           "or inconsistent"),
    }, body["gate"]
    stored = _proposal(seeded, body["proposal_id"])
    assert stored.hard_constraints_passed is False, stored
    explanation = json.loads(stored.explanation_json)
    assert explanation["gate_judged"] is False, explanation
    assert explanation["gate_refusal_code"] == "STALE_RECOMPOSE_REQUIRED", explanation
    assert body["evidence_gap"] is True, body
    # Nothing was frozen, so there is no basis to report -- an absence, and never a zero invented to
    # make the field look answered.
    assert body["evidence_basis"] is None, body


def _travel_delta(seeded, base_id: str, candidate_id: str) -> int:
    with seeded.factory() as session:
        totals = {}
        for label, plan_id in (("base", base_id), ("candidate", candidate_id)):
            totals[label] = sum(row.travel_from_prev_min for row in session.scalars(
                select(Activity).where(Activity.plan_version_id == plan_id)).all())
    return totals["candidate"] - totals["base"]


def test_the_stored_difference_is_the_delta_doors_own_answer_field_by_field(seeded):
    """One writer for the arithmetic: `diff_json` and `GET .../plans/delta` cannot disagree."""
    client = _app(seeded)
    ids = seeded.ids
    proposal_id = _submit(client, ids).json()["proposal_id"]
    delta = client.get(plan_delta.DELTA_PATH.format(journey_id=ids["journey"]),
                       params={"from_plan_version_id": ids["base"],
                               "to_plan_version_id": ids["candidate"]},
                       headers=_header(ids["owner"]))
    assert delta.status_code == 200, delta.text
    stored = json.loads(_proposal(seeded, proposal_id).diff_json)
    for block in ("counts", "sets", "map_delta", "budget_delta", "verified_cost",
                  "duration_delta", "evidence"):
        assert stored[block] == delta.json()[block], block
    assert stored["candidate_family"] == plan_submission.FAMILY, stored["candidate_family"]
    # The two keys the shipped Guardian reads off `diff_json` are this delta's own numbers.
    assert stored["cost_delta_minor"] == delta.json()["budget_delta"]["delta_minor"], stored
    assert stored["end_time_delta_min"] == delta.json()["duration_delta"]["delta_min"], stored
    assert "verified_evidence" not in stored, "no generator evidence is claimed for a hand-built plan"
    assert stored["read_from"] == "app.plan_delta.delta_of", stored["read_from"]


def test_an_unjudged_round_is_pointed_at_the_door_that_can_judge_it(seeded):
    """The round this door opens cannot be judged until the evidence exists, and the answer says so.

    A hand-built candidate is presented with `gate.judged` false -- that is the honest encoding of the
    shipped `STALE_RECOMPOSE_REQUIRED` wall -- and since the freeze door landed there is a door that
    closes the gap, so the pointer names it, with its own path template rather than a recopied string.
    """
    client = _app(seeded)
    ids = seeded.ids
    body = _submit(client, ids).json()
    assert body["evidence_gap"] is True, body
    freeze = plan_evidence.FREEZE_PATH.format(journey_id=ids["journey"],
                                              plan_version_id=ids["candidate"])
    assert body["next_actions"][0] == (
        "close the evidence gap with POST " + freeze +
        ", or this round stays gate.judged false with STALE_RECOMPOSE_REQUIRED"), (
        body["next_actions"][0])
    joined = " ".join(body["next_actions"])
    assert joined.count("/api/v1/") == len(body["next_actions"]), body["next_actions"]
    assert body["gate"]["refusal_code"] in body["next_actions"][0], body["gate"]
    # Run-time half of the pointer ruler: what the answer actually assembled must be pressable.
    from answer_pointers import assert_pointers_are_served
    assert_pointers_are_served(body["next_actions"], expect=3)


def test_the_consent_door_answers_for_a_submitted_proposal(seeded):
    """The two halves name each other: the submission's `consent_path` is the round's own door."""
    client = _app(seeded)
    ids = seeded.ids
    body = _submit(client, ids).json()
    assert body["consent_path"] == collective_consent.CONSENT_PATH.format(
        journey_id=ids["journey"], proposal_id=body["proposal_id"]), body["consent_path"]
    assert any("POST" in line and line.endswith(body["consent_path"])
               for line in body["next_actions"]), body["next_actions"]
    round_answer = client.get(body["consent_path"], headers=_header(ids["owner"]))
    assert round_answer.status_code == 200, round_answer.text
    round_body = round_answer.json()
    assert round_body["proposal_id"] == body["proposal_id"], round_body
    assert collective_consent.REASON_PROPOSAL_NOT_IN_JOURNEY not in str(round_body), round_body


def test_a_dropped_lock_is_reported_as_a_dropped_lock(seeded):
    client = _app(seeded)
    ids = seeded.ids
    with seeded.factory() as session:
        row = session.scalars(select(Activity).where(
            Activity.plan_version_id == ids["candidate"], Activity.sequence_no == 1)).one()
        # The locked place of the base is replaced rather than dropped: the candidate still has a slot 1
        # and it still says locked, but it no longer carries the base's locked place.
        row.place_id = ids["b"]
        row.title = "天一塔"
        session.commit()
    body = _submit(client, ids, key="submit-locked").json()
    assert body["locked_commitments_preserved"] is False, body
    assert body["locked_slots_dropped"] == [1], body
    stored = _proposal(seeded, body["proposal_id"])
    assert stored.locked_commitments_preserved is False, stored
    assert json.loads(stored.explanation_json)["locked_slots_dropped"] == [1], stored


def test_the_second_submission_of_the_same_pair_is_refused_by_name(seeded):
    client = _app(seeded)
    ids = seeded.ids
    first = _submit(client, ids)
    assert first.status_code == 201, first.text
    again = _submit(client, ids, key="submit-2")
    assert again.status_code == 409, again.text
    error = again.json()["error"]
    assert error["reason_code"] == plan_submission.REASON_ALREADY, error
    assert error["details"]["status"] == "PRESENTED", error
    assert len(_rows(seeded, ReplanProposal)) == 1, _rows(seeded, ReplanProposal)


def test_the_same_key_replays_one_proposal_and_a_changed_press_is_refused(seeded):
    """One key means one act: a replay returns the same proposal, a second press with new content is
    refused by name instead of quietly writing a second round."""
    client = _app(seeded)
    ids = seeded.ids
    first = _submit(client, ids)
    replay = _submit(client, ids)
    assert replay.status_code == 201, replay.text
    assert replay.json()["idempotency_replay"] is True, replay.json()
    assert replay.json()["proposal_id"] == first.json()["proposal_id"], replay.json()
    assert len(_rows(seeded, ReplanProposal)) == 1, _rows(seeded, ReplanProposal)

    clash = client.post(SUBMIT.format(journey_id=ids["journey"],
                                      plan_version_id=ids["other_candidate"]),
                        json={}, headers={"Idempotency-Key": "submit-1",
                                          **_header(ids["owner"])})
    assert clash.status_code == 409, clash.text
    assert clash.json()["error"]["reason_code"] == plan_submission.REASON_KEY_CONFLICT, clash.json()
    assert len(_rows(seeded, ReplanProposal)) == 1, _rows(seeded, ReplanProposal)
    assert len(_rows(seeded, IdempotencyKey)) == 1, _rows(seeded, IdempotencyKey)


def test_the_refusals_are_named_for_each_thing_that_is_not_a_submittable_candidate(seeded):
    client = _app(seeded)
    ids = seeded.ids
    anonymous = client.post(SUBMIT.format(journey_id=ids["journey"],
                                          plan_version_id=ids["candidate"]), json={},
                            headers={"Idempotency-Key": "k"})
    assert anonymous.status_code == 401, anonymous.text
    assert anonymous.json()["error"]["reason_code"] == "TRAVELER_CREDENTIALS_MISSING"

    outsider = _submit(client, ids, traveler_id=ids["stranger"])
    assert outsider.status_code == 403, outsider.text
    assert outsider.json()["error"]["reason_code"] == departure_read.REASON_MEMBER_REQUIRED

    foreign = _submit(client, ids, plan=ids["foreign"])
    assert foreign.status_code == 404, foreign.text
    assert foreign.json()["error"]["reason_code"] == plan_delta.REASON_PLAN_NOT_IN_JOURNEY

    not_candidate = _submit(client, ids, plan=ids["active_other"], key="submit-x")
    assert not_candidate.status_code == 409, not_candidate.text
    assert not_candidate.json()["error"]["reason_code"] == plan_submission.REASON_NOT_CANDIDATE

    body_carried = _submit(client, ids, key="submit-y", body={"utility_score": 0.99})
    assert body_carried.status_code == 422, body_carried.text
    assert body_carried.json()["error"]["reason_code"] == plan_submission.REASON_BODY, body_carried
    assert body_carried.json()["error"]["details"]["unexpected_fields"] == ["utility_score"]

    no_key = client.post(SUBMIT.format(journey_id=ids["journey"],
                                       plan_version_id=ids["candidate"]), json={},
                         headers=_header(ids["owner"]))
    assert no_key.status_code == 422, no_key.text
    assert no_key.json()["error"]["reason_code"] == plan_submission.REASON_KEY_REQUIRED


def test_a_journey_with_no_active_plan_has_no_base_to_differ_from(seeded):
    client = _app(seeded)
    ids = seeded.ids
    with seeded.factory() as session:
        journey = session.get(Journey, ids["journey"])
        journey.active_plan_version_id = None
        session.commit()
    refused = _submit(client, ids)
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["reason_code"] == plan_submission.REASON_NO_BASE


def test_the_active_version_itself_is_refused_as_a_change_against_itself(seeded):
    client = _app(seeded)
    ids = seeded.ids
    refused = _submit(client, ids, plan=ids["base"])
    assert refused.status_code == 422, refused.text
    assert refused.json()["error"]["reason_code"] == plan_submission.REASON_SAME


def test_two_currencies_have_no_cost_delta_so_the_submission_is_refused(seeded):
    """The Guardian bounds a proposal by `diff_json.cost_delta_minor`; a mixed pair has no such number."""
    client = _app(seeded)
    ids = seeded.ids
    with seeded.factory() as session:
        for row in session.scalars(select(Activity).where(
                Activity.plan_version_id == ids["candidate"])).all():
            row.currency = "USD"
        session.commit()
    refused = _submit(client, ids)
    assert refused.status_code == 422, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == plan_submission.REASON_CURRENCY, error
    assert error["details"]["currencies"] == ["CNY", "USD"], error
    assert _rows(seeded, ReplanProposal) == [], _rows(seeded, ReplanProposal)


def test_a_candidate_that_changes_nothing_is_refused_instead_of_opening_a_round(seeded):
    """The V3 order keeps a genuine absence named (`NO_MATERIAL_CHANGE`) instead of calling a vote.

    `ids["mirror"]` carries the base's places, instants, money and locks under a new version number,
    which is what a traveller gets for pressing the plan already in force back through the write door.
    The shipped DDL would take that proposal happily and the members would be asked to approve the plan
    they are already on, so the refusal is computed here, from the delta's own arithmetic.
    """
    client = _app(seeded)
    ids = seeded.ids
    refused = _submit(client, ids, plan=ids["mirror"], key="submit-mirror")
    assert refused.status_code == 422, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == plan_submission.REASON_NO_MATERIAL, error
    details = error["details"]
    assert details["counts"] == {"from_slots": 3, "to_slots": 3, "kept": 3, "moved": 0,
                                 "added": 0, "removed": 0}, details["counts"]
    assert details["sets_that_changed"] == {}, details
    assert details["kept_slots_whose_row_differs"] == [], details
    assert details["kept_slots_whose_lifecycle_word_differs"] == [], details
    assert details["lifecycle_word_not_counted"] == plan_submission.LIFECYCLE_DISCLOSURE, details
    assert details["lock_flags_changed"] == [], details
    assert details["budget_totals_minor"] == [9000, 9000], details
    for word in ("budget_delta_minor", "verified_cost_delta_minor", "duration_delta_min",
                 "travel_delta_min"):
        assert details[word] == 0, (word, details[word])
    assert details["read_from"] == ("app.plan_delta.delta_of + activities.locked / "
                                    "travel_from_prev_min"), details["read_from"]
    assert details["base_plan_version_id"] == ids["base"], details
    assert details["proposed_plan_version_id"] == ids["mirror"], details
    for model in (ReplanProposal, IdempotencyKey, AuditLog):
        assert _rows(seeded, model) == [], model.__name__
    with seeded.factory() as session:
        assert session.get(Journey, ids["journey"]).active_plan_version_id == ids["base"]
        assert session.get(PlanVersion, ids["mirror"]).status == "CANDIDATE"


def test_a_difference_only_in_the_word_the_server_writes_is_named_not_counted(seeded):
    """`/start` marks the live plan's first slot ACTIVE while a candidate says PLANNED: nothing else.

    Measured on a real socket (`_live_mirror_1020fc.py`): a traveller who presses a departed plan back
    at the server differs in `activities.status` and in no chosen fact. That column is this server's own
    lifecycle word, which no member can approve or reject, so the round is still refused -- and the
    difference is stated in the refusal rather than quietly dropped.
    """
    client = _app(seeded)
    ids = seeded.ids
    with seeded.factory() as session:
        slot = session.scalars(select(Activity).where(
            Activity.plan_version_id == ids["base"], Activity.sequence_no == 1)).one()
        slot.status = "ACTIVE"
        session.commit()
    refused = _submit(client, ids, plan=ids["mirror"], key="submit-lifecycle")
    assert refused.status_code == 422, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == plan_submission.REASON_NO_MATERIAL, error
    details = error["details"]
    assert details["kept_slots_whose_lifecycle_word_differs"] == [1], details
    assert details["kept_slots_whose_row_differs"] == [], details
    assert details["lifecycle_word_not_counted"] == "activities.status", details
    assert _rows(seeded, ReplanProposal) == [], _rows(seeded, ReplanProposal)


def test_every_column_a_delta_stamp_carries_is_classified_by_the_no_material_rule(seeded):
    """Default-deny, proved against the writer: a stamp field added later must not fall through unseen."""
    client = _app(seeded)
    ids = seeded.ids
    delta = client.get(plan_delta.DELTA_PATH.format(journey_id=ids["journey"]),
                       params={"from_plan_version_id": ids["base"],
                               "to_plan_version_id": ids["mirror"]},
                       headers=_header(ids["owner"]))
    assert delta.status_code == 200, delta.text
    keys: set[str] = set()
    for entry in delta.json()["sets"]["kept"]:
        keys |= set(entry["from"]) | set(entry["to"])
    chosen = {"place_id", "start_at", "end_at", "estimated_cost_minor", "currency"}
    assert keys == chosen | {"sequence_no"} | set(plan_submission.LIFECYCLE_STAMP_FIELDS), sorted(keys)


def test_the_no_material_verdict_is_the_same_function_the_door_answers_with(seeded):
    """One writer for the verdict: `material_comparison` re-run over the delta door's own answer."""
    client = _app(seeded)
    ids = seeded.ids
    with seeded.factory() as session:
        journey = session.get(Journey, ids["journey"])
        base = session.get(PlanVersion, ids["base"])
        mirror = session.get(PlanVersion, ids["mirror"])
        candidate = session.get(PlanVersion, ids["candidate"])
        mirror_delta = plan_delta.delta_of(session, journey, base, mirror)
        candidate_delta = plan_delta.delta_of(session, journey, base, candidate)
        mirror_travel = plan_submission._travel_delta(session, base.id, mirror.id)
        candidate_travel = plan_submission._travel_delta(session, base.id, candidate.id)
        mirror_dropped, mirror_added = plan_submission._lock_flag_states(session, base.id, mirror.id)
        candidate_dropped, candidate_added = plan_submission._lock_flag_states(
            session, base.id, candidate.id)
    nothing = plan_submission.material_comparison(
        mirror_delta, travel_delta_min=mirror_travel,
        lock_flag_changes=sorted(set(mirror_dropped) | set(mirror_added)))
    something = plan_submission.material_comparison(
        candidate_delta, travel_delta_min=candidate_travel,
        lock_flag_changes=sorted(set(candidate_dropped) | set(candidate_added)))
    assert nothing["unchanged"] is True, nothing
    assert something["unchanged"] is False, (something, something["sets_that_changed"])

    details = _submit(client, ids, plan=ids["mirror"], key="submit-parity").json()["error"]["details"]
    for word in ("counts", "sets_that_changed", "kept_slots_whose_row_differs",
                 "kept_slots_whose_lifecycle_word_differs", "lifecycle_word_not_counted",
                 "lock_flags_changed", "budget_delta_minor", "budget_totals_minor",
                 "verified_cost_delta_minor", "duration_delta_min", "travel_delta_min"):
        assert details[word] == nothing[word], (word, details[word], nothing[word])


def test_a_candidate_that_only_moves_the_clock_is_a_change_though_the_day_keeps_its_length(seeded):
    """The per-slot stamps are load-bearing: every aggregate still reads zero, so this must be asked."""
    client = _app(seeded)
    ids = seeded.ids
    with seeded.factory() as session:
        for row in session.scalars(select(Activity).where(
                Activity.plan_version_id == ids["mirror"])).all():
            row.start_at = (datetime.fromisoformat(row.start_at) + timedelta(minutes=30)).isoformat()
            row.end_at = (datetime.fromisoformat(row.end_at) + timedelta(minutes=30)).isoformat()
        session.commit()
    accepted = _submit(client, ids, plan=ids["mirror"], key="submit-shift")
    assert accepted.status_code == 201, accepted.text
    body = accepted.json()
    assert body["delta"]["counts"]["moved"] == 0 and body["delta"]["counts"]["added"] == 0, body
    assert body["delta"]["counts"]["kept"] == 3, body["delta"]["counts"]
    assert body["delta"]["duration_delta"]["delta_min"] == 0, body["delta"]["duration_delta"]
    assert body["delta"]["budget_delta"]["delta_minor"] == 0, body["delta"]["budget_delta"]
    assert len(_rows(seeded, ReplanProposal)) == 1, _rows(seeded, ReplanProposal)


def test_a_candidate_that_only_unlocks_a_commitment_is_still_a_change(seeded):
    """`activities.locked` is not in a delta stamp, so the guard reads it from the rows for itself."""
    client = _app(seeded)
    ids = seeded.ids
    with seeded.factory() as session:
        slot = session.scalars(select(Activity).where(
            Activity.plan_version_id == ids["mirror"], Activity.sequence_no == 1)).one()
        slot.locked = False
        session.commit()
    accepted = _submit(client, ids, plan=ids["mirror"], key="submit-unlock")
    assert accepted.status_code == 201, accepted.text
    body = accepted.json()
    assert body["delta"]["counts"]["kept"] == 3 and body["delta"]["counts"]["moved"] == 0, body
    assert body["delta"]["duration_delta"]["delta_min"] == 0, body["delta"]
    # The shipped place-based claim still says "preserved" here, and the door says so while naming the
    # flag it is not looking at -- this is the shape a `from-slots` candidate over a locked base has.
    assert body["locked_commitments_preserved"] is True, body
    assert body["lock_flags_dropped"] == [1], body
    assert body["lock_flags_added"] == [], body
    stored = _proposal(seeded, body["proposal_id"])
    assert json.loads(stored.explanation_json)["lock_flags_dropped"] == [1], stored.explanation_json


def test_a_candidate_that_adds_a_commitment_names_it_apart_from_a_dropped_one(seeded):
    """Two directions of the same column are two different facts for the people being asked."""
    client = _app(seeded)
    ids = seeded.ids
    with seeded.factory() as session:
        slot = session.scalars(select(Activity).where(
            Activity.plan_version_id == ids["mirror"], Activity.sequence_no == 2)).one()
        slot.locked = True
        session.commit()
    accepted = _submit(client, ids, plan=ids["mirror"], key="submit-lock-add")
    assert accepted.status_code == 201, accepted.text
    body = accepted.json()
    assert body["lock_flags_added"] == [2], body
    assert body["lock_flags_dropped"] == [], body
    assert body["locked_slots_dropped"] == [], body


def test_a_refusal_costs_the_idempotency_key_nothing_and_a_reprice_is_a_change(seeded):
    """No receipt rides a refusal: the same key carries the corrected press, which then writes a round."""
    client = _app(seeded)
    ids = seeded.ids
    refused = _submit(client, ids, plan=ids["mirror"], key="submit-once")
    assert refused.status_code == 422, refused.text
    assert refused.json()["error"]["reason_code"] == plan_submission.REASON_NO_MATERIAL, refused.text
    assert _rows(seeded, IdempotencyKey) == [], _rows(seeded, IdempotencyKey)
    with seeded.factory() as session:
        slot = session.scalars(select(Activity).where(
            Activity.plan_version_id == ids["mirror"], Activity.sequence_no == 3)).one()
        slot.estimated_cost_minor = 3500
        session.commit()
    accepted = _submit(client, ids, plan=ids["mirror"], key="submit-once")
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["delta"]["budget_delta"]["delta_minor"] == 500, accepted.json()["delta"]
    assert len(_rows(seeded, ReplanProposal)) == 1, _rows(seeded, ReplanProposal)
    assert len(_rows(seeded, IdempotencyKey)) == 1, _rows(seeded, IdempotencyKey)


def test_every_refusal_word_this_door_can_answer_with_is_written_in_the_contract():
    """A reason code a screen has to branch on is only a contract word if the contract carries it."""
    contract = yaml.safe_load(Path("../contracts/openapi.yaml").read_text(encoding="utf-8"))
    path = contract["paths"]["/journeys/{journey_id}/plans/{plan_version_id}/submission"]["post"]
    described = json.dumps(path["responses"], ensure_ascii=False)
    words = sorted(value for name, value in vars(plan_submission).items()
                   if name.startswith("REASON_"))
    assert len(words) >= 2, words
    missing = [word for word in words if word not in described]
    assert missing == [], (missing, words)


def test_no_event_and_no_epoch_are_invented_for_a_hand_built_candidate(seeded):
    client = _app(seeded)
    body = _submit(client, seeded.ids).json()
    stored = _proposal(seeded, body["proposal_id"])
    assert stored.trigger_event_id is None, stored.trigger_event_id
    assert stored.recovery_epoch_id is None, stored.recovery_epoch_id
    explanation = json.loads(stored.explanation_json)
    assert sorted(explanation) == ["currency", "gate_failures", "gate_judged", "gate_refusal_code",
                                   "lock_flags_added", "lock_flags_dropped", "locked_slots_dropped",
                                   "source", "submitted_by_traveler_id"], explanation
    assert explanation["source"] == plan_submission.FAMILY, explanation
    for value in explanation.values():
        if isinstance(value, str):
            # Codes and ids only: `explanation_json` is a column other doors read, and a sentence here
            # would be server-authored prose waiting to reach a screen.
            assert re.fullmatch(r"[0-9a-f-]{36}|[A-Z][A-Z_]+", value), value


def test_the_submission_writes_its_own_proposal_and_receipt_and_nothing_else(seeded):
    client = _app(seeded)
    ids = seeded.ids
    before = {model.__name__: len(_rows(seeded, model)) for model in
              (Activity, PlanVersion, Journey, JourneyMember, Place, Traveler)}
    answer = _submit(client, ids)
    assert answer.status_code == 201, answer.text
    assert len(_rows(seeded, ReplanProposal)) == 1
    assert len(_rows(seeded, IdempotencyKey)) == 1
    audits = _rows(seeded, AuditLog)
    assert [row.action for row in audits] == ["plan.candidate_submission.presented"], audits
    assert audits[0].actor_type == "traveler" and audits[0].actor_id == ids["owner"], vars(audits[0])
    after = {model.__name__: len(_rows(seeded, model)) for model in
             (Activity, PlanVersion, Journey, JourneyMember, Place, Traveler)}
    assert after == before, (before, after)


def test_no_provider_client_is_reachable_from_the_submission_module():
    tree = ast.parse(Path("app/plan_submission.py").read_text(encoding="utf-8"), filename="submission")
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(str(alias.name).split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(str(node.module).split(".")[0])
            modules.add(str(node.module))
    network = {"http", "httpx", "requests", "aiohttp", "urllib", "socket", "ssl", "urllib3"}
    assert modules.isdisjoint(network), sorted(modules & network)
    assert "app.plan_delta" in modules, sorted(modules)
    assert "app.agent" not in modules, "no guardian runtime import from a write door"


def test_the_words_a_submission_stores_are_words_the_shipped_ddl_allows(seeded):
    contract = yaml.safe_load(Path("../contracts/openapi.yaml").read_text(encoding="utf-8"))
    ddl = Path("db/schema.sql").read_text(encoding="utf-8")
    start = ddl.index("CREATE TABLE IF NOT EXISTS replan_proposals (")
    block = ddl[start:ddl.index("\n);", start)]
    marker = "status IN ("
    at = block.index(marker) + len(marker)
    words = [item.strip().strip("'") for item in block[at:block.index(")", at)].split(",")]
    assert plan_submission.STATUS_PRESENTED in words, words

    body = _submit(_app(seeded), seeded.ids).json()
    stored = _proposal(seeded, body["proposal_id"])
    assert stored.status in words, stored.status

    path = contract["paths"]["/journeys/{journey_id}/plans/{plan_version_id}/submission"]["post"]
    assert path["operationId"] == "postJourneyPlanSubmission", path["operationId"]
    assert [item["name"] for item in path["parameters"] if item.get("in") == "header"] == [
        "Idempotency-Key"], path["parameters"]
    answer = path["responses"]["201"]["content"]["application/json"]["schema"]
    assert answer.get("$ref") == "#/components/schemas/PlanCandidateSubmission", answer
    schema = contract["components"]["schemas"]["PlanCandidateSubmission"]
    assert sorted(schema["required"]) == sorted(body), (
        sorted(set(schema["required"]) ^ set(body)))
    assert schema["properties"]["status"]["const"] == plan_submission.STATUS_PRESENTED, schema
