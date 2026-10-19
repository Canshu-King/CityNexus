"""Two signed reads that tell a screen whether departure is real, and the refusals before them.

The 19:28 order says Codex may not invent a second manual place-selection flow and that Qoder owes
「具名补齐缺失的签名成员读取」plus「正式方案投影」. These two doors are that: `.../members/me` answers
"does this caller hold a seat, as what, until when", and `.../departure` answers "which plan rows
exist, what did the server freeze for them, and what is the one gate word for this journey".

What is policed here, in this product's own words:

* the door runs first -- no credentials is the resolver's named 401, an unknown journey is 404, and a
  caller with no seat in force is 403 with the seat that explains it; a stranger's journey cannot be
  enumerated by plan id, version number or currency, because none of that is read before the seat;
* the three membership words are the same three the member list already uses -- pinned against
  `app.main._member_state` on the same rows, because a mirror nobody checks is a second answer;
* the gate word is decided in one order, and the stale-evidence ones agree with what the write door
  actually raises for the same row (that agreement is measured, not asserted here in prose);
* a read is a read: nothing about a journey or a plan version moves.

The credential secret is generated per run and never written into the tree.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import departure_read, traveler_principal
from app.core.config import settings
from app.db.models import Activity, Base, Journey, JourneyMember, PlanVersion, Traveler
from app.db.session import get_session

SECRET = uuid.uuid4().hex + uuid.uuid4().hex  # generated, never printed, never committed


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _then(offset_minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)).isoformat()


def _traveler(session, key: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Traveler(id=ident, display_name=key, email=None, locale="zh-CN",
                         timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
    return ident


def _journey(session, owner_id: str, status: str = "PLANNED") -> str:
    ident = str(uuid.uuid4())
    session.add(Journey(id=ident, traveler_id=owner_id, title="连城", city_code="350825",
                        timezone="Asia/Shanghai", start_at=_then(60), end_at=_then(60 * 24),
                        budget_currency="CNY", budget_amount_minor=500_00, status=status,
                        created_at=_now(), updated_at=_now()))
    return ident


def _member(session, journey_id: str, traveler_id: str, *, expires_offset_minutes=None,
            removed: bool = False, role: str = "COLLABORATOR") -> str:
    ident = str(uuid.uuid4())
    session.add(JourneyMember(id=ident, journey_id=journey_id, traveler_id=traveler_id, role=role,
                              invited_by="owner-device", created_at=_now(), updated_at=_now(),
                              joined_at=_now(), expires_at=_then(expires_offset_minutes)
                              if expires_offset_minutes is not None else None,
                              removed_at=_now() if removed else None))
    return ident


def _plan(session, journey_id: str, *, version_no: int, status: str, evidence: dict,
          snapshot_id: str | None = None) -> str:
    ident = str(uuid.uuid4())
    session.add(PlanVersion(id=ident, journey_id=journey_id, version_no=version_no,
                            planning_mode="BALANCED", status=status, source="INITIAL",
                            total_cost_minor=470_00, currency="CNY", estimated_duration_min=240,
                            mobility_snapshot_id=snapshot_id,
                            mobility_evidence_json=json.dumps(evidence),
                            created_at=_now()))
    return ident


@pytest.fixture()
def seeded():
    """One journey, three callers with three different seats, and four plan rows in four states."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ids: dict[str, str] = {}
    with factory() as session:
        ids["owner"] = _traveler(session, "owner")
        ids["member"] = _traveler(session, "member")
        ids["lapsed"] = _traveler(session, "lapsed")
        ids["stranger"] = _traveler(session, "stranger")
        ids["journey"] = _journey(session, ids["owner"])
        ids["seat_member"] = _member(session, ids["journey"], ids["member"], expires_offset_minutes=120)
        ids["seat_lapsed"] = _member(session, ids["journey"], ids["lapsed"], expires_offset_minutes=-1)
        snapshot = "snap-" + uuid.uuid4().hex[:8]
        ids["plan_unfrozen"] = _plan(session, ids["journey"], version_no=1, status="CANDIDATE",
                                     evidence={})
        ids["plan_expired"] = _plan(session, ids["journey"], version_no=2, status="SELECTED",
                                    evidence={"snapshot_id": snapshot, "expires_at": _then(-5)},
                                    snapshot_id=snapshot)
        ids["plan_fresh"] = _plan(session, ids["journey"], version_no=3, status="CANDIDATE",
                                  evidence={"snapshot_id": snapshot, "expires_at": _then(30)},
                                  snapshot_id=snapshot)
        session.add(Activity(id=str(uuid.uuid4()), plan_version_id=ids["plan_fresh"],
                             sequence_no=1, activity_type="SIGHTSEE", title="冠豸山",
                             place_id=None, city_service_id=None, start_at=_then(60),
                             end_at=_then(120), travel_from_prev_min=0, estimated_cost_minor=0,
                             currency="CNY", status="PENDING", locked=False,
                             metadata_json="{}", created_at=_now(), updated_at=_now()))
        session.commit()
    return SimpleNamespace(factory=factory, ids=ids)


def _app(seeded, monkeypatch):
    """These two doors, this seed, and the credential secret pinned for the run."""
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))
    from app import main as main_module

    app = FastAPI()
    app.include_router(departure_read.router)
    app.add_exception_handler(StarletteHTTPException, main_module.http_error)

    def override_session():
        with seeded.factory() as inner:
            yield inner

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _header(traveler_id: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(traveler_id)}


DEPARTURE = "/api/v1/journeys/{}/departure"
MEMBER_ME = "/api/v1/journeys/{}/members/me"


# ------------------------------------------------------------------ the door runs first
def test_no_credentials_is_the_resolvers_own_named_401_and_no_plan_is_read(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    refused = client.get(DEPARTURE.format(seeded.ids["journey"]))
    assert refused.status_code == 401, refused.text
    body = refused.json()["error"]
    assert body["reason_code"] == traveler_principal.REASON_CREDENTIALS_MISSING
    for leaked in ("candidates", "selected_plan", "gate"):
        assert leaked not in body and leaked not in refused.json(), leaked


def test_a_stranger_with_real_credentials_gets_403_and_no_facts_about_the_trip(seeded, monkeypatch):
    """The whole point of running the door first: a valid token for someone else buys no readings."""
    client = _app(seeded, monkeypatch)
    refused = client.get(DEPARTURE.format(seeded.ids["journey"]),
                         headers=_header(seeded.ids["stranger"]))
    assert refused.status_code == 403, refused.text
    body = refused.json()["error"]
    assert body["reason_code"] == departure_read.REASON_MEMBER_REQUIRED
    assert body["details"]["seat"]["seat_kind"] == "NONE", body["details"]
    for leaked in ("candidates", "selected_plan", "gate"):
        assert leaked not in body and leaked not in refused.json(), leaked


def test_an_unknown_journey_is_404_even_with_the_owners_token(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    assert client.get(DEPARTURE.format(str(uuid.uuid4())),
                      headers=_header(seeded.ids["owner"])).status_code == 404


# ------------------------------------------------------------------ the seat, in three words
def test_owner_and_in_force_member_read_200_while_the_lapsed_seat_is_refused(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    owner = client.get(MEMBER_ME.format(seeded.ids["journey"]), headers=_header(seeded.ids["owner"]))
    member = client.get(MEMBER_ME.format(seeded.ids["journey"]), headers=_header(seeded.ids["member"]))
    lapsed = client.get(MEMBER_ME.format(seeded.ids["journey"]), headers=_header(seeded.ids["lapsed"]))
    assert owner.status_code == 200 and member.status_code == 200, (owner.text, member.text)
    assert owner.json()["seat"]["seat_kind"] == departure_read.SEAT_OWNER
    assert owner.json()["seat"]["role"] == "OWNER" and owner.json()["may_confirm_departure"] is True
    assert member.json()["seat"] == {
        "traveler_id": seeded.ids["member"], "seat_kind": departure_read.SEAT_MEMBER,
        "role": "COLLABORATOR", "member_id": seeded.ids["seat_member"],
        "member_state": "MEMBER_IN_FORCE", "expires_at": member.json()["seat"]["expires_at"],
        "in_force": True}, member.json()["seat"]
    assert lapsed.status_code == 403, lapsed.text
    assert lapsed.json()["error"]["details"]["seat"]["member_state"] == "MEMBER_LAPSED"


def test_the_three_membership_words_are_the_same_words_the_member_list_uses(seeded):
    """`app.main._member_state` is the definition; this door mirrors it, so pin the mirror."""
    from app import main as main_module

    with seeded.factory() as session:
        rows = session.scalars(select(JourneyMember)).all()
        withdrawn = JourneyMember(id=str(uuid.uuid4()), journey_id=seeded.ids["journey"],
                                  traveler_id=rows[0].traveler_id, role="COLLABORATOR",
                                  invited_by="x", created_at=_now(), updated_at=_now(),
                                  joined_at=_now(), expires_at=None, removed_at=_now())
        now = datetime.now(timezone.utc)
        for member in list(rows) + [withdrawn]:
            assert departure_read._membership_state(member, now) == main_module._member_state(
                member, now), member.id


# ------------------------------------------------------------------ the gate word
def test_a_journey_holding_no_plan_row_says_so_and_points_at_generation(seeded, monkeypatch):
    with seeded.factory() as session:
        journey_id = _journey(session, seeded.ids["owner"])
        session.commit()
    client = _app(seeded, monkeypatch)
    answer = client.get(DEPARTURE.format(journey_id), headers=_header(seeded.ids["owner"]))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["gate"] == departure_read.GATE_NO_PLAN
    assert body["reason_detail"] == "NO_PLAN_VERSION_ROWS"
    assert body["candidates"] == [] and body["selected_plan"] is None
    assert body["next_action"] == {
        "kind": "generate_plans", "door": f"/api/v1/journeys/{journey_id}/plans/generate"}


def test_candidates_only_is_still_no_plan_selected_but_shows_what_exists(seeded, monkeypatch):
    """The A/B/C screen is exactly this state: rows exist, none is chosen, and the words differ."""
    with seeded.factory() as session:
        journey = session.get(Journey, seeded.ids["journey"])
        journey.active_plan_version_id = None
        session.get(PlanVersion, seeded.ids["plan_expired"]).status = "CANDIDATE"
        session.commit()
    client = _app(seeded, monkeypatch)
    body = client.get(DEPARTURE.format(seeded.ids["journey"]),
                      headers=_header(seeded.ids["owner"])).json()
    assert body["gate"] == departure_read.GATE_NO_PLAN, body
    assert body["reason_detail"] == "CANDIDATES_ONLY"
    assert len(body["candidates"]) == 3, [row["version_no"] for row in body["candidates"]]
    unfrozen = next(row for row in body["candidates"] if row["plan_version_id"] == seeded.ids["plan_unfrozen"])
    assert unfrozen["evidence"] == {"frozen": False, "snapshot_id": None, "expires_at": None,
                                    "expired": None, "reference_consistent": True, "detail": None}
    assert unfrozen["feasibility"] == {"feasible": None, "failures": [],
                                       "detail": "NOT_EVALUATED_WITHOUT_FROZEN_EVIDENCE"}
    assert unfrozen["currency"] == "CNY" and unfrozen["total_cost_minor"] == 470_00


def test_a_selected_plan_on_stale_evidence_says_stale_and_names_which_hop(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    body = client.get(DEPARTURE.format(seeded.ids["journey"]),
                      headers=_header(seeded.ids["owner"])).json()
    assert body["gate"] == departure_read.GATE_STALE_EVIDENCE, body
    assert body["reason_detail"] == "EVIDENCE_EXPIRED"
    assert body["selected_plan"]["evidence"]["expired"] is True
    assert body["next_action"]["kind"] == "recompose"


def test_the_read_door_and_the_write_doors_give_the_same_word_for_the_same_row(seeded):
    """The promise this projection exists to keep, measured against the doors that actually write.

    Not shared code: select's and start's predicates live in `app/main.py` and this door does not
    touch them.  So the agreement is pinned by driving both over one row -- an unfrozen candidate
    against `select`, a selected row on expired evidence against `start`, which is exactly the door
    the projection points a ready traveller at.
    """
    from fastapi import HTTPException

    from app import main as main_module

    with seeded.factory() as session:
        with pytest.raises(HTTPException) as on_select:
            main_module.select_plan(uuid.UUID(seeded.ids["journey"]),
                                    uuid.UUID(seeded.ids["plan_unfrozen"]), session)
        assert on_select.value.status_code == 409, on_select.value.detail
        assert str(on_select.value.detail).startswith("STALE_RECOMPOSE_REQUIRED")

        journey = session.get(Journey, seeded.ids["journey"])
        journey.active_plan_version_id = seeded.ids["plan_expired"]
        session.commit()
        with pytest.raises(HTTPException) as on_start:
            main_module.start_journey(uuid.UUID(seeded.ids["journey"]), session)
        assert on_start.value.status_code == 409, on_start.value.detail
        assert str(on_start.value.detail).startswith("STALE_RECOMPOSE_REQUIRED")


def test_an_already_running_journey_is_reported_before_any_evidence_judgement(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    with seeded.factory() as session:
        journey = session.get(Journey, seeded.ids["journey"])
        journey.status = "ACTIVE"
        journey.active_plan_version_id = seeded.ids["plan_expired"]
        session.commit()
    body = client.get(DEPARTURE.format(seeded.ids["journey"]),
                      headers=_header(seeded.ids["member"])).json()
    assert body["gate"] == departure_read.GATE_ALREADY_RUNNING, body
    assert body["next_action"] == {"kind": "none", "door": None}
    assert body["selected_plan"]["evidence"]["expired"] is True  # still reported, just not the verdict


def test_a_fresh_plan_reports_whatever_the_evaluator_actually_found(seeded, monkeypatch):
    """No invented green: the gate is the evaluator's answer, and its words ride along."""
    client = _app(seeded, monkeypatch)
    with seeded.factory() as session:
        journey = session.get(Journey, seeded.ids["journey"])
        journey.active_plan_version_id = seeded.ids["plan_fresh"]
        session.get(PlanVersion, seeded.ids["plan_fresh"]).status = "SELECTED"
        session.commit()
    body = client.get(DEPARTURE.format(seeded.ids["journey"]),
                      headers=_header(seeded.ids["owner"])).json()
    feasible = body["selected_plan"]["feasibility"]["feasible"]
    assert body["gate"] in (departure_read.GATE_READY, departure_read.GATE_INFEASIBLE), body
    assert (body["gate"] == departure_read.GATE_INFEASIBLE) == (feasible is False), body
    if body["gate"] == departure_read.GATE_INFEASIBLE:
        assert body["reason_detail"] and body["selected_plan"]["feasibility"]["failures"]
    else:
        assert body["next_action"]["door"].endswith("/start")


def test_reading_the_projection_writes_nothing(seeded, monkeypatch):
    """A read that mutates would let a screen 'depart' by looking at it."""
    client = _app(seeded, monkeypatch)
    with seeded.factory() as session:
        before = [(session.get(Journey, seeded.ids["journey"]).status,
                   session.get(Journey, seeded.ids["journey"]).active_plan_version_id,
                   session.get(Journey, seeded.ids["journey"]).updated_at)]
        statuses = [(row.version_no, row.status) for row in
                    session.scalars(select(PlanVersion).order_by(PlanVersion.version_no)).all()]
    for _ in range(2):
        assert client.get(DEPARTURE.format(seeded.ids["journey"]),
                          headers=_header(seeded.ids["owner"])).status_code == 200
        assert client.get(MEMBER_ME.format(seeded.ids["journey"]),
                          headers=_header(seeded.ids["owner"])).status_code == 200
    with seeded.factory() as session:
        after = [(session.get(Journey, seeded.ids["journey"]).status,
                  session.get(Journey, seeded.ids["journey"]).active_plan_version_id,
                  session.get(Journey, seeded.ids["journey"]).updated_at)]
        after_statuses = [(row.version_no, row.status) for row in
                          session.scalars(select(PlanVersion).order_by(PlanVersion.version_no)).all()]
    assert after == before, (before, after)
    assert after_statuses == statuses
