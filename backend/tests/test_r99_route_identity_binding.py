from __future__ import annotations

import httpx

from app.integrations.mobility.valhalla_http import ValhallaHTTPMobilityProvider


def _provider(payload: dict) -> ValhallaHTTPMobilityProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/route"
        return httpx.Response(200, json=payload)

    return ValhallaHTTPMobilityProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        base_url="http://127.0.0.1:8999",
        place_lookup=lambda place_id: {
            "first": {"latitude": 31.2304, "longitude": 121.4737},
            "second": {"latitude": 31.231, "longitude": 121.474},
        }[place_id],
        test_provider=True,
    )


def test_r99_route_estimate_keeps_request_and_response_locations():
    provider = _provider(
        {
            "trip": {
                "summary": {"time": 780, "length": 0.9},
                "locations": [
                    {"lat": 31.2304, "lon": 121.4737},
                    {"lat": 31.231, "lon": 121.474},
                ],
            }
        }
    )

    estimate = provider.estimate("first", "second")

    expected = ((31.2304, 121.4737), (31.231, 121.474))
    assert estimate.origin_place_id == "first"
    assert estimate.destination_place_id == "second"
    assert estimate.request_locations == expected
    assert estimate.response_locations == expected


def test_r99_route_estimate_preserves_legacy_missing_response_locations():
    provider = _provider(
        {
            "trip": {
                "summary": {"time": 780, "length": 0.9},
                "legs": [{}],
            }
        }
    )

    estimate = provider.estimate("first", "second")

    assert estimate.request_locations == ((31.2304, 121.4737), (31.231, 121.474))
    assert estimate.response_locations is None
