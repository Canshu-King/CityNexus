"""Freeze the walking time the Agent already measured, instead of inventing one.

Selecting a plan needs frozen mobility evidence: `backend/app/main.py:18120` refuses any candidate whose
`mobility_evidence_json` carries no snapshot id, and the one capture door in this product
(`backend/app/integrations/mobility/snapshot_capture.py:95`) takes a provider that either answers for a
pair or raises -- with no mock fallback when it is asked to fail closed. Nothing on the Agent's draft
path ever wrote that evidence, which is why every formal candidate saved from an Agent draft stayed
unselectable at the second door after the facts door.

But the Agent *has* measured hops on real screens: `route_public_places` calls the live AMap walking
endpoint and keeps what came back -- distance, duration, provider, capture time and a public source url --
on the task (backend/app/agent/goal_amap.py:206 to :211). This is the adapter that lets those stored
measurements enter the existing door. Two rules it does not bend:

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

from app.replanning.provider_snapshots import LIVE_PROVIDER_CAPTURE


def _minutes(route: Mapping[str, Any]) -> int:
    seconds = route.get("duration_seconds")
    if type(seconds) not in (int, float) or not math.isfinite(float(seconds)) or float(seconds) < 0:
        raise ValueError("provider route carries no usable duration")
    return max(1, int(math.ceil(float(seconds) / 60.0)))


class StoredAmapWalkingRoutes:
    """The walking times this task already holds, as a capture-door provider."""

    provider_key = "amap_walking"
    capture_provenance = LIVE_PROVIDER_CAPTURE
    time_basis = "PROVIDER_CAPTURED_AT"

    def __init__(self, facts: Iterable[tuple[str, str, Mapping[str, Any]]]) -> None:
        self._facts: dict[tuple[str, str], Mapping[str, Any]] = {}
        for origin, destination, route in facts:
            key = (str(origin), str(destination))
            if key[0] and key[1] and key[0] != key[1]:
                self._facts[key] = route

    def _lookup(self, origin_key: str, destination_key: str) -> Mapping[str, Any]:
        for key in ((str(origin_key), str(destination_key)), (str(destination_key), str(origin_key))):
            route = self._facts.get(key)
            if route is not None:
                return route
        raise KeyError(f"no live provider measurement for {origin_key}|{destination_key}")

    def estimate_minutes(self, origin_key: str, destination_key: str) -> int:
        return _minutes(self._lookup(origin_key, destination_key))

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
