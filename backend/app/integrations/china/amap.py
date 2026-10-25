from __future__ import annotations

import logging
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

AMAP_BASE_URL = "https://restapi.amap.com"
MODE_PATHS = {
    "WALK": "walking",
    "BICYCLE": "bicycling",
    "TRANSIT": "transit/integrated",
    "AUTO": "driving",
}

# Two environment names, deliberately ordered. `CITYNEXUS_AMAP_WEB_KEY` is the one this deployment's
# local configuration tool writes; `AMAP_WEB_KEY` is what has always been read here, so a machine that
# is already configured keeps answering without anyone re-entering anything. The preferred name wins
# when both exist, and nothing in this module falls back to a key baked into the source.
KEY_ENV_PREFERRED = "CITYNEXUS_AMAP_WEB_KEY"
KEY_ENV_LEGACY = "AMAP_WEB_KEY"
KEY_PARAM_PATTERN = re.compile(r"([?&])key=[^&]*")


def web_key() -> str | None:
    return os.getenv(KEY_ENV_PREFERRED) or os.getenv(KEY_ENV_LEGACY)


def key_env_name() -> str | None:
    """Which name supplied the key -- the environment variable's own name, never its value."""
    if os.getenv(KEY_ENV_PREFERRED):
        return KEY_ENV_PREFERRED
    if os.getenv(KEY_ENV_LEGACY):
        return KEY_ENV_LEGACY
    return None


def missing_key_reason() -> str:
    return f"neither {KEY_ENV_PREFERRED} nor {KEY_ENV_LEGACY} is configured"


def sanitize_url(url: str) -> str:
    """The same URL with the key parameter replaced by a marker.

    This matters because `httpx.HTTPStatusError` prints the whole request URL, and the key travels as a
    query parameter: an exception that reaches a log line would otherwise carry the secret with it.
    """
    return KEY_PARAM_PATTERN.sub(lambda match: match.group(1) + "key=***", url)


def request_failure(exc: httpx.HTTPError) -> RuntimeError:
    """Turn an httpx failure into an exception whose message cannot carry the key.

    The HTTP-status leg knows the whole request URL and the transport leg knows only the exception
    type.  Both of them end up in a log line and, from here, in a product answer, so both go through
    this one rule.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return RuntimeError(
            f"Amap answered http_status={exc.response.status_code} for "
            + sanitize_url(str(exc.request.url))
        )
    return RuntimeError(f"Amap request did not complete: {type(exc).__name__}")


class KeyRedactionFilter(logging.Filter):
    """Masks `key=` in any log record that already carries one.

    `sanitize_url` only reaches the messages this module writes itself.  The wider risk is the
    library underneath: an `httpx` INFO line prints the full URL of every request it makes, and the
    key travels in that query string.  A filter on that logger is the only thing that can stop a
    secret from reaching a log line nobody read the source of.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except (TypeError, ValueError, AttributeError):
            # A record that cannot render is not ours to rewrite; letting it through keeps the
            # logging failure visible where it belongs instead of hiding it inside a guard.
            return True
        if KEY_PARAM_PATTERN.search(message):
            record.msg = KEY_PARAM_PATTERN.sub(lambda match: match.group(1) + "key=***", message)
            record.args = ()
        return True


FILTERED_LOGGERS: set[str] = set()


def install_log_redaction(*names: str) -> None:
    """Put the redaction filter on the request loggers, once per name, before any request is made."""
    targets = names or ("httpx",)
    for name in targets:
        logger = logging.getLogger(name)
        if name in FILTERED_LOGGERS and any(
            isinstance(existing, KeyRedactionFilter) for existing in logger.filters
        ):
            continue
        logger.addFilter(KeyRedactionFilter())
        FILTERED_LOGGERS.add(name)


async def amap_get(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> httpx.Response:
    """GET, failing only through `request_failure`, with the request loggers already masked."""
    install_log_redaction()
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
    except httpx.HTTPError as failure:
        raise request_failure(failure) from None
    return response


def amap_get_sync(client: httpx.Client, url: str, params: dict[str, Any]) -> httpx.Response:
    """The same two legs as `amap_get`, for callers that already hold a sync `httpx.Client`.

    The runtime mobility capture builds one sync client per operation and hands it to whichever
    provider is primary, so a provider that wants to be that primary has to answer on the same shape.
    The failure rule is shared here rather than retyped there: two writers of one rule drift, and the
    one that drifts is the one that starts leaking.
    """
    install_log_redaction()
    try:
        response = client.get(url, params=params)
        response.raise_for_status()
    except httpx.HTTPError as failure:
        raise request_failure(failure) from None
    return response


@dataclass(frozen=True)
class ProviderStatus:
    provider_key: str
    status: str
    provenance: str
    coordinate_crs: str
    reason: str | None = None


@dataclass(frozen=True)
class NormalizedRoute:
    mode: str
    duration_min: int
    distance_m: int
    cost_amount_minor: int | None
    currency: str | None
    cost_status: str
    walking_min: int
    transfers: int
    reliability_score: float
    geometry: dict[str, Any]
    source_crs: str
    domain_crs: str
    conversion: str
    provider_key: str = "amap-web-service"


def amap_status() -> ProviderStatus:
    configured = web_key() is not None
    return ProviderStatus(
        provider_key="amap-web-service",
        status="READY" if configured else "NOT_CONFIGURED",
        provenance="LIVE" if configured else "UNAVAILABLE",
        coordinate_crs="GCJ02",
        reason=None if configured else missing_key_reason(),
    )


def provider_for_region(city_code: str) -> str:
    return (
        "amap-web-service" if str(city_code).upper().startswith("CN-") else "global-provider-mesh"
    )


_REGION_ADCODE = re.compile(r"\d{6}")
_REGION_CJK = re.compile(r"[\u4e00-\u9fff]")


def is_amap_region(value: str | None) -> bool:
    """Can Amap use this string as a `region` filter, or will it silently answer elsewhere?

    Measured 2026-10-25 against the live service: `region=CN-12-01&citylimit=true` answered
    status=1 with a Shandong POI (adcode 370321) -- the internal city code was ignored rather than
    refused, so a caller that passed one got credible-looking results from the wrong province.
    Amap accepts a 6-digit adcode or a Chinese city name; every other form must not be sent.
    """
    text = str(value or "").strip()
    if not text:
        return True
    return bool(_REGION_ADCODE.fullmatch(text)) or bool(_REGION_CJK.search(text))


ROUTING_SEAM_ENV = "CITYNEXUS_CHINA_MOBILITY_ROUTING"


def china_routing_seam() -> str:
    """`off` puts a Chinese journey's legs back on the previous providers; `amap` is the default.

    The seam is read from the process environment rather than `Settings` so that switching the
    country routing off is an operation on the running process, not a code change -- and so this
    module stays the only place that knows the name.
    """
    value = str(os.getenv(ROUTING_SEAM_ENV, "amap") or "amap").strip().lower()
    return value if value in {"off", "amap"} else "amap"


def routes_via_amap(city_code: str) -> bool:
    """Would a journey in this city be routed through Amap right now?

    Three things have to be true together: the city is a Chinese administrative region, a key is
    configured under one of the two names, and the seam has not been switched off.  Anything else
    answers `False`, which is the same answer the tree gave before this provider existed.
    """
    return provider_for_region(city_code) == "amap-web-service" and web_key() is not None and (
        china_routing_seam() == "amap"
    )


def _outside_china(latitude: float, longitude: float) -> bool:
    return longitude < 72.004 or longitude > 137.8347 or latitude < 0.8293 or latitude > 55.8271


def _transform(latitude: float, longitude: float) -> tuple[float, float]:
    x = longitude - 105.0
    y = latitude - 35.0
    dlat = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    dlon = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    dlat += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    dlon += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    dlat += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    dlon += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    dlat += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    dlon += (
        (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    )
    radius = 6378245.0
    eccentricity = 0.006693421622965943
    radlat = latitude / 180.0 * math.pi
    magic = 1 - eccentricity * math.sin(radlat) ** 2
    sqrtmagic = math.sqrt(magic)
    dlat = dlat * 180.0 / ((radius * (1 - eccentricity)) / (magic * sqrtmagic) * math.pi)
    dlon = dlon * 180.0 / (radius / sqrtmagic * math.cos(radlat) * math.pi)
    return latitude + dlat, longitude + dlon


def wgs84_to_gcj02(latitude: float, longitude: float) -> tuple[float, float]:
    if _outside_china(latitude, longitude):
        return latitude, longitude
    return _transform(latitude, longitude)


def gcj02_to_wgs84(latitude: float, longitude: float) -> tuple[float, float]:
    if _outside_china(latitude, longitude):
        return latitude, longitude
    guess_lat, guess_lon = latitude, longitude
    for _ in range(8):
        transformed_lat, transformed_lon = wgs84_to_gcj02(guess_lat, guess_lon)
        guess_lat -= transformed_lat - latitude
        guess_lon -= transformed_lon - longitude
    return guess_lat, guess_lon


def _parse_polyline(polyline: str) -> list[list[float]]:
    points: list[list[float]] = []
    for raw in polyline.split(";"):
        if not raw:
            continue
        longitude, latitude = (float(value) for value in raw.split(",", 1))
        wgs_lat, wgs_lon = gcj02_to_wgs84(latitude, longitude)
        points.append([wgs_lon, wgs_lat])
    return points


class AmapPoiProvider:
    provider_key = "amap-web-service"

    async def search(
        self,
        query: str,
        city: str,
        *,
        limit: int = 10,
        client: httpx.AsyncClient | None = None,
    ) -> list[dict[str, Any]]:
        """Keyword search inside one administrative region, in the shape the lead surface reads.

        `client` is injectable so this leg can be driven in a test without a socket; when a caller
        passes one in, that caller owns closing it. `adcode` and `cityname` are copied only when the
        answer carried them -- the administrative region is the field that separates two places with
        the same name in different cities, so it is never filled in from the request.
        """
        key = web_key()
        if not key:
            raise RuntimeError(missing_key_reason())
        if not is_amap_region(city):
            raise ValueError(
                f"Amap POI search needs a city name or a 6-digit adcode as region, not {city!r}"
            )
        params: dict[str, Any] = {
            "key": key,
            "keywords": query,
            "region": city,
            "page_size": min(limit, 25),
            "show_fields": "business",
        }
        if city:
            # Without this the answer is not restricted to the named administrative region, so a
            # same-named place in another city is returned as if it were the one the traveller asked
            # for. The region is a filter, not a hint.
            params["citylimit"] = "true"
        owns_client = client is None
        if owns_client:
            client = httpx.AsyncClient(timeout=12.0)
        try:
            response = await amap_get(client, f"{AMAP_BASE_URL}/v5/place/text", params)
            payload = response.json()
        finally:
            if owns_client:
                await client.aclose()
        if str(payload.get("status")) != "1":
            raise RuntimeError(str(payload.get("info") or "Amap POI request failed"))
        captured = datetime.now(timezone.utc).isoformat(timespec="seconds")
        result = []
        for item in payload.get("pois", [])[:limit]:
            parts = str(item.get("location") or "").split(",", 1)
            latitude = None
            longitude = None
            if len(parts) == 2:
                try:
                    raw_lon, raw_lat = float(parts[0]), float(parts[1])
                except ValueError:
                    raw_lon = raw_lat = None
                if raw_lat is not None:
                    latitude, longitude = gcj02_to_wgs84(raw_lat, raw_lon)
            result.append(
                {
                    "external_id": item.get("id"),
                    "provider_item_id": item.get("id"),
                    "name": item.get("name"),
                    "latitude": latitude,
                    "longitude": longitude,
                    "source_crs": "GCJ02",
                    "domain_crs": "WGS84",
                    "coordinate_system": "WGS84",
                    "conversion": "ITERATIVE_GCJ02_TO_WGS84",
                    "provider_key": self.provider_key,
                    "adcode": item.get("adcode"),
                    "region": item.get("cityname"),
                    "captured_at": captured,
                }
            )
        return result


def normalize_direction_payload(payload: dict[str, Any], mode: str) -> NormalizedRoute:
    """One Amap direction answer, read once, for whoever asked.

    This is the only place that knows Amap's route shape.  The async provider above and the sync
    mobility-capture adapter both go through it, because a parsing rule with two writers is how a
    converted geometry ends up converted by one of them.

    The polyline arrives in GCJ-02 and leaves as WGS84 `[[lon, lat], …]` -- the order the snapshot
    capture's own geometry reader expects.  `transfers` is not read from this payload: v5 answers a
    transit with segments this function does not walk, so a transit answer carries `transfers=0` as
    "not derived from this answer", and nothing here is allowed to read it as "direct".
    """
    normalized_mode = mode.upper()
    if str(payload.get("status")) != "1":
        raise RuntimeError(str(payload.get("info") or "Amap route request failed"))
    route = payload.get("route", {})
    paths = route.get("paths") or route.get("transits") or []
    if not paths:
        raise RuntimeError("Amap returned no route path")
    selected = paths[0]
    steps = selected.get("steps") or []
    polyline = ";".join(str(step.get("polyline") or "") for step in steps)
    distance = int(float(selected.get("distance") or 0))
    duration = max(
        1,
        math.ceil(
            float(selected.get("cost", {}).get("duration") or selected.get("duration") or 60) / 60
        ),
    )
    taxi_cost = selected.get("cost", {}).get("taxi_fee")
    cost = int(float(taxi_cost) * 100) if taxi_cost not in (None, "") else None
    cost_status = (
        "ESTIMATED"
        if cost is not None
        else ("FREE_KNOWN" if normalized_mode == "WALK" else "UNKNOWN")
    )
    return NormalizedRoute(
        mode=normalized_mode,
        duration_min=duration,
        distance_m=distance,
        cost_amount_minor=cost,
        currency="CNY" if cost is not None else None,
        cost_status=cost_status,
        walking_min=duration if normalized_mode == "WALK" else 0,
        transfers=0,
        reliability_score=0.9,
        geometry={
            "type": "Feature",
            "properties": {"source_crs": "GCJ02", "domain_crs": "WGS84"},
            "geometry": {"type": "LineString", "coordinates": _parse_polyline(polyline)},
        },
        source_crs="GCJ02",
        domain_crs="WGS84",
        conversion="ITERATIVE_GCJ02_TO_WGS84",
    )


class AmapMobilityProvider:
    provider_key = "amap-web-service"

    async def route(
        self,
        mode: str,
        *,
        origin_wgs84: tuple[float, float],
        destination_wgs84: tuple[float, float],
        city_code: str,
    ) -> NormalizedRoute:
        normalized_mode = mode.upper()
        path = MODE_PATHS.get(normalized_mode)
        key = web_key()
        if not key:
            raise RuntimeError(missing_key_reason())
        if not path:
            raise ValueError(f"Amap does not provide mode {mode}")
        origin_lat, origin_lon = wgs84_to_gcj02(*origin_wgs84)
        dest_lat, dest_lon = wgs84_to_gcj02(*destination_wgs84)
        params = {
            "key": key,
            "origin": f"{origin_lon},{origin_lat}",
            "destination": f"{dest_lon},{dest_lat}",
            "city1": city_code,
            "city2": city_code,
            "show_fields": "cost,polyline",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await amap_get(client, f"{AMAP_BASE_URL}/v5/direction/{path}", params)
            payload = response.json()
        return normalize_direction_payload(payload, normalized_mode)


class AmapTrafficProvider:
    provider_key = "amap-web-service"

    def status(self) -> ProviderStatus:
        return amap_status()
