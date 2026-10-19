from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.integrations.discovery.provider_identity import PROVIDER_USER_AGENT


@dataclass(frozen=True)
class GeocodedPlace:
    external_id: str
    name: str
    # Nullable on purpose: an upstream geocoder CAN return a matched identity with no usable point --
    # a relation whose geometry it never resolved, or a hit it would not geocode.  Declaring these as
    # `float` while the provider had already returned None is how a "no coordinate" row used to become
    # either a dropped place or an invented coordinate; carrying the gap lets the catalog name it.
    latitude: float | None
    longitude: float | None
    country: str | None = None
    city: str | None = None
    raw: dict[str, Any] | None = None


class PhotonGeocoder:
    provider_key = "photon"

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str = "https://photon.komoot.io",
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def search(
        self, query: str, *, limit: int = 8, lang: str | None = None
    ) -> list[GeocodedPlace]:
        if not query.strip():
            return []
        params: dict[str, Any] = {"q": query, "limit": limit}
        if lang:
            params["lang"] = lang
        # The identity rides on the request, not on whoever built the client: this adapter speaks to a
        # provider that refuses an anonymous `python-httpx` caller (measured 2026-10-19 on
        # photon.komoot.io -- same URL, same params, `python-httpx/0.28.1` answered http_status=403 and
        # the product User-Agent answered http_status=200, one second apart).  Left to the caller, every
        # new `httpx.AsyncClient` re-introduces the refusal, and a refused provider reads as "this source
        # has nothing" instead of "nobody identified themselves".
        response = await self._client.get(
            f"{self._base_url}/api/",
            params=params,
            headers={"User-Agent": PROVIDER_USER_AGENT},
        )
        response.raise_for_status()
        features = response.json().get("features", [])
        result: list[GeocodedPlace] = []
        for feature in features:
            geometry = feature.get("geometry", {})
            coordinates = geometry.get("coordinates", [])
            properties = feature.get("properties", {})
            name = properties.get("name") or properties.get("street") or properties.get("city")
            osm_id = properties.get("osm_id")
            osm_type = properties.get("osm_type", "unknown")
            if name is None or osm_id is None:
                continue
            # A matched identity with no point is kept, not dropped: `GeocodedPlace` declares the gap,
            # and discarding the row here is how "found but not geocodable" silently became "not found"
            # -- the caller can only name that state if the row reaches it.
            has_point = len(coordinates) >= 2
            result.append(
                GeocodedPlace(
                    external_id=f"{osm_type}:{osm_id}",
                    name=str(name),
                    latitude=float(coordinates[1]) if has_point else None,
                    longitude=float(coordinates[0]) if has_point else None,
                    country=properties.get("country"),
                    city=properties.get("city"),
                    raw=feature,
                )
            )
        return result
