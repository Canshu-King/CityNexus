from __future__ import annotations

import ipaddress
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.db.models import Place, RealPlaceCandidate
from app.db.session import SessionLocal, ensure_schema
from app.fact_acquisition import (
    _safe_get,
    _validate_public_http_url,
    _search_fact_candidates,
    _acquire_overpass_payload,
    acquire_place_facts,
)
from app.services import _mobility_catalogue_place_ids


class _Response:
    def __init__(self, payload, *, status_code: int = 200, headers: dict | None = None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.text = ""

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_fact_acquisition_keeps_one_live_client_for_secondary_and_official_phases(monkeypatch):
    ensure_schema()
    city = f"R77-CLIENT-{uuid4().hex}"
    place_id = f"r77-place-{uuid4().hex}"
    journey = SimpleNamespace(id=f"journey-{uuid4().hex}", city_code=city)
    with SessionLocal() as session:
        place = Place(
            id=place_id,
            provider_key="overpass",
            external_id="overpass:node/123",
            city_code=city,
            name="Real viewpoint",
            category="viewpoint",
            latitude=27.7,
            longitude=98.6,
            opening_hours_json=json.dumps({"status": "UNKNOWN"}),
            tags_json="[]",
            metadata_json=json.dumps(
                {
                    "cost_evidence": {
                        "status": "KNOWN",
                        "amount_minor": 500,
                        "currency": "CNY",
                    },
                    "cost_minor": 500,
                    "price_known": True,
                }
            ),
            updated_at="2026-09-30T00:00:00+00:00",
        )
        session.add(place)
        session.commit()

        class Client:
            instances = []

            def __init__(self, **kwargs):
                self.closed = False
                self.__class__.instances.append(self)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.closed = True
                return False

            def post(self, *_args, **_kwargs):
                assert not self.closed
                return _Response(
                    {"elements": [{"type": "node", "id": 123, "tags": {"tourism": "viewpoint"}}]}
                )

            def get(self, url, *_args, **_kwargs):
                assert not self.closed
                assert "lookup" in url
                return _Response([{"osm_type": "node", "osm_id": 123, "extratags": {}}])

        monkeypatch.setattr("app.fact_acquisition.httpx.Client", Client)
        receipt = acquire_place_facts(session, journey)
        session.commit()

        refreshed = session.get(Place, place_id)
        metadata = json.loads(refreshed.metadata_json)
        assert receipt["status"] == "ACQUIRED"
        assert receipt["secondary_source"]["status"] == "ACQUIRED"
        assert receipt["places"][0]["secondary_source"]["matched_provider_entity"] is True
        assert metadata["cost_evidence"]["status"] == "UNKNOWN"
        assert metadata["cost_evidence"]["amount_minor"] is None
        assert metadata["price_known"] is False
        assert Client.instances[0].closed is True


def test_fact_acquisition_rotates_to_mirror_after_transport_failure(monkeypatch):
    from app import fact_acquisition

    monkeypatch.setattr(
        fact_acquisition,
        "settings",
        SimpleNamespace(overpass_url="https://primary.example/api"),
    )

    class Client:
        def __init__(self):
            self.calls = []

        def post(self, url, **_kwargs):
            self.calls.append(url)
            if len(self.calls) == 1:
                raise httpx.ReadTimeout("primary timed out")
            return _Response({"elements": [{"type": "node", "id": 456}]})

    client = Client()
    payload, endpoint, attempts = _acquire_overpass_payload(client, [("node", "456")])

    assert payload["elements"][0]["id"] == 456
    assert client.calls[:2] == [
        "https://primary.example/api/interpreter",
        "https://overpass-api.de/api/interpreter",
    ]
    assert endpoint == "https://overpass-api.de/api/interpreter"
    assert attempts[0]["answered"] is False
    assert attempts[0]["error"].startswith("ReadTimeout:")
    assert attempts[1]["answered"] is True
    assert attempts[1]["elements"] == 1


def test_strict_catalogue_mobility_excludes_unresolved_opening_rows():
    places = {
        "known-visit": SimpleNamespace(
            id="known-visit",
            category="attraction",
            opening_hours_json=json.dumps({"status": "NORMALIZED_VALID", "open": "09:00", "close": "17:00"}),
            metadata_json=json.dumps({}),
        ),
        "unknown-visit": SimpleNamespace(
            id="unknown-visit",
            category="attraction",
            opening_hours_json=json.dumps({"status": "UNKNOWN"}),
            metadata_json=json.dumps({}),
        ),
        "lodging": SimpleNamespace(
            id="lodging",
            category="hotel",
            opening_hours_json=json.dumps({"status": "NORMALIZED_VALID", "open": "00:00", "close": "24:00"}),
            metadata_json=json.dumps({}),
        ),
    }

    assert _mobility_catalogue_place_ids(places, [], []) == ("known-visit",)


def test_official_source_boundary_rejects_private_targets_and_redirects(monkeypatch):
    with pytest.raises(ValueError, match="OFFICIAL_SOURCE_PRIVATE_TARGET"):
        _validate_public_http_url("http://127.0.0.1:8080/facts")

    from app import fact_acquisition

    original_resolve = fact_acquisition._resolved_public_addresses

    def resolve(hostname):
        if hostname == "example.com":
            return {ipaddress.ip_address("93.184.216.34")}
        return original_resolve(hostname)

    monkeypatch.setattr("app.fact_acquisition._resolved_public_addresses", resolve)

    class RedirectClient:
        def get(self, *_args, **_kwargs):
            return _Response({}, status_code=302, headers={"location": "http://127.0.0.1/secret"})

    with pytest.raises(ValueError, match="OFFICIAL_SOURCE_PRIVATE_TARGET"):
        _safe_get(RedirectClient(), "https://example.com/facts", retrieved_at="now")


def test_search_source_returns_structured_candidates_without_authority(monkeypatch):
    from app import fact_acquisition
    from app.integrations.web.searxng import SearXNGObservation

    monkeypatch.setattr(
        fact_acquisition,
        "settings",
        SimpleNamespace(searxng_url="https://search.example.test"),
    )

    class Provider:
        def __init__(self, base_url, *, client):
            assert base_url == "https://search.example.test"

        def search(self, query, *, limit):
            assert '"way/1417996052"' in query
            assert limit == 5
            return (
                SearXNGObservation(
                    query=query,
                    url="https://example.gov.cn/park",
                    title="贡山县总体国家安全观主题公园",
                    domain="example.gov.cn",
                    content="开放时间：09:00-17:00；门票：30元",
                    captured_at="2026-09-25T00:00:00+00:00",
                ),
            )

        def close(self):
            return None

    monkeypatch.setattr(fact_acquisition, "SearXNGSearchProvider", Provider)
    result = _search_fact_candidates(
        object(),
        SimpleNamespace(name="贡山县总体国家安全观主题公园", external_id="overpass:way/1417996052"),
        SimpleNamespace(city_code="OSM:R:2729765"),
        retrieved_at="2026-09-25T00:00:01+00:00",
    )
    assert result["status"] == "CANDIDATES_FOUND"
    assert result["opening_hours"]["status"] == "SEARCH_CANDIDATE"
    assert result["cost_evidence"]["status"] == "SEARCH_CANDIDATE"
    assert result["cost_evidence"]["amount_minor"] == 3000
    assert result["observations"][0]["authority_status"] == "SEARCH_CANDIDATE"


def test_search_candidate_never_overwrites_unknown_place_facts(monkeypatch):
    from app import fact_acquisition
    from app.integrations.web.searxng import SearXNGObservation

    monkeypatch.setattr(
        fact_acquisition,
        "settings",
        SimpleNamespace(
            overpass_url="https://overpass.example/api",
            nominatim_url="https://nominatim.example",
            searxng_url="https://search.example",
        ),
    )

    class Response:
        def __init__(self, payload):
            self.payload = payload
            self.status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Client:
        def __init__(self, **kwargs):
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True
            return False

        def post(self, *args, **kwargs):
            assert not self.closed
            return Response({"elements": [{"type": "node", "id": 177, "tags": {"tourism": "viewpoint"}}]})

        def get(self, *args, **kwargs):
            assert not self.closed
            return Response([{"osm_type": "node", "osm_id": 177, "extratags": {}}])

    class Provider:
        def __init__(self, base_url, *, client):
            assert base_url == "https://search.example"

        def search(self, query, *, limit):
            return (
                SearXNGObservation(
                    query=query,
                    url="https://example.gov.cn/park",
                    title="贡山县总体国家安全观主题公园",
                    domain="example.gov.cn",
                    content="开放时间：09:00-17:00；门票：30元",
                    captured_at="2026-09-25T00:00:00+00:00",
                ),
            )

        def close(self):
            return None

    monkeypatch.setattr("app.fact_acquisition.httpx.Client", Client)
    monkeypatch.setattr(fact_acquisition, "SearXNGSearchProvider", Provider)
    ensure_schema()
    place_id = f"r77-search-{uuid4().hex}"
    with SessionLocal() as session:
        place = Place(
            id=place_id,
            provider_key="overpass",
            external_id="overpass:node/177",
            city_code="OSM:R:2729765",
            name="贡山县总体国家安全观主题公园",
            category="viewpoint",
            latitude=27.7,
            longitude=98.6,
            opening_hours_json=json.dumps({"status": "UNKNOWN"}),
            tags_json="[]",
            metadata_json=json.dumps({}),
            updated_at="2026-09-25T00:00:00+00:00",
        )
        session.add(place)
        session.commit()
        receipt = acquire_place_facts(
            session,
            SimpleNamespace(id=f"journey-{uuid4().hex}", city_code="OSM:R:2729765"),
        )
        session.commit()
        refreshed = session.get(Place, place_id)
        metadata = json.loads(refreshed.metadata_json)
        assert receipt["search_source"]["status"] == "CANDIDATES_FOUND"
        assert metadata["fact_acquisition"]["search_source"]["cost_evidence"]["status"] == "SEARCH_CANDIDATE"
        assert metadata["cost_evidence"]["status"] == "UNKNOWN"
        assert metadata["cost_evidence"]["amount_minor"] is None
        assert metadata["price_known"] is False
        assert json.loads(refreshed.opening_hours_json)["status"] == "UNKNOWN"
        session.delete(refreshed)
        session.commit()


def test_live_discovery_cache_is_keyed_by_the_provider_question():
    from app.integrations.discovery.real_city import _unexpired_cached_candidates

    ensure_schema()
    city = f"R77-CACHE-{uuid4().hex}"
    journey_id = None
    place_id = f"r77-cache-place-{uuid4().hex}"
    captured_at = datetime.now(timezone.utc).isoformat()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    with SessionLocal() as session:
        session.add(
            Place(
                id=place_id,
                provider_key="overpass",
                external_id=f"overpass:node/{uuid4().int % 100000000}",
                city_code=city,
                name="Question-keyed viewpoint",
                category="viewpoint",
                latitude=27.7,
                longitude=98.6,
                opening_hours_json=json.dumps({"status": "UNKNOWN"}),
                tags_json="[]",
                metadata_json=json.dumps({"cost_evidence": {"status": "UNKNOWN"}}),
                updated_at=captured_at,
            )
        )
        session.add(
            RealPlaceCandidate(
                id=f"rpc-{uuid4().hex}",
                journey_id=journey_id,
                provider_key="overpass",
                external_id="overpass:node/987654321",
                city_code=city,
                name="Question-keyed viewpoint",
                category="viewpoint",
                latitude=27.7,
                longitude=98.6,
                tags_json="[]",
                opening_hours_json=json.dumps({"status": "UNKNOWN"}),
                metadata_json=json.dumps({"cost_evidence": {"status": "UNKNOWN"}}),
                captured_at=captured_at,
                expires_at=expires_at,
                distance_m=12.0,
                evidence_json=json.dumps({"request": {"query": "park"}}),
                materialized_place_id=place_id,
                status="DISCOVERED",
            )
        )
        session.commit()
        journey = SimpleNamespace(id=journey_id, city_code=city)
        assert _unexpired_cached_candidates(session, journey, "park", None)
        assert _unexpired_cached_candidates(session, journey, "viewpoint", None) is None


def test_real_catalogue_fallback_is_visible_but_not_selectable():
    from fastapi.testclient import TestClient

    from app.main import app

    ensure_schema()
    city = f"R77-CATALOGUE-{uuid4().hex}"
    with SessionLocal() as session:
        session.add_all(
            [
                Place(
                    id=f"{city}-park",
                    provider_key="overpass",
                    external_id=f"overpass:node/{uuid4().int % 100000000}",
                    city_code=city,
                    name="Provider park",
                    category="park",
                    latitude=27.73,
                    longitude=98.67,
                    opening_hours_json=json.dumps({"status": "UNKNOWN"}),
                    tags_json="[]",
                    metadata_json=json.dumps({"cost_evidence": {"status": "UNKNOWN"}, "price_known": False}),
                    updated_at="2026-09-30T00:00:00+00:00",
                ),
                Place(
                    id=f"{city}-viewpoint",
                    provider_key="overpass",
                    external_id=f"overpass:node/{uuid4().int % 100000000}",
                    city_code=city,
                    name="Provider viewpoint",
                    category="viewpoint",
                    latitude=27.74,
                    longitude=98.68,
                    opening_hours_json=json.dumps({"status": "UNKNOWN"}),
                    tags_json="[]",
                    metadata_json=json.dumps({"cost_evidence": {"status": "UNKNOWN"}, "price_known": False}),
                    updated_at="2026-09-30T00:00:00+00:00",
                ),
            ]
        )
        session.commit()
    client = TestClient(app)
    traveler = client.post(
        "/api/v1/travelers",
        json={"display_name": "R77 test", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    ).json()
    journey = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": traveler["id"],
            "title": "R77 catalogue",
            "city_code": city,
            "timezone": "Asia/Shanghai",
            "start_at": "2026-10-03T09:00:00+08:00",
            "end_at": "2026-10-03T20:00:00+08:00",
            "budget": {"amount_minor": 100000, "currency": "CNY"},
        },
    ).json()
    generated = client.post(
        f"/api/v1/journeys/{journey['id']}/plans/generate",
        json={"candidate_count": 1},
    )
    assert generated.status_code == 201, generated.text
    plan = generated.json()[0]
    assert plan["selectable"] is False
    assert plan["explanation"]["authority_state"] == "PROVISIONAL_UNRESOLVED_FACTS"
    assert all(item["cost_status"] == "UNKNOWN" for item in plan["activities"])
    selected = client.post(
        f"/api/v1/journeys/{journey['id']}/plans/{plan['id']}/select"
    )
    assert selected.status_code == 409, selected.text
    assert selected.json()["error"]["reason_code"] == "UNRESOLVED_ACTIVITY_FACTS"
