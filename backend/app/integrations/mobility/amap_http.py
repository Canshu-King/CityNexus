"""Amap Web-service as a live routing provider for the runtime mobility capture.

Why this exists: `app/integrations/mobility/runtime.py` has exactly one live routing provider,
Valhalla, and it is only primary when somebody configures a URL for it.  Inside China that URL is
usually nobody's, so every leg of a Chinese trip is measured by the deterministic mock and frozen with
`SYNTHETIC_FIXTURE` provenance.  Amap is the source that does answer there.  This adapter turns one
Amap direction answer into the shape the capture already consumes, so the same fail-closed rules that
protect a Valhalla leg protect an Amap leg -- it is not a second gate.

Contract satisfied, read from the capture rather than invented here:
  * `provider_key`                                    -> app/integrations/mobility/snapshot_capture.py:126
  * `estimate(origin, destination)` with `.duration_min` and `.geometry`
                                                      -> app/integrations/mobility/snapshot_capture.py:26
  * `estimate_minutes(origin, destination)`           -> app/integrations/mobility/snapshot_capture.py:20
  * `fact_quality(origin, destination)`               -> app/integrations/mobility/snapshot_capture.py:71
  * `capture_provenance` / `time_basis`               -> app/integrations/mobility/snapshot_capture.py:132

Coordinate rule: the capture's own geometry reader wants WGS84 `[[lon, lat], …]`
(app/integrations/mobility/snapshot_capture.py:49).  Amap answers in GCJ-02, so the conversion happens
inside this adapter, before an answer leaves it; nothing downstream of here ever holds a GCJ-02 point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import httpx

from app.integrations.china.amap import (
    AMAP_BASE_URL,
    MODE_PATHS,
    NormalizedRoute,
    amap_get_sync,
    china_routing_seam,
    missing_key_reason,
    normalize_direction_payload,
    web_key,
    wgs84_to_gcj02,
)
from app.replanning.provider_snapshots import LIVE_PROVIDER_CAPTURE

WALKING_MODE = "WALK"


class AmapRouteError(RuntimeError):
    """Controlled error: Amap did not give this adapter a leg it could measure.

    Raising is the whole point.  A leg the provider could not answer must stay unavailable in the
    snapshot instead of quietly inheriting the fixture's blanket default (V4 #4), so the capture has
    to be able to tell "no answer" apart from "a bad number", and it can only do that through an
    exception type.
    """


@dataclass(frozen=True)
class AmapRouteEstimate:
    """What the capture reads off an `estimate()` call."""

    duration_min: int
    distance_m: int | None
    route: NormalizedRoute
    geometry: Any = field(default=None)
    cost_amount_minor: int | None = None
    currency: str | None = None
    cost_status: str = "UNKNOWN"

    @property
    def raw(self) -> dict[str, Any]:
        return self.route.geometry.get("properties", {})


class AmapHTTPMobilityProvider:
    """Thin adapter: one Amap direction request per leg, no synthetic default anywhere."""

    provider_key = "amap-web-service"
    capture_provenance = LIVE_PROVIDER_CAPTURE
    time_basis = "AMAP_ROUTE_CAPTURED_AT"

    def __init__(
        self,
        *,
        client: httpx.Client,
        place_lookup: Callable[[str], Mapping[str, Any]],
        city_code: str,
        mode: str = WALKING_MODE,
        timeout_s: float = 12.0,
        api_key: str | None = None,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError("Amap timeout must be positive")
        if mode.upper() not in MODE_PATHS:
            raise AmapRouteError(f"Amap does not provide mode {mode}")
        self._client = client
        self._place_lookup = place_lookup
        self._city_code = str(city_code or "")
        self._mode = mode.upper()
        # The capture reads `primary.mode` when it freezes a fact
        # (app/integrations/mobility/snapshot_capture.py:201), so the mode this provider was built to
        # ask for is published under that name: a leg measured as a taxi ride must not be readable as
        # "some mode".
        self.mode = self._mode
        self._timeout_s = timeout_s
        self._api_key = api_key

    def _key(self) -> str:
        key = self._api_key if self._api_key is not None else web_key()
        if not key:
            raise AmapRouteError(missing_key_reason())
        return str(key)

    def _gcj02_point(self, place_id: str) -> tuple[float, float]:
        """The place as the domain holds it (WGS84), pushed into the frame Amap speaks."""
        item = self._place_lookup(place_id)
        location = item.get("location", item)
        try:
            latitude = float(location["latitude"])
            longitude = float(location["longitude"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AmapRouteError(f"Place {place_id} carries no usable WGS84 position") from exc
        return wgs84_to_gcj02(latitude, longitude)

    def estimate(self, origin_place_id: str, destination_place_id: str) -> AmapRouteEstimate:
        path = MODE_PATHS[self._mode]
        origin_lat, origin_lon = self._gcj02_point(origin_place_id)
        dest_lat, dest_lon = self._gcj02_point(destination_place_id)
        params: dict[str, Any] = {
            "key": self._key(),
            "origin": f"{origin_lon},{origin_lat}",
            "destination": f"{dest_lon},{dest_lat}",
            "show_fields": "cost,polyline",
        }
        if self._mode == "TRANSIT":
            params["city1"] = self._city_code
            params["city2"] = self._city_code
        try:
            response = amap_get_sync(
                self._client, f"{AMAP_BASE_URL}/v5/direction/{path}", params
            )
        except RuntimeError as failure:
            # `amap_get_sync` already stripped the key from its message; re-raising under this
            # provider's own type is what lets the capture call it a failed leg.
            raise AmapRouteError(str(failure)) from None
        payload = response.json()
        if not isinstance(payload, dict):
            raise AmapRouteError("Amap route response must be an object")
        try:
            route = normalize_direction_payload(payload, self._mode)
        except (RuntimeError, ValueError, TypeError, KeyError) as failure:
            raise AmapRouteError(f"Amap answer could not be read as a route: {failure}") from None
        if not route.duration_min or route.duration_min < 0:
            raise AmapRouteError("Amap returned no usable travel time")
        return AmapRouteEstimate(
            duration_min=int(route.duration_min),
            distance_m=int(route.distance_m) if route.distance_m else None,
            route=route,
            geometry=route.geometry,
            cost_amount_minor=route.cost_amount_minor,
            currency=route.currency,
            cost_status=route.cost_status,
        )

    def estimate_minutes(self, origin_place_id: str, destination_place_id: str) -> int:
        return self.estimate(origin_place_id, destination_place_id).duration_min

    def fact_quality(self, origin_place_id: str, destination_place_id: str) -> str:
        """An answer that reached here came from one measured path, so it attests LIVE.

        Same rule as the other live provider (V4 #2): the capture trusts this declaration, not the
        provider's name, and a leg that raised never gets this far -- it stays unavailable instead of
        being laundered into feasibility.
        """
        return LIVE_PROVIDER_CAPTURE

    def status_capabilities(self) -> dict[str, Any]:
        """What this provider can say before any request is made, with no key in it."""
        seam = china_routing_seam()
        return {
            "status": "READY" if (web_key() and seam == "amap") else "NOT_CONFIGURED",
            "provider_key": self.provider_key,
            "mode": self._mode,
            "city_code": self._city_code,
            "coordinate_crs": "GCJ02",
            "domain_crs": "WGS84",
            "conversion": "ITERATIVE_GCJ02_TO_WGS84",
            "seam": seam,
        }
