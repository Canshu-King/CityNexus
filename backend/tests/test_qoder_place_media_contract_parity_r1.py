"""The contract those two doors ship against has to agree with what they actually answer.

第五十五笔 wrote `contracts/openapi.yaml` by hand. A hand-written contract is exactly the kind of
claim that quietly stops being true: a key renamed in code, a reason code that no longer appears, a
response the door never sends. These controls compare the document to real answers from the router --
same seed, same envelope handler the product uses, a MockTransport provider so the *shape* is the
production one without leaving the tree.

What is being pinned:
* both paths exist in the contract and in the served document (`/api/v1` prefix stripped);
* every key the 200 body carries is declared, and every key the schema calls required is present;
* the enums in the document contain the values this build actually answers;
* every refusal reason code the door sends appears verbatim in that path's own contract block.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import main as main_module
from app import place_media_routes, place_source_lead, traveler_principal
from app.core.config import settings
from app.db.models import Base, Journey, JourneyCheckin, Place, Traveler
from app.db.session import get_session
from app.integrations.media import place_media
from app.main import app as product_app  # the served document

CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "openapi.yaml"
MEDIA_PATH = "/journeys/{journey_id}/places/{place_id}/media"
IDENTITY_PATH = "/journeys/{journey_id}/place-identity"
SECRET = uuid.uuid4().hex + uuid.uuid4().hex  # generated, never printed, never committed


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def spec() -> dict:
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


def schema(name: str) -> dict:
    return spec()["components"]["schemas"][name]


@pytest.fixture(scope="module")
def world():
    """One traveller, one journey holding one place, and a provider that answers in the real shape."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    owner, journey = str(uuid.uuid4()), str(uuid.uuid4())
    place = "real-place-" + "a" * 24
    outsider = str(uuid.uuid4())
    with factory() as session:
        for ident, name in ((owner, "owner"), (outsider, "outsider")):
            session.add(Traveler(id=ident, display_name=name, email=None, locale="zh-CN",
                                 timezone="Asia/Shanghai", created_at=_now(), updated_at=_now()))
        session.add(Journey(id=journey, traveler_id=owner, title="连城", city_code="350825",
                            timezone="Asia/Shanghai", start_at=_now(), end_at=_now(),
                            budget_currency="CNY", budget_amount_minor=1, status="ACTIVE",
                            created_at=_now(), updated_at=_now()))
        session.add(Place(id=place, provider_key="photon", external_id="photon:Q1209125",
                          city_code="连城县", name="冠豸山", category="poi", latitude=25.7,
                          longitude=116.75, opening_hours_json="{}", tags_json="[]",
                          metadata_json="{}", updated_at=_now()))
        session.add(JourneyCheckin(id=str(uuid.uuid4()), journey_id=journey, activity_id=None,
                                   place_id=place, target_kind="place", target_key=place,
                                   stamped_at=_now()))
        session.commit()

    app = FastAPI()
    app.include_router(place_media_routes.router)
    app.add_exception_handler(StarletteHTTPException, main_module.http_error)

    def override_session():
        with factory() as session:
            yield session

    def override_client():
        return httpx.AsyncClient(transport=httpx.MockTransport(_respond), timeout=5.0)

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[place_media_routes._media_client] = override_client
    # The secret is swapped for the duration of this module only: leaving it set is how the next
    # test file starts answering 401 to calls it wrote expecting an unconfigured credential door.
    original = traveler_principal.settings
    traveler_principal.settings = replace(settings, traveler_auth_secret=SECRET)
    try:
        headers = {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(owner)}
        stranger = {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(outsider)}
        yield TestClient(app), journey, place, headers, stranger
    finally:
        traveler_principal.settings = original


def _respond(request: httpx.Request) -> httpx.Response:
    """Stand-in provider answers in Wikimedia's shape, so `as_payload()` runs for real.

    EntityData is fetched by url path, not by an `action` parameter -- answering only the query form is
    how a mock can look complete while the product never sees an entity document.
    """
    path = str(request.url)
    action = request.url.params.get("action")
    if "Special:EntityData" in path or action == "wbgetentities":
        return httpx.Response(200, json={"entities": {"Q10895162": {
            "labels": {"zh": {"value": "冠豸山"}},
            "descriptions": {"en": {"value": "mountain in Liancheng, Longyan, Fujian"}},
            "claims": {place_media.IMAGE_PROPERTY: [
                {"mainsnak": {"datavalue": {"value": "灵芝峰顶看长寿亭.jpg"}}}]}}}})
    if action == "wbsearchentities":
        return httpx.Response(200, json={"search": [
            {"id": "Q10895162", "label": "冠豸山",
             "description": "mountain in Liancheng, Longyan, Fujian"}]})
    if "commons" in path:
        return httpx.Response(200, json={"query": {"pages": {"1": {"imageinfo": [{
            "url": "https://example.invalid/lingzhi.jpg",
            "thumburl": "https://example.invalid/lingzhi-thumb.jpg",
            "descriptionurl": "https://example.invalid/File:灵芝峰顶看长寿亭.jpg",
            "extmetadata": {"Artist": {"value": '<a href="https://e.x">某作者</a>'},
                            "LicenseShortName": {"value": "CC BY 3.0"}},
            "width": 1555, "height": 1166, "mime": "image/jpeg"}]}}}})
    return httpx.Response(200, json={})


def media_url(journey: str, place: str) -> str:
    return "/api/v1" + MEDIA_PATH.format(journey_id=journey, place_id=place)


def identity_url(journey: str, lead: str) -> str:
    return "/api/v1" + IDENTITY_PATH.format(journey_id=journey) + "?lead=" + lead


# ---------------------------------------------------------------- existence
def test_both_doors_are_in_the_contract_and_in_the_served_document():
    declared, served = spec()["paths"], product_app.openapi()["paths"]
    for path in (MEDIA_PATH, IDENTITY_PATH):
        assert path in declared, path + " is not in contracts/openapi.yaml"
        assert "/api/v1" + path in served, path + " is not served by app.main"


def test_the_documented_status_codes_are_the_ones_the_doors_answer(world):
    """A code the door answers but the document never lists is the drift this file is for."""
    client, journey, place, headers, stranger = world
    answers = {
        MEDIA_PATH: [client.get(media_url(journey, place)),
                     client.get(media_url(journey, place), headers=stranger),
                     client.get(media_url(journey, "real-place-" + "b" * 24), headers=headers),
                     client.get(media_url(journey, place), headers=headers)],
        IDENTITY_PATH: [client.get(identity_url(journey, place)),
                        client.get(identity_url(journey, place + "x")),
                        client.get(identity_url(journey, "冠豸山"), headers=headers)],
    }
    for path, responses in answers.items():
        documented = set(spec()["paths"][path]["get"]["responses"])
        for response in responses:
            assert str(response.status_code) in documented, (
                f"{path} answered {response.status_code} but the document lists {sorted(documented)}")


def path_block(path: str) -> str:
    """One path's own contract block, so a reason code cannot borrow another door's promise."""
    document = CONTRACT.read_text(encoding="utf-8")
    start = document.index("\n  " + path + ":\n") + 1
    rest = document[start:]
    nxt = re.search(r"\n  /[^\n]+:\n", rest)
    return rest[:nxt.start()] if nxt else rest


def test_every_refusal_reason_code_is_written_in_its_own_door(world):
    client, journey, place, headers, stranger = world
    seen = [
        (MEDIA_PATH, client.get(media_url(journey, place))),
        (MEDIA_PATH, client.get(media_url(journey, place), headers=stranger)),
        (MEDIA_PATH, client.get(media_url(journey, "real-place-" + "b" * 24), headers=headers)),
        (IDENTITY_PATH, client.get(identity_url(journey, "冠豸山"), headers=headers)),
    ]
    for path, response in seen:
        assert response.status_code in (401, 403, 404), response.text
        code = (response.json().get("error") or {}).get("reason_code")
        block = path_block(path)
        assert code, path + " refused without naming a reason_code"
        assert code in block, (
            f"{code} is answered by {path} but written nowhere in that path's block")


# ---------------------------------------------------------------- 200 shapes
def test_the_identity_answer_carries_exactly_the_declared_keys(world):
    client, journey, place, headers, _stranger = world
    ok = client.get(identity_url(journey, place), headers=headers)
    assert ok.status_code == 200, ok.text
    body = ok.json()
    declared = set(schema("PlaceLeadResponse")["properties"])
    assert set(body) <= declared, f"the door answers keys the document never declared: {sorted(set(body) - declared)}"
    required = set(schema("PlaceLeadResponse")["required"])
    assert required <= set(body), f"the document requires {sorted(required - set(body))} and the door omits them"
    for field, value in (("lead_shape", body["lead_shape"]), ("status", body["status"]),
                         ("reason_code", body["reason_code"])):
        allowed = set(schema("PlaceLeadResponse")["properties"][field]["enum"])
        assert value in allowed, f"{field}={value} is not one of the documented {sorted(allowed)}"


def test_the_media_answer_carries_exactly_the_declared_keys(world):
    client, journey, place, headers, _stranger = world
    ok = client.get(media_url(journey, place), headers=headers)
    assert ok.status_code == 200, ok.text
    body = ok.json()
    declared = set(schema("PlaceMediaResponse")["properties"])
    assert set(body) <= declared, f"the door answers keys the document never declared: {sorted(set(body) - declared)}"
    required = set(schema("PlaceMediaResponse")["required"])
    assert required <= set(body), f"the document requires {sorted(required - set(body))} and the door omits them"
    allowed = set(schema("PlaceMediaResponse")["properties"]["status"]["enum"])
    assert body["status"] in allowed, f"status={body['status']} is not documented"
    media = body.get("media") or {}
    media_declared = set(schema("PlaceMedia")["properties"])
    assert set(media) <= media_declared, f"media carries {sorted(set(media) - media_declared)}"
    assert body["status"] == "REAL_POI_PHOTO", "the stand-in provider should have produced a showable photo"


# ---------------------------------------------------------------- refusals name themselves
def test_the_identity_status_vocabulary_is_the_one_the_adapter_can_answer():
    """A renderer decides how much to trust a picture from this word, so the word list is a contract.

    The bound names are derived from the module's own arm table rather than typed out here, and a
    documented value that appears nowhere in the adapter -- a name the code stopped producing -- is red.
    """
    source = Path(place_media.__file__).read_text(encoding="utf-8")
    minted = {"BOUND_" + arm for arm in place_media.CONFIDENCE_BY_ARM.values()}
    literals = set(re.findall(r'"([A-Z][A-Z_]{3,})"', source))
    documented = {value for value in schema("IdentityStatus")["enum"] if value != "null"}
    missing = sorted(minted - documented)
    assert not missing, f"the adapter can answer {missing} and the document does not list them"
    stale = sorted(documented - minted - literals)
    assert not stale, f"the document lists {stale} which this adapter no longer produces"
    # The confidence slot is the arm table itself, in both directions: no arm the code cannot fire,
    # and no fired arm the document forgot.
    armed = set(place_media.CONFIDENCE_BY_ARM.values())
    documented_confidence = set(schema("PlaceMedia")["properties"]["confidence"]["enum"])
    assert documented_confidence == armed, (
        "the document says {} while the adapter's arm table is {}".format(
            sorted(documented_confidence), sorted(armed)))


def test_the_schema_enums_close_over_the_reason_codes_the_resolver_can_answer():
    """The document must know every code the module can produce -- not the ones I happened to write."""
    source = Path(place_source_lead.__file__).read_text(encoding="utf-8")
    produced = set(re.findall(r'^REASON_[A-Z_]+ = "([A-Z_]+)"', source, re.MULTILINE))
    documented = set(schema("PlaceLeadResponse")["properties"]["reason_code"]["enum"])
    assert produced <= documented, (
        f"the resolver can answer {sorted(produced - documented)} and the document does not list them")
