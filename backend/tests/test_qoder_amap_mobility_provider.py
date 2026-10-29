"""The AMap walking adapter answers runtime captures without inventing a leg.

These cases pin four behaviours the replan path depends on: the minutes come from the provider's own
walking answer, the fact is classified as a live capture, coordinates are converted once from the
Place row's WGS84 into the GCJ-02 system the client expects, and a provider error stays an error so
the capture door reports the pair unavailable.
"""

from __future__ import annotations

import math

import pytest

from app.integrations.mobility.amap_http import AmapWalkingMobilityProvider
from app.integrations.mobility.snapshot_capture import (
    MobilitySnapshotCaptureError,
    capture_mobility_snapshot,
)
from app.replanning.provider_snapshots import LIVE_PROVIDER_CAPTURE

WGS = {
    "origin": {"latitude": 39.90178087398688, "longitude": 116.39151443624468, "provider_key": "amap"},
    "destination": {"latitude": 39.9164375921294, "longitude": 116.39078695427294, "provider_key": "overpass"},
}
ROUTE = {
    "provider_key": "amap-web-service",
    "mode": "WALK",
    "distance_m": 2100,
    "duration_seconds": 1815,
    "duration_min": 31,
}


class FakeClient:
    provider_key = "amap-web-service"

    def __init__(self, answer: dict) -> None:
        self.answer = answer
        self.calls: list[tuple[tuple[float, float], tuple[float, float]]] = []

    def walking(self, origin, destination):
        self.calls.append((origin, destination))
        return self.answer


def _lookup(key: str) -> dict:
    return WGS[key]


def _provider(client: FakeClient) -> AmapWalkingMobilityProvider:
    return AmapWalkingMobilityProvider(client=client, place_lookup=_lookup)


def test_minutes_come_from_the_provider_answer_and_quality_is_live() -> None:
    provider = _provider(FakeClient({"status": "ok", "route": ROUTE}))

    assert provider.estimate_minutes("origin", "destination") == 31
    assert provider.fact_quality("origin", "destination") == LIVE_PROVIDER_CAPTURE
    details = provider.pair_details("origin", "destination")
    assert details == {"mode": "WALK", "distance_m": 2100, "walking_distance_m": 2100, "walking_min": 31}


def test_coordinates_are_converted_once_into_gcj02() -> None:
    client = FakeClient({"status": "ok", "route": ROUTE})
    provider = _provider(client)

    provider.estimate_minutes("origin", "destination")
    provider.estimate_minutes("origin", "destination")

    assert len(client.calls) == 1
    (lat, lon), _ = client.calls[0]
    assert lat != pytest.approx(WGS["origin"]["latitude"], abs=1e-6)
    assert lon != pytest.approx(WGS["origin"]["longitude"], abs=1e-6)
    assert lat > WGS["origin"]["latitude"] and lon > WGS["origin"]["longitude"]


def test_a_provider_error_never_becomes_a_fact() -> None:
    provider = _provider(FakeClient({"status": "error", "route": None}))

    with pytest.raises(KeyError):
        provider.estimate_minutes("origin", "destination")
    with pytest.raises(KeyError):
        provider.fact_quality("origin", "destination")


def test_a_hard_capture_without_fallback_fails_closed() -> None:
    provider = _provider(FakeClient({"status": "error", "route": None}))

    with pytest.raises(MobilitySnapshotCaptureError):
        capture_mobility_snapshot(
            [("origin", "destination")],
            primary=provider,
            captured_at="2026-10-25T00:00:00+00:00",
            operation_key="test",
        )


def test_distance_is_carried_when_the_provider_reports_it() -> None:
    provider = _provider(FakeClient({"status": "ok", "route": ROUTE}))
    estimate = provider.estimate("origin", "destination")

    assert estimate.duration_min == 31
    assert estimate.distance_m == 2100
    assert math.isfinite(estimate.duration_min)


def test_a_seeded_place_is_never_sent_to_the_live_router() -> None:
    client = FakeClient({"status": "ok", "route": ROUTE})
    provider = AmapWalkingMobilityProvider(
        client=client,
        place_lookup=lambda key: {
            "latitude": 39.9,
            "longitude": 116.4,
            "provider_key": "mock-city",
        },
    )

    with pytest.raises(KeyError):
        provider.estimate_minutes("origin", "destination")
    assert client.calls == []
