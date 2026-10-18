from __future__ import annotations

import json
import math

import httpx
import pytest

from app.execution.bootstrap_discovery import _attempts, _osm_identity
from app.integrations.discovery.provider_identity import PROVIDER_USER_AGENT
from app.integrations.discovery.photon_poi import (
    MAX_LIMIT,
    OSM_ATTRIBUTION,
    OSM_ATTRIBUTION_URL,
    PHOTON_REJECTION_REASONS,
    PHOTON_REVERSE_URL,
    PhotonPOIProvider,
    UnsupportedPhotonQuery,
)
from app.integrations.provider_config import ExternalProviderSettings


def _feature(
    *,
    osm_type: str = "W",
    osm_id: int = 123,
    osm_key: str = "tourism",
    osm_value: str = "museum",
    name: str = "Offline Museum",
    lon: float = 135.7,
    lat: float = 35.0,
    extra: dict | None = None,
) -> dict:
    properties = {
        "osm_type": osm_type,
        "osm_id": osm_id,
        "osm_key": osm_key,
        "osm_value": osm_value,
        "name": name,
        "countrycode": "jp",
    }
    if extra is not None:
        properties["extra"] = extra
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": properties,
    }


def _provider(handler, *, timeout_s: float = 2.0) -> tuple[PhotonPOIProvider, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def capture(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(capture), follow_redirects=False)
    return PhotonPOIProvider(client=client, timeout_s=timeout_s), requests


def test_museum_gallery_query_uses_one_offline_reverse_request_and_keeps_osm_provenance():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"features": [_feature(extra={"opening_hours": "Mo-Fr 09:00-18:00"})]}
        )

    provider, requests = _provider(handler)
    try:
        candidates, attempts = provider.search_with_evidence(
            "museum/gallery",
            latitude=35.0,
            longitude=135.7,
            radius_m=2500,
            limit=8,
        )
        request = requests[0]
        query = request.url.params
        timeout = request.extensions["timeout"]
    finally:
        provider.close()

    assert len(requests) == 1
    assert str(request.url).startswith(PHOTON_REVERSE_URL)
    assert query["include"] == "osm.tourism.museum,osm.tourism.gallery,osm.amenity.arts_centre"
    assert query["radius"] == "2.5"
    assert query["limit"] == "8"
    assert timeout["connect"] == 2.0 and timeout["read"] == 2.0
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.provider_key == "photon"
    assert candidate.external_id == "photon:way/123"
    assert candidate.metadata["osm_id"] == "way/123"
    assert _osm_identity(candidate) == ("way", "123")
    assert candidate.name == "Offline Museum"
    assert candidate.category == "museum"
    assert candidate.metadata["source_status"] == "LIVE_PROVIDER"
    assert candidate.metadata["source_url"] == "https://www.openstreetmap.org/way/123"
    assert candidate.metadata["attribution"] == OSM_ATTRIBUTION
    assert candidate.metadata["attribution_url"] == OSM_ATTRIBUTION_URL
    assert candidate.opening_hours["status"] == "NORMALIZED_VALID"
    assert candidate.cost_evidence["status"] == "UNKNOWN"
    assert attempts[0]["answered"] is True and attempts[0]["http_status"] == 200
    assert attempts[0]["source_status"] == "LIVE_PROVIDER"


def test_named_place_search_is_one_bounded_forward_request_not_a_category_guess():
    provider, requests = _provider(lambda request: httpx.Response(200, json={"features": [
        _feature(name="TEST_FIXTURE 目的地博物馆", extra={"opening_hours": "24/7", "fee": "no"}),
        _feature(osm_id=124, osm_key="place", osm_value="city", name="TEST_FIXTURE not a POI"),
        _feature(osm_id=125, lon=136.7, name="TEST_FIXTURE outside selected area"),
    ]}))
    try:
        places, attempts = provider.search_with_evidence(
            "目的地博物馆", query_mode="name", latitude=35.0, longitude=135.7, radius_m=2500, limit=3,
        )
    finally:
        provider.close()
    assert len(requests) == 1
    assert requests[0].url.path == "/api/"
    assert requests[0].url.params["q"] == "目的地博物馆"
    assert "radius" not in requests[0].url.params
    bbox = list(map(float, requests[0].url.params["bbox"].split(",")))
    assert bbox[0] < 135.7 < bbox[2] and bbox[1] < 35.0 < bbox[3]
    assert len(places) == 1 and places[0].name == "TEST_FIXTURE 目的地博物馆"
    assert places[0].opening_hours["status"] == "NORMALIZED_VALID"
    assert attempts[0]["endpoint"] == "https://photon.komoot.io/api/"
    assert attempts[0]["rejected_by_reason"]["category_mismatch"] == 1
    assert attempts[0]["rejected_by_reason"]["out_of_range"] == 1


def test_named_place_search_error_keeps_actual_endpoint_and_does_not_retry():
    provider, requests = _provider(lambda request: httpx.Response(503, json={}))
    try:
        with pytest.raises(httpx.HTTPError) as failed:
            provider.search_with_evidence("目的地博物馆", query_mode="name", latitude=35, longitude=135.7, radius_m=2500, limit=3)
    finally:
        provider.close()
    assert len(requests) == 1
    assert failed.value.provider_attempts[0]["endpoint"] == "https://photon.komoot.io/api/"


@pytest.mark.parametrize("name", ["", "x", "a" * 121])
def test_invalid_place_name_is_rejected_before_network(name):
    provider, requests = _provider(lambda request: httpx.Response(200, json={"features": []}))
    try:
        with pytest.raises(UnsupportedPhotonQuery):
            provider.search_with_evidence(name, query_mode="name", latitude=35, longitude=135.7, radius_m=2500, limit=3)
    finally:
        provider.close()
    assert requests == []


def test_configured_contact_email_is_only_sent_in_photon_user_agent(
    monkeypatch, caplog, capsys
):
    email = "photon-contact@example.invalid"
    user_agent = f"CityNexus-RevolutionFirstLook/1.0 (mailto:{email})"
    monkeypatch.setenv("CITYNEXUS_PHOTON_USER_AGENT", user_agent)
    assert email not in repr(ExternalProviderSettings())
    provider, requests = _provider(
        lambda _request: httpx.Response(200, json={"features": []})
    )
    try:
        _candidates, attempts = provider.search_with_evidence(
            "museum", latitude=35.0, longitude=135.7, radius_m=2500, limit=3
        )
    finally:
        provider.close()

    assert len(requests) == 1
    request = requests[0]
    assert request.headers["User-Agent"] == user_agent
    assert [
        name.lower() for name, value in request.headers.items() if email in value
    ] == ["user-agent"]
    assert email not in str(request.url.params.multi_items())
    assert request.content == b""
    assert email not in json.dumps(attempts)
    assert email not in caplog.text
    captured = capsys.readouterr()
    assert email not in captured.out + captured.err

    monkeypatch.delenv("CITYNEXUS_PHOTON_USER_AGENT")
    default_provider, default_requests = _provider(
        lambda _request: httpx.Response(200, json={"features": []})
    )
    try:
        default_provider.search_with_evidence(
            "museum", latitude=35.0, longitude=135.7, radius_m=2500, limit=3
        )
    finally:
        default_provider.close()
    assert default_requests[0].headers["User-Agent"] == PROVIDER_USER_AGENT


@pytest.mark.parametrize(
    ("osm_type", "expected_kind"),
    [("N", "node"), ("W", "way"), ("R", "relation")],
)
def test_photon_identity_matches_bootstrap_identity_contract(
    osm_type: str, expected_kind: str
):
    provider, _requests = _provider(
        lambda _request: httpx.Response(200, json={"features": [_feature(osm_type=osm_type)]})
    )
    try:
        candidates, _attempts = provider.search_with_evidence(
            "museum", latitude=35.0, longitude=135.7, radius_m=2500, limit=3
        )
    finally:
        provider.close()

    assert len(candidates) == 1
    assert candidates[0].external_id == f"photon:{expected_kind}/123"
    assert _osm_identity(candidates[0]) == (expected_kind, "123")


def test_response_is_category_checked_radius_checked_and_finite():
    wrong_category = _feature(osm_key="amenity", osm_value="cafe", osm_id=124)
    outside_radius = _feature(osm_id=125, lon=135.8)
    malformed_identity = _feature(osm_id=0)
    valid = _feature(osm_id=126, extra={"fee": "no"})

    provider, requests = _provider(
        lambda _request: httpx.Response(
            200,
            json={"features": [wrong_category, outside_radius, malformed_identity, valid]},
        )
    )
    try:
        candidates, attempts = provider.search_with_evidence(
            "museum", latitude=35.0, longitude=135.7, radius_m=5000, limit=99
        )
        params = requests[0].url.params
    finally:
        provider.close()

    assert len(requests) == 1
    assert params["limit"] == str(MAX_LIMIT)
    assert [item.external_id for item in candidates] == ["photon:way/126"]
    assert candidates[0].cost_evidence == {
        "status": "KNOWN",
        "amount_minor": 0,
        "currency": None,
        "currency_agnostic": True,
        "evidence_basis": "OSM_FEE_NO",
        "source": "photon",
    }
    assert attempts[0]["elements"] == attempts[0]["features"] == 4
    assert attempts[0]["returned"] == 1
    assert attempts[0]["rejected_by_reason"] == {
        "malformed_structure": 0,
        "missing_osm_identity": 1,
        "missing_name": 0,
        "category_mismatch": 1,
        "invalid_coordinates": 0,
        "out_of_range": 1,
    }
    assert attempts[0]["result_status"] == "LIVE_RESULTS"
    assert math.isfinite(candidates[0].distance_m)


@pytest.mark.parametrize(
    ("feature", "reason", "private_marker"),
    [
        pytest.param(
            {
                "type": "Feature",
                "properties": {"name": "PRIVATE_BAD_STRUCTURE_MARKER"},
                "geometry": None,
            },
            "malformed_structure",
            "PRIVATE_BAD_STRUCTURE_MARKER",
            id="bad-structure",
        ),
        pytest.param(
            _feature(osm_id=0, name="PRIVATE_IDENTITY_MARKER"),
            "missing_osm_identity",
            "PRIVATE_IDENTITY_MARKER",
            id="missing-osm-identity",
        ),
        pytest.param(
            _feature(name="", extra={"private_note": "PRIVATE_NAME_MARKER"}),
            "missing_name",
            "PRIVATE_NAME_MARKER",
            id="missing-name",
        ),
        pytest.param(
            _feature(
                osm_key="amenity",
                osm_value="cafe",
                name="PRIVATE_CATEGORY_MARKER",
            ),
            "category_mismatch",
            "PRIVATE_CATEGORY_MARKER",
            id="category-mismatch",
        ),
        pytest.param(
            _feature(lon="not-a-coordinate", name="PRIVATE_COORDINATE_MARKER"),
            "invalid_coordinates",
            "PRIVATE_COORDINATE_MARKER",
            id="invalid-coordinates",
        ),
        pytest.param(
            _feature(lon=135.8, name="PRIVATE_RANGE_MARKER"),
            "out_of_range",
            "PRIVATE_RANGE_MARKER",
            id="out-of-range",
        ),
    ],
)
def test_rejection_reason_counts_are_isolated_and_count_only(
    feature: dict, reason: str, private_marker: str
):
    provider, requests = _provider(
        lambda _request: httpx.Response(200, json={"features": [feature]})
    )
    try:
        candidates, attempts = provider.search_with_evidence(
            "museum", latitude=35.0, longitude=135.7, radius_m=1000, limit=5
        )
    finally:
        provider.close()

    expected = {key: int(key == reason) for key in PHOTON_REJECTION_REASONS}
    assert len(requests) == 1
    assert candidates == []
    assert attempts[0]["elements"] == attempts[0]["features"] == 1
    assert attempts[0]["returned"] == 0
    assert attempts[0]["rejected_by_reason"] == expected
    assert set(attempts[0]["rejected_by_reason"]) == set(PHOTON_REJECTION_REASONS)
    assert private_marker not in json.dumps(attempts)


def test_bootstrap_attempts_allowlist_only_fixed_photon_rejection_counts():
    attempts = _attempts(
        [
            {
                "endpoint": PHOTON_REVERSE_URL,
                "answered": True,
                "http_status": 200,
                "rejected_by_reason": {
                    "malformed_structure": 1,
                    "missing_osm_identity": True,
                    "missing_name": -2,
                    "category_mismatch": 2,
                    "invalid_coordinates": 3,
                    "out_of_range": 4,
                    "private_detail": "PRIVATE_ATTEMPT_MARKER",
                },
                "private_detail": "PRIVATE_ATTEMPT_MARKER",
            }
        ],
        provider_key="photon",
    )

    assert attempts[0]["rejected_by_reason"] == {
        "malformed_structure": 1,
        "missing_osm_identity": 0,
        "missing_name": 0,
        "category_mismatch": 2,
        "invalid_coordinates": 3,
        "out_of_range": 4,
    }
    assert "PRIVATE_ATTEMPT_MARKER" not in json.dumps(attempts)


def test_empty_success_is_live_zero_while_failure_is_runtime_and_never_retried():
    empty_provider, empty_requests = _provider(
        lambda _request: httpx.Response(200, json={"features": []})
    )
    try:
        candidates, attempts = empty_provider.search_with_evidence(
            "museum", latitude=35, longitude=135, radius_m=5000, limit=4
        )
    finally:
        empty_provider.close()
    assert candidates == []
    assert len(empty_requests) == 1 and attempts[0]["answered"] is True
    assert attempts[0]["result_status"] == "LIVE_ZERO_RESULTS"

    failing_provider, failing_requests = _provider(
        lambda _request: httpx.Response(503, json={"message": "down"})
    )
    try:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            failing_provider.search_with_evidence(
                "museum", latitude=35, longitude=135, radius_m=5000, limit=4
            )
    finally:
        failing_provider.close()
    assert len(failing_requests) == 1
    assert exc_info.value.provider_attempts[0]["source_status"] == "RUNTIME_FAILURE"
    assert exc_info.value.provider_attempts[0]["http_status"] == 503


@pytest.mark.parametrize(
    "kwargs",
    [
        {"latitude": float("nan"), "longitude": 135, "radius_m": 1000, "limit": 5},
        {"latitude": 35, "longitude": 181, "radius_m": 1000, "limit": 5},
        {"latitude": 35, "longitude": 135, "radius_m": 0, "limit": 5},
        {"latitude": 35, "longitude": 135, "radius_m": 1000, "limit": 0},
    ],
)
def test_invalid_input_fails_before_any_provider_request(kwargs):
    provider, requests = _provider(lambda _request: httpx.Response(200, json={"features": []}))
    try:
        with pytest.raises(ValueError):
            provider.search_with_evidence("museum", **kwargs)
    finally:
        provider.close()
    assert requests == []


def test_unsupported_fee_filter_and_multi_attempt_request_fail_closed_offline():
    provider, requests = _provider(lambda _request: httpx.Response(200, json={"features": []}))
    try:
        with pytest.raises(UnsupportedPhotonQuery, match="free-entry"):
            provider.search_with_evidence(
                "free museum", latitude=35, longitude=135, radius_m=1000, limit=5
            )
        with pytest.raises(ValueError, match="exactly one request"):
            provider.search_with_evidence(
                "museum", latitude=35, longitude=135, radius_m=1000, limit=5, max_attempts=2
            )
    finally:
        provider.close()
    assert requests == []


@pytest.mark.parametrize(
    "base_url",
    [
        "http://photon.komoot.io",
        "https://user@photon.komoot.io",
        "https://photon.komoot.io/path",
        "https://example.test",
        "https://photon.komoot.io/?next=https://example.test",
    ],
)
def test_only_the_official_photon_https_origin_is_accepted(base_url):
    with pytest.raises(ValueError, match="official HTTPS Photon host"):
        PhotonPOIProvider(base_url=base_url)
