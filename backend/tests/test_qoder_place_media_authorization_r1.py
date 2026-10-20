"""The media door has to answer "may this caller see this place" before it answers "what is the photo".

The 21:42 order names both halves: `session.get(Journey)` + `session.get(Place)` only prove two rows
exist, and a path that asks Wikimedia on behalf of whoever guesses two uuids is an enumeration
interface with a picture attached. These controls hold:

* nobody signed -> 401, and NO outbound request;
* a stranger with perfectly valid credentials -> 403, named `JOURNEY_MEMBER_REQUIRED`, no outbound;
* a withdrawn membership -> the same 403 (the seat has to be in force, not merely once granted);
* the owner and a member in force -> the 200 contract, outbound request counted;
* a place the journey does not hold -> 404, the SAME status as a place that does not exist, so the
  answer cannot be walked to discover which place ids belong to somebody else's trip;
* an unknown journey -> 404 before any provider is asked;
* the membership question is asked of `app.main`'s own predicate, not a second copy of it.

The token secret is generated per run and never written into the tree, the way ORD-0685 does it.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import place_media_routes, traveler_principal
from app.core.config import settings
from app.db.models import (
    Activity,
    Base,
    Journey,
    JourneyCheckin,
    JourneyMember,
    Place,
    PlanVersion,
    Traveler,
)
from app.db.session import get_session

SECRET = uuid.uuid4().hex + uuid.uuid4().hex  # generated, never printed, never committed
PATH = "/api/v1/journeys/{}/places/{}/media"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture()
def seeded():
    """One journey with an owner, one held place, one outsider, and a provider that counts its calls."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ids = {
        "owner": str(uuid.uuid4()), "member": str(uuid.uuid4()), "outsider": str(uuid.uuid4()),
        "journey": str(uuid.uuid4()), "other_journey": str(uuid.uuid4()),
        "place": str(uuid.uuid4()), "foreign_place": str(uuid.uuid4()),
    }
    with factory() as session:
        for key in ("owner", "member", "outsider"):
            session.add(Traveler(id=ids[key], display_name=key, email=None, locale="zh-CN",
                                 timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
        for key in ("journey", "other_journey"):
            session.add(Journey(id=ids[key], traveler_id=ids["owner"], title=key,
                                city_code="350825", timezone="Asia/Shanghai", start_at=_now(),
                                end_at=_now(), budget_currency="CNY", budget_amount_minor=1,
                                status="ACTIVE", created_at=_now(), updated_at=_now()))
        for key in ("place", "foreign_place"):
            session.add(Place(id=ids[key], provider_key="photon", external_id="N:" + key,
                              city_code="350825", name="冠豸山" if key == "place" else "外滩",
                              category="poi", latitude=25.7, longitude=116.75,
                              opening_hours_json="{}", tags_json="[]", metadata_json="{}",
                              updated_at=_now()))
        # This journey holds `place` through one footprint stamp, and the OTHER journey holds
        # `foreign_place` through one scheduled activity -- both reachability shapes, each proven once.
        session.add(JourneyCheckin(id=str(uuid.uuid4()), journey_id=ids["journey"],
                                   activity_id=None, place_id=ids["place"], target_kind="place",
                                   target_key=ids["place"], stamped_at=_now()))
        plan = PlanVersion(id=str(uuid.uuid4()), journey_id=ids["other_journey"], version_no=1,
                           planning_mode="AUTO", status="CURRENT", source="test",
                           parent_plan_version_id=None, total_cost_minor=0, currency="CNY",
                           estimated_duration_min=0, created_at=_now())
        session.add(plan)
        session.add(Activity(id=str(uuid.uuid4()), plan_version_id=plan.id, sequence_no=1,
                             activity_type="sight", title="外滩", place_id=ids["foreign_place"],
                             city_service_id=None, start_at=_now(), end_at=_now(),
                             travel_from_prev_min=0, estimated_cost_minor=0, currency="CNY",
                             status="PLANNED", locked=False, metadata_json="{}",
                             created_at=_now(), updated_at=_now()))
        session.commit()
        session.add(JourneyMember(id=str(uuid.uuid4()), journey_id=ids["journey"],
                                  traveler_id=ids["member"], role="viewer",
                                  invited_by=ids["owner"], expires_at=None, joined_at=_now(),
                                  removed_at=None, created_at=_now(), updated_at=_now()))
        session.commit()
    return SimpleNamespace(factory=factory, ids=ids)


class _CountingTransport(httpx.AsyncClient):
    """A client that records every outbound request, so 'refused before asking' is measurable."""

    def __init__(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(self._respond)
        self.calls: list[str] = []
        super().__init__(*args, **kwargs)

    def _respond(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(str(request.url))
        if request.url.params.get("action") == "wbsearchentities":
            return httpx.Response(200, json={"search": [{"id": "Q1209125", "label": "冠豸山",
                                                        "description": "mountain in Liancheng"}]})
        if request.url.params.get("action") == "wbgetentities":
            return httpx.Response(200, json={"entities": {
                "Q1209125": {"labels": {"zh": {"value": "冠豸山"}},
                             "claims": {"P18": [{"mainsnak": {"datavalue": {
                                 "value": "Farthest Rock in远处冠豸山.jpg"}}}]}},
                "Q8686": {"labels": {"zh": {"value": "连城县"}}, "claims": {}}}})
        if "commons" in str(request.url):
            return httpx.Response(200, json={"query": {"pages": {"1": {"imageinfo": [{
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/x/远望冠豸山.jpg/640px.jpg",
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:远望冠豸山.jpg",
                "extmetadata": {"Artist": {"value": '<a href="x">rheins</a>'},
                                "LicenseShortName": {"value": "CC BY 3.0"}},
                "width": 640, "height": 480, "mime": "image/jpeg"}]}}}})
        return httpx.Response(200, json={})


def _app(seeded, monkeypatch):
    """The router on its own app, with the session and the outbound client pinned to this seed."""
    # ORD-0685 的形状：Settings 是 dataclass，用 replace 造一枚只改 secret 的副本，不落盘。
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))
    from app import main as main_module

    app = FastAPI()
    app.include_router(place_media_routes.router)
    # The refusal has to arrive in the envelope the screens already read, so the test app carries
    # main's own HTTPException handler instead of inventing a second answer shape.
    app.add_exception_handler(StarletteHTTPException, main_module.http_error)

    def override_session():
        with seeded.factory() as session:
            yield session

    holder: dict[str, _CountingTransport] = {}

    async def override_client():
        client = _CountingTransport(timeout=5.0)
        holder["client"] = client
        return client

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[place_media_routes._media_client] = override_client
    return TestClient(app), holder


def _header(traveler_id: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(traveler_id)}


def test_the_owner_reads_the_contract_and_the_provider_was_asked(seeded, monkeypatch):
    client, calls = _app(seeded, monkeypatch)
    url = PATH.format(seeded.ids["journey"], seeded.ids["place"])
    ok = client.get(url, headers=_header(seeded.ids["owner"]))
    assert ok.status_code == 200, ok.text
    assert ok.json()["place_name"] == "冠豸山"
    assert len(calls["client"].calls) > 0, "an authorised read should have asked the provider"


def test_a_member_in_force_reads_the_same_contract(seeded, monkeypatch):
    client, _calls = _app(seeded, monkeypatch)
    ok = client.get(PATH.format(seeded.ids["journey"], seeded.ids["place"]),
                    headers=_header(seeded.ids["member"]))
    assert ok.status_code == 200, ok.text
    assert ok.json()["journey_id"] == seeded.ids["journey"]


def test_nobody_signed_gets_401_and_asks_nothing(seeded, monkeypatch):
    client, calls = _app(seeded, monkeypatch)
    refused = client.get(PATH.format(seeded.ids["journey"], seeded.ids["place"]))
    assert refused.status_code == 401, refused.text
    assert calls["client"].calls == [], "an unsigned read must not spend a provider request"


def test_a_stranger_with_valid_credentials_gets_403_not_the_photo(seeded, monkeypatch):
    client, calls = _app(seeded, monkeypatch)
    refused = client.get(PATH.format(seeded.ids["journey"], seeded.ids["place"]),
                         headers=_header(seeded.ids["outsider"]))
    assert refused.status_code == 403, refused.text
    assert refused.json()["error"]["reason_code"] == place_media_routes.REASON_MEMBER_REQUIRED
    assert calls["client"].calls == [], "the refusal happens before the provider is asked"


def test_a_withdrawn_seat_is_refused_the_same_way(seeded, monkeypatch):
    client, calls = _app(seeded, monkeypatch)
    from sqlalchemy import select

    with seeded.factory() as session:
        member = session.scalars(select(JourneyMember)).first()
        member.removed_at = _now()
        session.commit()
    refused = client.get(PATH.format(seeded.ids["journey"], seeded.ids["place"]),
                         headers=_header(seeded.ids["member"]))
    assert refused.status_code == 403, refused.text
    assert calls["client"].calls == []


def test_a_place_this_journey_does_not_hold_is_404_like_a_missing_one(seeded, monkeypatch):
    """`foreign_place` exists and is real -- it is simply somebody else's stop.

    Same status and same reason code as "no such row": the difference between the two is exactly what
    a caller could enumerate, so the door refuses to tell.
    """
    client, calls = _app(seeded, monkeypatch)
    missing = client.get(PATH.format(seeded.ids["journey"], seeded.ids["place"]),
                         headers=_header(seeded.ids["owner"]))
    assert missing.status_code == 200
    not_here = client.get(PATH.format(seeded.ids["journey"], seeded.ids["foreign_place"]),
                          headers=_header(seeded.ids["owner"]))
    foreign = client.get(PATH.format(seeded.ids["other_journey"], seeded.ids["foreign_place"]),
                         headers=_header(seeded.ids["owner"]))
    gone = client.get(PATH.format(seeded.ids["journey"], str(uuid.uuid4())),
                      headers=_header(seeded.ids["owner"]))
    assert not_here.status_code == 404 and foreign.status_code == 200
    assert gone.status_code == 404
    assert not_here.json()["error"]["reason_code"] == gone.json()["error"]["reason_code"]
    assert calls["client"].calls == [], "a place outside the journey never reaches the network"


def test_an_unknown_journey_is_404_before_anything_is_asked(seeded, monkeypatch):
    client, calls = _app(seeded, monkeypatch)
    refused = client.get(PATH.format(str(uuid.uuid4()), seeded.ids["place"]),
                         headers=_header(seeded.ids["owner"]))
    assert refused.status_code == 404, refused.text
    assert calls["client"].calls == []


def test_the_membership_question_is_asked_of_main_s_one_definition(seeded, monkeypatch):
    """This door must not keep its own copy of 'is this traveller still in'.

    The test replaces `app.main._member_is_in_force` with a recorder: if the route reaches it, the
    answer came from the one place that decides; if a future edit grows a second predicate here, this
    control goes red instead of quietly agreeing with itself.
    """
    from app import main as main_module

    seen: list[tuple[str, str]] = []
    real = main_module._member_is_in_force

    def spy(session, journey_id, traveler_id, now):
        seen.append((str(journey_id), str(traveler_id)))
        return real(session, journey_id, traveler_id, now)

    monkeypatch.setattr(main_module, "_member_is_in_force", spy)
    client, _ = _app(seeded, monkeypatch)
    ok = client.get(PATH.format(seeded.ids["journey"], seeded.ids["place"]),
                    headers=_header(seeded.ids["member"]))
    assert ok.status_code == 200, ok.text
    assert (seeded.ids["journey"], seeded.ids["member"]) in seen, "the route did not use main's predicate"
