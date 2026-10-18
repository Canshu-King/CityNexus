"""Bounded Photon POI adapter for the existing discovery candidate contract.

This adapter uses Photon's reverse endpoint with the documented OSM category
filter.  It supports only the explicit category families below.  Photon is an
OSM geocoder, not a full-tag catalogue: optional OSM ``extra`` fields may be
absent, so opening hours and prices remain UNKNOWN unless the response carries
those tags.  A successful empty response is kept distinct from transport or
payload failure.

No candidate produced here is a CityNexus canonical identity or an attestation
of access, opening status, price, or catalogue completeness.
"""

from __future__ import annotations

import math
import re
import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.integrations.discovery.provider_identity import PROVIDER_USER_AGENT
from app.integrations.provider_config import ExternalProviderSettings
from app.integrations.discovery.real_city import (
    DiscoveryCandidate,
    cost_evidence_from_tags,
    normalize_opening_hours,
)

PHOTON_BASE_URL = "https://photon.komoot.io"
PHOTON_REVERSE_URL = f"{PHOTON_BASE_URL}/reverse"
OSM_ATTRIBUTION = "© OpenStreetMap contributors"
OSM_ATTRIBUTION_URL = "https://www.openstreetmap.org/copyright"
DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_TIMEOUT_SECONDS = 5.0
MAX_LIMIT = 20
MAX_RADIUS_METERS = 5_000_000
PHOTON_REJECTION_REASONS = (
    "malformed_structure",
    "missing_osm_identity",
    "missing_name",
    "category_mismatch",
    "invalid_coordinates",
    "out_of_range",
)


class UnsupportedPhotonQuery(ValueError):
    """Raised when Photon cannot safely represent a discovery category request."""


# The category names are Photon categories produced by the standard OSM
# importer.  Values in each tuple form an OR set in one `include` parameter.
_CATEGORY_RULES: tuple[tuple[tuple[str, ...], tuple[tuple[str, str], ...]], ...] = (
    (
        (
            "museum/gallery",
            "museum gallery",
            "art history",
            "arts and history",
            "博物馆/美术馆",
            "博物馆美术馆",
        ),
        (("tourism", "museum"), ("tourism", "gallery"), ("amenity", "arts_centre")),
    ),
    (
        ("park/garden", "park garden", "green walk", "quiet green"),
        (("leisure", "park"), ("leisure", "garden")),
    ),
    (("museum", "博物馆"), (("tourism", "museum"),)),
    (("gallery", "美术馆", "画廊"), (("tourism", "gallery"), ("amenity", "arts_centre"))),
    (("theatre", "theater", "剧院", "剧场"), (("amenity", "theatre"),)),
    (("library", "图书馆"), (("amenity", "library"),)),
    (("cafe", "coffee", "咖啡馆", "咖啡"), (("amenity", "cafe"),)),
    (
        ("restaurant", "food", "餐厅", "吃饭", "美食"),
        (("amenity", "restaurant"), ("amenity", "food_court")),
    ),
    (
        ("park", "garden", "公园", "户外", "花园", "庭园"),
        (("leisure", "park"), ("leisure", "garden")),
    ),
    (
        ("hotel", "住宿", "酒店"),
        (("tourism", "hotel"), ("tourism", "hostel"), ("tourism", "guest_house")),
    ),
    (
        ("attraction", "sight", "viewpoint", "景点", "tourist"),
        (("tourism", "attraction"), ("tourism", "viewpoint")),
    ),
    (
        ("nightlife", "夜生活", "酒吧", "夜店"),
        (("amenity", "bar"), ("amenity", "pub"), ("amenity", "nightclub")),
    ),
    (
        ("mobility", "地铁站", "公交", "交通站点"),
        (
            ("railway", "station"),
            ("railway", "subway_entrance"),
            ("amenity", "bus_station"),
            ("highway", "bus_stop"),
        ),
    ),
    (
        ("booking", "门票预约", "票务", "售票"),
        (("tourism", "ticket_converter"), ("amenity", "ticket_office")),
    ),
)
_FREE_MARKERS = ("free", "free entry", "no cost", "免费", "免票", "免费票")
_OSM_TYPES = {"N": "node", "W": "way", "R": "relation"}


def _query_contains(query: str, keyword: str) -> bool:
    """Match whole English words and literal Chinese category phrases."""

    if any(ord(char) > 127 for char in keyword):
        return keyword.casefold() in query.casefold()
    folded_query = re.sub(r"[\s/_-]+", " ", query.casefold()).strip()
    folded_keyword = re.sub(r"[\s/_-]+", " ", keyword.casefold()).strip()
    return (
        re.search(
            rf"(?<![a-z0-9_]){re.escape(folded_keyword)}(?![a-z0-9_])",
            folded_query,
        )
        is not None
    )


def _category_tags(query: str) -> tuple[tuple[str, str], ...]:
    normalized = " ".join(str(query or "").split())
    if not normalized:
        raise UnsupportedPhotonQuery("query must name one supported POI category")
    if any(_query_contains(normalized, marker) for marker in _FREE_MARKERS):
        raise UnsupportedPhotonQuery(
            "Photon cannot reliably filter free-entry status; fee tags may be absent"
        )
    for keywords, tags in _CATEGORY_RULES:
        if any(_query_contains(normalized, keyword) for keyword in keywords):
            return tags
    raise UnsupportedPhotonQuery("query is outside Photon POI category coverage")


def _finite_number(name: str, value: Any, low: float, high: float) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError(f"{name} must be between {low:g} and {high:g}")
    return number


def _validate_base_url(base_url: str) -> str:
    try:
        parsed = urlsplit(str(base_url))
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid Photon base URL") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != "photon.komoot.io"
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Photon base URL must be the official HTTPS Photon host")
    return PHOTON_BASE_URL


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(min(1.0, a)))


def _osm_identity(properties: Mapping[str, Any]) -> tuple[str, str] | None:
    raw_type = str(properties.get("osm_type") or "").strip()
    kind = raw_type.upper()
    if kind not in _OSM_TYPES and raw_type.casefold() in {v: k for k, v in _OSM_TYPES.items()}:
        kind = {v: k for k, v in _OSM_TYPES.items()}[raw_type.casefold()]
    raw_id = properties.get("osm_id")
    if kind not in _OSM_TYPES or isinstance(raw_id, bool):
        return None
    identifier = str(raw_id).strip()
    if not re.fullmatch(r"[1-9][0-9]*", identifier):
        return None
    return kind, identifier


def _feature_candidate_with_rejection(
    feature: Any,
    *,
    center_latitude: float,
    center_longitude: float,
    radius_m: float,
    allowed_categories: frozenset[tuple[str, str]],
) -> tuple[DiscoveryCandidate | None, str | None]:
    if not isinstance(feature, dict):
        return None, "malformed_structure"
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None, "malformed_structure"
    osm_identity = _osm_identity(properties)
    if osm_identity is None:
        return None, "missing_osm_identity"
    osm_type, osm_id = osm_identity
    name = properties.get("name")
    if not isinstance(name, str) or not name.strip():
        return None, "missing_name"
    osm_key = str(properties.get("osm_key") or "").strip().casefold()
    osm_value = str(properties.get("osm_value") or "").strip().casefold()
    if (osm_key, osm_value) not in allowed_categories:
        return None, "category_mismatch"
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
        return None, "invalid_coordinates"
    try:
        longitude = float(coordinates[0])
        latitude = float(coordinates[1])
    except (TypeError, ValueError, OverflowError):
        return None, "invalid_coordinates"
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        return None, "invalid_coordinates"
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None, "invalid_coordinates"
    distance = _distance_m(center_latitude, center_longitude, latitude, longitude)
    if distance > radius_m:
        return None, "out_of_range"

    extra = properties.get("extra")
    source_tags = dict(extra) if isinstance(extra, Mapping) else {}
    source_tags.setdefault("name", name.strip())
    source_tags.setdefault(osm_key, osm_value)
    source_url = f"https://www.openstreetmap.org/{_OSM_TYPES[osm_type]}/{osm_id}"
    category = osm_value
    return (
        DiscoveryCandidate(
            provider_key="photon",
            external_id=f"photon:{_OSM_TYPES[osm_type]}/{osm_id}",
            name=name.strip(),
            category=category,
            latitude=latitude,
            longitude=longitude,
            tags=tuple(
                sorted({category, "real_city", "indoor" if osm_key != "leisure" else "outdoor"})
            ),
            opening_hours=normalize_opening_hours(source_tags.get("opening_hours")),
            metadata={
                "osm_id": f"{_OSM_TYPES[osm_type]}/{osm_id}",
                "tags": source_tags,
                "photon_type": properties.get("type"),
                "countrycode": properties.get("countrycode"),
                "source_status": "LIVE_PROVIDER",
                "source_url": source_url,
                "attribution": OSM_ATTRIBUTION,
                "attribution_url": OSM_ATTRIBUTION_URL,
            },
            distance_m=distance,
            cost_evidence=cost_evidence_from_tags(source_tags, source="photon"),
        ),
        None,
    )


class PhotonPOIProvider:
    """One-shot, bounded POI query against the documented Photon reverse API."""

    provider_key = "photon"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        base_url: str = PHOTON_BASE_URL,
        timeout_s: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = _validate_base_url(base_url)
        self.timeout_s = _finite_number("timeout_s", timeout_s, 0.001, MAX_TIMEOUT_SECONDS)
        self.user_agent = (
            ExternalProviderSettings().photon_user_agent.strip() or PROVIDER_USER_AGENT
        )
        self.client = client or httpx.Client(
            timeout=self.timeout_s,
            follow_redirects=False,
            headers={"User-Agent": self.user_agent},
        )
        self._owned_client = client is None

    def search(
        self,
        query: str,
        *,
        latitude: float,
        longitude: float,
        radius_m: int,
        limit: int,
        max_attempts: int | None = 1,
    ) -> list[DiscoveryCandidate]:
        candidates, _attempts = self.search_with_evidence(
            query,
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
            limit=limit,
            max_attempts=max_attempts,
        )
        return candidates

    def search_with_evidence(
        self,
        query: str,
        *,
        latitude: float,
        longitude: float,
        radius_m: int,
        limit: int,
        max_attempts: int | None = 1,
    ) -> tuple[list[DiscoveryCandidate], list[dict[str, Any]]]:
        """Return bounded results and one factual request record; never retry."""

        if max_attempts is not None and (
            isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts != 1
        ):
            raise ValueError("Photon POI adapter permits exactly one request")
        category_tags = _category_tags(query)
        center_lat = _finite_number("latitude", latitude, -90, 90)
        center_lon = _finite_number("longitude", longitude, -180, 180)
        radius = _finite_number("radius_m", radius_m, 1, MAX_RADIUS_METERS)
        if not radius.is_integer():
            raise ValueError("radius_m must be an integer")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        effective_limit = min(limit, MAX_LIMIT)
        allowed = frozenset(category_tags)
        include = ",".join(f"osm.{key}.{value}" for key, value in category_tags)
        params = {
            "lat": center_lat,
            "lon": center_lon,
            # Photon documents reverse radius in kilometres (0..5000). The
            # local haversine check below enforces the caller's exact metre bound.
            "radius": radius / 1000.0,
            "limit": effective_limit,
            "include": include,
        }
        started = time.monotonic()
        try:
            response = self.client.get(
                f"{self.base_url}/reverse",
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout_s,
                follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            attempt = self._failed_attempt(started, error=exc)
            _attach_attempts(exc, [attempt])
            raise

        status = response.status_code
        if not 200 <= status < 300:
            try:
                response.raise_for_status()
            except httpx.HTTPError as exc:
                attempt = self._failed_attempt(started, status=status, error=exc)
                _attach_attempts(exc, [attempt])
                raise
            error = httpx.HTTPStatusError(
                f"Photon returned HTTP {status}", request=response.request, response=response
            )
            attempt = self._failed_attempt(started, status=status, error=error)
            _attach_attempts(error, [attempt])
            raise error

        try:
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
                raise TypeError("Photon response must contain a feature list")
        except (ValueError, TypeError) as exc:
            attempt = self._failed_attempt(started, status=status, error=exc)
            _attach_attempts(exc, [attempt])
            raise

        features = payload["features"]
        candidates: list[DiscoveryCandidate] = []
        rejected_by_reason = {reason: 0 for reason in PHOTON_REJECTION_REASONS}
        for feature in features:
            candidate, rejection_reason = _feature_candidate_with_rejection(
                feature,
                center_latitude=center_lat,
                center_longitude=center_lon,
                radius_m=radius,
                allowed_categories=allowed,
            )
            if rejection_reason is not None:
                rejected_by_reason[rejection_reason] += 1
            elif candidate is not None:
                candidates.append(candidate)
        candidates = candidates[:effective_limit]
        attempt = {
            "endpoint": PHOTON_REVERSE_URL,
            "answered": True,
            "http_status": status,
            "elapsed_ms": round((time.monotonic() - started) * 1000.0, 1),
            "elements": len(features),
            "features": len(features),
            "returned": len(candidates),
            "rejected_by_reason": rejected_by_reason,
            "source_status": "LIVE_PROVIDER",
            "result_status": "LIVE_RESULTS" if candidates else "LIVE_ZERO_RESULTS",
            "attribution": OSM_ATTRIBUTION,
            "attribution_url": OSM_ATTRIBUTION_URL,
        }
        return candidates, [attempt]

    @staticmethod
    def _failed_attempt(
        started: float, *, status: int | None = None, error: Exception
    ) -> dict[str, Any]:
        return {
            "endpoint": PHOTON_REVERSE_URL,
            "answered": False,
            "http_status": status,
            "elapsed_ms": round((time.monotonic() - started) * 1000.0, 1),
            "source_status": "RUNTIME_FAILURE",
            "error": f"{type(error).__name__}: {str(error)[:160]}",
        }

    def close(self) -> None:
        if self._owned_client:
            self.client.close()


def _attach_attempts(error: Exception, attempts: list[dict[str, Any]]) -> None:
    error.provider_attempts = attempts  # type: ignore[attr-defined]
