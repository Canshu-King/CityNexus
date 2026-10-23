"""A narrow, one-request-per-call adapter for AMap China Web APIs.

All returned place and route coordinates are provider-native GCJ-02.  Callers
must preserve that coordinate system when displaying or routing these leads.
The API key is required by AMap in the query string, so the httpx/httpcore
request loggers receive a redaction filter before any request can be made.
"""
from __future__ import annotations

import logging
import math
import os
import re
from typing import Any

import httpx

AMAP_BASE_URL = "https://restapi.amap.com"
_ADCODE_RE = re.compile(r"^[0-9]{6}$")
# The transit endpoint wants AMap's telephone-style city code ("010" for Beijing), which is a different
# thing from the six-digit adcode a place search returns; the two are not interchangeable.
_CITY_CODE_RE = re.compile(r"^[0-9]{3,4}$")
_DATE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$")
_TIME_RE = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
_KEY_QUERY_RE = re.compile(r"(?i)([?&]key=)[^&\s]+")
_MAX_RESULTS = 25
_MIN_RADIUS_M = 100
_MAX_RADIUS_M = 5000
_TIMEOUT_SECONDS = 12.0
_INFOCODE_REASON_CODES = {
    # Key validity / platform / IP / domain binding / signature failures.
    "10001": "AMAP_INVALID_KEY",
    "10005": "AMAP_SERVICE_PERMISSION_DENIED",
    "10006": "AMAP_INVALID_KEY",
    "10007": "AMAP_INVALID_KEY",
    "10008": "AMAP_INVALID_KEY",
    "10009": "AMAP_INVALID_KEY",
    "10013": "AMAP_INVALID_KEY",
    # Daily, per-minute, IP, service, account and purchased-plan quota limits.
    "10003": "AMAP_QUOTA_EXCEEDED",
    "10010": "AMAP_QUOTA_EXCEEDED",
    "10014": "AMAP_QUOTA_EXCEEDED",
    "10015": "AMAP_QUOTA_EXCEEDED",
    "10019": "AMAP_QUOTA_EXCEEDED",
    "10020": "AMAP_QUOTA_EXCEEDED",
    "10029": "AMAP_QUOTA_EXCEEDED",
    "10044": "AMAP_QUOTA_EXCEEDED",
    "10045": "AMAP_QUOTA_EXCEEDED",
    "40000": "AMAP_QUOTA_EXCEEDED",
    "40003": "AMAP_QUOTA_EXCEEDED",
    # Asked too often at once, not out of today's allowance.  Measured, not read off the docs: eight
    # walking calls fired back to back on one short city pair -- the first three answered OK, the next
    # three came back infocode 10021 CUQPS_HAS_EXCEEDED_THE_LIMIT, and a single call four seconds later
    # answered OK again (trial/results/20261022_v3_human_chrome/amap-burst-infocode-1.txt:2 against :3).
    # Telling a traveller "今天的查询次数已经用完" about this sends them to the wrong door: nothing is
    # spent, and waiting a moment is enough.  10004 is the provider's other too-fast code
    # (ACCESS_TOO_FREQUENTLY); it has not been reproduced here, but it names the same condition.
    "10004": "AMAP_RATE_LIMITED",
    "10021": "AMAP_RATE_LIMITED",
    # Missing, insufficient, expired, or geographically unavailable service.
    "10002": "AMAP_SERVICE_PERMISSION_DENIED",
    "10012": "AMAP_SERVICE_PERMISSION_DENIED",
    "10041": "AMAP_SERVICE_PERMISSION_DENIED",
    "20011": "AMAP_SERVICE_PERMISSION_DENIED",
    "40002": "AMAP_SERVICE_PERMISSION_DENIED",
    # The provider's own words for "this pair is beyond what I will route".  Measured, not inferred:
    # walking 王府井步行街 -> 八达岭长城 (about 45 km) comes back infocode 20803 OVER_DIRECTION_RANGE,
    # an 800 m hop in the same city comes back OK at the same minute, and the transit door answers that
    # very same pair with five routes
    # (trial/results/20261022_v3_human_chrome/amap-quota-vs-qps-1.txt:2, :3 and :4, read 2026-10-23
    # 12:24 +08).  Until now 20803 fell into the catch-all AMAP_PROVIDER_REJECTED, so the traveller was
    # told 这一段没有步行路线 -- a weaker sentence than the one the source actually said, and a sentence
    # that hides the reason a bus answer exists for the same pair.
    "20803": "AMAP_OUT_OF_PROVIDER_RANGE",
}


class _AmapKeyRedactionFilter(logging.Filter):
    """Remove AMap query credentials from library log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
        except Exception:
            return False
        record.msg = _KEY_QUERY_RE.sub(r"\1[redacted]", rendered)
        record.args = ()
        return True


def _install_log_redaction() -> None:
    # httpx emits its request URL at INFO; httpcore can emit request targets at
    # DEBUG.  Installing once at module import avoids request-scoped global
    # logger mutations and ensures both paths redact the key.
    redactor = _AmapKeyRedactionFilter()
    logger_names = {
        "httpx",
        "httpcore",
        "httpcore.connection",
        "httpcore.http11",
        "httpcore.http2",
        "httpcore.proxy",
        "httpcore._sync.connection_pool",
        "httpcore._sync.http11",
        "httpcore._sync.http2",
        "httpcore._async.connection_pool",
        "httpcore._async.http11",
        "httpcore._async.http2",
    }
    logger_names.update(
        name
        for name in logging.root.manager.loggerDict
        if isinstance(name, str) and (name == "httpcore" or name.startswith("httpcore."))
    )
    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        if not any(isinstance(item, _AmapKeyRedactionFilter) for item in logger.filters):
            logger.addFilter(redactor)


_install_log_redaction()


def _text(value: Any, *, maximum: int = 200) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    if not normalized or len(normalized) > maximum:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        return None
    return normalized


def _adcode(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized if _ADCODE_RE.fullmatch(normalized) else None


def _region_status(place_adcode: str | None, requested_adcode: str | None) -> str:
    """Compare provider and requested regions at the requested admin level."""
    if place_adcode is None or requested_adcode is None:
        return "UNKNOWN"
    if requested_adcode.endswith("0000"):
        matches = place_adcode[:2] == requested_adcode[:2]
    elif requested_adcode.endswith("00"):
        matches = place_adcode[:4] == requested_adcode[:4]
    else:
        matches = place_adcode == requested_adcode
    return "MATCH" if matches else "CONFLICT"


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return int(number)


def _coordinate_pair(value: Any) -> tuple[float, float] | None:
    """Validate a (latitude, longitude) pair without changing its datum."""
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        return None
    if isinstance(value[0], bool) or isinstance(value[1], bool):
        return None
    try:
        latitude, longitude = float(value[0]), float(value[1])
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        return None
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        return None
    return latitude, longitude


def _base_result(status: str, reason_code: str | None, http_status: int | None) -> dict[str, Any]:
    return {"status": status, "reason_code": reason_code, "http_status": http_status}


class AmapClient:
    """AMap district, POI, nearby, and walking-route client.

    ``transport`` is injectable for deterministic unit tests.  Each public
    method performs at most one HTTP request; redirects and retries are off.
    Coordinates passed to ``around`` and ``walking`` must already be GCJ-02.
    When ``search`` receives an adcode, callers should take it from a matching
    ``district`` result and check the exact requested district and ancestry.
    """

    provider_key = "amap-web-service"
    coordinate_system = "GCJ02"

    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        *,
        timeout_s: float = _TIMEOUT_SECONDS,
    ) -> None:
        if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
            raise ValueError("timeout_s must be a positive finite number")
        if not math.isfinite(float(timeout_s)) or timeout_s <= 0:
            raise ValueError("timeout_s must be a positive finite number")
        self._api_key = str(api_key if api_key is not None else os.getenv("AMAP_WEB_KEY", "")).strip()
        self._timeout_s = float(timeout_s)
        self._client = httpx.Client(
            transport=transport,
            timeout=self._timeout_s,
            follow_redirects=False,
            trust_env=False,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "AmapClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def district(self, query: str) -> dict[str, Any]:
        """Resolve candidate Chinese administrative areas and their adcodes."""
        normalized = _text(query, maximum=100)
        if normalized is None or len(normalized) < 2:
            return {**_base_result("error", "AMAP_INVALID_QUERY", None), "districts": []}
        payload, http_status, error = self._request(
            "/v3/config/district",
            {"keywords": normalized, "subdistrict": 1, "extensions": "base"},
        )
        if error:
            return {**_base_result("error", error, http_status), "districts": []}
        if not isinstance(payload.get("districts"), list):
            return {**_base_result("error", "AMAP_INVALID_RESPONSE", http_status), "districts": []}
        candidates: list[dict[str, Any]] = []
        self._collect_districts(payload.get("districts"), candidates, ancestors=())
        return {**_base_result("ok", None, http_status), "districts": candidates}

    def search(
        self,
        query: str,
        city: str,
        adcode: str | None = None,
        limit: int = 8,
    ) -> dict[str, Any]:
        """Search POIs within a city name or an exact six-digit adcode."""
        normalized_query = _text(query, maximum=120)
        normalized_city = _text(city, maximum=100)
        normalized_adcode = _adcode(adcode) if adcode is not None else None
        if normalized_query is None or len(normalized_query) < 2:
            return {**_base_result("error", "AMAP_INVALID_QUERY", None), "places": []}
        if normalized_city is None:
            return {**_base_result("error", "AMAP_INVALID_CITY", None), "places": []}
        if adcode is not None and normalized_adcode is None:
            return {**_base_result("error", "AMAP_INVALID_ADCODE", None), "places": []}
        result_limit = self._limit(limit)
        if result_limit is None:
            return {**_base_result("error", "AMAP_INVALID_LIMIT", None), "places": []}
        payload, http_status, error = self._request(
            "/v5/place/text",
            {
                "keywords": normalized_query,
                "region": normalized_adcode or normalized_city,
                "city_limit": "true",
                "page_size": result_limit,
                "show_fields": "business",
            },
        )
        if error:
            return {**_base_result("error", error, http_status), "places": []}
        rows = payload.get("pois")
        if not isinstance(rows, list):
            return {**_base_result("error", "AMAP_INVALID_RESPONSE", http_status), "places": []}
        places = self._parse_places(rows, result_limit, requested_adcode=normalized_adcode)
        return {**_base_result("ok", None, http_status), "places": places}

    def around(
        self,
        latitude: float,
        longitude: float,
        query: str,
        radius_m: int = 1500,
        limit: int = 8,
        adcode: str | None = None,
    ) -> dict[str, Any]:
        """Search near a GCJ-02 center; returned coordinates stay GCJ-02."""
        normalized_query = _text(query, maximum=120)
        if normalized_query is None or len(normalized_query) < 2:
            return {**_base_result("error", "AMAP_INVALID_QUERY", None), "places": []}
        center = _coordinate_pair((latitude, longitude))
        if center is None:
            return {**_base_result("error", "AMAP_INVALID_COORDINATE", None), "places": []}
        if isinstance(radius_m, bool) or not isinstance(radius_m, int) \
                or not _MIN_RADIUS_M <= radius_m <= _MAX_RADIUS_M:
            return {**_base_result("error", "AMAP_INVALID_RADIUS", None), "places": []}
        normalized_adcode = _adcode(adcode) if adcode is not None else None
        if adcode is not None and normalized_adcode is None:
            return {**_base_result("error", "AMAP_INVALID_ADCODE", None), "places": []}
        result_limit = self._limit(limit)
        if result_limit is None:
            return {**_base_result("error", "AMAP_INVALID_LIMIT", None), "places": []}
        lat, lon = center
        params: dict[str, Any] = {
            "keywords": normalized_query,
            "location": f"{lon:.6f},{lat:.6f}",
            "radius": radius_m,
            "sortrule": "distance",
            "page_size": result_limit,
            "show_fields": "business",
        }
        if normalized_adcode:
            params.update({"region": normalized_adcode, "city_limit": "true"})
        payload, http_status, error = self._request("/v5/place/around", params)
        if error:
            return {**_base_result("error", error, http_status), "places": []}
        rows = payload.get("pois")
        if not isinstance(rows, list):
            return {**_base_result("error", "AMAP_INVALID_RESPONSE", http_status), "places": []}
        places = self._parse_places(rows, result_limit, requested_adcode=normalized_adcode)
        return {**_base_result("ok", None, http_status), "places": places}

    def walking(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        adcode: str | None = None,
    ) -> dict[str, Any]:
        """Return an AMap walking path for GCJ-02 (latitude, longitude) pairs."""
        origin_pair = _coordinate_pair(origin)
        destination_pair = _coordinate_pair(destination)
        if origin_pair is None or destination_pair is None:
            return {**_base_result("error", "AMAP_INVALID_COORDINATE", None), "route": None}
        normalized_adcode = _adcode(adcode) if adcode is not None else None
        if adcode is not None and normalized_adcode is None:
            return {**_base_result("error", "AMAP_INVALID_ADCODE", None), "route": None}
        origin_lat, origin_lon = origin_pair
        destination_lat, destination_lon = destination_pair
        payload, http_status, error = self._request(
            "/v5/direction/walking",
            {
                "origin": f"{origin_lon:.6f},{origin_lat:.6f}",
                "destination": f"{destination_lon:.6f},{destination_lat:.6f}",
                "show_fields": "cost,polyline",
            },
        )
        if error:
            return {**_base_result("error", error, http_status), "route": None}
        route_data = payload.get("route")
        paths = route_data.get("paths") if isinstance(route_data, dict) else None
        if not isinstance(paths, list) or not paths or not isinstance(paths[0], dict):
            return {**_base_result("error", "AMAP_NO_ROUTE", http_status), "route": None}
        selected = paths[0]
        distance = _nonnegative_int(selected.get("distance"))
        cost = selected.get("cost")
        duration_value = cost.get("duration") if isinstance(cost, dict) else None
        if duration_value is None:
            duration_value = selected.get("duration")
        duration = _nonnegative_int(duration_value)
        steps = selected.get("steps")
        if distance is None or duration is None or not isinstance(steps, list):
            return {**_base_result("error", "AMAP_INVALID_RESPONSE", http_status), "route": None}
        coordinates: list[list[float]] = []
        for step in steps:
            if not isinstance(step, dict) or not isinstance(step.get("polyline"), str):
                continue
            for point in step["polyline"].split(";"):
                parsed = self._parse_location(point)
                if parsed is not None and (not coordinates or coordinates[-1] != parsed):
                    coordinates.append(parsed)
        if len(coordinates) < 2:
            return {**_base_result("error", "AMAP_INVALID_RESPONSE", http_status), "route": None}
        route = {
            "provider_key": self.provider_key,
            "mode": "WALK",
            "distance_m": distance,
            "duration_seconds": duration,
            "duration_min": math.ceil(duration / 60),
            "origin": self._point(*origin_pair),
            "destination": self._point(*destination_pair),
            "path": {"type": "LineString", "coordinates": coordinates, "coordinate_system": "GCJ02"},
            "coordinate_system": "GCJ02",
            "adcode": normalized_adcode,
        }
        return {**_base_result("ok", None, http_status), "route": route}

    def transit(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        city_code: str,
        *,
        departure_date: str | None = None,
        departure_time: str | None = None,
    ) -> dict[str, Any]:
        """Return AMap's public-transport answer for GCJ-02 (latitude, longitude) pairs.

        Why this sits next to `walking`: the hop a traveller cannot walk is the one that closes a day and
        opens the next, and a walking minute for it is a number for a trip nobody actually makes.  Two
        facts were measured on the live service before this method was written, and both are encoded here
        (trial/results/20261022_v3_human_chrome/amap-transit-night-3.txt): a departure hour is honoured
        only as a `date`+`time` pair -- `departure_time` returned the daytime answer unchanged -- and the
        provider's own `nightflag` reads 0 even on a night line, so this method keeps that field as sent
        and never turns it into a claim.  A half-specified departure is therefore refused rather than
        quietly dropped, because a daytime answer to a night question is exactly the failure this exists
        to avoid.

        No geometry is returned.  Nothing in the product draws a transit polyline yet, and a half-parsed
        one would look on the map like a route the provider never showed us.
        """
        origin_pair = _coordinate_pair(origin)
        destination_pair = _coordinate_pair(destination)
        if origin_pair is None or destination_pair is None:
            return {**_base_result("error", "AMAP_INVALID_COORDINATE", None), "route": None}
        normalized_city = _text(city_code, maximum=8)
        if normalized_city is None or not _CITY_CODE_RE.fullmatch(normalized_city):
            return {**_base_result("error", "AMAP_INVALID_CITY_CODE", None), "route": None}
        date_text = _text(departure_date, maximum=10) if departure_date is not None else None
        time_text = _text(departure_time, maximum=5) if departure_time is not None else None
        if (date_text is None) != (time_text is None):
            return {**_base_result("error", "AMAP_INVALID_DEPARTURE", None), "route": None}
        if date_text is not None and not _DATE_RE.fullmatch(date_text):
            return {**_base_result("error", "AMAP_INVALID_DEPARTURE", None), "route": None}
        if time_text is not None and not _TIME_RE.fullmatch(time_text):
            return {**_base_result("error", "AMAP_INVALID_DEPARTURE", None), "route": None}
        origin_lat, origin_lon = origin_pair
        destination_lat, destination_lon = destination_pair
        params: dict[str, Any] = {
            "origin": f"{origin_lon:.6f},{origin_lat:.6f}",
            "destination": f"{destination_lon:.6f},{destination_lat:.6f}",
            "city1": normalized_city,
            "city2": normalized_city,
            "show_fields": "cost",
        }
        if date_text is not None and time_text is not None:
            params["date"] = date_text
            params["time"] = time_text
        payload, http_status, error = self._request("/v5/direction/transit/integrated", params)
        if error:
            return {**_base_result("error", error, http_status), "route": None}
        route_data = payload.get("route")
        transits = route_data.get("transits") if isinstance(route_data, dict) else None
        if not isinstance(transits, list) or not transits or not isinstance(transits[0], dict):
            return {**_base_result("error", "AMAP_NO_ROUTE", http_status), "route": None}
        selected = transits[0]
        distance = _nonnegative_int(selected.get("distance"))
        cost = selected.get("cost")
        duration_value = cost.get("duration") if isinstance(cost, dict) else None
        if duration_value is None:
            duration_value = selected.get("duration")
        duration = _nonnegative_int(duration_value)
        if distance is None or duration is None:
            return {**_base_result("error", "AMAP_INVALID_RESPONSE", http_status), "route": None}
        lines: list[str] = []
        segments = selected.get("segments")
        for segment in segments if isinstance(segments, list) else []:
            if not isinstance(segment, dict):
                continue
            bus = segment.get("bus")
            buslines = bus.get("buslines") if isinstance(bus, dict) else None
            for line in buslines if isinstance(buslines, list) else []:
                name = _text(line.get("name"), maximum=120) if isinstance(line, dict) else None
                if name and name not in lines:
                    lines.append(name)
        fare: int | None = None
        fare_text = cost.get("transit_fee") if isinstance(cost, dict) else None
        if fare_text not in (None, ""):
            try:
                fare = int(round(float(str(fare_text)) * 100))
            except (TypeError, ValueError):
                fare = None
        route = {
            "provider_key": self.provider_key,
            "mode": "TRANSIT",
            "distance_m": distance,
            "duration_seconds": duration,
            "duration_min": math.ceil(duration / 60),
            "origin": self._point(*origin_pair),
            "destination": self._point(*destination_pair),
            "lines": lines,
            "walking_distance_m": _nonnegative_int(selected.get("walking_distance")),
            "fare_minor": fare,
            "nightflag": selected.get("nightflag"),
            "requested_departure": {"date": date_text, "time": time_text} if date_text and time_text else None,
            "coordinate_system": "GCJ02",
            "city_code": normalized_city,
        }
        return {**_base_result("ok", None, http_status), "route": route}

    @staticmethod
    def _limit(limit: int) -> int | None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            return None
        return min(limit, _MAX_RESULTS)

    @staticmethod
    def _point(latitude: float, longitude: float) -> dict[str, Any]:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "coordinate_system": "GCJ02",
        }

    @staticmethod
    def _parse_location(value: Any) -> list[float] | None:
        if not isinstance(value, str):
            return None
        parts = value.split(",", 1)
        if len(parts) != 2:
            return None
        pair = _coordinate_pair((parts[1], parts[0]))
        if pair is None:
            return None
        latitude, longitude = pair
        return [longitude, latitude]

    def _parse_places(
        self,
        rows: Any,
        limit: int,
        *,
        requested_adcode: str | None,
    ) -> list[dict[str, Any]]:
        if not isinstance(rows, list):
            return []
        places: list[dict[str, Any]] = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            provider_id = _text(row.get("id"), maximum=120)
            name = _text(row.get("name"), maximum=200)
            location = self._parse_location(row.get("location"))
            if provider_id is None or name is None or location is None:
                continue
            lon, lat = location
            place_adcode = _adcode(row.get("adcode")) if row.get("adcode") else None
            # Both POI calls already ask AMap for its business block (``show_fields=business`` above),
            # and this projection used to keep none of it -- so every researched place reached the
            # departure door with an empty opening-hours envelope, and the door said "营业时间" was
            # missing.  Measured live 2026-10-23: 天坛公园 answers 「周一至周日 06:30-22:00 最晚进入21:00 …」
            # and 故宫博物院 answers a seasonal sentence that also names its Monday closure.
            business = row.get("business") if isinstance(row.get("business"), dict) else {}
            opening_text = _text(business.get("opentime_week") or business.get("opentime_today"), maximum=400)
            places.append(
                {
                    "external_id": f"amap:{provider_id}",
                    "provider_id": provider_id,
                    "provider_key": self.provider_key,
                    "name": name,
                    "category": _text(row.get("type"), maximum=120),
                    "address": _text(row.get("address"), maximum=300),
                    "province": _text(row.get("pname"), maximum=100),
                    "city": _text(row.get("cityname"), maximum=100),
                    "district": _text(row.get("adname"), maximum=100),
                    "adcode": place_adcode,
                    "citycode": _text(row.get("citycode"), maximum=12),
                    "requested_adcode": requested_adcode,
                    "region_status": _region_status(place_adcode, requested_adcode),
                    "latitude": lat,
                    "longitude": lon,
                    "coordinate_system": "GCJ02",
                    "opening_hours_text": opening_text,
                }
            )
        return places

    @classmethod
    def _collect_districts(
        cls,
        rows: Any,
        output: list[dict[str, Any]],
        *,
        ancestors: tuple[str, ...],
    ) -> None:
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = _text(row.get("name"), maximum=100)
            code = _adcode(row.get("adcode"))
            citycode = _text(row.get("citycode"), maximum=12)
            level = _text(row.get("level"), maximum=30)
            parent = ancestors[-1] if ancestors else None
            if name is not None and code is not None:
                output.append(
                    {
                        "name": name,
                        "adcode": code,
                        "citycode": citycode,
                        "level": level,
                        "parent": parent,
                        "ancestors": list(ancestors),
                        "center": _text(row.get("center"), maximum=80),
                    }
                )
            next_ancestors = (*ancestors, name) if name is not None else ancestors
            cls._collect_districts(row.get("districts"), output, ancestors=next_ancestors)

    def _request(
        self,
        path: str,
        params: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, int | None, str | None]:
        if not self._api_key:
            return None, None, "AMAP_NOT_CONFIGURED"
        try:
            response = self._client.get(
                f"{AMAP_BASE_URL}{path}",
                params={**params, "key": self._api_key},
                timeout=self._timeout_s,
                follow_redirects=False,
            )
        except httpx.HTTPError:
            return None, None, "AMAP_HTTP_ERROR"
        http_status = response.status_code
        if not 200 <= http_status < 300:
            return None, http_status, "AMAP_HTTP_ERROR"
        try:
            payload = response.json()
        except (ValueError, TypeError):
            return None, http_status, "AMAP_INVALID_RESPONSE"
        if not isinstance(payload, dict):
            return None, http_status, "AMAP_INVALID_RESPONSE"
        if str(payload.get("status")) != "1":
            infocode = str(payload.get("infocode", ""))
            return None, http_status, _INFOCODE_REASON_CODES.get(infocode, "AMAP_PROVIDER_REJECTED")
        return payload, http_status, None
