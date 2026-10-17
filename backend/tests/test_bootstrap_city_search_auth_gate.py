from __future__ import annotations

from uuid import uuid4

from app.core.config import settings
from app.execution import bootstrap_discovery as discovery
from test_bootstrap_filter_summary_route import (
    TEST_SECRET,
    _new_journey,
    _new_traveler,
    client as TEST_CLIENT,
)


def test_city_search_rejects_signed_nonmember_before_geocoder_creation(monkeypatch):
    """A valid bearer without Journey membership gets 403 before geocoding."""
    previous_secret = settings.traveler_auth_secret
    previous_real_city_enabled = settings.real_city_enabled
    previous_real_city_mode = settings.real_city_mode
    suffix = uuid4().hex
    private_query = "PRIVATE_CITY_SEARCH_SENTINEL 31.248631,121.913579"
    provider_constructors: list[str] = []

    def fail_if_provider_constructed(*_args, **_kwargs):
        provider_constructors.append("constructed")
        raise AssertionError("city provider constructed before member authorization")

    try:
        object.__setattr__(settings, "traveler_auth_secret", TEST_SECRET)
        object.__setattr__(settings, "real_city_enabled", True)
        object.__setattr__(settings, "real_city_mode", "live")

        owner = _new_traveler(f"City search owner {suffix}")
        nonmember = _new_traveler(f"City search nonmember {suffix}")
        journey = _new_journey(owner["id"], suffix)

        # If authorization regresses, service-side gates must allow execution to
        # reach the sentinel, while no real provider or network can be used.
        monkeypatch.setattr(
            discovery,
            "_city_search_config",
            lambda: ("nominatim", "http://127.0.0.1:8765", "test-only-agent"),
        )
        monkeypatch.setattr(discovery, "_city_search_cache_get", lambda *_a, **_k: None)
        monkeypatch.setattr(
            discovery, "_bootstrap_rate_limited", lambda *_a, **_k: False
        )
        monkeypatch.setattr(
            discovery, "_reserve_city_search_global_slot", lambda *_a, **_k: True
        )
        monkeypatch.setattr(
            discovery, "NominatimGeocoder", fail_if_provider_constructed
        )
        monkeypatch.setattr(
            discovery, "PhotonCityGeocoder", fail_if_provider_constructed
        )

        response = TEST_CLIENT.post(
            f"/api/v1/journeys/{journey['id']}/bootstrap-city-search",
            headers={"Authorization": f"Bearer {nonmember['access_token']}"},
            json={
                "query": private_query,
                "provider_consent": True,
                "limit": 3,
            },
        )

        assert response.status_code == 403, response.text
        assert provider_constructors == []
        for private_value in (
            private_query,
            "PRIVATE_CITY_SEARCH_SENTINEL",
            "31.248631",
            "121.913579",
        ):
            assert private_value not in response.text
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)
        object.__setattr__(settings, "real_city_enabled", previous_real_city_enabled)
        object.__setattr__(settings, "real_city_mode", previous_real_city_mode)


def test_traveler_session_returns_identity_from_signed_bearer_only(monkeypatch):
    """The browser can recover its paired ID without trusting a client-supplied traveler ID."""
    previous_secret = settings.traveler_auth_secret
    suffix = uuid4().hex
    try:
        object.__setattr__(settings, "traveler_auth_secret", TEST_SECRET)
        traveler = _new_traveler(f"Session identity {suffix}")

        unauthenticated = TEST_CLIENT.get("/api/v1/travelers/session")
        assert unauthenticated.status_code == 401

        response = TEST_CLIENT.get(
            "/api/v1/travelers/session",
            headers={"Authorization": f"Bearer {traveler['access_token']}"},
        )

        assert response.status_code == 200, response.text
        assert response.json() == {"traveler_id": traveler["id"]}
        assert response.headers["cache-control"] == "private, no-store, max-age=0"
        assert response.headers["vary"] == "Authorization, X-CityNexus-Traveler-Token"
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)
