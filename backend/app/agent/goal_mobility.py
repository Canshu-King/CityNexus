"""Freeze the AMap route time and geometry the Agent already measured, instead of inventing either.

Selecting a plan needs frozen mobility evidence: `backend/app/main.py:18120` refuses any candidate whose
`mobility_evidence_json` carries no snapshot id, and the one capture door in this product
(`backend/app/integrations/mobility/snapshot_capture.py:95`) takes a provider that either answers for a
pair or raises -- with no mock fallback when it is asked to fail closed. Nothing on the Agent's draft
path ever wrote that evidence, which is why every formal candidate saved from an Agent draft stayed
unselectable at the second door after the facts door.

But the Agent *has* measured hops on real screens: `route_public_places` calls the live AMap walking
endpoint, and route freeze can call its public-transport endpoint, keeping provider time, geometry,
provenance, and source links on the task. This adapter lets those stored measurements enter the existing
door. Two rules it does not bend:

* A hop nobody measured raises, so `capture_mobility_snapshot` fails the whole capture closed. A fixture
  number, a distance estimate or the mock provider's blanket default never becomes a hard fact here
  (V4 #4, T2 / docs/MOBILITY_TRUTH_CONTRACT.md).
* Keys are the canonical `places.id` values the selection gate itself asks about: with no semantic key on
  a draft row, `app/replanning/feasibility.py:259` falls back to `activity.place_id`, so the pairs frozen
  at preparation time are addressed the same way they will be read back at selection time.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

from app.integrations.china.amap import gcj02_to_wgs84
from app.integrations.mobility.routingpy_adapter import TravelEstimate
from app.replanning.provider_snapshots import LIVE_PROVIDER_CAPTURE


def _minutes(route: Mapping[str, Any]) -> int:
    seconds = route.get("duration_seconds")
    if type(seconds) not in (int, float) or not math.isfinite(float(seconds)) or float(seconds) < 0:
        raise ValueError("provider route carries no usable duration")
    return max(1, int(math.ceil(float(seconds) / 60.0)))


def route_geometry_wgs84(
    route: Mapping[str, Any], *, provider_call_id: str | None = None
) -> dict[str, Any] | None:
    """Convert a complete provider LineString to WGS84 while keeping its source provenance."""
    status = str(route.get("geometry_status") or "").upper()
    if status and status != "AVAILABLE":
        return None

    raw = route.get("route_geometry")
    source_field = "route_geometry"
    if not isinstance(raw, Mapping):
        raw = route.get("path")
        source_field = "path"
    if not isinstance(raw, Mapping):
        return None

    properties = raw.get("properties") if raw.get("type") == "Feature" else {}
    properties = properties if isinstance(properties, Mapping) else {}
    geometry = raw.get("geometry") if raw.get("type") == "Feature" else raw
    if not isinstance(geometry, Mapping) or geometry.get("type") != "LineString":
        return None
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, (list, tuple)):
        return None

    crs = str(
        properties.get("domain_crs")
        or geometry.get("coordinate_system")
        or raw.get("coordinate_system")
        or route.get("coordinate_system")
        or ""
    ).upper().replace("-", "")
    if crs not in {"GCJ02", "WGS84"}:
        return None

    converted: list[list[float]] = []
    for point in coordinates:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            return None
        if isinstance(point[0], bool) or isinstance(point[1], bool):
            return None
        try:
            longitude, latitude = float(point[0]), float(point[1])
        except (TypeError, ValueError):
            return None
        if not math.isfinite(longitude) or not math.isfinite(latitude):
            return None
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            return None
        if crs == "GCJ02":
            latitude, longitude = gcj02_to_wgs84(latitude, longitude)
        converted.append([longitude, latitude])
    if len(converted) < 2:
        return None

    source_provenance = route.get("geometry_provenance")
    source_provenance = dict(source_provenance) if isinstance(source_provenance, Mapping) else {}
    source_crs = str(properties.get("source_crs") or crs)
    feature_properties = dict(properties)
    feature_properties.update(
        {
            "source_provider": properties.get("source_provider")
            or route.get("provider_key")
            or route.get("provider")
            or "amap",
            "provider_call_id": provider_call_id
            or properties.get("provider_call_id")
            or route.get("provider_call_id")
            or route.get("id"),
            "measurement_captured_at": route.get("captured_at"),
            "measurement_from_place_id": route.get("measurement_from_place_id")
            or route.get("from_place_id"),
            "measurement_to_place_id": route.get("measurement_to_place_id")
            or route.get("to_place_id"),
            "source_crs": source_crs,
            "domain_crs": "WGS84",
            "conversion": properties.get("conversion")
            or ("ITERATIVE_GCJ02_TO_WGS84" if crs == "GCJ02" else "IDENTITY_WGS84"),
            "source_geometry_field": properties.get("source_geometry_field") or source_field,
            "geometry_status": "AVAILABLE",
            "source_fields": properties.get("source_fields")
            or source_provenance.get("source_fields")
            or [source_field + ".coordinates"],
            "provider_geometry_provenance": source_provenance,
        }
    )
    if source_provenance.get("lookup_direction"):
        feature_properties["lookup_direction"] = source_provenance["lookup_direction"]
    return {
        "type": "Feature",
        "properties": feature_properties,
        "geometry": {"type": "LineString", "coordinates": converted},
    }


def _reverse_geometry(feature: dict[str, Any]) -> dict[str, Any]:
    geometry = dict(feature["geometry"])
    geometry["coordinates"] = [list(point) for point in reversed(geometry["coordinates"])]
    properties = dict(feature.get("properties") or {})
    properties["lookup_direction"] = "REVERSED_STORED_MEASUREMENT"
    return {**feature, "properties": properties, "geometry": geometry}


class StoredAmapRoutes:
    """Stored AMap walking/transit measurements, exposed through the snapshot estimate contract."""

    provider_key = "amap-web-service"
    capture_provenance = LIVE_PROVIDER_CAPTURE
    time_basis = "PROVIDER_CAPTURED_AT"

    def __init__(self, facts: Iterable[tuple[str, str, Mapping[str, Any]]]) -> None:
        self._facts: dict[tuple[str, str], Mapping[str, Any]] = {}
        for origin, destination, route in facts:
            key = (str(origin), str(destination))
            if key[0] and key[1] and key[0] != key[1]:
                self._facts[key] = route

    def _lookup_with_direction(
        self, origin_key: str, destination_key: str
    ) -> tuple[Mapping[str, Any], bool]:
        for key, reversed_lookup in (
            ((str(origin_key), str(destination_key)), False),
            ((str(destination_key), str(origin_key)), True),
        ):
            route = self._facts.get(key)
            if route is not None:
                return route, reversed_lookup
        raise KeyError(f"no live provider measurement for {origin_key}|{destination_key}")

    def _lookup(self, origin_key: str, destination_key: str) -> Mapping[str, Any]:
        return self._lookup_with_direction(origin_key, destination_key)[0]

    def estimate_minutes(self, origin_key: str, destination_key: str) -> int:
        return _minutes(self._lookup(origin_key, destination_key))

    def estimate(self, origin_key: str, destination_key: str) -> TravelEstimate:
        route, reversed_lookup = self._lookup_with_direction(origin_key, destination_key)
        geometry = route_geometry_wgs84(route)
        if geometry is not None and reversed_lookup:
            geometry = _reverse_geometry(geometry)
        distance = route.get("distance_m")
        if type(distance) not in (int, float) or not math.isfinite(float(distance)):
            distance = None
        else:
            distance = int(distance)
        return TravelEstimate(
            provider_key=self.provider_key,
            duration_min=_minutes(route),
            distance_m=distance,
            geometry=geometry,
            raw={
                "measurement_id": route.get("provider_call_id") or route.get("id"),
                "measurement_captured_at": route.get("captured_at"),
                "measurement_from_place_id": route.get("measurement_from_place_id") or route.get("from_place_id"),
                "measurement_to_place_id": route.get("measurement_to_place_id") or route.get("to_place_id"),
                "lookup_reused_in_reverse": bool(reversed_lookup or route.get("lookup_reused_in_reverse")),
                "geometry_status": route.get("geometry_status")
                or ("AVAILABLE" if geometry is not None else "BLOCKED_GEOMETRY_UNAVAILABLE"),
            },
        )

    def fact_quality(self, origin_key: str, destination_key: str) -> str:
        self._lookup(origin_key, destination_key)
        return LIVE_PROVIDER_CAPTURE

    def pair_details(self, origin_key: str, destination_key: str) -> dict[str, Any]:
        """What this hop's own measurement says beyond minutes.

        A row written before the transport door existed carries no mode, and the only door that ever
        wrote one is the walking one -- so an absent mode means WALK.  That is a fact about this code,
        not a guess about the provider (the same reading the freeze door documents at
        backend/app/agent/goal_route_freeze.py:464).
        """
        route = self._lookup(origin_key, destination_key)

        def _whole(value):
            return int(value) if isinstance(value, (int, float)) and math.isfinite(float(value)) else None

        return {"mode": str(route.get("mode") or "WALK").upper(), "distance_m": _whole(route.get("distance_m")),
                "walking_distance_m": _whole(route.get("walking_distance_m")),
                "walking_min": _whole(route.get("walking_min"))}


class StoredAmapWalkingRoutes(StoredAmapRoutes):
    """Compatibility name retained for existing imports of the stored-route adapter."""
