"""`POST /api/v1/places/discover`: the B leg's door into the catalogue.

What these gates pin:

  1. an Amap lead lands as a WGS-84 row that still names the GCJ-02 frame it arrived in, and the
     existing catalogue read (`GET /api/v1/places`) reaches it without any change;
  2. the provider item is the identity -- discovering it twice updates one row;
  3. a lead the provider named but did not locate is answered and not stored, because
     `places.latitude` is NOT NULL and an invented coordinate is not a place;
  4. `persist=false` is a pure read;
  5. our internal city codes are refused as Amap regions before any provider is constructed --
     measured 2026-10-25, `region=CN-12-01` answered with a POI in another province.

The provider is faked and the session is an in-memory SQLite built from the product's own metadata,
so no test here writes the development database or opens a socket.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models
from app.db.models import Place
from app.integrations.capability import place_leads
from app.main import app
from app.main import get_session as main_get_session

TEST_CITY = "CN-TEST-DISCOVERY"
AMAP_KEY_ENV = "CITYNEXUS_AMAP_WEB_KEY"


@pytest.fixture()
def session() -> Session:
    # TestClient runs the endpoint in a worker thread; one shared connection is what lets the
    # in-memory database be read back from the test's own thread.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    db = maker()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def client(session: Session) -> TestClient:
    def _session_override():
        yield session

    app.dependency_overrides[main_get_session] = _session_override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(main_get_session, None)


def _amap_row(*, item_id: str = "B000A83M61", latitude: float = 39.08505, name: str = "天津博物馆"):
    return {
        "provider_item_id": item_id,
        "external_id": item_id,
        "name": name,
        "latitude": latitude,
        "longitude": 117.211801,
        "adcode": "120103",
        "region": "天津市",
        "coordinate_system": "WGS84",
        "source_crs": "GCJ02",
        "conversion": "ITERATIVE_GCJ02_TO_WGS84",
        "captured_at": "2026-10-25T00:00:00+00:00",
    }


def _fake_collection(rows):
    leads = tuple(
        lead
        for lead in (
            place_leads.lead_from_row(row, fallback_source="amap-web-service") for row in rows
        )
        if lead is not None
    )
    return place_leads.PlaceLeadResult(
        query="天津博物馆",
        region="天津市",
        leads=leads,
        provider_readings=(
            {
                "source": "amap-web-service",
                "attempted": True,
                "answered": True,
                "outcome": "ANSWERED",
                "rows": len(rows),
                "usable": len(leads),
            },
        ),
        counts_as_draft_supply=any(lead.has_position() for lead in leads),
        unknown_fields=tuple(sorted({field for lead in leads for field in lead.unknown_fields})),
    )


def _patch_providers(monkeypatch, rows):
    calls = {"build": 0}

    def fake_build(**kwargs):
        calls["build"] += 1
        return []

    async def fake_collect(query, *, region, sources, limit=8, stop_on_first_answer=True, on_provider_call=None):
        return _fake_collection(rows)

    monkeypatch.setattr("app.main.build_place_lead_sources", fake_build)
    monkeypatch.setattr("app.main.collect_place_leads", fake_collect)
    return calls


def test_a_discovered_amap_lead_lands_as_a_wgs84_row_that_names_its_native_frame(monkeypatch, client):
    _patch_providers(monkeypatch, [_amap_row()])

    response = client.post(
        "/api/v1/places/discover",
        json={"query": "天津博物馆", "city_code": TEST_CITY, "region": "天津市"},
    )

    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer["counts_as_draft_supply"] is True
    assert len(answer["persisted"]) == 1
    written = answer["persisted"][0]
    assert written["provider_key"] == "amap-web-service"
    assert written["provider_item_id"] == "B000A83M61"
    assert written["coordinate_system"] == "WGS84"
    assert written["source_coordinate_system"] == "GCJ02"

    # The catalogue read the rest of the product already uses reaches the new row unchanged: the
    # provider blacklist names server-owned schedule rows, not provider-discovered places.
    listed = client.get("/api/v1/places", params={"city_code": TEST_CITY})
    assert listed.status_code == 200, listed.text
    assert [row["id"] for row in listed.json()] == [written["place_id"]]
    assert listed.json()[0]["source_coordinate_system"] == "GCJ02"


def test_the_same_provider_item_discovered_twice_is_one_row_at_its_newest_position(monkeypatch, client, session):
    _patch_providers(monkeypatch, [_amap_row(latitude=39.08505)])
    first = client.post(
        "/api/v1/places/discover",
        json={"query": "天津博物馆", "city_code": TEST_CITY, "region": "天津市"},
    )
    assert first.status_code == 200, first.text

    _patch_providers(monkeypatch, [_amap_row(latitude=39.08510)])
    second = client.post(
        "/api/v1/places/discover",
        json={"query": "天津博物馆", "city_code": TEST_CITY, "region": "天津市"},
    )
    assert second.status_code == 200, second.text

    count = session.scalar(
        select(func.count()).select_from(Place).where(Place.provider_key == "amap-web-service")
    )
    assert count == 1
    row = session.scalar(
        select(Place).where(Place.external_id == "B000A83M61")
    )
    assert row.latitude == pytest.approx(39.08510)
    assert first.json()["persisted"][0]["place_id"] == second.json()["persisted"][0]["place_id"]


def test_a_lead_the_provider_could_not_locate_is_answered_but_not_stored(monkeypatch, client, session):
    located = _amap_row()
    unlocated = {"provider_item_id": "B-NOWHERE", "name": "只有名字", "coordinate_system": "WGS84"}
    _patch_providers(monkeypatch, [located, unlocated])

    response = client.post(
        "/api/v1/places/discover",
        json={"query": "天津博物馆", "city_code": TEST_CITY, "region": "天津市"},
    )

    assert response.status_code == 200, response.text
    answer = response.json()
    assert [lead["provider_item_id"] for lead in answer["leads"]] == ["B000A83M61", "B-NOWHERE"]
    assert [row["provider_item_id"] for row in answer["persisted"]] == ["B000A83M61"]
    assert "position" in answer["unknown_fields"]
    count = session.scalar(select(func.count()).select_from(Place))
    assert count == 1


def test_persist_false_is_a_pure_read(monkeypatch, client, session):
    _patch_providers(monkeypatch, [_amap_row()])

    response = client.post(
        "/api/v1/places/discover",
        json={"query": "天津博物馆", "city_code": TEST_CITY, "region": "天津市", "persist": False},
    )

    assert response.status_code == 200, response.text
    assert response.json()["leads"]
    assert response.json()["persisted"] == []
    assert session.scalar(select(func.count()).select_from(Place)) == 0


def test_an_internal_city_code_is_refused_before_any_provider_is_built(monkeypatch, client):
    monkeypatch.setenv(AMAP_KEY_ENV, "0123456789abcdef0123456789abcdef")
    calls = _patch_providers(monkeypatch, [])

    response = client.post(
        "/api/v1/places/discover",
        json={"query": "天津博物馆", "city_code": "CN-12-01", "region": "CN-12-01"},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["reason_code"] == "AMAP_REGION_UNUSABLE", response.text
    assert calls["build"] == 0, "a region Amap would silently ignore still reached the provider chain"
