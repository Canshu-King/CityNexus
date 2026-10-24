"""AMap walking as a runtime mobility provider.

The replan hard capture needs a live provider of its own.  This stack has no Valhalla deployment, but
it does carry the traveller's AMap web-service key, and the Agent's goal chain already measures
walking hops with it.  This adapter lets the same measurement door answer a runtime capture, so a
newly adjacent leg can be measured instead of refused.

It never invents a leg: a provider error raises, and the capture door's own fail-closed path reports
that pair unavailable.  Coordinates are read from the server-owned Place rows (WGS84) and converted
to the GCJ-02 system AMap expects; nothing here reads or writes the key.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Mapping

from app.integrations.china.amap import wgs84_to_gcj02
from app.integrations.china.amap_provider import AmapClient
from app.integrations.mobility.routingpy_adapter import TravelEstimate
from app.replanning.provider_snapshots import LIVE_PROVIDER_CAPTURE

#: Place sources whose coordinates describe a real-world object.  A seeded or mock city carries
#: fictional places with plausible coordinates; sending those to a live router would mint a
#: real-looking measurement for a place that does not exist, so the adapter refuses them.
REAL_PLACE_SOURCES = frozenset({
    "amap",
    "amap-web-service",
    "gaode",
    "overpass",
    "osm",
    "openstreetmap",
    "wikidata",
    "location-observation",
    "citynexus-v12-authoritative",
    "citynexus-v9-domain",
})


class AmapWalkingMobilityProvider:
    provider_key = "amap_walking"
    capture_provenance = LIVE_PROVIDER_CAPTURE
    time_basis = "PROVIDER_CAPTURED_AT"
    mode = "WALK"

    def __init__(
        self,
        *,
        client: AmapClient,
        place_lookup: Callable[[str], Mapping[str, float]],
    ) -> None:
        self._client = client
        self._place_lookup = place_lookup
        self._routes: dict[tuple[str, str], Mapping[str, Any]] = {}

    def _gcj02(self, key: str) -> tuple[float, float]:
        point = self._place_lookup(key)
        source = str(point.get("provider_key") or "").strip().lower()
        if source not in REAL_PLACE_SOURCES:
            raise KeyError(f"place {key} has no real provider source ({source or 'unknown'})")
        return wgs84_to_gcj02(float(point["latitude"]), float(point["longitude"]))

    def _route(self, origin_key: str, destination_key: str) -> Mapping[str, Any]:
        pair = (str(origin_key), str(destination_key))
        cached = self._routes.get(pair)
        if cached is not None:
            return cached
        answer = self._client.walking(self._gcj02(pair[0]), self._gcj02(pair[1]))
        route = answer.get("route")
        if answer.get("status") != "ok" or not isinstance(route, Mapping):
            raise KeyError(f"amap walking measured no route for {pair[0]}|{pair[1]}")
        self._routes[pair] = route
        return route

    def estimate_minutes(self, origin_key: str, destination_key: str) -> int:
        route = self._route(origin_key, destination_key)
        minutes = route.get("duration_min")
        if not isinstance(minutes, (int, float)) or not math.isfinite(float(minutes)):
            seconds = route.get("duration_seconds")
            if not isinstance(seconds, (int, float)) or not math.isfinite(float(seconds)):
                raise KeyError(f"amap route carries no usable duration for {origin_key}|{destination_key}")
            minutes = math.ceil(float(seconds) / 60.0)
        return max(1, int(math.ceil(float(minutes))))

    def fact_quality(self, origin_key: str, destination_key: str) -> str:
        self._route(origin_key, destination_key)
        return LIVE_PROVIDER_CAPTURE

    def estimate(self, origin_key: str, destination_key: str) -> TravelEstimate:
        route = self._route(origin_key, destination_key)
        distance = route.get("distance_m")
        return TravelEstimate(
            provider_key=self.provider_key,
            duration_min=self.estimate_minutes(origin_key, destination_key),
            distance_m=int(distance) if isinstance(distance, (int, float)) else None,
            raw=route,
        )

    def pair_details(self, origin_key: str, destination_key: str) -> dict[str, Any]:
        route = self._route(origin_key, destination_key)
        minutes = self.estimate_minutes(origin_key, destination_key)
        distance = route.get("distance_m")
        distance_m = int(distance) if isinstance(distance, (int, float)) else None
        return {
            "mode": "WALK",
            "distance_m": distance_m,
            "walking_distance_m": distance_m,
            "walking_min": minutes,
        }
