"""Amap research inside an owner-bound GoalTask, with provider-native coordinates."""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import HTTPException

from app.core.config import settings
from app.db.models import ProviderCall
from app.agent.goal_place_identity import attach_canonical_places
from app.integrations.china.amap_provider import AmapClient
from app.integrations.china.amap import wgs84_to_gcj02
from app.integrations.discovery.real_city import normalize_opening_hours


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _client() -> AmapClient:
    return AmapClient(api_key=settings.amap_web_key)


def _receipt(session, operation: str, arguments: dict, result: dict) -> dict:
    result = dict(result)
    if result.get("status") == "ok":
        result["status"] = "ROUTE_READY" if isinstance(result.get("route"), dict) else ("RESULTS" if result.get("places") or result.get("districts") else "NO_RESULTS")
    elif result.get("status") == "error":
        result["status"] = "PROVIDER_UNAVAILABLE"
    receipt_id = str(uuid4())
    safe_response = {key: result[key] for key in (
        "status", "reason_code", "http_status", "places", "districts", "route", "elapsed_ms"
    ) if key in result}
    session.add(ProviderCall(
        id=receipt_id, provider_key="amap-web-service", operation=operation,
        request_json=json.dumps(arguments, ensure_ascii=False),
        response_json=json.dumps(safe_response, ensure_ascii=False),
        status="SUCCESS" if result.get("status") in {"RESULTS", "NO_RESULTS", "ROUTE_READY", "SUCCESS"} else "FAILURE",
        latency_ms=result.get("elapsed_ms"), created_at=_now(),
    ))
    return {**result, "provider_call_id": receipt_id}


def _region(session, journey, task: dict, client: AmapClient) -> dict:
    from app.agent.goal_artifacts import public_city_label
    label = public_city_label(journey, session).strip()
    saved = task.get("amap_region")
    if isinstance(saved, dict) and saved.get("query") == label:
        return saved
    if not label:
        return {"status": "NEEDS_DECISION", "reason_code": "AMAP_DESTINATION_REQUIRED"}
    signature = "amap:district:" + label
    queries = task.setdefault("public_queries", [])
    if signature in queries:
        return {"status": "PROVIDER_UNAVAILABLE", "reason_code": "AMAP_REGION_UNRESOLVED"}
    queries.append(signature)
    result = _receipt(session, "goal_amap_district", {"region": label}, client.district(label))
    normalize = lambda name: re.sub(r"(自治县|自治州|地区|省|市|县|区)$", "", str(name).strip())
    candidates = [item for item in result.get("districts", []) if isinstance(item, dict)
                  and re.fullmatch(r"[0-9]{6}", str(item.get("adcode", "")))
                  and (normalize(item.get("name")) == normalize(label) or str(item.get("name", "")) in label)]
    if len(candidates) != 1:
        return {"status": "NEEDS_DECISION", "reason_code": result.get("reason_code") or "AMAP_REGION_AMBIGUOUS"}
    task["amap_region"] = {**candidates[0], "query": label, "status": "RESOLVED"}
    return task["amap_region"]


CLOSURE_MARKS = ("关闭", "不开放", "休息", "暂停营业")


def _amap_opening_envelope(value: object, source_url: str) -> dict:
    """Turn AMap's own opening sentence into the fact envelope the departure door reads.

    The parsing is the one the product already has (``normalize_opening_hours``): it refuses to read
    unknown text as all-day opening and answers ``RAW_UNPARSED`` for a sentence with no clock in it, so
    nothing here can invent an opening time.  Two things are added, both about honesty rather than
    coverage.  The status names the provider as the source -- this is AMap's aggregate, not the venue's
    own page.  And the day mapping is marked unresolved with the provider's closure sentences kept
    beside it, because AMap writes 「周二至周日 08:30-17:00 … 周一全天关闭」 in prose whose intervals the
    shared parser flattens to "every day", and a traveller must not be told 故宫 opens on a Monday.
    """
    text = str(value or "").strip()[:400]
    if not text:
        return {"status": "UNKNOWN", "raw": None, "intervals": []}
    normalized = normalize_opening_hours(text)
    if normalized.get("status") not in {"NORMALIZED_VALID", "CLOSED"}:
        return {"status": "RAW_UNPARSED", "raw": text, "intervals": []}
    envelope = dict(normalized)
    envelope.update({
        "status": "VERIFIED_PROVIDER",
        "source": "amap_business_opentime",
        "source_url": source_url or None,
        "raw": text,
        "weekday_coverage": "UNRESOLVED",
        "closure_notes": [part.strip()[:160] for part in re.split(r"[；;，,]", text)
                          if any(mark in part for mark in CLOSURE_MARKS)][:4],
    })
    return envelope


def _store_places(task: dict, result: dict, region: dict) -> list[dict]:
    places = []
    for item in result.get("places", []):
        if not isinstance(item, dict):
            continue
        external_id = str(item.get("provider_object_id") or item.get("external_id") or item.get("poi_id") or item.get("id") or "")
        if external_id.startswith("amap:"):
            external_id = external_id[5:]
        latitude, longitude = item.get("latitude"), item.get("longitude")
        if not re.fullmatch(r"[A-Za-z0-9_-]{4,80}", external_id) or type(latitude) not in {int, float} or type(longitude) not in {int, float}:
            continue
        if not math.isfinite(latitude) or not math.isfinite(longitude) or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            continue
        adcode = str(item.get("adcode") or "")
        expected = str(region["adcode"])
        width = 2 if expected.endswith("0000") else 4 if expected.endswith("00") else 6
        status = "MATCHED" if adcode and adcode[:width] == expected[:width] else "CONFLICT" if adcode else "UNKNOWN"
        name = str(item.get("name") or "")[:160]
        address = item.get("public_address")
        if not isinstance(address, dict):
            address = {key: item[key] for key in ("province", "city", "district", "address") if isinstance(item.get(key), str)}
        places.append({
            "id": "amap:" + external_id, "name": name, "category": str(item.get("category") or "attraction")[:80],
            "provider": "amap", "provider_object_id": external_id, "provider_provenance": "LIVE_PROVIDER",
            "latitude": latitude, "longitude": longitude, "coordinate_system": "GCJ02", "adcode": adcode,
            "public_address": address, "region_status": status, "location_kind": "POI",
            "source_url": "https://uri.amap.com/marker?" + urlencode({"position": f"{longitude},{latitude}", "name": name, "coordinate": "gaode", "callnative": "0"}),
            "captured_at": item.get("captured_at") or _now(),
            "opening_status": "UNKNOWN", "cost_status": "UNKNOWN",
        })
        # AMap's own opening sentence, carried through the shared parser -- the helper's note says what
        # this does and does not claim.  A place whose sentence cannot be read stays UNKNOWN, so the
        # departure door keeps naming that gap instead of being handed an invented all-day opening.
        places[-1]["opening_hours"] = _amap_opening_envelope(
            item.get("opening_hours_text"), str(places[-1].get("source_url") or ""))
        places[-1]["opening_status"] = str(places[-1]["opening_hours"].get("status") or "UNKNOWN")
    existing = {item["id"]: item for item in task.get("research_places", [])}
    existing.update({item["id"]: item for item in places})
    task["research_places"] = list(existing.values())[-80:]
    return places


def discover_amap_goal_places(session, journey, task: dict, *, query: str, public_action: str = "", center: dict | None = None,
                              radius_m: int = 1500, limit: int = 8) -> dict:
    tool = "discover_nearby_places" if center else "discover_places"
    base = {"tool": tool, "provider": "amap", "provider_provenance": "UNVERIFIED", "places": [], "areas": [], "public_action": public_action[:120]}
    if not settings.amap_web_key:
        return {**base, "status": "PROVIDER_DISABLED", "reason_code": "AMAP_NOT_CONFIGURED"}
    client = _client()
    try:
        region = _region(session, journey, task, client)
        if region.get("status") != "RESOLVED":
            return {**base, **region}
        signature = f"amap:{region['adcode']}:{center['id'] if center else ''}:{radius_m if center else ''}:{' '.join(query.casefold().split())}"
        prior = task.setdefault("public_queries", [])
        if signature in prior:
            return {**base, "status": "QUERY_ALREADY_ATTEMPTED", "reason_code": "AMAP_QUERY_ALREADY_ATTEMPTED"}
        prior.append(signature)
        if center:
            raw = client.around(center["latitude"], center["longitude"], query, radius_m=radius_m, limit=limit, adcode=region["adcode"])
            operation = "goal_amap_nearby"
        else:
            raw = client.search(query, city=region["name"], adcode=region["adcode"], limit=limit)
            operation = "goal_amap_search"
        result = _receipt(session, operation, {"query": query, "adcode": region["adcode"], "center_place_id": center.get("id") if center else None, "limit": limit}, raw)
        places = _store_places(task, result, region)
        attach_canonical_places(session, journey, task, places)
        return {**base, **result, "places": places, "provider_provenance": "LIVE_PROVIDER" if result.get("status") in {"RESULTS", "NO_RESULTS", "SUCCESS"} else "UNVERIFIED"}
    finally:
        client.close()


def route_public_places(session, journey, task: dict, *, from_place_id: str, to_place_id: str, public_action: str = "") -> dict:
    from app.agent.goal_artifacts import goal_research_lead
    from app.agent.goal_mobility import route_geometry_wgs84
    origin, destination = goal_research_lead(task, from_place_id), goal_research_lead(task, to_place_id)
    if not origin or not destination or from_place_id == to_place_id:
        raise HTTPException(403, "ROUTE_POINTS_NOT_IN_GOAL_TASK_SCOPE")
    if any(point.get("region_status") == "CONFLICT" for point in (origin, destination)):
        raise HTTPException(422, "ROUTE_POINT_REGION_CONFLICT")
    saved = next((row for row in task.get("research_routes", []) if row.get("from_place_id") == from_place_id and row.get("to_place_id") == to_place_id), None)
    if saved:
        return {"tool": "route_public_places", "status": "ROUTE_READY", "provider": "amap", "provider_provenance": "LIVE_PROVIDER", "route": saved, "cached": True}
    if not settings.amap_web_key:
        return {"tool": "route_public_places", "status": "PROVIDER_DISABLED", "reason_code": "AMAP_NOT_CONFIGURED"}
    def native(point):
        lat, lon = point.get("latitude"), point.get("longitude")
        if type(lat) not in {int, float} or type(lon) not in {int, float} or not math.isfinite(lat) or not math.isfinite(lon):
            raise HTTPException(422, "ROUTE_COORDINATES_INVALID")
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise HTTPException(422, "ROUTE_COORDINATES_INVALID")
        return (lat, lon) if point.get("coordinate_system") == "GCJ02" else wgs84_to_gcj02(lat, lon)
    start, end = native(origin), native(destination)
    signature = f"amap:walk:{from_place_id}:{to_place_id}"
    if signature in task.setdefault("public_queries", []):
        return {"tool": "route_public_places", "status": "QUERY_ALREADY_ATTEMPTED", "reason_code": "AMAP_ROUTE_ALREADY_ATTEMPTED"}
    task["public_queries"].append(signature)
    with _client() as client:
        result = _receipt(session, "goal_amap_walking", {"from_place_id": from_place_id, "to_place_id": to_place_id, "coordinate_system": "GCJ02"}, client.walking(start, end))
    route = result.get("route")
    if isinstance(route, dict) and result.get("status") in {"ROUTE_READY", "RESULTS", "SUCCESS"}:
        provider_route = route
        provider_call_id = str(result["provider_call_id"])
        captured_at = _now()
        geometry_source = {
            **provider_route,
            "id": provider_call_id,
            "provider_call_id": provider_call_id,
            "from_place_id": from_place_id,
            "to_place_id": to_place_id,
            "captured_at": captured_at,
        }
        route_geometry = route_geometry_wgs84(geometry_source, provider_call_id=provider_call_id)
        provider_geometry_status = str(provider_route.get("geometry_status") or "")
        if route_geometry is not None:
            geometry_status = provider_geometry_status or "AVAILABLE"
        elif provider_geometry_status and provider_geometry_status != "AVAILABLE":
            geometry_status = provider_geometry_status
        elif isinstance(provider_route.get("path"), dict) or isinstance(provider_route.get("route_geometry"), dict):
            geometry_status = "BLOCKED_GEOMETRY_CONVERSION_FAILED"
        else:
            geometry_status = "BLOCKED_GEOMETRY_UNAVAILABLE"
        raw_provenance = provider_route.get("geometry_provenance")
        geometry_provenance = dict(raw_provenance) if isinstance(raw_provenance, dict) else {}
        if route_geometry is not None:
            geometry_provenance.update(route_geometry["properties"])
        else:
            path = provider_route.get("path")
            source_crs = path.get("coordinate_system") if isinstance(path, dict) else provider_route.get("coordinate_system")
            geometry_provenance.update(
                {
                    "source_provider": provider_route.get("provider_key") or "amap-web-service",
                    "provider_call_id": provider_call_id,
                    "source_coordinate_system": source_crs or "UNKNOWN",
                    "domain_crs": "WGS84",
                    "conversion": "FAILED" if geometry_status == "BLOCKED_GEOMETRY_CONVERSION_FAILED" else None,
                    "geometry_status": geometry_status,
                }
            )
        stored_route = {
            "id": provider_call_id,
            "from_place_id": from_place_id,
            "to_place_id": to_place_id,
            "from_name": origin["name"],
            "to_name": destination["name"],
            "provider": "amap",
            "coordinate_system": "GCJ02",
            "distance_m": provider_route.get("distance_m"),
            "duration_seconds": provider_route.get("duration_seconds"),
            "captured_at": captured_at,
            "path": provider_route.get("path"),
            "geometry_segments": list(provider_route["geometry_segments"])
            if isinstance(provider_route.get("geometry_segments"), list)
            else [],
            "geometry_status": geometry_status,
            "route_geometry": route_geometry,
            "geometry_provenance": geometry_provenance,
            "source_url": "https://uri.amap.com/navigation?" + urlencode({"from": f"{start[1]},{start[0]},{origin['name']}", "to": f"{end[1]},{end[0]},{destination['name']}", "mode": "walk", "coordinate": "gaode", "callnative": "0"}),
        }
        task.setdefault("research_routes", []).append(stored_route)
        task["research_routes"] = task["research_routes"][-16:]
        return {**result, "tool": "route_public_places", "status": "ROUTE_READY", "provider": "amap", "provider_provenance": "LIVE_PROVIDER", "route": stored_route}
    return {**result, "tool": "route_public_places", "provider": "amap", "public_action": public_action[:120]}


def route_definition() -> dict:
    return {"type": "function", "function": {"name": "route_public_places",
        "description": "Fetch one real Amap walking route between two source-backed IDs already in this task. Uses server-owned coordinates. Preserve distance/time as provider estimates, not an arrival claim. Reuses a stored route on repetition.",
        "parameters": {"type": "object", "properties": {"from_place_id": {"type": "string"}, "to_place_id": {"type": "string"}, "public_action": {"type": "string", "maxLength": 120}}, "required": ["from_place_id", "to_place_id"], "additionalProperties": False}}}
