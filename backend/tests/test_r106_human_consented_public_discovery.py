from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.execution import bootstrap_discovery as discovery


def _set(name: str, value):
    object.__setattr__(settings, name, value)


def test_r106_live_capability_is_not_live_evidence():
    names = ("real_city_enabled", "real_city_mode", "overpass_url", "city_search_test_provider")
    previous = {name: getattr(settings, name) for name in names}
    try:
        _set("real_city_enabled", True)
        _set("real_city_mode", "live")
        _set("city_search_test_provider", False)
        _set("overpass_url", "https://overpass-api.de/api")
        readiness = discovery.bootstrap_discovery_readiness()
        assert readiness["status"] == "READY"
        assert readiness["capability_state"] == "LIVE_CAPABLE"
        assert readiness["provider_grade"] == "LIVE_CAPABLE"
        assert readiness["external_request_allowed"] is True
        assert "LIVE_VERIFIED" not in str(readiness)
    finally:
        for name, value in previous.items():
            _set(name, value)


def test_r106_private_dns_resolution_blocks_before_provider(monkeypatch):
    names = ("real_city_enabled", "real_city_mode", "overpass_url", "city_search_test_provider")
    previous = {name: getattr(settings, name) for name in names}
    provider = MagicMock()
    try:
        _set("real_city_enabled", True)
        _set("real_city_mode", "live")
        _set("city_search_test_provider", False)
        _set("overpass_url", "https://overpass-api.de/api")
        monkeypatch.setattr(
            discovery.socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(2, 1, 6, "", ("10.20.30.40", 443))],
        )
        monkeypatch.setattr(discovery, "OverpassPOIProvider", provider)
        session = MagicMock()
        session.scalar.return_value = None
        journey = SimpleNamespace(id="journey-r106", status="DRAFT", active_plan_version_id=None, city_code="Shanghai")
        result = discovery.discover_bootstrap_candidates(
            session,
            journey,
            member=SimpleNamespace(id="member-r106"),
            traveler_id="traveler-r106",
            query="art history",
            radius_m=2500,
            limit=3,
            source_kind="MANUAL_PUBLIC_CENTER",
            provider_consent=True,
            latitude=31.2304,
            longitude=121.4737,
            accuracy_m=None,
        )
        assert result["status"] == "PROVIDER_DISABLED"
        assert result["failure_code"] == "PROVIDER_PRIVATE_ADDRESS"
        provider.assert_not_called()
    finally:
        for name, value in previous.items():
            _set(name, value)


def test_r106_consent_and_gps_gates_precede_provider(monkeypatch):
    session = MagicMock()
    session.scalar.return_value = None
    journey = SimpleNamespace(id="journey-r106-gates", status="DRAFT", active_plan_version_id=None)
    provider = MagicMock()
    monkeypatch.setattr(discovery, "OverpassPOIProvider", provider)

    with pytest.raises(discovery.BootstrapDiscoveryError) as no_consent:
        discovery.discover_bootstrap_candidates(
            session,
            journey,
            member=SimpleNamespace(id="member-r106"),
            traveler_id="traveler-r106",
            query="art history",
            radius_m=2500,
            limit=3,
            source_kind="MANUAL_PUBLIC_CENTER",
            provider_consent=False,
            latitude=31.2304,
            longitude=121.4737,
            accuracy_m=None,
        )
    assert no_consent.value.code == "PROVIDER_CONSENT_REQUIRED"

    with pytest.raises(discovery.BootstrapDiscoveryError) as gps:
        discovery.discover_bootstrap_candidates(
            session,
            journey,
            member=SimpleNamespace(id="member-r106"),
            traveler_id="traveler-r106",
            query="art history",
            radius_m=2500,
            limit=3,
            source_kind="FOREGROUND_GPS",
            provider_consent=True,
            latitude=31.2304,
            longitude=121.4737,
            accuracy_m=15,
        )
    assert gps.value.code == "PUBLIC_CENTER_REQUIRED"
    provider.assert_not_called()
