"""The slot-level place-fact read: which facts this server holds for the places a plan names.

The V3 order's first item is 地点事实统一, and it names the failure to close: an unknown must be
answered as an unknown, not filled in. So this file is mostly about the `UNKNOWN` arms -- a slot with
no location, a slot pointing at a row this store no longer holds, a row whose opening window is
inverted, a row whose cost evidence declares itself unknown, a row that never recorded hours, a
service that carries no point. Each one has to come back named, and each one has to leave the number
it does not have absent rather than zero.

What is policed here:

* the door runs first: no credentials is the resolver's named refusal, an unknown journey is 404, a
  caller without a seat in force is 403 -- all before an activity row is read, and a foreign
  `plan_version_id` is answered before any slot is counted, so this cannot enumerate a trip;
* one writer per judgement: `app.services._place_window` and `_place_verified_cost` decide whether a
  row "says when it is open" and "says what it costs". One test runs those two predicates over every
  seeded row and compares each answer with the door's, so a change to either predicate must move this
  door or go red there -- the door is not allowed to re-decide quietly;
* nothing is asked of the network: the module's own imports are read out of its syntax tree and no
  HTTP client is allowed among them, and every statement the door runs is checked to be a read;
* a verified place cost and the number a plan row happens to carry are two fields, never merged;
* the fact is worth what its timestamp says: `fact_retrieved_at` is only present when the row records
  it, and licence and author stay behind the media door, whose path this one names.
"""

from __future__ import annotations

import ast
import json
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

from app import departure_facts, departure_read, traveler_principal
from app.core.config import settings
from app.db.models import (
    Activity,
    Base,
    CityService,
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

HOURS = {"open": "09:00", "close": "17:00"}
INVERTED_HOURS = {"open": "17:00", "close": "09:00"}
VERIFIED = {"cost_evidence": {"status": "VERIFIED_PROVIDER", "amount_minor": 6000,
                              "currency": "CNY", "retrieved_at": "2026-10-18T02:03:04+00:00"}}
DECLARED_UNKNOWN = {"cost_evidence": {"status": "UNKNOWN", "amount_minor": None,
                                      "currency": "CNY"}}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _then(offset_minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)).isoformat()


def _traveler(session, key: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Traveler(id=ident, display_name=key, email=None, locale="zh-CN",
                         timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
    return ident


def _journey(session, owner_id: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Journey(id=ident, traveler_id=owner_id, title="连城", city_code=CITY,
                        timezone="Asia/Shanghai", start_at=_then(60), end_at=_then(60 * 24),
                        budget_currency="CNY", budget_amount_minor=500_00, status="PLANNED",
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


def _place(session, *, name: str, hours: dict | None, metadata: dict | None,
           point: tuple[float, float] | None = None, provider: str = "amap") -> str:
    ident = str(uuid.uuid4())
    session.add(Place(id=ident, provider_key=provider, external_id="x-" + ident[:8],
                      city_code=CITY, name=name, category="SIGHTSEE",
                      latitude=None if point is None else point[0],
                      longitude=None if point is None else point[1],
                      opening_hours_json=json.dumps(hours or {}), tags_json="[]",
                      metadata_json=json.dumps(metadata or {}), updated_at=_now()))
    return ident


def _service(session, *, name: str, availability: dict) -> str:
    ident = str(uuid.uuid4())
    session.add(CityService(id=ident, provider_key="official_web", external_id="svc-" + ident[:8],
                            place_id=None, city_code=CITY, service_type="TICKET", name=name,
                            availability_json=json.dumps(availability), metadata_json="{}",
                            updated_at=_now()))
    return ident


def _plan(session, journey_id: str) -> str:
    ident = str(uuid.uuid4())
    session.add(PlanVersion(id=ident, journey_id=journey_id, version_no=1,
                            planning_mode="BALANCED", status="CANDIDATE", source="INITIAL",
                            total_cost_minor=0, currency="CNY", estimated_duration_min=240,
                            created_at=_now()))
    return ident


def _activity(session, plan_id: str, sequence_no: int, *, place_id: str | None = None,
              service_id: str | None = None, estimate_minor: int = 0, title: str = "冠豸山") -> str:
    ident = str(uuid.uuid4())
    session.add(Activity(id=ident, plan_version_id=plan_id, sequence_no=sequence_no,
                         activity_type="SIGHTSEE", title=title, place_id=place_id,
                         city_service_id=service_id, start_at=_then(60), end_at=_then(120),
                         travel_from_prev_min=0, estimated_cost_minor=estimate_minor,
                         currency="CNY", status="PENDING", locked=False, metadata_json="{}",
                         created_at=_now(), updated_at=_now()))
    return ident


#: Slot number -> the row it points at, and the shape of absence it carries.
SLOTS = {
    1: "place_verified",       # says when, says what it costs, has a point
    2: "place_no_evidence",    # says when, has no cost_evidence object at all
    3: "place_inverted",       # hands an unusable window, has a verified cost, no point
    4: "place_no_hours",       # never recorded an open/close, cost evidence says UNKNOWN
    5: None,                   # the city-service row, which carries no point
    6: None,                   # a slot that points at nothing
}


@pytest.fixture()
def seeded():
    """One journey, three seats, and one plan whose six slots cover every shape of missing fact."""
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
        _member(session, ids["journey"], ids["member"], expires_offset_minutes=120)
        _member(session, ids["journey"], ids["lapsed"], expires_offset_minutes=-1)

        ids["place_verified"] = _place(session, name="冠豸山", hours=HOURS, metadata=VERIFIED,
                                       point=(25.7, 116.75))
        ids["place_no_evidence"] = _place(session, name="天一塔", hours=HOURS, metadata={},
                                          point=(25.71, 116.76))
        ids["place_inverted"] = _place(session, name="石门水库", hours=INVERTED_HOURS,
                                       metadata=VERIFIED, point=None)
        ids["place_no_hours"] = _place(session, name="龙王滩", hours=None, metadata=DECLARED_UNKNOWN,
                                       point=(25.72, 116.77))
        ids["service"] = _service(session, name="景区班车", availability={"note": "on demand"})
        ids["plan"] = _plan(session, ids["journey"])
        ids["foreign_plan"] = _plan(session, ids["other_journey"])
        _activity(session, ids["plan"], 1, place_id=ids["place_verified"], estimate_minor=6000)
        _activity(session, ids["plan"], 2, place_id=ids["place_no_evidence"], estimate_minor=0)
        _activity(session, ids["plan"], 3, place_id=ids["place_inverted"], estimate_minor=1200)
        _activity(session, ids["plan"], 4, place_id=ids["place_no_hours"], estimate_minor=800)
        _activity(session, ids["plan"], 5, service_id=ids["service"], estimate_minor=300)
        _activity(session, ids["plan"], 6, title="自由安排", estimate_minor=0)
        # A slot naming a row this store no longer holds, so `UNKNOWN` cannot be read as `not asked`.
        _activity(session, ids["foreign_plan"], 1, place_id="deleted-place", title="删除的地点")
        session.commit()
    return SimpleNamespace(engine=engine, factory=factory, ids=ids)


def _app(seeded, monkeypatch):
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))
    from app import main as main_module

    app = FastAPI()
    app.include_router(departure_read.router)
    app.include_router(departure_facts.router)
    app.add_exception_handler(StarletteHTTPException, main_module.http_error)

    def override_session():
        with seeded.factory() as inner:
            yield inner

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _header(traveler_id: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(traveler_id)}


FACTS = "/api/v1/journeys/{}/departure/facts"


def _read(client, journey_id, plan_id, traveler_id):
    return client.get(FACTS.format(journey_id), params={"plan_version_id": plan_id},
                      headers=_header(traveler_id))


def _slot(answer: dict, sequence_no: int) -> dict:
    return next(item for item in answer["slots"] if item["sequence_no"] == sequence_no)


def _answer(seeded, monkeypatch, sequence_no: int) -> dict:
    client = _app(seeded, monkeypatch)
    got = _read(client, seeded.ids["journey"], seeded.ids["plan"], seeded.ids["owner"])
    assert got.status_code == 200, got.text
    return _slot(got.json(), sequence_no)


# ------------------------------------------------------------------ the door runs first
def test_no_credentials_is_the_resolvers_own_named_401_and_no_slot_is_read(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    refused = client.get(FACTS.format(seeded.ids["journey"]),
                         params={"plan_version_id": seeded.ids["plan"]})
    assert refused.status_code == 401, refused.text
    assert refused.json()["error"]["reason_code"] == traveler_principal.REASON_CREDENTIALS_MISSING
    assert "slots" not in refused.json()


def test_a_stranger_and_a_lapsed_member_get_the_same_words_the_read_door_uses(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    read_path = departure_read.DEPARTURE_PATH.format(journey_id=seeded.ids["journey"])
    for who_name in ("stranger", "lapsed"):
        who = seeded.ids[who_name]
        facts = _read(client, seeded.ids["journey"], seeded.ids["plan"], who)
        read = client.get(read_path, headers=_header(who))
        assert facts.status_code == read.status_code == 403, (facts.text, read.text)
        assert facts.json()["error"]["reason_code"] == read.json()["error"]["reason_code"]
        assert facts.json()["error"]["details"]["seat"]["in_force"] is False
        assert "slots" not in facts.json()


def test_an_unknown_journey_is_404_with_the_owners_token_and_no_slot_is_counted(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    refused = client.get(FACTS.format(str(uuid.uuid4())), params={"plan_version_id": "x"},
                         headers=_header(seeded.ids["owner"]))
    assert refused.status_code == 404, refused.text
    assert "slots" not in refused.json()


def test_a_plan_of_another_journey_is_answered_before_any_slot_is_counted(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    refused = _read(client, seeded.ids["journey"], seeded.ids["foreign_plan"], seeded.ids["owner"])
    assert refused.status_code == 404, refused.text
    assert refused.json()["error"]["reason_code"] == departure_facts.REASON_PLAN_NOT_IN_JOURNEY
    assert "slots" not in refused.json()


def test_a_missing_plan_version_is_refused_by_name(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    refused = client.get(FACTS.format(seeded.ids["journey"]), headers=_header(seeded.ids["owner"]))
    assert refused.status_code == 422, refused.text
    assert refused.json()["error"]["reason_code"] == departure_facts.REASON_PLAN_REQUIRED


# ------------------------------------------------------------------ unknowns, each named
def test_a_slot_that_names_no_location_is_unknown_and_not_zero(seeded, monkeypatch):
    free = _answer(seeded, monkeypatch, 6)
    assert free["location_kind"] == "NONE"
    assert free["identity"]["canonical_id"] is None
    assert free["identity"]["detail"] == departure_facts.REASON_SLOT_HAS_NO_LOCATION
    for fact in ("opening_hours", "cost"):
        assert free[fact]["state"] == departure_facts.STATE_UNKNOWN, fact
    # A point has its own shipped pair of words, READY / UNAVAILABLE; nothing to plot is UNAVAILABLE.
    assert free["coordinate"]["state"] == departure_facts.COORD_UNAVAILABLE
    assert free["coordinate"]["reason"] == departure_facts.REASON_SLOT_HAS_NO_LOCATION
    assert free["cost"]["verified_amount_minor"] is None
    assert free["cost"]["activity_estimate_minor"] == 0
    assert free["media_door"] is None
    assert free["fact_retrieved_at"] is None


def test_a_slot_naming_a_row_this_store_does_not_hold_says_so(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    # The other journey belongs to the stranger; the owner of this one cannot buy a look at it.
    refused = _read(client, seeded.ids["other_journey"], seeded.ids["foreign_plan"],
                    seeded.ids["owner"])
    assert refused.status_code == 403, refused.text
    answer = _read(client, seeded.ids["other_journey"], seeded.ids["foreign_plan"],
                   seeded.ids["stranger"])
    assert answer.status_code == 200, answer.text
    gone = _slot(answer.json(), 1)
    assert gone["identity"]["detail"] == departure_facts.REASON_NO_ROW
    assert gone["identity"]["source_identity"] is None
    assert gone["opening_hours"]["state"] == departure_facts.STATE_UNKNOWN
    assert gone["coordinate"]["reason"] == departure_facts.REASON_NO_ROW
    assert gone["cost"]["detail"] == departure_facts.REASON_NO_ROW
    assert gone["cost"]["verified_amount_minor"] is None
    assert gone["cost"]["activity_estimate_minor"] == 0


def test_an_inverted_window_and_a_missing_point_are_two_separate_answers(seeded, monkeypatch):
    bad = _answer(seeded, monkeypatch, 3)
    assert bad["opening_hours"]["state"] == departure_facts.STATE_UNKNOWN
    assert bad["opening_hours"]["detail"] == departure_facts.REASON_WINDOW_NOT_AN_INTERVAL
    assert bad["coordinate"]["state"] == departure_facts.COORD_UNAVAILABLE
    assert bad["coordinate"]["reason"] == departure_facts.REASON_PLACE_HAS_NO_POINT
    # A place can carry a verified cost and still not be plottable: the two answers stay apart.
    assert bad["cost"]["state"] == departure_facts.STATE_KNOWN
    assert bad["cost"]["verified_amount_minor"] == 6000
    assert bad["fact_retrieved_at"] == VERIFIED["cost_evidence"]["retrieved_at"]


def test_a_row_that_never_recorded_hours_is_named_apart_from_an_unusable_one(seeded, monkeypatch):
    blank = _answer(seeded, monkeypatch, 4)
    assert blank["opening_hours"]["state"] == departure_facts.STATE_UNKNOWN
    assert blank["opening_hours"]["detail"] == departure_facts.REASON_WINDOW_NOT_RECORDED
    # The row does state a cost, and what it states is that it does not know one.
    assert blank["cost"]["state"] == departure_facts.STATE_UNKNOWN
    assert blank["cost"]["detail"] == departure_facts.REASON_COST_NOT_KNOWN
    assert blank["cost"]["verified_amount_minor"] is None
    assert blank["cost"]["activity_estimate_minor"] == 800
    assert blank["fact_retrieved_at"] is None


def test_a_verified_cost_and_a_plans_own_estimate_are_two_fields_not_one(seeded, monkeypatch):
    without = _answer(seeded, monkeypatch, 2)
    assert without["cost"]["state"] == departure_facts.STATE_UNKNOWN
    assert without["cost"]["detail"] == departure_facts.REASON_NO_COST_EVIDENCE
    assert without["cost"]["verified_amount_minor"] is None
    assert without["cost"]["activity_estimate_minor"] == 0
    assert without["opening_hours"]["state"] == departure_facts.STATE_KNOWN
    full = _answer(seeded, monkeypatch, 1)
    assert full["cost"]["verified_amount_minor"] == 6000
    assert full["cost"]["activity_estimate_minor"] == 6000
    assert full["coordinate"] == {"state": departure_facts.COORD_READY, "reason": None,
                                  "coordinate_system": "WGS84"}
    assert full["identity"]["source_identity"] == "amap:" + full["identity"]["external_id"]
    assert full["media_door"] == departure_facts.MEDIA_DOOR.format(
        journey_id=seeded.ids["journey"], place_id=seeded.ids["place_verified"])


def test_a_city_service_slot_keeps_its_identity_and_declares_it_has_no_point(seeded, monkeypatch):
    bus = _answer(seeded, monkeypatch, 5)
    assert bus["location_kind"] == "CITY_SERVICE"
    assert bus["identity"]["provider_key"] == "official_web"
    assert bus["coordinate"]["state"] == departure_facts.COORD_UNAVAILABLE
    assert bus["coordinate"]["reason"] == departure_facts.REASON_SERVICE_HAS_NO_POINT
    assert bus["opening_hours"]["state"] == departure_facts.STATE_UNKNOWN
    assert bus["opening_hours"]["detail"] == departure_facts.REASON_SERVICE_WINDOW_NOT_RECORDED
    assert bus["media_door"] is None, "media belongs to a place, not to a service row"


# ------------------------------------------------------------------ the judgements are borrowed
def test_the_door_reports_what_the_houses_own_predicates_decide(seeded, monkeypatch):
    """Every place slot's two facts must match a direct call of the same two predicates."""
    client = _app(seeded, monkeypatch)
    answer = _read(client, seeded.ids["journey"], seeded.ids["plan"], seeded.ids["owner"]).json()
    by_slot = {item["sequence_no"]: item for item in answer["slots"]}
    compared = 0
    with seeded.factory() as session:
        for sequence_no, place_key in SLOTS.items():
            if place_key is None:
                continue
            row = session.get(Place, seeded.ids[place_key])
            window = _place_window(row)
            verified = _place_verified_cost(row)
            slot = by_slot[sequence_no]
            assert slot["opening_hours"]["state"] == (
                departure_facts.STATE_KNOWN if window is not None
                else departure_facts.STATE_UNKNOWN), sequence_no
            assert (slot["opening_hours"]["open_minutes"],
                    slot["opening_hours"]["close_minutes"]) == (window or (None, None)), sequence_no
            assert slot["cost"]["verified_amount_minor"] == verified, sequence_no
            assert (slot["cost"]["state"] == departure_facts.STATE_KNOWN) == (
                verified is not None), sequence_no
            compared += 1
    assert compared == sum(1 for key in SLOTS.values() if key), (
        f"the pin only ran over place rows: {compared}")


# ------------------------------------------------------------------ a read, and only a read
def test_a_read_runs_only_reads_and_counts_its_own_answers(seeded, monkeypatch):
    spoken: list[str] = []

    def listen(conn, cursor, statement, params, context, many):
        spoken.append(statement)

    event.listen(seeded.engine, "before_cursor_execute", listen)
    try:
        client = _app(seeded, monkeypatch)
        first = _read(client, seeded.ids["journey"], seeded.ids["plan"], seeded.ids["owner"])
        again = _read(client, seeded.ids["journey"], seeded.ids["plan"], seeded.ids["owner"])
    finally:
        event.remove(seeded.engine, "before_cursor_execute", listen)
    assert first.status_code == again.status_code == 200, (first.text, again.text)
    assert spoken, "the listener never saw a statement, so this arm proves nothing"
    kinds = {row.split()[0].upper() for row in spoken}
    assert kinds <= {"SELECT", "BEGIN", "COMMIT", "ROLLBACK", "PRAGMA"}, sorted(kinds)
    body = again.json()
    assert body["slots"] == first.json()["slots"]
    assert len(body["slots"]) == len(SLOTS)
    known = sum(1 for slot in body["slots"] for fact in ("opening_hours", "cost")
                if slot[fact]["state"] == departure_facts.STATE_KNOWN)
    assert body["facts_counted"] == {"known": known,
                                     "unknown": len(body["slots"]) * 2 - known}
    observed = datetime.fromisoformat(body["observed_at"])
    assert observed <= datetime.now(timezone.utc) + timedelta(seconds=5)
    assert again.headers["cache-control"] == "private, no-store"
    with seeded.factory() as session:
        assert session.get(PlanVersion, seeded.ids["plan"]).status == "CANDIDATE"
        assert session.get(Journey, seeded.ids["journey"]).active_plan_version_id is None
        assert len(session.scalars(select(Activity)).all()) == len(SLOTS) + 1


def test_the_door_imports_no_client_that_could_ask_the_network():
    """No HTTP/socket library may be reachable from this module: the answer comes from stored rows."""
    tree = ast.parse(Path(departure_facts.__file__).read_text(encoding="utf-8"))
    roots: set[str] = set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
            modules.add(node.module)
    network = {"http", "https", "httpx", "requests", "aiohttp", "urllib", "urllib2", "socket",
               "ssl", "websocket"}
    assert not sorted(roots & network), sorted(roots & network)
    assert "app.services" in modules, "the two judgements must stay borrowed, not re-implemented"


def test_the_door_is_a_plain_get_route_on_the_real_app(seeded, monkeypatch):
    from app import main as main_module

    doors = [route for route in main_module.app.routes if route.path == departure_facts.FACTS_PATH]
    assert [route.methods for route in doors] == [{"GET"}], doors
    client = _app(seeded, monkeypatch)
    assert client.post(FACTS.format(seeded.ids["journey"]),
                       json={"plan_version_id": seeded.ids["plan"]},
                       headers=_header(seeded.ids["owner"])).status_code == 405
