"""The difference a candidate actually makes: places on the map, money, minutes, evidence.

The V3 order's third item asks for map/budget delta projection, and the acceptance chain insists a real
miss stays a named miss -- so this file is mostly about the numbers that must NOT be invented: an
unpriced slot is counted, not priced; two currencies produce no delta; a coordinate that never arrived
stays UNAVAILABLE and is counted where it is drawn.

What is policed:

* the two versions are the only inputs, and a version of another journey is answered before a single
  activity row is read, so this cannot enumerate someone else's plan;
* every per-slot judgement is the fact door's: one arm runs `GET .../departure/facts` over the same
  rows and compares the views field by field, so the delta cannot re-decide identity, coordinate,
  window, cost or the media door;
* kept / moved / added / removed are derived by `sequence_no` plus place identity -- the same shape
  `app.collective_mediation` compares two plans with -- and a slot whose place appeared in neither is
  not silently a "move";
* the frozen-evidence block is `departure_read.frozen_evidence_of` verbatim, because that is the door
  which later refuses or accepts the selection;
* the read writes nothing, and no provider client is reachable from the module.
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
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import departure_facts, departure_read, plan_delta, traveler_principal
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
    TravelerTwinSnapshot,
)
from app.db.session import get_session

SECRET = uuid.uuid4().hex + uuid.uuid4().hex  # generated, never printed, never committed
CITY = "350825"
HOURS = {"open": "09:00", "close": "17:00"}
VERIFIED = {"cost_evidence": {"status": "VERIFIED_PROVIDER", "amount_minor": 6000,
                              "currency": "CNY", "retrieved_at": "2026-10-18T02:03:04+00:00"}}

DELTA = "/api/v1/journeys/{}/plans/delta"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _then(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def _traveler(session, key: str) -> str:
    ident = str(uuid.uuid4())
    session.add(Traveler(id=ident, display_name=key, email=None, locale="zh-CN",
                         timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
    return ident


def _place(session, *, name: str, hours: dict | None, metadata: dict | None,
           point: tuple[float, float] | None = None) -> str:
    ident = str(uuid.uuid4())
    session.add(Place(id=ident, provider_key="amap", external_id="x-" + ident[:8],
                      city_code=CITY, name=name, category="SIGHTSEE",
                      latitude=None if point is None else point[0],
                      longitude=None if point is None else point[1],
                      opening_hours_json=json.dumps(hours or {}), tags_json="[]",
                      metadata_json=json.dumps(metadata or {}), updated_at=_now()))
    return ident


def _plan(session, journey_id: str, *, number: int, status: str, minutes: int) -> str:
    ident = str(uuid.uuid4())
    session.add(PlanVersion(id=ident, journey_id=journey_id, version_no=number,
                            planning_mode="balanced", status=status, source="INITIAL",
                            total_cost_minor=0, currency="CNY", estimated_duration_min=minutes,
                            created_at=_now()))
    return ident


def _activity(session, plan_id: str, sequence_no: int, place_id: str | None, *, cost: int,
              start: int, length: int, title: str, currency: str = "CNY") -> str:
    ident = str(uuid.uuid4())
    session.add(Activity(id=ident, plan_version_id=plan_id, sequence_no=sequence_no,
                         activity_type="SIGHTSEE", title=title, place_id=place_id,
                         city_service_id=None, start_at=_then(start), end_at=_then(start + length),
                         travel_from_prev_min=0, estimated_cost_minor=cost, currency=currency,
                         status="PLANNED", locked=False, metadata_json="{}",
                         created_at=_now(), updated_at=_now()))
    return ident


@pytest.fixture()
def seeded():
    """Two versions of one journey: slot 1 kept, slot 2 moved, slot 3 dropped, slot 4 added.

    The numbers this file asserts on are computed here from the same seed tables, not copied from an
    answer, so a wrong sum in the door goes red rather than agreeing with itself.
    """
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
        ids["base"] = _plan(session, ids["journey"], number=1, status="ACTIVE", minutes=1)
        ids["candidate"] = _plan(session, ids["journey"], number=2, status="CANDIDATE", minutes=1)
        ids["foreign_plan"] = _plan(session, ids["other_journey"], number=1, status="CANDIDATE",
                                    minutes=1)
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
        ids["a"] = _place(session, name="冠豸山", hours=HOURS, metadata=VERIFIED,
                          point=(25.7, 116.75))
        ids["b"] = _place(session, name="天一塔", hours=HOURS, metadata={}, point=(25.71, 116.76))
        ids["c"] = _place(session, name="龙王滩", hours=None, metadata={}, point=(25.72, 116.77))
        ids["d"] = _place(session, name="石门水库", hours=None, metadata={}, point=None)
        # base: 1=a, 2=b, 3=c           candidate: 1=a, 2=c, 4=d
        _activity(session, ids["base"], 1, ids["a"], title="冠豸山", cost=6000, start=60, length=45)
        _activity(session, ids["base"], 2, ids["b"], title="天一塔", cost=0, start=120, length=30)
        _activity(session, ids["base"], 3, ids["c"], title="龙王滩", cost=500, start=180, length=30)
        _activity(session, ids["candidate"], 1, ids["a"], title="冠豸山", cost=6000, start=60,
                  length=45)
        _activity(session, ids["candidate"], 2, ids["c"], title="龙王滩", cost=500, start=120,
                  length=40)
        _activity(session, ids["candidate"], 4, ids["d"], title="石门水库", cost=0, start=200,
                  length=20)
        _activity(session, ids["foreign_plan"], 1, ids["a"], title="冠豸山", cost=0, start=60,
                  length=30)
        session.commit()
    totals = {
        "base": 6000 + 0 + 500,
        "candidate": 6000 + 500 + 0,
        "base_minutes": 45 + 30 + 30,
        "candidate_minutes": 45 + 40 + 20,
    }
    return SimpleNamespace(engine=engine, factory=factory, ids=ids, totals=totals)


def _app(seeded, monkeypatch):
    """Mount the doors the way `app.main` does, so a test answers for the shipped app.

    `include_router` would also hide a missing `status_code` on the plain-route loop, which is a
    defect this family already shipped once and had to fix.
    """
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))
    from app import main as main_module

    app = FastAPI()
    for route in (*plan_delta.router.routes, *departure_facts.router.routes):
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


def _delta(client, ids, traveler_id=None, *, src=None, dst=None):
    params = {"from_plan_version_id": src if src is not None else ids["base"],
              "to_plan_version_id": dst if dst is not None else ids["candidate"]}
    return client.get(DELTA.format(ids["journey"]), params=params,
                      headers=_header(traveler_id or ids["owner"]))


def test_the_two_versions_are_reduced_to_kept_moved_added_removed(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    answer = _delta(client, ids)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["counts"] == {
        "from_slots": 3, "to_slots": 3, "kept": 1, "moved": 1, "added": 1, "removed": 1,
    }, body["counts"]
    assert [entry["sequence_no"] for entry in body["sets"]["kept"]] == [1], body["sets"]["kept"]
    assert [entry["sequence_no"] for entry in body["sets"]["moved"]] == [2], body["sets"]["moved"]
    assert [entry["sequence_no"] for entry in body["sets"]["added"]] == [4], body["sets"]["added"]
    assert [entry["sequence_no"] for entry in body["sets"]["removed"]] == [3], \
        body["sets"]["removed"]
    moved = body["sets"]["moved"][0]
    assert moved["from"]["place_id"] == ids["b"] and moved["to"]["place_id"] == ids["c"], moved


def test_the_map_delta_carries_the_points_in_slot_order_on_both_sides(seeded, monkeypatch):
    """One rule for ordering, stated so a map cannot receive a different walk on each read."""
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    body = _delta(client, ids).json()
    added = body["map_delta"]["points_added"]
    removed = body["map_delta"]["points_removed"]
    # Slot 2 moved 天一塔 -> 龙王滩 and slot 4 was added, so both lists run 2 before 3/4 no matter
    # which set contributed a place; the moved pair sits between its neighbours on each side.
    assert [item["sequence_no"] for item in added] == [2, 4], added
    assert [item["sequence_no"] for item in removed] == [2, 3], removed
    assert [item["label"] for item in added] == ["龙王滩", "石门水库"], added
    assert [item["label"] for item in removed] == ["天一塔", "龙王滩"], removed
    assert [item["coordinate"]["state"] for item in added] == [
        departure_facts.COORD_READY, departure_facts.COORD_UNAVAILABLE], added
    assert [item["coordinate"]["state"] for item in removed] == [
        departure_facts.COORD_READY, departure_facts.COORD_READY], removed
    # Only 石门水库 has no point in the seed, and it is the one place this delta adds. The counts are
    # keyed by the fact door's own words, so a state this module did not imagine cannot be folded into
    # "unavailable".
    assert body["map_delta"]["coordinate_states"] == {
        departure_facts.COORD_READY: 3, departure_facts.COORD_UNAVAILABLE: 1}, \
        body["map_delta"]["coordinate_states"]
    for item in added + removed:
        assert item["place_id"] and item["media_door"], item
        assert item["source_identity"] and item["source_identity"].startswith("amap:"), item


def test_budget_and_duration_are_sums_of_the_seeded_rows_not_the_doors_opinion(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids, totals = seeded.ids, seeded.totals
    body = _delta(client, ids).json()
    budget = body["budget_delta"]
    assert budget["from_total_minor"] == totals["base"], budget
    assert budget["to_total_minor"] == totals["candidate"], budget
    assert budget["delta_minor"] == totals["candidate"] - totals["base"], budget
    assert budget["currency"] == "CNY" and budget["mixed_or_missing_currency"] is False, budget
    duration = body["duration_delta"]
    assert duration["from_minutes"] == totals["base_minutes"], duration
    assert duration["to_minutes"] == totals["candidate_minutes"], duration
    assert duration["delta_min"] == totals["candidate_minutes"] - totals["base_minutes"], duration
    assert duration["from_unreadable_slots"] == 0, duration
    assert duration["to_unreadable_slots"] == 0, duration


def test_a_slot_whose_times_this_door_cannot_read_is_named_not_quietly_dropped(seeded, monkeypatch):
    """`activities.start_at` is free text (backend/app/db/models.py:575), so a row can carry anything.

    The pair used here is chosen to be producible under the shipped DDL, not just under `create_all`:
    `activities` carries `CHECK (end_at > start_at)` (backend/db/schema.sql:257) and that is a text
    comparison, so a malformed-but-ordered timestamp string passes the constraint and reaches the door.
    A duration quietly shortened by a row the door did not understand would be a number the screen
    cannot question, so the count of unreadable slots rides next to the minutes it left out.
    """
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    # Why this pair and not a word: the DDL's `end_at > start_at` compares text, so an unparseable pair
    # that is still in ascending order passes the constraint and reaches the door -- and neither half
    # parses, so the arm below cannot be reading real minutes by accident.
    unreadable_start, unreadable_end = "2026-13-45T99:99:99", "2026-13-46T99:99:99"
    assert unreadable_end > unreadable_start, "the DDL compares these two as text"
    for value in (unreadable_start, unreadable_end):
        with pytest.raises(ValueError):
            datetime.fromisoformat(value)
    with seeded.factory() as session:
        row = session.scalars(select(Activity).where(
            Activity.plan_version_id == ids["candidate"],
            Activity.sequence_no == 4)).one()
        row.start_at = unreadable_start
        row.end_at = unreadable_end
        session.commit()
    duration = _delta(client, ids).json()["duration_delta"]
    assert duration["to_unreadable_slots"] == 1, duration
    assert duration["from_unreadable_slots"] == 0, duration
    assert duration["to_minutes"] == seeded.totals["candidate_minutes"] - 20, duration
    assert duration["read_from"] == "activities.start_at / end_at", duration


def test_an_unpriced_slot_is_counted_and_never_makes_the_verified_difference_smaller(seeded,
                                                                                    monkeypatch):
    """Only 冠豸山 states a verified price; the rest must not silently become zero in a claim."""
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    verified = _delta(client, ids).json()["verified_cost"]
    assert verified["from_total_minor"] == 6000 and verified["to_total_minor"] == 6000, verified
    assert verified["delta_minor"] == 0, verified
    assert verified["priced_slots"] == 1, verified
    assert verified["unpriced_slots"] == 2, verified
    assert verified["read_from"] == "app.services._place_verified_cost", verified


def test_two_currencies_produce_no_delta_rather_than_a_subtracted_pair(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    with seeded.factory() as session:
        for row in session.scalars(select(Activity).where(
                Activity.plan_version_id == ids["candidate"])).all():
            row.currency = "USD"
        session.commit()
    body = _delta(client, ids).json()
    assert body["budget_delta"]["currency"] is None, body["budget_delta"]
    assert body["budget_delta"]["delta_minor"] is None, body["budget_delta"]
    assert body["budget_delta"]["mixed_or_missing_currency"] is True, body["budget_delta"]
    assert body["budget_delta"]["from_total_minor"] == seeded.totals["base"], body["budget_delta"]


def test_the_delta_answers_with_the_fact_doors_own_views_field_by_field(seeded, monkeypatch):
    """One writer per judgement: the same slot cannot be READY here and UNAVAILABLE there."""
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    body = _delta(client, ids).json()
    facts = client.get(departure_facts.FACTS_PATH.format(journey_id=ids["journey"]),
                       params={"plan_version_id": ids["candidate"]}, headers=_header(ids["owner"]))
    assert facts.status_code == 200, facts.text
    by_sequence = {slot["sequence_no"]: slot for slot in facts.json()["slots"]}
    for entry in body["sets"]["added"] + body["sets"]["moved"]:
        view = entry["to_slot"]
        peer = by_sequence[entry["sequence_no"]]
        for fact in ("identity", "coordinate", "opening_hours", "cost"):
            assert view[fact] == peer[fact], (entry["sequence_no"], fact, view[fact], peer[fact])
        assert view["media_door"] == peer["media_door"], entry


def test_the_evidence_block_is_the_selection_doors_own_answer(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    body = _delta(client, ids).json()
    with seeded.factory() as session:
        candidate = session.get(PlanVersion, ids["candidate"])
        base = session.get(PlanVersion, ids["base"])
    assert body["evidence"]["to"] == departure_read.frozen_evidence_of(candidate), body["evidence"]
    assert body["evidence"]["from"] == departure_read.frozen_evidence_of(base), body["evidence"]
    assert body["evidence"]["read_from"] == "app.departure_read.frozen_evidence_of"


def test_a_version_of_another_journey_is_answered_before_any_slot_is_read(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    spoken: list[str] = []

    @event.listens_for(seeded.engine, "before_cursor_execute")
    def capture(conn, cursor, statement, parameters, context, executemany):
        del conn, cursor, parameters, context, executemany
        spoken.append(statement.strip().upper())

    refused = _delta(client, ids, src=ids["foreign_plan"])
    assert refused.status_code == 404, refused.text
    error = refused.json()["error"]
    assert error["reason_code"] == departure_facts.REASON_PLAN_NOT_IN_JOURNEY, error
    assert error["details"]["which"] == "from", error
    assert not [row for row in spoken if "FROM ACTIVITIES" in row], spoken


def test_the_doors_refusals_are_named_for_the_missing_half_of_a_comparison(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    for missing, code in (
        ("from_plan_version_id", plan_delta.REASON_FROM_REQUIRED),
        ("to_plan_version_id", plan_delta.REASON_TO_REQUIRED),
    ):
        params = {"from_plan_version_id": ids["base"], "to_plan_version_id": ids["candidate"]}
        params.pop(missing)
        refused = client.get(DELTA.format(ids["journey"]), params=params,
                             headers=_header(ids["owner"]))
        assert refused.status_code == 422, (missing, refused.text)
        assert refused.json()["error"]["reason_code"] == code, refused.json()

    same = _delta(client, ids, src=ids["base"], dst=ids["base"])
    assert same.status_code == 422, same.text
    assert same.json()["error"]["reason_code"] == plan_delta.REASON_SAME_VERSION

    outsider = client.get(DELTA.format(ids["journey"]),
                          params={"from_plan_version_id": ids["base"],
                                  "to_plan_version_id": ids["candidate"]},
                          headers=_header(ids["stranger"]))
    assert outsider.status_code == 403, outsider.text
    assert outsider.json()["error"]["reason_code"] == departure_read.REASON_MEMBER_REQUIRED


def test_the_delta_read_runs_only_reads(seeded, monkeypatch):
    client = _app(seeded, monkeypatch)
    ids = seeded.ids
    spoken: list[str] = []

    @event.listens_for(seeded.engine, "before_cursor_execute")
    def capture(conn, cursor, statement, parameters, context, executemany):
        del conn, cursor, parameters, context, executemany
        spoken.append(statement.strip().split()[0].upper())

    before = len(_rows(seeded, Activity))
    audits = len(_rows(seeded, AuditLog))
    answer = _delta(client, ids)
    assert answer.status_code == 200, answer.text
    assert spoken, "the listener never saw a statement"
    assert set(spoken) <= {"SELECT", "BEGIN", "COMMIT", "ROLLBACK", "PRAGMA"}, sorted(set(spoken))
    assert len(_rows(seeded, Activity)) == before
    assert len(_rows(seeded, AuditLog)) == audits
    assert _rows(seeded, TravelerTwinSnapshot) == []


def test_no_provider_client_is_reachable_from_the_delta_module():
    tree = ast.parse(Path("app/plan_delta.py").read_text(encoding="utf-8"), filename="delta")
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(str(alias.name).split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(str(node.module).split(".")[0])
            modules.add(str(node.module))
    network = {"http", "httpx", "requests", "aiohttp", "urllib", "socket", "ssl", "urllib3"}
    assert modules.isdisjoint(network), sorted(modules & network)
    assert "app.departure_facts" in modules, sorted(modules)
    assert "app.agent" not in {str(getattr(node, "module", "")) for node in ast.walk(tree)
                               if isinstance(node, ast.ImportFrom)}, "no agent runtime import"


def test_the_status_words_a_delta_reports_are_words_the_shipped_ddl_allows(seeded, monkeypatch):
    ddl = Path("db/schema.sql").read_text(encoding="utf-8")
    start = ddl.index("CREATE TABLE IF NOT EXISTS activities (")
    block = ddl[start:ddl.index(chr(10) + ");", start)]
    marker = "status IN ("
    at = block.index(marker) + len(marker)
    words = [item.strip().strip("'") for item in
             block[at:block.index(")", at)].split(",")]
    assert "PLANNED" in words, words
    body = _delta(_app(seeded, monkeypatch), seeded.ids).json()
    reported = [entry["to"]["status"] for entry in body["sets"]["kept"] + body["sets"]["moved"]]
    reported += [entry["from"]["status"] for entry in body["sets"]["removed"]]
    assert reported and set(reported) <= set(words), reported
    assert re.match(r"^[0-9a-f-]{36}$", body["to_plan_version_id"]), body["to_plan_version_id"]


def _rows(seeded, model):
    with seeded.factory() as session:
        return list(session.scalars(select(model)).all())


def test_the_contract_promises_exactly_the_keys_this_door_emits(seeded, monkeypatch):
    """`PlanDeltaAnswer` is checked against a live answer, so the schema cannot rot into a promise.

    Both directions: a key the door stopped emitting stays in the contract's `required` list and goes
    red here, and a key the door added is refused because the contract declares no reader for it --
    which is what Codex's generated client would silently drop.
    """
    contract = yaml.safe_load(Path("../contracts/openapi.yaml").read_text(encoding="utf-8"))
    answer = contract["components"]["schemas"]["PlanDeltaAnswer"]
    path = contract["paths"]["/journeys/{journey_id}/plans/delta"]["get"]
    assert path["operationId"] == "getJourneyPlanDelta", path["operationId"]
    assert path["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PlanDeltaAnswer"}, path["responses"]["200"]

    body = _delta(_app(seeded, monkeypatch), seeded.ids).json()
    assert sorted(answer["required"]) == sorted(body), (
        sorted(set(answer["required"]) ^ set(body)))
    assert sorted(answer["properties"]) == sorted(body), (
        sorted(set(answer["properties"]) ^ set(body)))

    query = [item["name"] for item in path["parameters"] if item.get("in") == "query"]
    assert sorted(query) == ["from_plan_version_id", "to_plan_version_id"], query

    blocks = ("counts", "sets", "map_delta", "budget_delta", "verified_cost", "duration_delta",
              "evidence")
    for block in blocks:
        promised = sorted(answer["properties"][block]["required"])
        emitted = sorted(body[block])
        assert promised == emitted, (block, promised, emitted)
    # The slot views the delta carries are the fact door's own schema, referenced not recopied.
    entry = answer["properties"]["sets"]["properties"]["moved"]["items"]["$ref"]
    assert entry == "#/components/schemas/PlanDeltaSetEntry", entry
    moved_schema = contract["components"]["schemas"]["PlanDeltaSetEntry"]["properties"]
    assert moved_schema["to_slot"] == {
        "$ref": "#/components/schemas/DepartureFactsSlot"}, moved_schema["to_slot"]
    facts_slots = contract["paths"]["/journeys/{journey_id}/departure/facts"]["get"]["responses"][
        "200"]["content"]["application/json"]["schema"]["properties"]["slots"]["items"]
    assert facts_slots == {"$ref": "#/components/schemas/DepartureFactsSlot"}, facts_slots
