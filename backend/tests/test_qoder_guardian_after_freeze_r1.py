"""What the Guardian says about a plan the traveller hand-built, once that plan can be judged.

Before `POST .../mobility-freeze` existed, a hand-built candidate could never become the journey's active
plan: the shipped `select` gate raises `STALE_RECOMPOSE_REQUIRED` for a version carrying no frozen mobility
evidence, so `app.live_context_watch.run_live_context_watch` -- which reads the activities of
`journeys.active_plan_version_id` and nothing else -- had no way to ever see a traveller's own slots. This
file is the other half of that delivery: the watcher's honest words, over a plan this branch's own doors
committed.

Real here: the rows, the statuses, the persisted `web_observations`, the created `events` and their
payloads, the decision words, and the fact that a repeated poll does not multiply an incident. Replaced:
only `acquire_place_facts`, the provider edge -- with a receipt built from this run's own `places` rows and
their exact `external_id`, which is the binding the watcher requires. Naming that boundary matters: these
cells pin the watcher's judgement and its persistence, not a provider's freshness, and the offline reach
of the real edge is what `_live_evidence_1020eo.txt` reports.

`classroom_mode()` is pinned off, because that seam turns an absence into a labelled estimate and these
cells are about the absence.
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

from app import (
    departure_commit,
    live_context_watch,
    plan_evidence,
    plan_submission,
    traveler_principal,
)
from app.core.config import settings
from app.db.models import (
    Activity,
    Base,
    Event,
    Journey,
    JourneyMember,
    Place,
    PlanVersion,
    Traveler,
    WebObservation,
)
from app.db.session import get_session

SECRET = uuid.uuid4().hex + uuid.uuid4().hex  # generated, never printed, never committed
CITY = "350825"
FREEZE = "/api/v1/journeys/{journey_id}/plans/{plan_version_id}/mobility-freeze"
SUBMIT = "/api/v1/journeys/{journey_id}/plans/{plan_version_id}/submission"
COMMIT = "/api/v1/journeys/{journey_id}/departure/commit"
# The words the watcher's own predicate accepts as a qualified opening fact.
VALID_OPENING = {"status": "NORMALIZED_VALID",
                 "intervals": [{"open": "00:00", "close": "23:59"}]}
CLOSED = {"status": "CLOSED"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _then(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


@pytest.fixture(autouse=True)
def _signing_secret(monkeypatch):
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))


@pytest.fixture(autouse=True)
def _offline_capture(monkeypatch):
    """The evidence this chain freezes comes from the server's own deterministic fixture provider."""
    from app.integrations.mobility import runtime as mobility_runtime

    monkeypatch.setattr(mobility_runtime, "settings", replace(settings, live_valhalla_url=None))
    monkeypatch.setattr(mobility_runtime, "routes_via_amap", lambda city_code: False)


@pytest.fixture(autouse=True)
def _classroom_off(monkeypatch):
    monkeypatch.setattr(live_context_watch, "classroom_mode", lambda: False)


def _place(session, *, name: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Place(id=ident, provider_key="overpass", external_id="overpass:node-" + ident[:8],
                      city_code=CITY, name=name, category="SIGHTSEE",
                      latitude=25.7, longitude=116.75,
                      opening_hours_json=json.dumps(VALID_OPENING),
                      tags_json="[]", metadata_json="{}", updated_at=_now()))
    return ident


def _activity(session, plan_id: str, sequence_no: int, place_id: str, *, start: int) -> str:
    ident = str(uuid.uuid4())
    session.add(Activity(id=ident, plan_version_id=plan_id, sequence_no=sequence_no,
                         activity_type="SIGHTSEE", title="slot", place_id=place_id,
                         city_service_id=None, start_at=_then(start), end_at=_then(start + 45),
                         travel_from_prev_min=10, estimated_cost_minor=3000, currency="CNY",
                         status="PLANNED", locked=False, metadata_json="{}",
                         created_at=_now(), updated_at=_now()))
    return ident


@pytest.fixture()
def seeded():
    """A journey on an ACTIVE base, plus one hand-built CANDIDATE with two slots at one venue."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ids: dict[str, str] = {}
    with factory() as session:
        ids["owner"] = str(uuid.uuid4())
        session.add(Traveler(id=ids["owner"], display_name="组织者", email=None, locale="zh-CN",
                             timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
        ids["journey"] = str(uuid.uuid4())
        ids["base"] = str(uuid.uuid4())
        ids["candidate"] = str(uuid.uuid4())
        session.add(PlanVersion(id=ids["base"], journey_id=ids["journey"], version_no=1,
                                planning_mode="balanced", status="ACTIVE", source="INITIAL",
                                total_cost_minor=3000, currency="CNY",
                                estimated_duration_min=45, created_at=_now()))
        session.add(PlanVersion(id=ids["candidate"], journey_id=ids["journey"], version_no=2,
                                planning_mode="balanced", status="CANDIDATE", source="MANUAL",
                                total_cost_minor=6000, currency="CNY",
                                estimated_duration_min=90, created_at=_now()))
        session.add(Journey(id=ids["journey"], traveler_id=ids["owner"], title="连城",
                            city_code=CITY, timezone="Asia/Shanghai", start_at=_then(30),
                            end_at=_then(60 * 48), budget_currency="CNY",
                            budget_amount_minor=500_00, status="DRAFT",
                            active_plan_version_id=ids["base"], created_at=_now(),
                            updated_at=_now()))
        session.add(JourneyMember(id=str(uuid.uuid4()), journey_id=ids["journey"],
                                  traveler_id=ids["owner"], role="OWNER", invited_by="self",
                                  created_at=_now(), updated_at=_now(), joined_at=_now(),
                                  expires_at=None, removed_at=None))
        ids["venue_a"] = _place(session, name="冠豸山")
        ids["venue_b"] = _place(session, name="天一塔")
        _activity(session, ids["base"], 1, ids["venue_a"], start=60)
        _activity(session, ids["candidate"], 1, ids["venue_a"], start=60)
        _activity(session, ids["candidate"], 2, ids["venue_b"], start=150)
        session.commit()
        ids["entities"] = sorted(str(session.get(Place, ids[key]).external_id)
                                 for key in ("venue_a", "venue_b"))
    return SimpleNamespace(engine=engine, factory=factory, ids=ids)


def _client(seeded):
    from app import main as main_module

    app = FastAPI()
    for route in (*plan_evidence.router.routes, *plan_submission.router.routes,
                  *departure_commit.router.routes):
        app.add_api_route(route.path, route.endpoint, methods=sorted(route.methods),
                          name=route.name, status_code=route.status_code)
    app.add_exception_handler(StarletteHTTPException, main_module.http_error)

    def override_session():
        with seeded.factory() as inner:
            yield inner

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _press(seeded, url, *, key, body=None):
    token = traveler_principal.issue_traveler_token(seeded.ids["owner"])
    return _client(seeded).post(
        url.format(journey_id=seeded.ids["journey"], plan_version_id=seeded.ids["candidate"]),
        json={} if body is None else body,
        headers={"Idempotency-Key": key, "Authorization": "Bearer " + token})


def _receipt_for(seeded, *, include: bool, hours: dict = VALID_OPENING):
    """Stand in for the provider edge with this run's own rows, matched by their exact entity."""
    def acquire(session, journey, *, place_ids=None, **_kwargs):
        rows = []
        for place_id in place_ids or []:
            if not include:
                continue
            place = session.get(Place, place_id)
            rows.append({
                "place_id": place_id,
                "provider_entity": place.external_id,
                "opening_hours": hours,
                "identity_evidence": {"provider_key": place.provider_key},
                "cost_evidence": {"status": "UNKNOWN"},
                "source_binding": {"source_url": "https://overpass-api.de/api/interpreter",
                                   "source_class": "PROVIDER_TAGS"},
            })
        return {"places": rows, "degraded_providers": []}

    return acquire


def _commit_the_hand_built_plan(seeded):
    assert _press(seeded, FREEZE, key="freeze-1").status_code == 200
    committed = _press(seeded, COMMIT, key="commit-1",
                       body={"plan_version_id": seeded.ids["candidate"]})
    assert committed.status_code == 200, committed.text


def _watch(seeded, monkeypatch, *, include=True, hours=VALID_OPENING):
    monkeypatch.setattr(live_context_watch, "acquire_place_facts",
                        _receipt_for(seeded, include=include, hours=hours))
    with seeded.factory() as session:
        answer = live_context_watch.run_live_context_watch(
            session, session.get(Journey, seeded.ids["journey"]))
        session.commit()
    return answer


def test_a_hand_built_plan_can_be_committed_and_then_read_by_the_watcher(seeded, monkeypatch):
    ids = seeded.ids
    _commit_the_hand_built_plan(seeded)
    with seeded.factory() as session:
        journey = session.get(Journey, ids["journey"])
        plan = session.get(PlanVersion, ids["candidate"])
        assert journey.active_plan_version_id == ids["candidate"], vars(journey)
        assert plan.status == "SELECTED", vars(plan)
        assert journey.status in {"PLANNED", "ACTIVE"}, vars(journey)
    answer = _watch(seeded, monkeypatch)
    assert answer["status"] == "NO_MATERIAL_CHANGE", answer
    assert len(answer["checked_activities"]) == 2, answer["checked_activities"]
    assert answer["material_conflicts"] == [] and answer["unknown_or_degraded"] == [], answer
    assert answer["mutation_count"] == 0 and answer["agent_started"] is False, answer


def test_each_observation_the_watcher_keeps_names_its_source_and_its_moment(seeded, monkeypatch):
    """V3's "sourced, timestamped observation" pinned as rows, not as prose."""
    ids = seeded.ids
    _commit_the_hand_built_plan(seeded)
    answer = _watch(seeded, monkeypatch)
    assert {item["status"] for item in answer["classifications"]} == {"OPEN_COMPATIBLE"}, (
        answer["classifications"])
    with seeded.factory() as session:
        rows = session.scalars(select(WebObservation).order_by(WebObservation.id)).all()
    assert len(rows) == 2, "two venues on one poll: one observation each, no more"
    assert sorted(json.loads(row.content_excerpt)["provider_entity"] for row in rows) == (
        seeded.ids["entities"]), [row.content_excerpt[:60] for row in rows]
    row = rows[0]
    assert row.journey_id == ids["journey"] and row.provider_key == "truth-mesh", vars(row)
    assert row.source_class == "PROVIDER_TAGS", vars(row)
    assert row.authority_status == "NON_AUTHORITATIVE", "a kept observation is not a verdict"
    assert row.captured_at and row.evidence_fingerprint, vars(row)
    excerpt = json.loads(row.content_excerpt)
    assert excerpt["provider_entity"] in seeded.ids["entities"], excerpt
    assert excerpt["opening_hours"]["status"] == "NORMALIZED_VALID", excerpt
    assert len({item["observation_id"] for item in answer["classifications"]}) == 2, (
        answer["classifications"])
    with seeded.factory() as session:
        assert session.scalars(select(Event)).all() == [], "a compatible venue opens nothing"


def test_a_genuine_absence_stays_an_absence_and_opens_no_incident(seeded, monkeypatch):
    answer = _watch(seeded, monkeypatch)  # commit first
    assert answer["status"] == "NO_MATERIAL_CHANGE", answer
    _commit_the_hand_built_plan(seeded)
    missing = _watch(seeded, monkeypatch, include=False)
    assert missing["status"] == "UNKNOWN", missing["status"]
    assert {item["reason_code"] for item in missing["unknown_or_degraded"]} == {
        "EXACT_PLACE_EVIDENCE_MISSING"}, missing["unknown_or_degraded"]
    assert missing["material_conflicts"] == [] and missing["recovery_event_ids"] == []
    assert missing["mutation_count"] == 0 and missing["agent_started"] is False, missing
    with seeded.factory() as session:
        assert session.scalars(select(Event)).all() == [], "an absence is not an incident"


def test_a_venue_that_says_closed_is_the_one_case_that_opens_an_incident(seeded, monkeypatch):
    _commit_the_hand_built_plan(seeded)
    answer = _watch(seeded, monkeypatch, hours=CLOSED)
    assert answer["status"] == "MATERIAL_CONFLICT", answer["status"]
    assert {item["reason_code"] for item in answer["material_conflicts"]} == {
        "EXPLICIT_CLOSED_STATE"}, answer["material_conflicts"]
    with seeded.factory() as session:
        events = session.scalars(select(Event)).all()
    assert len(events) == 2, "two slots, two affected activities: each carries its own incident"
    payloads = [json.loads(row.payload_json) for row in events]
    assert {str(item["affected_activity_id"]) for item in payloads} == {
        str(row.id) for row in _candidate_activities(seeded)}, payloads
    assert all(item["provider_key"] == "truth-mesh" and item["captured_at"] for item in payloads)
    assert all(item["observation_ids"] for item in payloads), "no incident without a source row"


def test_the_same_incident_polled_again_does_not_make_a_second_one(seeded, monkeypatch):
    _commit_the_hand_built_plan(seeded)
    first = _watch(seeded, monkeypatch, hours=CLOSED)
    assert first["status"] == "MATERIAL_CONFLICT", first
    with seeded.factory() as session:
        events = session.scalars(select(Event)).all()
        fingerprints = {json.loads(row.payload_json)["incident_fingerprint"] for row in events}
        ids_before = sorted(row.id for row in events)
        observations_before = len(session.scalars(select(WebObservation)).all())
    again = _watch(seeded, monkeypatch, hours=CLOSED)
    with seeded.factory() as session:
        after = session.scalars(select(Event)).all()
        observations_after = len(session.scalars(select(WebObservation)).all())
    assert sorted(row.id for row in after) == ids_before, "a repeated poll refreshed, not multiplied"
    assert len(fingerprints) == 2 and again["status"] == "MATERIAL_CONFLICT", again
    assert observations_after >= observations_before, "the new moment is still kept"


def test_the_evidence_the_gate_judged_is_still_the_pair_the_committed_plan_carries(seeded):
    """No drift across the chain: what the door froze is what the shipped loader reads back."""
    ids = seeded.ids
    frozen = _press(seeded, FREEZE, key="freeze-1").json()
    assert _press(seeded, SUBMIT, key="submit-1").json()["gate"]["judged"] is True
    assert _press(seeded, COMMIT, key="commit-1",
                  body={"plan_version_id": ids["candidate"]}).status_code == 200
    from app.services import _snapshot_for_plan

    with seeded.factory() as session:
        plan = session.get(PlanVersion, ids["candidate"])
        evidence = json.loads(plan.mobility_evidence_json)
        assert plan.mobility_snapshot_id == frozen["mobility_snapshot_id"] == evidence["snapshot_id"]
        snapshot = _snapshot_for_plan(session, session.get(Journey, ids["journey"]), plan)
    assert snapshot.snapshot_id == frozen["mobility_snapshot_id"], snapshot.snapshot_id
    assert len(snapshot.facts) == frozen["counts"]["legs_frozen"], frozen["counts"]
    assert plan.status == "SELECTED", vars(plan)


def _candidate_activities(seeded):
    with seeded.factory() as session:
        return session.scalars(
            select(Activity).where(Activity.plan_version_id == seeded.ids["candidate"])
            .order_by(Activity.sequence_no)
        ).all()
