"""A map point's `candidate_id` is a lead, and a lead must resolve through stored identity only.

The 13:42 order names the defect: Codex's workspace map carries Photon / Nominatim / GoalTask source
leads, and most of them are not `Place.id`, so asking the media read with one mostly answers 404. The
tempting fix -- look the place up by the name the map shows -- is the one that puts another city's
photograph on this landmark. These controls hold the line the order drew:

* the three lead shapes this product really mints resolve to one row, and both mint formulas are
  recomputed here rather than written down as a literal;
* free text and urls are refused with a named shape, even when a row with that exact name exists;
* a provider object id carried by two rows is refused instead of guessed, and stops being ambiguous as
  soon as the journey picks one;
* a candidate lead from another trip is refused, a candidate with no place row says NOT_MATERIALIZED,
  and a candidate whose own region column disagrees with the row's is flagged, not silently accepted;
* resolving costs no provider call, and media asked with a lead reaches the same row as media asked
  with the id.

The token secret is generated per run and never written into the tree, the way ORD-0685 does it.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import place_media_routes, place_source_lead, traveler_principal
from app.core.config import settings
from app.db.models import Base, Journey, JourneyCheckin, Place, RealPlaceCandidate, Traveler
from app.db.session import get_session

IDENTITY_PATH = "/api/v1/journeys/{}/place-identity"
MEDIA_PATH = "/api/v1/journeys/%s/places/%s/media"
SECRET = uuid.uuid4().hex + uuid.uuid4().hex  # generated, never printed, never committed
#: What the route handed the provider on the last media read, so the identity columns are checked
#: and not just the place id.  `_app` installs the spy; the test that reads it clears it first.
HANDED: list[dict] = []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _candidate_id(owner: str, provider_key: str, external_id: str) -> str:
    """Discovery's own candidate mint, recomputed so the test uses the shape the map really carries."""
    digest = hashlib.sha1(f"{owner}|{provider_key}|{external_id}".encode()).hexdigest()
    return f"rpc-{digest[:24]}"


def _place(session, *, external_id, city_code, name, provider_key="photon", place_id=None):
    """Seed a Place whose id is the same mint discovery uses, computed here, never hard-coded."""
    ident = place_id or place_source_lead.minted_place_id(provider_key, external_id)
    session.add(Place(id=ident, provider_key=provider_key, external_id=external_id,
                      city_code=city_code, name=name, category="poi", latitude=25.7,
                      longitude=116.75, opening_hours_json="{}", tags_json="[]",
                      metadata_json="{}", updated_at=_now()))
    return ident


def _candidate(session, *, journey_id, external_id, city_code, name, provider_key="photon"):
    ident = _candidate_id(str(journey_id or ""), provider_key, external_id)
    session.add(RealPlaceCandidate(id=ident, journey_id=journey_id, provider_key=provider_key,
                                   external_id=external_id, city_code=city_code, name=name,
                                   category="poi", latitude=25.7, longitude=116.75, tags_json="[]",
                                   opening_hours_json="{}", metadata_json="{}", evidence_json="{}",
                                   captured_at=_now(), status="DISCOVERED"))
    return ident


@pytest.fixture()
def seeded():
    """Two same-named places in two cities, one candidate row per shape, and one journey that holds one."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    ids = {"owner": str(uuid.uuid4()), "outsider": str(uuid.uuid4()), "journey": str(uuid.uuid4())}
    with factory() as session:
        for key in ("owner", "outsider"):
            session.add(Traveler(id=ids[key], display_name=key, email=None, locale="zh-CN",
                                 timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
        session.add(Journey(id=ids["journey"], traveler_id=ids["owner"], title="连城",
                            city_code="350825", timezone="Asia/Shanghai", start_at=_now(),
                            end_at=_now(), budget_currency="CNY", budget_amount_minor=1,
                            status="ACTIVE", created_at=_now(), updated_at=_now()))
        # 同名异地：两行都叫「外滩」，一行在这趟行程里，另一行在上海。同名不是身份。
        ids["shanghai"] = _place(session, external_id="photon:node/1", city_code="上海市",
                                 name="外滩")
        ids["held"] = _place(session, external_id="photon:node/2", city_code="连城县",
                             name="冠豸山")
        session.add(JourneyCheckin(id=str(uuid.uuid4()), journey_id=ids["journey"],
                                   activity_id=None, place_id=ids["held"], target_kind="place",
                                   target_key=ids["held"], stamped_at=_now()))
        ids["cand_held"] = _candidate(session, journey_id=ids["journey"], external_id="photon:node/2",
                                      city_code="连城县", name="冠豸山")
        ids["cand_hollow"] = _candidate(session, journey_id=None, external_id="photon:node/404",
                                        city_code="连城县", name="无名展馆")
        ids["cand_other"] = _candidate(session, journey_id="another-journey",
                                       external_id="photon:node/2", city_code="连城县", name="冠豸山")
        ids["cand_split"] = _candidate(session, journey_id=None, external_id="photon:node/1",
                                       city_code="厦门市", name="外滩")
        # One provider object id claimed by two rows: a collision, not a choice.
        ids["twin"] = _place(session, place_id="plc-twin", external_id="photon:node/9",
                             city_code="上海市", name="孪生站")
        session.add(Place(id="plc-twin-2", provider_key="nominatim", external_id="photon:node/9",
                          city_code="北京市", name="孪生站", category="poi", latitude=31.2,
                          longitude=121.4, opening_hours_json="{}", tags_json="[]",
                          metadata_json="{}", updated_at=_now()))
        session.commit()
    return SimpleNamespace(factory=factory, ids=ids)


@pytest.fixture()
def session_of(seeded):
    with seeded.factory() as session:
        yield session


class _FixtureResult:
    """The adapter boundary as a stand-in: it records what was asked and answers TEST_FIXTURE."""

    def __init__(self, place_id: str):
        self.place_id = place_id

    def as_payload(self):
        return {
            "place_id": self.place_id,
            "status": "TEST_FIXTURE",
            "reason_code": "TEST_FIXTURE",
            "media": None,
            "provider_readings": [],
            "identity_status": "TEST_FIXTURE",
        }


def _app(seeded, monkeypatch):
    """The router with this seed, the credential secret pinned, and a provider that only records."""
    monkeypatch.setattr(traveler_principal, "settings",
                        replace(settings, traveler_auth_secret=SECRET))
    from app import main as main_module

    app = FastAPI()
    app.include_router(place_media_routes.router)
    app.add_exception_handler(StarletteHTTPException, main_module.http_error)

    def override_session():
        with seeded.factory() as inner:
            yield inner

    seen: list[str] = []

    async def _spy(**kwargs):
        seen.append(str(kwargs.get("place_id")))
        HANDED.append(dict(kwargs))
        return _FixtureResult(str(kwargs.get("place_id")))

    monkeypatch.setattr(place_media_routes.place_media, "collect_place_media", _spy)
    app.dependency_overrides[get_session] = override_session
    # A real httpx.AsyncClient would open a socket on an authorised media read; the route builds one
    # through its own dependency, so pin it to an unconnected transport to keep this file offline.
    import httpx

    def override_client():
        return httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200,
                                                                                             json={})))

    app.dependency_overrides[place_media_routes._media_client] = override_client
    return TestClient(app), seen


def _header(traveler_id: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(traveler_id)}


# ---------------------------------------------------------------- the shapes that resolve
def test_a_provider_object_lead_mints_to_the_row_the_media_read_needs(session_of, seeded):
    """The lead the map carries and the id the media read wants come out of the same two columns."""
    reading = place_source_lead.resolve_place_lead(session_of, "photon:node/2")
    assert reading.resolved, reading.note
    assert reading.place_id == seeded.ids["held"]
    assert reading.city_code == "连城县"
    assert reading.as_payload()["region"] == "连城县"
    assert reading.matched_by == "provider_object_id"
    assert place_source_lead.minted_place_id("photon", "photon:node/2") == seeded.ids["held"]


def test_a_minted_place_id_lead_resolves_directly(session_of, seeded):
    reading = place_source_lead.resolve_place_lead(session_of, seeded.ids["held"])
    assert reading.resolved
    assert reading.place_id == seeded.ids["held"]
    assert reading.matched_by == "place_id"


def test_a_candidate_lead_resolves_through_its_own_identity_columns(session_of, seeded):
    reading = place_source_lead.resolve_place_lead(session_of, seeded.ids["cand_held"])
    assert reading.resolved
    assert reading.place_id == seeded.ids["held"]
    assert reading.matched_by == "candidate_identity"
    assert reading.region_conflict is False


# ---------------------------------------------------------------- the shapes that must refuse
def test_place_text_is_not_a_lead_even_when_a_row_carries_that_name(session_of):
    """同名异地的那一刀：屏上写着「外滩」不等于 photon:node/1 就是外滩。"""
    for lead in ("外滩", "https://commons.wikimedia.org/wiki/File:Bund.jpg", "外滩 上海"):
        reading = place_source_lead.resolve_place_lead(session_of, lead)
        assert reading.status == place_source_lead.STATUS_UNRESOLVED, lead
        assert reading.reason_code == place_source_lead.REASON_NOT_A_LEAD, lead
        assert reading.place_id is None, lead


def test_a_colliding_provider_object_id_is_refused_not_chosen(session_of, seeded):
    reading = place_source_lead.resolve_place_lead(session_of, "photon:node/9")
    assert reading.reason_code == place_source_lead.REASON_AMBIGUOUS
    assert reading.place_id is None
    # 一旦按这趟行程收窄，同一枚线索就不再是两行：范围替它选，不是名字替它选。
    scoped = place_source_lead.resolve_place_lead(
        session_of, "photon:node/2", journey_id=seeded.ids["journey"])
    assert scoped.resolved and scoped.place_id == seeded.ids["held"]


def test_a_hollow_candidate_says_it_has_no_place_row(session_of, seeded):
    reading = place_source_lead.resolve_place_lead(session_of, seeded.ids["cand_hollow"])
    assert reading.reason_code == place_source_lead.REASON_NOT_MATERIALIZED


def test_a_candidate_from_another_journey_is_not_this_callers_to_resolve(session_of, seeded):
    reading = place_source_lead.resolve_place_lead(
        session_of, seeded.ids["cand_other"], journey_id=seeded.ids["journey"])
    assert reading.reason_code == place_source_lead.REASON_NOT_IN_JOURNEY


def test_a_candidate_whose_region_disagrees_with_the_row_is_flagged(session_of, seeded):
    reading = place_source_lead.resolve_place_lead(session_of, seeded.ids["cand_split"])
    assert reading.resolved
    assert reading.place_id == seeded.ids["shanghai"]
    assert reading.region_conflict is True, "厦门市 vs 上海市 must not pass silently"


def test_a_place_the_journey_does_not_hold_stays_unreachable(session_of, seeded):
    reading = place_source_lead.resolve_place_lead(
        session_of, seeded.ids["shanghai"], journey_id=seeded.ids["journey"])
    assert reading.reason_code == place_source_lead.REASON_NOT_IN_JOURNEY


# ---------------------------------------------------------------- the reads themselves
def test_the_owner_gets_identity_and_region_from_the_lead(seeded, monkeypatch):
    client, seen = _app(seeded, monkeypatch)
    url = IDENTITY_PATH.format(seeded.ids["journey"]) + "?lead=" + seeded.ids["cand_held"]
    ok = client.get(url, headers=_header(seeded.ids["owner"]))
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["place_id"] == seeded.ids["held"]
    assert body["region"] == "连城县"
    assert body["lead_shape"] == place_source_lead.SHAPE_CANDIDATE_ID
    assert body["reason_code"] == place_source_lead.REASON_RESOLVED
    assert seen == [], "an identity read must cost no provider call"


def test_an_outsider_still_gets_the_same_403_on_the_new_read(seeded, monkeypatch):
    client, seen = _app(seeded, monkeypatch)
    url = IDENTITY_PATH.format(seeded.ids["journey"]) + "?lead=photon:node/2"
    refused = client.get(url, headers=_header(seeded.ids["outsider"]))
    assert refused.status_code == 403
    assert refused.json()["error"]["reason_code"] == place_media_routes.REASON_MEMBER_REQUIRED
    assert seen == []


def test_unsigned_and_unknown_journey_answer_the_house_codes(seeded, monkeypatch):
    client, _seen = _app(seeded, monkeypatch)
    missing = client.get(IDENTITY_PATH.format(seeded.ids["journey"]) + "?lead=photon:node/2")
    assert missing.status_code == 401
    assert missing.json()["error"]["reason_code"] == "TRAVELER_CREDENTIALS_MISSING"
    gone = client.get(IDENTITY_PATH.format(str(uuid.uuid4())) + "?lead=photon:node/2",
                      headers=_header(seeded.ids["owner"]))
    assert gone.status_code == 404


def test_a_text_lead_on_the_route_is_a_404_that_names_the_shape(seeded, monkeypatch):
    client, _seen = _app(seeded, monkeypatch)
    refused = client.get(IDENTITY_PATH.format(seeded.ids["journey"]) + "?lead=外滩",
                         headers=_header(seeded.ids["owner"]))
    assert refused.status_code == 404
    error = refused.json()["error"]
    assert error["reason_code"] == place_source_lead.REASON_NOT_A_LEAD
    assert error["details"]["lead_shape"] == place_source_lead.SHAPE_NOT_A_LEAD


def test_media_asked_with_a_lead_reaches_the_same_row_as_media_asked_with_the_id(
        seeded, monkeypatch):
    client, seen = _app(seeded, monkeypatch)
    headers = _header(seeded.ids["owner"])
    by_lead = client.get(MEDIA_PATH % (seeded.ids["journey"], seeded.ids["cand_held"]),
                         headers=headers)
    by_id = client.get(MEDIA_PATH % (seeded.ids["journey"], seeded.ids["held"]), headers=headers)
    assert by_lead.status_code == 200, by_lead.text
    assert by_id.status_code == 200, by_id.text
    assert seen == [seeded.ids["held"], seeded.ids["held"]]
    assert by_lead.json()["place_id"] == by_id.json()["place_id"]
    assert by_lead.json()["place_name"] == "冠豸山"


def test_the_media_read_hands_the_provider_the_row_s_own_identity_columns(seeded, monkeypatch):
    """Reading a column is not the same as handing over something that can never be empty.

    The route passes four values to the provider.  They are policed here rather than by a defensive
    `or ""` that would swallow a NULL into an empty string: an empty region silently turns a bound
    photograph into NO_IMAGE, and no test would notice.  Both leads reach the same row, so both must
    hand over the same columns.
    """
    client, seen = _app(seeded, monkeypatch)
    HANDED.clear()
    headers = _header(seeded.ids["owner"])
    assert client.get(MEDIA_PATH % (seeded.ids["journey"], seeded.ids["held"]),
                      headers=headers).status_code == 200
    assert client.get(MEDIA_PATH % (seeded.ids["journey"], seeded.ids["cand_held"]),
                      headers=headers).status_code == 200
    assert HANDED and all(
        handed["place_id"] == seeded.ids["held"] and handed["label"] == "冠豸山"
        and handed["region"] == "连城县" and handed["provider_object_id"] == "photon:node/2"
        for handed in HANDED), HANDED
    assert set(HANDED[0]) == {"place_id", "label", "region", "provider_object_id", "client"}
    assert seen == [seeded.ids["held"], seeded.ids["held"]]


def test_a_lead_carrying_a_slash_resolves_and_the_answer_carries_the_path_to_call(
        seeded, monkeypatch):
    """The wiring the order asks for: two calls, no free text, and no client-side rule to memorise.

    `photon:node/2` cannot ride the media path -- a slash starts a new segment -- so the identity read
    takes it as a query value and answers with `media_path`: that door, with the id it resolved already
    substituted.  The client follows what it was handed instead of learning which lead shapes need a hop.
    """
    client, seen = _app(seeded, monkeypatch)
    headers = _header(seeded.ids["owner"])
    ok = client.get(IDENTITY_PATH.format(seeded.ids["journey"]) + "?lead=photon:node/2",
                    headers=headers)
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["place_id"] == seeded.ids["held"]
    assert seen == [], "the identity read itself must not ask a provider"
    assert "note" not in body, "a refusal's reason is the reason code, not a second prose field"
    media = client.get(body["media_path"], headers=headers)
    assert media.status_code == 200, media.text
    assert seen == [seeded.ids["held"]]


def test_the_path_it_hands_back_carries_the_resolved_id_not_the_lead(seeded, monkeypatch):
    """A candidate id and a place id are two different rows; the path has to name the second.

    Building this from the lead the client sent would look identical for `real-place-` leads and would
    only be caught by a provider miss -- so the shape is pinned here with the one lead kind whose two
    ids never look alike.
    """
    client, seen = _app(seeded, monkeypatch)
    headers = _header(seeded.ids["owner"])
    ok = client.get(IDENTITY_PATH.format(seeded.ids["journey"]) + "?lead=" + seeded.ids["cand_held"],
                    headers=headers)
    assert ok.status_code == 200, ok.text
    path = ok.json()["media_path"]
    assert seeded.ids["cand_held"] not in path, path
    assert seeded.ids["held"] in path and path.endswith("/media"), path
    media = client.get(path, headers=headers)
    assert media.status_code == 200, media.text
    assert seen == [seeded.ids["held"]]


def test_media_never_reaches_another_trips_place(seeded, monkeypatch):
    client, seen = _app(seeded, monkeypatch)
    refused = client.get(MEDIA_PATH % (seeded.ids["journey"], seeded.ids["shanghai"]),
                         headers=_header(seeded.ids["owner"]))
    assert refused.status_code == 404
    assert refused.json()["error"]["reason_code"] == place_media_routes.REASON_PLACE_OUT_OF_SCOPE
    assert seen == [], "a refused place must not have asked the provider"
