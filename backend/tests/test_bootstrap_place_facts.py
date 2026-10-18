"""Signed API + persisted receipt tests; OSM responses below are TEST_FIXTURE."""
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main
from app.core.config import settings
from app.db.models import JourneyMember, ProviderCall, RealPlaceCandidate
from app.db.session import SessionLocal
from app.execution import bootstrap_place_facts as facts
from app.execution import bootstrap_discovery as discovery


@pytest.fixture
def enabled_settings():
    previous = {key: getattr(settings, key) for key in ("traveler_auth_secret", "real_city_enabled", "real_city_mode")}
    for key, value in {"traveler_auth_secret": uuid4().hex + uuid4().hex,
                       "real_city_enabled": True, "real_city_mode": "live"}.items():
        object.__setattr__(settings, key, value)
    try:
        yield
    finally:
        for key, value in previous.items():
            object.__setattr__(settings, key, value)


@pytest.fixture
def signed_place(enabled_settings):
    with TestClient(main.app) as client:
        owner = client.post("/api/v1/travelers", json={"display_name": "TEST_FIXTURE facts owner", "timezone": "Asia/Shanghai"}).json()
        outsider = client.post("/api/v1/travelers", json={"display_name": "TEST_FIXTURE facts outsider", "timezone": "Asia/Shanghai"}).json()
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        journey = client.post("/api/v1/journeys", headers=headers, json={
            "traveler_id": owner["id"], "title": "TEST_FIXTURE place details", "city_code": uuid4().hex,
            "timezone": "Asia/Shanghai", "start_at": "2026-11-01T09:00:00+08:00",
            "end_at": "2026-11-01T18:00:00+08:00", "budget": {"amount_minor": 50000, "currency": "CNY"},
        })
        assert journey.status_code == 201, journey.text
        journey_id = journey.json()["id"]
        receipt_id, candidate_id = str(uuid4()), str(uuid4())
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            member = session.scalar(select(JourneyMember).where(JourneyMember.journey_id == journey_id))
            scope = {"member_id": member.id, "traveler_id": owner["id"], "receipt_id": receipt_id,
                     "expires_at": (now + timedelta(hours=1)).isoformat(), "captured_at": now.isoformat(),
                     "source_kind": "MANUAL_PUBLIC_CENTER", "provider_provenance": "LIVE_PROVIDER",
                     "opening_hours": {"status": "UNKNOWN"}, "cost_evidence": {"status": "UNKNOWN"},
                     "osm_tags": {"name": "TEST_FIXTURE park"}, "observed_name": "TEST_FIXTURE park",
                     "latitude": 31.2, "longitude": 121.4}
            # A second member's observation must survive owner enrichment unchanged.
            other_scope = {**scope, "member_id": str(uuid4()), "traveler_id": outsider["id"],
                           "receipt_id": str(uuid4()), "observed_name": "OTHER_MEMBER_ORIGINAL"}
            session.add(RealPlaceCandidate(
                id=candidate_id, journey_id=journey_id, provider_key="photon", external_id="photon:way/8123",
                city_code=journey.json()["city_code"], name="TEST_FIXTURE park", category="park",
                latitude=31.2, longitude=121.4, captured_at=now.isoformat(), expires_at=scope["expires_at"],
                evidence_json=json.dumps({"bootstrap": True, "bootstrap_scopes": [scope, other_scope]}),
                status="BOOTSTRAP_PRIVATE",
            ))
            session.commit()
        yield client, headers, {"Authorization": f"Bearer {outsider['access_token']}"}, journey_id, candidate_id, receipt_id, other_scope


@pytest.mark.parametrize("tags,expected,blocker", [
    ({"opening_hours": "24/7", "fee": "no"}, "READY_FOR_NATIVE_PLAN", None),
    ({"opening_hours": "24/7", "charge": "20 CNY"}, "READY_FOR_NATIVE_PLAN", None),
    ({}, "OPENING_UNVERIFIED", "OPENING_UNVERIFIED"),
    ({"opening_hours": "24/7", "fee": "no", "access": "private"}, "OPENING_UNVERIFIED", "ACCESS_RESTRICTED"),
])
def test_signed_details_persist_only_owner_and_keep_missing_facts(monkeypatch, signed_place, tags, expected, blocker):
    client, headers, outsider, journey_id, candidate_id, receipt_id, other_scope = signed_place
    calls = []
    monkeypatch.setattr(facts, "read_osm_tags", lambda *identity: calls.append(identity) or tags)
    path = f"/api/v1/journeys/{journey_id}/bootstrap-discovery/facts"
    body = {"receipt_id": receipt_id, "candidate_id": candidate_id, "provider_consent": True}
    assert client.post(path, json=body).status_code == 401
    assert client.post(path, json=body, headers=outsider).status_code == 403
    assert client.post(path, json={**body, "provider_consent": False}, headers=headers).status_code == 422
    assert client.post(path, json={**body, "receipt_id": str(uuid4())}, headers=headers).status_code == 403
    assert calls == []
    result = client.post(path, json=body, headers=headers)
    assert result.status_code == 200, result.text
    place = result.json()["candidate"]
    assert place["selection_state"] == expected
    assert place["facts_status"] == "SUCCESS"
    assert place["opening_source"] == "OpenStreetMap element API"
    if blocker:
        assert blocker in place["selection_blockers"]
    assert "no-store" in result.headers["cache-control"]
    assert client.post(path, json=body, headers=headers).json()["cached"] is True
    assert calls == [("way", "8123")]
    with SessionLocal() as session:
        row = session.get(RealPlaceCandidate, candidate_id)
        scopes = json.loads(row.evidence_json)["bootstrap_scopes"]
        assert next(scope for scope in scopes if scope["member_id"] == other_scope["member_id"])["observed_name"] == "OTHER_MEMBER_ORIGINAL"
        assert discovery._candidate_payload(row, member_id=other_scope["member_id"], traveler_id=other_scope["traveler_id"])["facts_status"] is None
        assert row.materialized_place_id is None
        audit = session.scalars(select(ProviderCall).where(ProviderCall.operation == "bootstrap_place_facts")).all()
        matching = [entry for entry in audit if entry.created_at == place["opening_observed_at"]]
        assert len(matching) == 1
        assert owner_private_ids_absent(matching[0], headers, journey_id)


def owner_private_ids_absent(audit, headers, journey_id):
    serialized = audit.request_json + audit.response_json
    return headers["Authorization"] not in serialized and journey_id not in serialized


def test_signed_named_search_dispatches_once_and_restores_private_receipt(monkeypatch, signed_place):
    from app.integrations.discovery.photon_poi import PhotonPOIProvider

    client, headers, outsider, journey_id, *_ = signed_place
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"features": [{
            "type": "Feature", "geometry": {"type": "Point", "coordinates": [121.4, 31.2]},
            "properties": {"name": "TEST_FIXTURE named museum", "osm_type": "W", "osm_id": 991223,
                           "osm_key": "tourism", "osm_value": "museum", "countrycode": "cn"},
        }]})

    monkeypatch.setattr(discovery, "_bootstrap_discovery_provider_config", lambda: {
        "provider": "photon", "provider_name": "Photon POI search",
        "expected_recipient": "Photon by Komoot public geocoding service", "base_url": "https://photon.komoot.io",
    })
    monkeypatch.setattr(discovery, "_bootstrap_live_endpoint_block_reason", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(discovery, "PhotonPOIProvider", lambda **_kwargs: PhotonPOIProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    ))
    path = f"/api/v1/journeys/{journey_id}/bootstrap-discovery"
    body = {"query": "TEST_FIXTURE named museum", "query_mode": "name", "radius_m": 2500, "limit": 3,
            "source_kind": "MANUAL_PUBLIC_CENTER", "latitude": 31.2, "longitude": 121.4,
            "coordinate_system": "WGS84", "mode": "live", "provider_consent": True, "consented_provider": "photon"}
    assert client.post(path, json=body).status_code == 401
    assert client.post(path, json=body, headers=outsider).status_code == 403
    assert client.post(path, json={**body, "provider_consent": False}, headers=headers).status_code == 422
    assert requests == []
    response = client.post(path, json=body, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "LIVE_RESULTS"  # Contract label under MockTransport, not live evidence.
    assert len(result["candidates"]) == 1
    assert len(requests) == 1
    assert requests[0].url.path == "/api/"
    assert requests[0].url.params["q"] == body["query"]
    assert "bbox" in requests[0].url.params
    restored = client.get(path + "/current", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["receipt_id"] == result["receipt_id"]
    assert restored.json()["candidates"][0]["name"] == "TEST_FIXTURE named museum"
    assert len(requests) == 1
    assert client.get(path + "/current", headers=outsider).status_code == 403


def test_failed_details_leave_prior_facts_and_do_not_retry(monkeypatch, signed_place):
    client, headers, _, journey_id, candidate_id, receipt_id, _other = signed_place
    calls = []
    def unavailable(*_identity):
        calls.append(1)
        raise httpx.ReadTimeout("TEST_FIXTURE timeout")
    monkeypatch.setattr(facts, "read_osm_tags", unavailable)
    body = {"receipt_id": receipt_id, "candidate_id": candidate_id, "provider_consent": True}
    path = f"/api/v1/journeys/{journey_id}/bootstrap-discovery/facts"
    result = client.post(path, json=body, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()["candidate"]["facts_status"] == "UNAVAILABLE"
    assert result.json()["candidate"]["opening_state"] == "UNKNOWN"
    assert client.post(path, json=body, headers=headers).json()["cached"] is True
    assert calls == [1]
    with SessionLocal() as session:
        scope = json.loads(session.get(RealPlaceCandidate, candidate_id).evidence_json)["bootstrap_scopes"][0]
        assert scope["osm_facts"]["failure_code"] == "OSM_TIMEOUT"


def test_search_restore_is_signed_scoped_expiring_and_never_fetches_provider(monkeypatch, signed_place):
    client, headers, outsider, journey_id, candidate_id, receipt_id, _other = signed_place
    def unexpected_io(*_args):
        raise AssertionError("Readonly restore must not fetch a provider")
    monkeypatch.setattr(facts, "read_osm_tags", unexpected_io)
    path = f"/api/v1/journeys/{journey_id}/bootstrap-discovery/current"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=outsider).status_code == 403
    result = client.get(path, headers=headers)
    assert result.status_code == 200
    assert result.json()["receipt_id"] == receipt_id
    assert [item["candidate_id"] for item in result.json()["candidates"]] == [candidate_id]
    assert result.json()["candidates"][0]["name"] != "OTHER_MEMBER_ORIGINAL"
    assert result.json()["result_state"] == "PARTIAL_1"
    assert "no-store" in result.headers["cache-control"]
    with SessionLocal() as session:
        row = session.get(RealPlaceCandidate, candidate_id)
        evidence = json.loads(row.evidence_json)
        evidence["bootstrap_scopes"][0]["expires_at"] = "2000-01-01T00:00:00+00:00"
        row.evidence_json = json.dumps(evidence)
        session.commit()
    assert client.get(path, headers=headers).json() is None


def test_enriched_place_enters_existing_native_plan_generator(monkeypatch, signed_place):
    client, headers, _, journey_id, candidate_id, receipt_id, _other = signed_place
    monkeypatch.setattr(facts, "read_osm_tags", lambda *_: {"opening_hours": "24/7", "fee": "no"})
    body = {"receipt_id": receipt_id, "candidate_id": candidate_id}
    base = f"/api/v1/journeys/{journey_id}"
    refreshed = client.post(base + "/bootstrap-discovery/facts", headers=headers,
                            json={**body, "provider_consent": True})
    assert refreshed.status_code == 200, refreshed.text
    selected = client.post(base + "/bootstrap-discovery/select", headers=headers, json=body)
    assert selected.status_code == 200, selected.text
    generated = client.post(base + "/plans/generate", headers={**headers, "Idempotency-Key": str(uuid4())}, json={
        "candidate_count": 1, "place_ids": [selected.json()["selected_place_id"]],
        "allow_single_place": True, "allow_unknown_cost": True,
    })
    assert generated.status_code == 201, generated.text
    assert len(generated.json()) == 1
    assert generated.json()[0]["activities"]
    restored = client.get(base + "/plans", headers=headers)
    assert restored.status_code == 200
    assert restored.json()[0]["id"] == generated.json()[0]["id"]


@pytest.mark.parametrize("element", [
    {"type": "way", "id": 8123, "tags": {"opening_hours": "24/7", "user": "OMIT"}},
    {"type": "way", "id": 999, "tags": {}},
])
def test_osm_reader_binds_identity_and_projects_only_fact_tags(monkeypatch, element):
    real_client = httpx.Client
    def respond(request):
        assert str(request.url) == "https://api.openstreetmap.org/api/0.6/way/8123.json"
        assert "Authorization" not in request.headers
        return httpx.Response(200, json={"elements": [element]})
    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(facts.httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs))
    if element["id"] == 999:
        with pytest.raises(ValueError):
            facts.read_osm_tags("way", "8123")
    else:
        assert facts.read_osm_tags("way", "8123") == {"opening_hours": "24/7"}
