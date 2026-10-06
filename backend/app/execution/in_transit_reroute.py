"""Read-only in-transit route deviation semantics.

The module deliberately separates advisory browser location from trusted
device/location evidence. It does not mutate execution state or plans.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_TRUSTED_LOCATION_SOURCES = {"DEVICE_ATTESTED", "LOCATION_ATTESTED"}


@dataclass(frozen=True)
class TransitDeviationDecision:
    state: str
    authoritative: bool
    material: bool
    reason: str
    deviation_threshold_m: float | None


def deviation_threshold_m(*, accuracy_m: float) -> float:
    return max(150.0, float(accuracy_m) * 3.0)


def classify_transit_deviation(
    *,
    activity_status: str,
    location_source: str | None,
    location_fresh: bool,
    accuracy_m: float | None,
    route_shape_available: bool,
    distance_to_route_m: float | None,
    consecutive_deviation_count: int = 1,
    near_target: bool = False,
) -> TransitDeviationDecision:
    """Classify one current-location observation against the active route."""

    if str(activity_status or "").upper() != "EN_ROUTE":
        return TransitDeviationDecision(
            "INACTIVE", False, False, "ACTIVITY_NOT_EN_ROUTE", None
        )

    if location_source is None or accuracy_m is None:
        return TransitDeviationDecision(
            "LOCATION_UNAVAILABLE", False, False, "NO_LOCATION_OBSERVATION", None
        )

    source = str(location_source).upper()
    trusted = source in _TRUSTED_LOCATION_SOURCES

    if not location_fresh:
        return TransitDeviationDecision(
            "LOCATION_STALE", trusted, False, "LOCATION_NOT_FRESH", None
        )

    if float(accuracy_m) > 100.0:
        return TransitDeviationDecision(
            "LOCATION_IMPRECISE", trusted, False, "LOCATION_ACCURACY_TOO_LOW", None
        )

    if near_target:
        return TransitDeviationDecision(
            "ARRIVAL_READY", trusted, False, "LOCATION_NEAR_TARGET", None
        )

    if not route_shape_available or distance_to_route_m is None:
        return TransitDeviationDecision(
            "ROUTE_SHAPE_UNAVAILABLE",
            trusted,
            False,
            "ACTIVE_ROUTE_GEOMETRY_UNAVAILABLE",
            None,
        )

    threshold = deviation_threshold_m(accuracy_m=float(accuracy_m))
    off_route = float(distance_to_route_m) > threshold

    if not off_route:
        return TransitDeviationDecision(
            "ON_ROUTE", trusted, False, "LOCATION_WITHIN_ROUTE_CORRIDOR", threshold
        )

    if not trusted:
        return TransitDeviationDecision(
            "ADVISORY_DEVIATION",
            False,
            False,
            "FOREGROUND_LOCATION_OUTSIDE_ROUTE_CORRIDOR",
            threshold,
        )

    if int(consecutive_deviation_count) < 2:
        return TransitDeviationDecision(
            "POSSIBLE_VERIFIED_DEVIATION",
            True,
            False,
            "TRUSTED_LOCATION_DEVIATION_NOT_YET_PERSISTENT",
            threshold,
        )

    return TransitDeviationDecision(
        "VERIFIED_DEVIATION",
        True,
        True,
        "TRUSTED_LOCATION_PERSISTENTLY_OUTSIDE_ROUTE_CORRIDOR",
        threshold,
    )


def reroute_origin_authority(location_source: str) -> str:
    source = str(location_source or "").upper()
    if source in _TRUSTED_LOCATION_SOURCES:
        return "TRUSTED_CURRENT_LOCATION_ROUTE"
    if source == "FOREGROUND_WEB":
        return "ADVISORY_ROUTE"
    return "UNKNOWN_LOCATION_ROUTE"


def reroute_semantic_key(
    *,
    journey_id: str,
    activity_id: str,
    location_observation_id: str,
    target_place_id: str,
    mode: str,
) -> str:
    """Stable reroute identity for the same current-location generation."""
    import hashlib
    import json

    payload: dict[str, Any] = {
        "journey_id": str(journey_id),
        "activity_id": str(activity_id),
        "location_observation_id": str(location_observation_id),
        "target_place_id": str(target_place_id),
        "mode": str(mode).upper(),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
