from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from app.core.config import settings
from app.execution import bootstrap_discovery as discovery
from app.integrations.discovery.photon_poi import PhotonPOIProvider


def _set(name: str, value):
    object.__setattr__(settings, name, value)


def _photon_config() -> dict[str, str]:
    return {
        "provider": "photon",
        "provider_name": "Photon POI search",
        "expected_recipient": "Photon by Komoot public geocoding service",
        "base_url": "https://photon.komoot.io",
    }


@pytest.mark.parametrize(
    ("poi_provider", "geocoder_photon_enabled", "expected_provider"),
    [("overpass", True, "overpass"), ("photon", False, "photon")],
)
def test_poi_discovery_selection_is_independent_of_geocoder_flag(
    monkeypatch, poi_provider: str, geocoder_photon_enabled: bool, expected_provider: str
):
    monkeypatch.setattr(
        discovery,
        "ExternalProviderSettings",
        lambda: SimpleNamespace(
            poi_discovery_provider=poi_provider,
            photon_enabled=geocoder_photon_enabled,
            photon_base_url="https://photon.komoot.io",
        ),
    )

    assert discovery._bootstrap_discovery_provider_config()["provider"] == expected_provider


def test_photon_readiness_names_configured_recipient(monkeypatch):
    names = ("real_city_enabled", "real_city_mode")
    previous = {name: getattr(settings, name) for name in names}
    try:
        _set("real_city_enabled", True)
        _set("real_city_mode", "live")
        monkeypatch.setattr(discovery, "_bootstrap_discovery_provider_config", _photon_config)

        readiness = discovery.bootstrap_discovery_readiness()

        assert readiness["provider"] == "photon"
        assert readiness["expected_recipient"] == "Photon by Komoot public geocoding service"
        assert readiness["status"] == "READY"
        assert readiness["provider_grade"] == "LIVE_CAPABLE"
    finally:
        for name, value in previous.items():
            _set(name, value)


def test_exact_lookup_default_endpoint_remains_overpass_when_photon_is_selected(monkeypatch):
    previous = settings.overpass_url
    resolved_hosts: list[str] = []
    try:
        _set("overpass_url", "https://overpass-api.de/api")
        monkeypatch.setattr(
            discovery,
            "ExternalProviderSettings",
            lambda: SimpleNamespace(
                poi_discovery_provider="photon",
                photon_base_url="https://photon.komoot.io",
            ),
        )

        def resolve(host, *args, **kwargs):
            resolved_hosts.append(host)
            return [(2, 1, 6, "", ("8.8.8.8", 443))]

        monkeypatch.setattr(discovery.socket, "getaddrinfo", resolve)

        assert discovery._bootstrap_live_endpoint_block_reason() is None
        assert resolved_hosts == ["overpass-api.de"]
    finally:
        _set("overpass_url", previous)


def test_exact_shared_lookup_readiness_is_pinned_to_overpass(monkeypatch):
    names = ("real_city_enabled", "real_city_mode", "overpass_url")
    previous = {name: getattr(settings, name) for name in names}
    try:
        _set("real_city_enabled", True)
        _set("real_city_mode", "live")
        _set("overpass_url", "https://overpass-api.de/api")
        monkeypatch.setattr(discovery, "_bootstrap_discovery_provider_config", _photon_config)

        readiness = discovery.bootstrap_discovery_readiness(
            provider_config=discovery._bootstrap_overpass_provider_config()
        )

        assert readiness["provider"] == "overpass"
        assert readiness["expected_recipient"] == "OpenStreetMap/Overpass public map data service"
        assert readiness["status"] == "READY"
    finally:
        for name, value in previous.items():
            _set(name, value)


def test_changed_consent_provider_conflicts_before_dns_or_provider(monkeypatch):
    names = ("real_city_enabled", "real_city_mode")
    previous = {name: getattr(settings, name) for name in names}
    session = MagicMock()
    session.scalar.return_value = None
    photon = MagicMock()
    overpass = MagicMock()
    endpoint_check = MagicMock(return_value=None)
    try:
        _set("real_city_enabled", True)
        _set("real_city_mode", "live")
        monkeypatch.setattr(discovery, "_bootstrap_discovery_provider_config", _photon_config)
        monkeypatch.setattr(discovery, "_bootstrap_live_endpoint_block_reason", endpoint_check)
        monkeypatch.setattr(discovery, "PhotonPOIProvider", photon)
        monkeypatch.setattr(discovery, "OverpassPOIProvider", overpass)

        with pytest.raises(discovery.BootstrapDiscoveryError) as exc:
            discovery.discover_bootstrap_candidates(
                session,
                SimpleNamespace(id="journey-consent", status="DRAFT", active_plan_version_id=None),
                member=SimpleNamespace(id="member-consent"),
                traveler_id="traveler-consent",
                query="cafe",
                radius_m=2500,
                limit=3,
                source_kind="MANUAL_PUBLIC_CENTER",
                provider_consent=True,
                consented_provider="overpass",
                latitude=31.2,
                longitude=121.4,
                accuracy_m=None,
            )

        assert exc.value.code == "PROVIDER_CONSENT_PROVIDER_MISMATCH"
        assert exc.value.status_code == 409
        endpoint_check.assert_not_called()
        photon.assert_not_called()
        overpass.assert_not_called()
        session.add.assert_not_called()
    finally:
        for name, value in previous.items():
            _set(name, value)


def test_photon_failure_is_one_call_without_overpass_fallback(monkeypatch):
    names = ("real_city_enabled", "real_city_mode")
    previous = {name: getattr(settings, name) for name in names}
    session = MagicMock()
    session.scalar.return_value = None

    class FailingPhoton:
        base_url = "https://photon.komoot.io"

        def __init__(self):
            self.calls = 0
            self.closed = False
            self.attempt_limits: list[int | None] = []

        def search_with_evidence(self, *args, **kwargs):
            self.calls += 1
            self.attempt_limits.append(kwargs.get("max_attempts"))
            error = RuntimeError("fixture timeout")
            error.provider_attempts = [
                {
                    "endpoint": "https://photon.komoot.io/reverse",
                    "answered": False,
                    "http_status": None,
                    "error": "timeout",
                }
            ]
            raise error

        def close(self):
            self.closed = True

    provider = FailingPhoton()
    photon_factory = MagicMock(return_value=provider)
    overpass_factory = MagicMock()
    try:
        _set("real_city_enabled", True)
        _set("real_city_mode", "live")
        monkeypatch.setattr(discovery, "_bootstrap_discovery_provider_config", _photon_config)
        monkeypatch.setattr(discovery, "_bootstrap_live_endpoint_block_reason", lambda *args, **kwargs: None)
        monkeypatch.setattr(discovery, "_bootstrap_rate_limited", lambda *args, **kwargs: False)
        monkeypatch.setattr(discovery, "PhotonPOIProvider", photon_factory)
        monkeypatch.setattr(discovery, "OverpassPOIProvider", overpass_factory)

        result = discovery.discover_bootstrap_candidates(
            session,
            SimpleNamespace(
                id="journey-photon-failure",
                status="DRAFT",
                active_plan_version_id=None,
                city_code="Shanghai",
            ),
            member=SimpleNamespace(id="member-photon-failure"),
            traveler_id="traveler-photon-failure",
            query="cafe",
            radius_m=2500,
            limit=3,
            source_kind="MANUAL_PUBLIC_CENTER",
            provider_consent=True,
            consented_provider="photon",
            latitude=31.2,
            longitude=121.4,
            accuracy_m=None,
        )

        assert result["status"] == "PROVIDER_UNAVAILABLE"
        assert result["provider"] == "photon"
        assert provider.calls == 1
        assert provider.attempt_limits == [1]
        assert provider.closed is True
        overpass_factory.assert_not_called()
        audit = session.add.call_args.args[0]
        assert audit.provider_key == "photon"
    finally:
        for name, value in previous.items():
            _set(name, value)


def test_osm_identity_accepts_photon_ids_and_rejects_provider_mismatch():
    assert discovery._osm_identity(
        SimpleNamespace(provider_key="photon", external_id="photon:way/8123")
    ) == ("way", "8123")
    assert discovery._osm_identity(
        SimpleNamespace(provider_key="overpass", external_id="photon:way/8123")
    ) is None


@pytest.mark.parametrize(
    ("osm_type", "expected_kind"),
    [("N", "node"), ("W", "way"), ("R", "relation")],
)
def test_photon_osm_identity_normalization_preserves_source_url(osm_type, expected_kind):
    feature = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [121.4, 31.2]},
        "properties": {
            "osm_type": osm_type,
            "osm_id": 8123,
            "osm_key": "tourism",
            "osm_value": "museum",
            "name": "Fixture Museum",
            "countrycode": "cn",
        },
    }
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"features": [feature]})

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
    )
    provider = PhotonPOIProvider(client=client)
    try:
        candidates, _attempts = provider.search_with_evidence(
            "museum",
            latitude=31.2,
            longitude=121.4,
            radius_m=2500,
            limit=1,
        )
    finally:
        provider.close()

    assert len(requests) == 1
    assert len(candidates) == 1
    candidate = candidates[0]
    external_id = f"photon:{expected_kind}/8123"
    source_url = f"https://www.openstreetmap.org/{expected_kind}/8123"
    assert candidate.external_id == external_id
    assert candidate.metadata["source_url"] == source_url
    assert discovery._osm_identity(candidate) == (expected_kind, "8123")
    scope = discovery._candidate_scope_observation(
        candidate,
        captured_at="2026-10-17T00:00:00+00:00",
        provider_provenance="TEST_PROVIDER",
        expires_at="2026-10-17T01:00:00+00:00",
        source_kind="MANUAL_PUBLIC_CENTER",
    )
    assert scope["source_url"] == source_url
