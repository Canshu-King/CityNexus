"""One signed, idempotent commit door, and the refusals that come before it writes anything.

The V3 order's second item is 「选定的 Agent GoalDraft/Variant → 正式 PlanVersion」 with the
instruction to search the existing persistence domain first and not hand Codex a second manual place
selection. What the search found, read at HEAD:

* there is no agent-draft table -- `app.agent` persists `JourneyMission`, `AgentRun` and
  `AgentRunStep` in `app.db.models`, none of which holds a plan, and the only `Variant` in the
  backend is the in-memory dataclass `app.planning.adapter.PlannerVariant`;
* the A/B/C the traveller picks *are* the `CANDIDATE` PlanVersion rows `app.services.generate_plans`
  already writes, and `POST .../plans/{id}/select` already performs the transition;
* `app.main.select_plan` answers no identity question and takes no `Idempotency-Key`, so a screen
  cannot say who confirmed, and a retry after a dropped response is a second write.

So the bridge adds exactly those two missing properties and delegates everything else: it calls the
same `select_plan` that `app.main` already calls in-process for its seed-supply loop and its staged
advance. Nothing here re-decides frozen evidence, feasibility, retirement of the previous SELECTED
row, the cursor or the single-ACTIVE invariant -- the refusals below are pinned to `select`'s own
sentences so the two doors cannot drift.

`plan_versions.source` gets no new vocabulary: the CHECK in `backend/db/schema.sql` allows only
INITIAL / REPLAN / MANUAL. No migration is needed for the decision record either -- `audit_logs`
already carries `actor_type` / `actor_id`, and `traveler` is the word the member doors use, as
`backend/tests/test_qoder_ord0503_member_doors.py` asserts. The credential secret is generated per
run and never written into the tree.
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

from app import departure_commit, departure_read, traveler_principal
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
    Traveler,
)
from app.db.session import get_session

SECRET = uuid.uuid4().hex + uuid.uuid4().hex  # generated, never printed, never committed

COMMIT = "/api/v1/journeys/{}/departure/commit"
DEPARTURE = "/api/v1/journeys/{}/departure"
OPEN_ALL_DAY = json.dumps({"open": "00:00", "close": "23:59"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _then(offset_minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)).isoformat()


def _traveler(session, key: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Traveler(id=ident, display_name=key, email=None, locale="zh-CN",
                         timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
    return ident


def _journey(session, owner_id: str, status: str = "DRAFT") -> str:
    ident = str(uuid.uuid4())
    session.add(Journey(id=ident, traveler_id=owner_id, title="连城", city_code="350825",
                        timezone="Asia/Shanghai", start_at=_then(60), end_at=_then(60 * 24),
                        budget_currency="CNY", budget_amount_minor=500_00, status=status,
                        created_at=_now(), updated_at=_now()))
    return ident


def _member(session, journey_id: str, traveler_id: str, *, expires_offset_minutes=None,
            removed: bool = False) -> str:
    ident = str(uuid.uuid4())
    session.add(JourneyMember(id=ident, journey_id=journey_id, traveler_id=traveler_id,
                              role="COLLABORATOR", invited_by="owner-device", created_at=_now(),
                              updated_at=_now(), joined_at=_now(),
                              expires_at=_then(expires_offset_minutes)
                              if expires_offset_minutes is not None else None,
                              removed_at=_now() if removed else None))
    return ident


def _place(session, city_code: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Place(id=ident, provider_key="offline-fixture",
                      external_id="guanzhai-" + ident[:8], city_code=city_code, name="冠豸山",
                      category="SIGHTSEE", latitude=25.7, longitude=116.75,
                      opening_hours_json=OPEN_ALL_DAY, tags_json="[]", metadata_json="{}",
                      updated_at=_now()))
    return ident


def _plan(session, journey_id: str, *, version_no: int, status: str, evidence: dict,
          snapshot_id: str | None = None) -> str:
    ident = str(uuid.uuid4())
    session.add(PlanVersion(id=ident, journey_id=journey_id, version_no=version_no,
                            planning_mode="BALANCED", status=status, source="INITIAL",
                            total_cost_minor=470_00, currency="CNY", estimated_duration_min=240,
                            mobility_snapshot_id=snapshot_id,
                            mobility_evidence_json=json.dumps(evidence), created_at=_now()))
    return ident


def _activity(session, plan_id: str, place_id: str | None) -> str:
    ident = str(uuid.uuid4())
    session.add(Activity(id=ident, plan_version_id=plan_id, sequence_no=1, activity_type="SIGHTSEE",
                         title="冠豸山", place_id=place_id, city_service_id=None,
                         start_at=_then(60), end_at=_then(120), travel_from_prev_min=0,
                         estimated_cost_minor=0, currency="CNY", status="PENDING", locked=False,
                         metadata_json="{}", created_at=_now(), updated_at=_now()))
    return ident


@pytest.fixture()
def seeded():
    """One draft journey, three seats, and four plan rows: commitable, infeasible, unfrozen, foreign."""
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
        ids["other_journey"] = _journey(session, ids["stranger"])
        ids["seat_member"] = _member(session, ids["journey"], ids["member"],
                                     expires_offset_minutes=120)
        ids["seat_lapsed"] = _member(session, ids["journey"], ids["lapsed"],
                                     expires_offset_minutes=-1)
        snapshot = "snap-" + uuid.uuid4().hex[:8]
        place = _place(session, "350825")
        ids["place"] = place
        fresh = {"snapshot_id": snapshot, "expires_at": _then(30)}
        ids["plan_committable"] = _plan(session, ids["journey"], version_no=1, status="CANDIDATE",
                                       evidence=fresh, snapshot_id=snapshot)
        _activity(session, ids["plan_committable"], place)
        ids["plan_infeasible"] = _plan(session, ids["journey"], version_no=2, status="CANDIDATE",
                                      evidence=dict(fresh), snapshot_id=snapshot)
        _activity(session, ids["plan_infeasible"], None)
        ids["plan_unfrozen"] = _plan(session, ids["journey"], version_no=3, status="CANDIDATE",
                                    evidence={})
        ids["plan_foreign"] = _plan(session, ids["other_journey"], version_no=1, status="CANDIDATE",
                                   evidence=dict(fresh), snapshot_id=snapshot)
        session.commit()
    ids["snapshot"] = snapshot
    return SimpleNamespace(factory=factory, ids=ids)


def _app(seeded, monkeypatch):
    """The commit door plus the read door it is designed to pair with, on this seed."""
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))
    from app import main as main_module

    app = FastAPI()
    app.include_router(departure_read.router)
    app.include_router(departure_commit.router)
    app.add_exception_handler(StarletteHTTPException, main_module.http_error)

    def override_session():
        with seeded.factory() as inner:
            yield inner

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _header(traveler_id: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(traveler_id)}


def _key() -> str:
    return "cmdr-" + uuid.uuid4().hex[:12]


def _commit(client, journey_id, plan_id, traveler_id, *, idempotency_key=None, body=None):
    headers = _header(traveler_id)
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    payload = {"plan_version_id": plan_id} if body is None else body
    return client.post(COMMIT.format(journey_id), headers=headers, json=payload)


def _rows(seeded, model, **filters):
    with seeded.factory() as session:
        statement = select(model)
        for name, value in filters.items():
            statement = statement.where(getattr(model, name) == value)
        return list(session.scalars(statement).all())


def _status_of(seeded, plan_id: str) -> str:
    rows = _rows(seeded, PlanVersion, id=plan_id)
    return rows[0].status if rows else "MISSING"


# ------------------------------------------------------------------ the door runs first
def test_no_credentials_is_the_resolvers_own_401_and_nothing_moves(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    refused = client.post(COMMIT.format(seeded.ids["journey"]),
                          json={"plan_version_id": seeded.ids["plan_committable"]})
    assert refused.status_code == 401, refused.text
    assert refused.json()["error"]["reason_code"] == traveler_principal.REASON_CREDENTIALS_MISSING
    assert _status_of(seeded, seeded.ids["plan_committable"]) == "CANDIDATE"
    assert _rows(seeded, IdempotencyKey) == []


def test_a_stranger_is_refused_before_the_plan_row_is_consulted(seeded, monkeypatch):
    """A valid token for somebody else must not turn this door into a plan-id prober."""
    client = _app(seeded, monkeypatch)
    refused = _commit(client, seeded.ids["journey"], seeded.ids["plan_foreign"],
                      seeded.ids["stranger"], idempotency_key=_key())
    assert refused.status_code == 403, refused.text
    body = refused.json()["error"]
    assert body["reason_code"] == departure_read.REASON_MEMBER_REQUIRED
    assert body["details"]["seat"]["seat_kind"] == "NONE", body["details"]
    for leaked in ("plan_status", "journey", "committed_by"):
        assert leaked not in body and leaked not in refused.json(), leaked
    assert _rows(seeded, IdempotencyKey) == []


def test_a_lapsed_seat_is_refused_with_the_same_word_the_read_door_gives(seeded, monkeypatch):
    """One seat answer for both doors: the screen's disabled button and the server's refusal agree."""
    client = _app(seeded, monkeypatch)
    read = client.get(DEPARTURE.format(seeded.ids["journey"]), headers=_header(seeded.ids["lapsed"]))
    write = _commit(client, seeded.ids["journey"], seeded.ids["plan_committable"],
                    seeded.ids["lapsed"], idempotency_key=_key())
    assert read.status_code == write.status_code == 403, (read.text, write.text)
    assert read.json()["error"]["reason_code"] == write.json()["error"]["reason_code"]
    assert write.json()["error"]["details"]["seat"]["member_state"] == "MEMBER_LAPSED"
    assert _status_of(seeded, seeded.ids["plan_committable"]) == "CANDIDATE"


def test_a_foreign_plan_is_answered_as_not_found_and_the_owner_still_commits_its_own(seeded,
                                                                                    monkeypatch):
    client = _app(seeded, monkeypatch)
    wrong = _commit(client, seeded.ids["journey"], seeded.ids["plan_foreign"], seeded.ids["owner"],
                    idempotency_key=_key())
    assert wrong.status_code == 404, wrong.text
    assert wrong.json()["error"]["reason_code"] == departure_commit.REASON_PLAN_NOT_IN_JOURNEY
    assert _status_of(seeded, seeded.ids["plan_foreign"]) == "CANDIDATE"
    mine = _commit(client, seeded.ids["journey"], seeded.ids["plan_committable"],
                   seeded.ids["owner"], idempotency_key=_key())
    assert mine.status_code == 200, mine.text


# ------------------------------------------------------------------ the two properties select lacks
def test_a_commit_without_an_idempotency_key_is_refused_by_name_and_writes_nothing(seeded,
                                                                                   monkeypatch):
    client = _app(seeded, monkeypatch)
    refused = _commit(client, seeded.ids["journey"], seeded.ids["plan_committable"],
                      seeded.ids["owner"], idempotency_key=None)
    assert refused.status_code == 422, refused.text
    body = refused.json()["error"]
    assert body["reason_code"] == departure_commit.REASON_KEY_REQUIRED
    assert body["details"]["header"] == "Idempotency-Key"
    assert body["details"]["rows_protected"] is True
    assert _status_of(seeded, seeded.ids["plan_committable"]) == "CANDIDATE"
    assert _rows(seeded, AuditLog, action=departure_commit.COMMIT_ACTION) == []


def test_a_body_that_names_anything_but_the_plan_is_refused_by_name(seeded, monkeypatch):
    """The 13:42 order: no invented place text and no client-supplied URL through this door."""
    client = _app(seeded, monkeypatch)
    refused = _commit(client, seeded.ids["journey"], seeded.ids["plan_committable"],
                      seeded.ids["owner"], idempotency_key=_key(),
                      body={"plan_version_id": seeded.ids["plan_committable"],
                            "place_name": "冠豸山", "image_url": "https://example.test/a.jpg"})
    assert refused.status_code == 422, refused.text
    body = refused.json()["error"]
    assert body["reason_code"] == departure_commit.REASON_BODY_FIELDS
    assert body["details"]["refused_fields"] == ["image_url", "place_name"], body["details"]
    assert _status_of(seeded, seeded.ids["plan_committable"]) == "CANDIDATE"


def test_a_replayed_key_answers_the_stored_receipt_and_writes_no_second_decision(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    key = _key()
    first = _commit(client, seeded.ids["journey"], seeded.ids["plan_committable"],
                    seeded.ids["owner"], idempotency_key=key)
    assert first.status_code == 200, first.text
    assert first.json().get("idempotency_replay") is None
    again = _commit(client, seeded.ids["journey"], seeded.ids["plan_committable"],
                    seeded.ids["owner"], idempotency_key=key)
    assert again.status_code == 200, again.text
    assert again.json() == {**first.json(), "idempotency_replay": True}, again.json()
    assert again.headers["cache-control"] == "private, no-store"
    assert len(_rows(seeded, AuditLog, action=departure_commit.COMMIT_ACTION)) == 1
    assert len(_rows(seeded, AuditLog, action="plan.selected")) == 1


def test_the_same_key_for_a_different_plan_version_is_a_named_conflict(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    key = _key()
    assert _commit(client, seeded.ids["journey"], seeded.ids["plan_committable"],
                   seeded.ids["owner"], idempotency_key=key).status_code == 200
    refused = _commit(client, seeded.ids["journey"], seeded.ids["plan_infeasible"],
                      seeded.ids["owner"], idempotency_key=key)
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["reason_code"] == departure_commit.REASON_KEY_CONFLICT
    assert _status_of(seeded, seeded.ids["plan_committable"]) == "SELECTED"


# ------------------------------------------------------------------ what it actually does
def test_the_commit_moves_the_same_rows_the_select_door_moves_and_says_who_did_it(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    answer = _commit(client, seeded.ids["journey"], seeded.ids["plan_committable"],
                     seeded.ids["member"], idempotency_key=_key())
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["plan_version_id"] == seeded.ids["plan_committable"]
    assert body["committed_by"] == seeded.ids["member"]
    assert body["seat"]["seat_kind"] == departure_read.SEAT_MEMBER
    assert body["seat"]["member_state"] == "MEMBER_IN_FORCE"
    assert body["journey"]["active_plan_version_id"] == seeded.ids["plan_committable"]
    assert _status_of(seeded, seeded.ids["plan_committable"]) == "SELECTED"
    with seeded.factory() as session:
        journey = session.get(Journey, seeded.ids["journey"])
        assert journey.status == "PLANNED" and journey.active_plan_version_id == body["plan_version_id"]
    events = _rows(seeded, AuditLog, action=departure_commit.COMMIT_ACTION)
    assert len(events) == 1 and events[0].actor_type == "traveler"
    assert events[0].actor_id == seeded.ids["member"] and events[0].journey_id == journey.id


def test_after_a_commit_the_read_door_answers_ready_to_depart(seeded, monkeypatch):
    """The two doors are one flow: what the write door changed is what the read door then says."""
    client = _app(seeded, monkeypatch)
    before = client.get(DEPARTURE.format(seeded.ids["journey"]), headers=_header(seeded.ids["owner"]))
    assert before.json()["gate"] == departure_read.GATE_NO_PLAN, before.json()
    assert before.json()["next_action"]["kind"] == "generate_plans"
    committed = _commit(client, seeded.ids["journey"], seeded.ids["plan_committable"],
                        seeded.ids["owner"], idempotency_key=_key())
    assert committed.status_code == 200, committed.text
    after = client.get(DEPARTURE.format(seeded.ids["journey"]), headers=_header(seeded.ids["owner"]))
    assert after.json()["gate"] == departure_read.GATE_READY, after.json()
    assert after.json()["next_action"]["door"] == f"/api/v1/journeys/{seeded.ids['journey']}/start"
    assert after.json()["selected_plan"]["plan_version_id"] == seeded.ids["plan_committable"]


def test_the_commit_door_gives_selects_own_stale_word_for_the_same_row(seeded, monkeypatch):
    """Measured, not asserted in prose: the transition's sentence arrives unedited, plus a code."""
    from app import main as main_module

    with seeded.factory() as session:
        try:
            main_module.select_plan(uuid.UUID(seeded.ids["journey"]),
                                   uuid.UUID(seeded.ids["plan_unfrozen"]), session)
            raise AssertionError("select was expected to refuse the unfrozen candidate")
        except StarletteHTTPException as direct:
            expected = str(direct.detail)
        session.rollback()
    client = _app(seeded, monkeypatch)
    refused = _commit(client, seeded.ids["journey"], seeded.ids["plan_unfrozen"],
                      seeded.ids["owner"], idempotency_key=_key())
    assert refused.status_code == 409, refused.text
    body = refused.json()["error"]
    assert body["message"] == expected, (body["message"], expected)
    assert body["reason_code"] == departure_read.GATE_STALE_EVIDENCE
    assert body["details"]["gate"] == departure_read.GATE_STALE_EVIDENCE


def test_a_plan_the_gate_refuses_arrives_as_a_named_infeasible_refusal_not_a_crash(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    refused = _commit(client, seeded.ids["journey"], seeded.ids["plan_infeasible"],
                      seeded.ids["owner"], idempotency_key=_key())
    assert refused.status_code == 422, refused.text
    body = refused.json()["error"]
    assert body["reason_code"] == "PLAN_INFEASIBLE"
    assert "is infeasible" in body["message"] and "LOCATION_MISSING" in body["message"], body
    assert _status_of(seeded, seeded.ids["plan_infeasible"]) == "CANDIDATE"
    assert _rows(seeded, AuditLog, action=departure_commit.COMMIT_ACTION) == []
    assert _rows(seeded, IdempotencyKey) == []


def test_a_refused_commit_keeps_no_receipt_so_a_fixed_retry_can_use_a_new_key(seeded, monkeypatch):
    """The refusal is not allowed to consume the key: the traveller's next real attempt must work."""
    client = _app(seeded, monkeypatch)
    key = _key()
    refused = _commit(client, seeded.ids["journey"], seeded.ids["plan_unfrozen"],
                      seeded.ids["owner"], idempotency_key=key)
    assert refused.status_code == 409, refused.text
    assert _rows(seeded, IdempotencyKey, operation=departure_commit.COMMIT_OPERATION) == []
    again = _commit(client, seeded.ids["journey"], seeded.ids["plan_unfrozen"],
                    seeded.ids["owner"], idempotency_key=key)
    assert again.status_code == 409, again.text
    ok = _commit(client, seeded.ids["journey"], seeded.ids["plan_committable"],
                 seeded.ids["owner"], idempotency_key=key)
    assert ok.status_code == 200, ok.text


def test_the_door_is_a_plain_route_on_the_real_app_so_the_contract_can_walk_it(seeded, monkeypatch):
    """This app's own contract test reads route.path off app.routes; an include_router wrapper hides it."""
    from app import main as main_module

    paths = {route.path for route in main_module.app.routes}
    assert departure_commit.COMMIT_PATH in paths, sorted(p for p in paths if "departure" in p)
    assert departure_read.DEPARTURE_PATH in paths


def test_no_new_plan_source_vocabulary_is_invented_by_this_door(seeded, monkeypatch):
    """The shipped DDL closes `source` to INITIAL / REPLAN / MANUAL; a commit must not add a fourth."""
    allowed = {"INITIAL", "REPLAN", "MANUAL"}
    client = _app(seeded, monkeypatch)
    assert _commit(client, seeded.ids["journey"], seeded.ids["plan_committable"],
                   seeded.ids["owner"], idempotency_key=_key()).status_code == 200
    for row in _rows(seeded, PlanVersion):
        assert row.source in allowed, (row.id, row.source)
    committed = _rows(seeded, PlanVersion, id=seeded.ids["plan_committable"])[0]
    assert committed.source == "INITIAL" and committed.status == "SELECTED"
