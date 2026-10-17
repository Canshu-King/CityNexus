from __future__ import annotations

import json
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import settings
from app.execution import bootstrap_discovery as discovery
from app.integrations.discovery.real_city import DiscoveryCandidate


client = TestClient(main_module.app)
TEST_SECRET = "bootstrap-filter-summary-route-test-secret-0123456789"
_FILTER_REASONS = (
    "provider_mismatch",
    "invalid_identity",
    "missing_name",
    "invalid_coordinates",
    "invalid_distance",
    "out_of_radius",
    "restricted_access",
    "duplicate",
)


def _new_traveler(name: str) -> dict:
    response = client.post(
        "/api/v1/travelers",
        json={"display_name": name, "timezone": "Asia/Shanghai", "locale": "en-GB"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _new_journey(traveler_id: str, suffix: str) -> dict:
    response = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": traveler_id,
            "title": f"Bootstrap filter summary route {suffix}",
            "city_code": f"CN-BFS-{suffix[:8].upper()}",
            "timezone": "Asia/Shanghai",
            "start_at": "2030-10-13T10:00:00+08:00",
            "end_at": "2030-10-14T18:00:00+08:00",
            "budget": {"amount_minor": 10000, "currency": "CNY"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_signed_draft_bootstrap_route_returns_counts_only_filter_summary(monkeypatch):
    previous_secret = settings.traveler_auth_secret
    suffix = uuid4().hex
    private_name = "PRIVATE_FILTER_SUMMARY_PLACE_SENTINEL"
    private_tag = "PRIVATE_FILTER_SUMMARY_TAG_SENTINEL"
    provider_candidate = DiscoveryCandidate(
        provider_key="photon",
        external_id="photon:way/912345",
        name=private_name,
        category="museum",
        latitude=31.2304,
        longitude=121.4737,
        tags=("museum", "private"),
        opening_hours={"status": "UNKNOWN"},
        metadata={
            "tags": {
                "name": private_name,
                "tourism": "museum",
                "access": "private",
                "fixture_marker": private_tag,
            }
        },
        distance_m=45.0,
        cost_evidence={"status": "UNKNOWN"},
    )

    class _PhotonFixture:
        base_url = "http://127.0.0.1:8765"
        closed = False

        def search_with_evidence(self, *_args, **kwargs):
            assert kwargs["max_attempts"] == 1
            return [provider_candidate], [
                {
                    "endpoint": f"{self.base_url}/reverse",
                    "answered": True,
                    "http_status": 200,
                    "features": 1,
                    "returned": 1,
                    "private_detail": "PRIVATE_FILTER_SUMMARY_ATTEMPT_SENTINEL",
                }
            ]

        def close(self):
            self.closed = True

    provider = _PhotonFixture()
    try:
        object.__setattr__(settings, "traveler_auth_secret", TEST_SECRET)
        monkeypatch.setattr(
            discovery,
            "_bootstrap_discovery_provider_config",
            lambda: {
                "provider": "photon",
                "provider_name": "Photon POI search",
                "expected_recipient": "Photon by Komoot public geocoding service",
                "base_url": provider.base_url,
            },
        )
        monkeypatch.setattr(
            discovery,
            "bootstrap_discovery_readiness",
            lambda **_kwargs: {
                "provider": "photon",
                "provider_name": "Photon POI search",
                "expected_recipient": "Photon by Komoot public geocoding service",
                "external_request_allowed": True,
                "test_only": True,
                "capability_state": "TEST_ONLY",
                "status": "READY",
                "reason_code": "READY",
                "provider_grade": "TEST_PROVIDER",
            },
        )
        monkeypatch.setattr(
            discovery, "_bootstrap_rate_limited", lambda *_args, **_kwargs: False
        )
        monkeypatch.setattr(discovery, "PhotonPOIProvider", lambda **_kwargs: provider)

        traveler = _new_traveler(f"Filter summary route {suffix}")
        journey = _new_journey(traveler["id"], suffix)
        assert journey["status"] == "DRAFT"

        response = client.post(
            f"/api/v1/journeys/{journey['id']}/bootstrap-discovery",
            headers={"Authorization": f"Bearer {traveler['access_token']}"},
            json={
                "query": "museum",
                "radius_m": 2500,
                "limit": 3,
                "source_kind": "MANUAL_PUBLIC_CENTER",
                "provider_consent": True,
                "consented_provider": "photon",
                "latitude": 31.2304,
                "longitude": 121.4737,
                "coordinate_system": "WGS84",
                "mode": "live",
            },
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "LIVE_ZERO_RESULTS"
        assert body["attempts"][0]["returned"] == 1
        assert body["candidates"] == []
        expected_rejections = {reason: 0 for reason in _FILTER_REASONS}
        expected_rejections["restricted_access"] = 1
        assert body["filter_summary"] == {
            "raw_count": 1,
            "accepted_count": 0,
            "rejected_by_reason": expected_rejections,
        }
        assert set(body["filter_summary"]) == {
            "raw_count",
            "accepted_count",
            "rejected_by_reason",
        }
        count_values = [
            body["filter_summary"]["raw_count"],
            body["filter_summary"]["accepted_count"],
            *body["filter_summary"]["rejected_by_reason"].values(),
        ]
        assert all(type(value) is int and value >= 0 for value in count_values)

        response_json = json.dumps(body, ensure_ascii=False)
        for private_value in (
            private_name,
            private_tag,
            "fixture_marker",
            "PRIVATE_FILTER_SUMMARY_ATTEMPT_SENTINEL",
            "31.2304",
            "121.4737",
            '"access": "private"',
            '"osm_tags"',
            '"tags"',
        ):
            assert private_value not in response_json
        assert provider.closed is True
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)
