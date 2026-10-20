"""The draft-to-candidate write door: given slots this server already holds, write a CANDIDATE plan.

The shipped generator re-schedules, so a draft whose days were chosen cannot be turned into a plan
with it without claiming preservation that did not happen. This file is the other half: times and
order are taken from the request and written as they came, the row lands as `CANDIDATE`, and nothing
is selected, activated or fetched.

Policed here, in this order: what a caller may not say (a provider id, a described place, a city that
is not this journey's), what the door must not do (select, activate, ask a network, invent a cost),
and what it must answer instead (the gap by name, judged by the same two predicates the feasibility
gate and the fact read use).
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
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import plan_from_slots, traveler_principal
from app.core.config import settings
from app.db.models import (
    Activity,
    AuditLog,
    Base,
    Journey,
    JourneyMember,
    Place,
    PlanVersion,
    Traveler,
)
from app.db.session import get_session
from app.services import _place_verified_cost, _place_window

SECRET = uuid.uuid4().hex + uuid.uuid4().hex  # generated, never printed, never committed
CITY = "350825"
OTHER_CITY = "350200"

HOURS = {"open": "09:00", "close": "17:00"}
VERIFIED = {"cost_evidence": {"status": "VERIFIED_PROVIDER", "amount_minor": 6000,
                              "currency": "CNY", "retrieved_at": "2026-10-18T02:03:04+00:00"}}

DOOR = "/api/v1/journeys/{}/plans/from-slots"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _then(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def _traveler(session, key: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Traveler(id=ident, display_name=key, email=None, locale="zh-CN",
                         timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
    return ident


def _place(session, *, name: str, city_code: str = CITY, hours: dict | None = None,
           metadata: dict | None = None, point: tuple[float, float] | None = None) -> str:
    ident = str(uuid.uuid4())
    session.add(Place(id=ident, provider_key="amap", external_id="x-" + ident[:8],
                      city_code=city_code, name=name, category="SIGHTSEE",
                      latitude=None if point is None else point[0],
                      longitude=None if point is None else point[1],
                      opening_hours_json=json.dumps(hours or {}), tags_json="[]",
                      metadata_json=json.dumps(metadata or {}), updated_at=_now()))
    return ident


@pytest.fixture()
def seeded():
    """One active journey with one active plan, four places in three shapes, and two seats.

    Rows come from the ORM. The words this door writes are pinned against the shipped DDL in
    `test_the_words_this_door_writes_are_words_the_shipped_ddl_allows`, because `create_all` carries
    none of those CHECKs and a seed that production would refuse has already bitten this family once.
    """
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ids: dict[str, str] = {}
    with factory() as session:
        ids["owner"] = _traveler(session, "组织者")
        ids["member"] = _traveler(session, "小雨")
        ids["stranger"] = _traveler(session, "陌生人")
        ids["journey"] = str(uuid.uuid4())
        ids["base"] = str(uuid.uuid4())
        session.add(PlanVersion(id=ids["base"], journey_id=ids["journey"], version_no=1,
                                planning_mode="balanced", status="ACTIVE", source="INITIAL",
                                total_cost_minor=0, currency="CNY", estimated_duration_min=0,
                                created_at=_now()))
        session.add(Journey(id=ids["journey"], traveler_id=ids["owner"], title="连城",
                            city_code=CITY, timezone="Asia/Shanghai", start_at=_then(60),
                            end_at=_then(60 * 24), budget_currency="CNY",
                            budget_amount_minor=500_00, status="ACTIVE",
                            active_plan_version_id=ids["base"], created_at=_now(),
                            updated_at=_now()))
        session.add(JourneyMember(id=str(uuid.uuid4()), journey_id=ids["journey"],
                                  traveler_id=ids["member"], role="COLLABORATOR",
                                  invited_by="owner-device", created_at=_now(), updated_at=_now(),
                                  joined_at=_now(), expires_at=_then(120), removed_at=None))
        ids["good"] = _place(session, name="冠豸山", hours=HOURS, metadata=VERIFIED,
                             point=(25.7, 116.75))
        ids["no_hours"] = _place(session, name="龙王滩", hours=None, metadata={},
                                 point=(25.72, 116.77))
        ids["no_point"] = _place(session, name="天一塔", hours=HOURS, metadata={}, point=None)
        ids["foreign"] = _place(session, name="鼓浪屿", city_code=OTHER_CITY, hours=HOURS,
                               metadata=VERIFIED, point=(24.4, 118.06))
        session.commit()
    return SimpleNamespace(engine=engine, factory=factory, ids=ids)


def _app(seeded, monkeypatch):
    """Mount the door the way `app.main` does, not the way `include_router` does.

    This is the arm's whole point: a test app built with `include_router` inherits the router's
    `status_code`, so it answered 201 for every spec in this file while a real uvicorn -- where the
    door is mounted through main.py's plain-route loop -- answered 200. Registering the same way the
    app does is what makes `http_status 201` below a claim about the shipped door.
    """
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))
    from app import main as main_module

    app = FastAPI()
    for route in plan_from_slots.router.routes:
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


def _slot(place_id: str, *, start: int = 120, end: int = 180, cost=None) -> dict:
    slot = {"place_id": place_id, "start_at": _then(start), "end_at": _then(end)}
    if cost is not None:
        slot["estimated_cost_minor"] = cost
    return slot


def _press(client, ids, traveler_id, slots, *, key="make-1", revision=None, **extra):
    body = {"slots": slots, "expected_revision": revision if revision is not None
            else ids["base"]}
    body.update(extra)
    return client.post(DOOR.format(ids["journey"]),
                       headers={**_header(traveler_id), "Idempotency-Key": key}, json=body)


def _plans(seeded) -> list[tuple[str, str, str, int]]:
    with seeded.factory() as session:
        return sorted(
            (plan.id, plan.status, plan.source, plan.version_no)
            for plan in session.scalars(select(PlanVersion)).all()
        )


def test_the_slots_arrive_as_a_candidate_with_their_own_times_and_order(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    first_slot = _slot(ids["good"], start=120, end=180, cost=6000)
    second_slot = _slot(ids["no_hours"], start=240, end=300)
    answer = _press(client, ids, ids["owner"], [first_slot, second_slot])
    assert answer.status_code == 201, answer.text
    body = answer.json()
    assert body["status"] == plan_from_slots.PLAN_STATUS_CANDIDATE, body
    assert body["version_no"] == 2, body
    assert body["selected"] is False and body["activated"] is False, body

    # Times and order are the request's, not a new schedule.
    assert [(item["sequence_no"], item["place_id"]) for item in body["slots"]] == [
        (1, ids["good"]), (2, ids["no_hours"])], body["slots"]
    assert body["slots"][0]["start_at"] == first_slot["start_at"], body["slots"][0]
    assert body["slots"][1]["end_at"] == second_slot["end_at"], body["slots"][1]
    with seeded.factory() as session:
        written = list(session.scalars(
            select(Activity).where(Activity.plan_version_id == body["plan_version_id"])
            .order_by(Activity.sequence_no)
        ).all())
    assert [row.sequence_no for row in written] == [1, 2], written
    assert [row.place_id for row in written] == [ids["good"], ids["no_hours"]], written
    assert written[0].title == "冠豸山", written[0].title
    assert written[0].start_at == first_slot["start_at"], written[0].start_at
    assert written[1].end_at == second_slot["end_at"], written[1].end_at
    assert written[0].status == plan_from_slots.ACTIVITY_STATUS_PLANNED
    assert written[1].estimated_cost_minor == 0, written[1].estimated_cost_minor


def test_a_provider_id_is_refused_by_name_and_no_row_is_written(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    before = _plans(seeded)
    refused = _press(client, ids, ids["owner"], [{"place_id": "amap:B00140WBI1",
                                                 "start_at": _then(120), "end_at": _then(180)}])
    assert refused.status_code == 422, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == plan_from_slots.REASON_DELEGATED_SHAPE, error
    assert error["details"]["accepted_shape"] == "canonical Place uuid", error
    # The pointer has to be a door the caller can actually press. Reading it for the word `identity`
    # was green while it named `/places/{place_id}/identity`, a path no router serves: whoever pressed
    # that answer got a 404. So: the exact string this module builds, the refused lead echoed back
    # where a query value can hold it, the old shape named as the negative control, and the path
    # checked against the constant the identity GET is registered with -- read off that router here, so
    # a drift between the two shows up red in this file rather than as a dead link for a traveller.
    pointer = error["details"]["next_action"]
    assert pointer == plan_from_slots.identity_pointer(ids["journey"], "amap:B00140WBI1"), pointer
    assert pointer.endswith("?lead=amap:B00140WBI1"), pointer
    assert "/places/" not in pointer, pointer
    from app import place_media_routes
    pressed_path = place_media_routes.IDENTITY_PATH.format(journey_id=ids["journey"])
    assert pressed_path in pointer, (pressed_path, pointer)
    registered = {getattr(route, "path", "") for route in place_media_routes.router.routes}
    assert place_media_routes.IDENTITY_PATH in registered, sorted(registered)
    assert _plans(seeded) == before, "a refused draft still wrote a plan version"


def test_a_lead_that_cannot_sit_in_a_query_is_not_echoed_into_one(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    refused = _press(client, ids, ids["owner"], [{"place_id": "amap:B001#7",
                                                 "start_at": _then(120), "end_at": _then(180)}])
    assert refused.status_code == 422, refused.text
    pointer = refused.json()["error"]["details"]["next_action"]
    assert "amap:B001#7" not in pointer, pointer
    assert pointer.endswith("?lead= (name the refused id from details; this door will not put it in "
                            "a url)"), pointer


def test_a_uuid_that_is_not_a_row_in_this_store_is_answered_as_missing(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    refused = _press(client, ids, ids["owner"], [_slot(str(uuid.uuid4()))])
    assert refused.status_code == 404, refused.text
    assert refused.json()["error"]["reason_code"] == plan_from_slots.REASON_PLACE_NOT_FOUND


def test_a_same_named_place_two_cities_over_is_refused_rather_than_dropped_in(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    refused = _press(client, ids, ids["owner"], [_slot(ids["foreign"])])
    assert refused.status_code == 409, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == plan_from_slots.REASON_PLACE_OTHER_CITY, error
    assert error["details"]["place_city_code"] == OTHER_CITY, error
    assert error["details"]["journey_city_code"] == CITY, error


def test_a_slot_cannot_describe_a_place_to_the_server(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    slot = _slot(ids["good"])
    slot.update({"title": "我随便写的名字", "url": "https://example.invalid",
                 "external_id": "B00140WBI1"})
    refused = _press(client, ids, ids["owner"], [slot])
    assert refused.status_code == 422, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == plan_from_slots.REASON_SLOT_FIELDS, error
    assert error["details"]["refused_fields"] == ["external_id", "title", "url"], error
    assert error["details"]["descriptive_fields_present"] == ["external_id", "title", "url"], error


def test_the_gaps_are_the_same_two_predicates_the_fact_read_and_the_gate_use(seeded, monkeypatch):
    """One writer per judgement: the door cannot call a row "has hours" where the gate says not."""
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    answer = _press(client, ids, ids["owner"], [
        _slot(ids["good"], cost=6000), _slot(ids["no_hours"]), _slot(ids["no_point"]),
    ])
    assert answer.status_code == 201, answer.text
    body = answer.json()

    with seeded.factory() as session:
        rows = {place_id: session.get(Place, place_id)
                for place_id in (ids["good"], ids["no_hours"], ids["no_point"])}
    by_sequence = {item["sequence_no"]: item for item in body["slots"]}
    for sequence, place_id in ((1, ids["good"]), (2, ids["no_hours"]), (3, ids["no_point"])):
        place = rows[place_id]
        window = _place_window(SimpleNamespace(opening_hours_json=place.opening_hours_json))
        verified = _place_verified_cost(place)
        item = by_sequence[sequence]
        assert item["facts"]["opening_hours_recorded"] == (window is not None), (sequence, item)
        assert item["facts"]["verified_cost_minor"] == verified, (sequence, item)

    assert by_sequence[1]["facts"]["gaps"] == [], by_sequence[1]["facts"]
    assert by_sequence[2]["facts"]["gaps"] == [
        plan_from_slots.GAP_HOURS, plan_from_slots.GAP_COST], by_sequence[2]["facts"]
    assert plan_from_slots.GAP_COORDINATE in by_sequence[3]["facts"]["gaps"], by_sequence[3]
    assert body["counts"] == {
        "slots": 3, "with_coordinate": 2, "hours_recorded": 2, "cost_verified": 1,
        "cost_declared": 1,
    }, body["counts"]
    assert [gap["sequence_no"] for gap in body["gaps"]] == [2, 3], body["gaps"]


def test_an_undeclared_cost_stays_undeclared_rather_than_becoming_a_price(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    body = _press(client, ids, ids["owner"], [_slot(ids["no_hours"])]).json()
    slot = body["slots"][0]
    assert slot["cost_declared"] is False, slot
    assert slot["estimated_cost_minor"] == 0, slot
    assert plan_from_slots.GAP_COST in slot["facts"]["gaps"], slot
    assert body["counts"]["cost_declared"] == 0, body["counts"]
    with seeded.factory() as session:
        written = session.scalars(
            select(Activity).where(Activity.plan_version_id == body["plan_version_id"])).all()
    assert written[0].estimated_cost_minor == 0, written[0]


def test_a_draft_read_against_a_plan_that_moved_is_refused(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    stale = _press(client, ids, ids["owner"], [_slot(ids["good"])],
                   revision=str(uuid.uuid4()), key="stale-1")
    assert stale.status_code == 409, stale.text
    error = stale.json()["error"]
    assert error["reason_code"] == plan_from_slots.REASON_REVISION, error
    assert error["details"]["current_active_plan_version_id"] == ids["base"], error

    missing = client.post(DOOR.format(ids["journey"]),
                          headers={**_header(ids["owner"]), "Idempotency-Key": "no-rev"},
                          json={"slots": [_slot(ids["good"])]})
    assert missing.status_code == 422, missing.text
    assert missing.json()["error"]["reason_code"] == plan_from_slots.REASON_REVISION_MISSING


def test_a_journey_that_has_never_had_a_plan_can_get_its_first_one(seeded, monkeypatch):
    """Issue #42 P0-1: `expected_revision` names the plan in force, or null when there is none.

    The whole body used to be one check: a null was refused for being empty, and any id was refused
    for not matching -- so a journey with no `active_plan_version_id` had no legal request, and the
    seeded store could not show it because every journey in it already had a base. Presence is now
    what is required; the value is what is compared.
    """
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    first = str(uuid.uuid4())
    with seeded.factory() as session:
        session.add(Journey(id=first, traveler_id=ids["owner"], title="广州首趟", city_code=CITY,
                            timezone="Asia/Shanghai", start_at=_then(60), end_at=_then(60 * 24),
                            budget_currency="CNY", budget_amount_minor=500_00, status="DRAFT",
                            active_plan_version_id=None, created_at=_now(), updated_at=_now()))
        session.commit()
    before = _plans(seeded)
    slot = [_slot(ids["good"])]

    pressed = client.post(DOOR.format(first),
                          headers={**_header(ids["owner"]), "Idempotency-Key": "first-1"},
                          json={"slots": slot, "expected_revision": None,
                                "planning_mode": "balanced"})
    assert pressed.status_code == 201, pressed.text
    body = pressed.json()
    assert body["status"] == "CANDIDATE" and body["version_no"] == 1, body
    assert body["draft_revision"] is None, body
    with seeded.factory() as session:
        journey = session.get(Journey, first)
        assert journey.active_plan_version_id is None, "a first draft must not select itself"
    assert _plans(seeded) == sorted(before + [(body["plan_version_id"], "CANDIDATE", "MANUAL", 1)]), \
        _plans(seeded)

    # A replay of the same key and content gives the same row, not a second first plan.
    again = client.post(DOOR.format(first),
                        headers={**_header(ids["owner"]), "Idempotency-Key": "first-1"},
                        json={"slots": slot, "expected_revision": None,
                              "planning_mode": "balanced"})
    assert again.status_code == 201, again.text
    assert again.json()["plan_version_id"] == body["plan_version_id"], again.json()
    assert _plans(seeded) == sorted(before + [(body["plan_version_id"], "CANDIDATE", "MANUAL", 1)]), \
        _plans(seeded)

    # Naming null where a plan *is* in force is the mismatch it always was -- not a way to skip it.
    against_base = client.post(DOOR.format(ids["journey"]),
                               headers={**_header(ids["owner"]), "Idempotency-Key": "null-vs-base"},
                               json={"slots": [_slot(ids["good"])], "expected_revision": None})
    assert against_base.status_code == 409, against_base.text
    refused = against_base.json()["error"]
    assert refused["reason_code"] == plan_from_slots.REASON_REVISION, refused
    assert refused["details"]["expected_revision"] == "", refused
    assert refused["details"]["current_active_plan_version_id"] == ids["base"], refused


def test_one_press_one_plan_version_under_a_retried_key(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    slot = [_slot(ids["good"])]
    first = _press(client, ids, ids["owner"], slot, key="same-key")
    again = _press(client, ids, ids["owner"], slot, key="same-key")
    assert first.status_code == 201, first.text
    assert "idempotency_replay" not in first.json(), first.json()
    assert again.json()["idempotency_replay"] is True, again.json()
    assert again.json()["plan_version_id"] == first.json()["plan_version_id"], again.json()
    assert len(_plans(seeded)) == 2, _plans(seeded)  # the seeded ACTIVE one plus one CANDIDATE

    clash = _press(client, ids, ids["member"], [_slot(ids["no_hours"])], key="same-key")
    assert clash.status_code == 409, clash.text
    assert clash.json()["error"]["reason_code"] == plan_from_slots.REASON_KEY_CONFLICT


def test_the_door_never_selects_and_never_leaves_the_journey_pointing_elsewhere(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    body = _press(client, ids, ids["owner"], [_slot(ids["good"], cost=6000)]).json()
    with seeded.factory() as session:
        journey = session.get(Journey, ids["journey"])
        plans = {plan.id: plan.status for plan in session.scalars(select(PlanVersion)).all()}
        assert journey.active_plan_version_id == ids["base"], journey.active_plan_version_id
    assert plans[body["plan_version_id"]] == "CANDIDATE", plans
    assert plans[ids["base"]] == "ACTIVE", plans
    assert body["next_actions"] == [
        "read GET /api/v1/journeys/{}/departure/facts".format(ids["journey"]),
        "select POST /api/v1/journeys/{}/departure/commit".format(ids["journey"]),
    ], body["next_actions"]


def test_the_write_answers_only_reads_and_its_own_inserts(seeded, monkeypatch):
    """A draft write must not reach a network: every statement is a read, an insert or a commit."""
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    spoken: list[str] = []

    @event.listens_for(seeded.engine, "before_cursor_execute")
    def capture(conn, cursor, statement, parameters, context, executemany):
        del conn, cursor, parameters, context, executemany
        spoken.append(statement.strip().split()[0].upper())

    answer = _press(client, ids, ids["owner"], [_slot(ids["good"])], key="listener-1")
    assert answer.status_code == 201, answer.text
    assert spoken, "the listener never saw a statement"
    assert set(spoken) <= {"SELECT", "INSERT", "BEGIN", "COMMIT", "ROLLBACK", "PRAGMA"}, \
        sorted(set(spoken))
    assert "UPDATE" not in spoken, "a draft write moved a row it should only append"


def test_no_provider_client_is_reachable_from_the_draft_door():
    tree = ast.parse(Path("app/plan_from_slots.py").read_text(encoding="utf-8"),
                     filename="from_slots")
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(str(alias.name).split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(str(node.module).split(".")[0])
            modules.add(str(node.module))
    network = {"http", "httpx", "requests", "aiohttp", "urllib", "socket", "ssl", "urllib3"}
    assert modules.isdisjoint(network), sorted(modules & network)
    assert "app.services" in modules, sorted(modules)
    assert "app.agent" not in {str(node.module) for node in ast.walk(tree)
                               if isinstance(node, ast.ImportFrom)}, "no agent runtime import"


def test_the_words_this_door_writes_are_words_the_shipped_ddl_allows(seeded, monkeypatch):
    ddl = Path("db/schema.sql").read_text(encoding="utf-8")

    def allowed(table: str, column: str) -> list[str]:
        start = ddl.index("CREATE TABLE IF NOT EXISTS " + table + " (")
        block = ddl[start:ddl.index(chr(10) + ");", start)]
        marker = column + " IN ("
        at = block.index(marker) + len(marker)
        listed = block[at:block.index(")", at)]
        words = [item.strip().strip("'") for item in listed.split(",")]
        assert words, (table, column)
        return words

    plan_status = allowed("plan_versions", "status")
    plan_source = allowed("plan_versions", "source")
    planning_modes = allowed("plan_versions", "planning_mode")
    activity_status = allowed("activities", "status")
    assert plan_from_slots.PLAN_STATUS_CANDIDATE in plan_status, plan_status
    assert plan_from_slots.PLAN_SOURCE_MANUAL in plan_source, plan_source
    assert plan_from_slots.ACTIVITY_STATUS_PLANNED in activity_status, activity_status
    assert list(plan_from_slots.PLANNING_MODES) == planning_modes, (
        plan_from_slots.PLANNING_MODES, planning_modes)

    body = _press(_app(seeded, monkeypatch), seeded.ids, seeded.ids["owner"],
                  [_slot(seeded.ids["good"])], key="vocab-1").json()
    with seeded.factory() as session:
        plan = session.get(PlanVersion, body["plan_version_id"])
        activities = session.scalars(
            select(Activity).where(Activity.plan_version_id == plan.id)).all()
    assert plan.status in plan_status and plan.source in plan_source, plan.status
    assert all(row.status in activity_status for row in activities), activities


def test_the_audit_row_names_the_traveller_who_pressed_and_the_revision_they_claimed(
        seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    body = _press(client, ids, ids["member"], [_slot(ids["good"])], key="audit-1").json()
    with seeded.factory() as session:
        rows = list(session.scalars(select(AuditLog).where(
            AuditLog.action == plan_from_slots.FROM_SLOTS_ACTION)).all())
    assert len(rows) == 1, rows
    row = rows[0]
    assert row.actor_type == "traveler" and row.actor_id == ids["member"], row.actor_id
    before = json.loads(row.before_json)
    after = json.loads(row.after_json)
    assert before["expected_revision"] == ids["base"], before
    assert before["active_plan_version_id"] == ids["base"], before
    assert after == {"plan_version_id": body["plan_version_id"], "status": "CANDIDATE",
                     "source": "MANUAL", "version_no": 2, "slots": 1}, after


def test_a_second_draft_takes_the_next_version_number_and_a_third_the_one_after(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    first = _press(client, ids, ids["owner"], [_slot(ids["good"])], key="v-1").json()
    second = _press(client, ids, ids["owner"], [_slot(ids["no_hours"])], key="v-2").json()
    assert (first["version_no"], second["version_no"]) == (2, 3), (first, second)
    with seeded.factory() as session:
        rows = list(session.scalars(select(PlanVersion).where(
            PlanVersion.journey_id == ids["journey"])).all())
    assert sorted(row.version_no for row in rows) == [1, 2, 3], rows
    assert re.match(r"^[0-9a-f-]{36}$", second["plan_version_id"]), second["plan_version_id"]
