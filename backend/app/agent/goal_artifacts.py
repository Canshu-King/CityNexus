"""Task-scoped public research and editable suggestions; canonical plans stay separate."""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.db.models import ProviderCall
from app.integrations.discovery.real_city import PhotonCityGeocoder, NominatimGeocoder, OverpassPOIProvider, _resolver_city_label
from app.integrations.provider_config import ExternalProviderSettings, trust_environment_for_public_providers


def public_city_label(journey, session=None) -> str:
    """Resolve a public region from the owner's structured brief or stable city code."""
    if session is not None:
        from app.planning.travel_brief import current_brief
        row = current_brief(session, journey.id, journey.traveler_id)
        if row is not None:
            try:
                brief = json.loads(row.semantic_envelope_json or "{}")
            except (TypeError, ValueError):
                brief = {}
            label = brief.get("public_region_label")
            if isinstance(label, str):
                label = label.strip()
                if 0 < len(label) <= 60 and not any(ord(char) < 32 for char in label):
                    return label
    code = str(journey.city_code).strip()
    if code.upper().startswith("CN-RV-"):
        # Older journeys may have no structured region. Never infer one from title.
        return ""
    try:
        return _resolver_city_label(code)
    except ValueError:
        return ""


def empty_draft(journey) -> dict[str, Any]:
    first = datetime.fromisoformat(journey.start_at).date()
    last = datetime.fromisoformat(journey.end_at).date()
    dates = [(first + timedelta(days=i)).isoformat() for i in range(min(14, max(1, (last-first).days+1)))]
    return {"revision": 0, "status": "DRAFT", "days": [{"date": date, "slots": []} for date in dates]}


def normalize_draft(journey, task: dict, days: Any, *, author: str) -> dict[str, Any]:
    valid_dates = {day["date"] for day in empty_draft(journey)["days"]}
    if not isinstance(days, list) or not 1 <= len(days) <= 14:
        raise HTTPException(422, "DRAFT_DAYS_INVALID")
    known_ids = set(task.get("candidate_place_ids") or []) | {p["id"] for p in task.get("research_places") or []}
    output, seen = [], set()
    for day in days:
        if not isinstance(day, dict) or day.get("date") not in valid_dates or day["date"] in seen:
            raise HTTPException(422, "DRAFT_DATE_OUTSIDE_JOURNEY")
        seen.add(day["date"])
        slots = day.get("slots")
        if not isinstance(slots, list) or len(slots) > 6:
            raise HTTPException(422, "DRAFT_SLOTS_INVALID")
        normalized = []
        for slot in slots:
            if not isinstance(slot, dict):
                raise HTTPException(422, "DRAFT_SLOT_INVALID")
            title = str(slot.get("title") or "").strip()
            period = slot.get("time_of_day", "flexible")
            if not title or len(title) > 160 or period not in {"morning", "afternoon", "evening", "flexible"}:
                raise HTTPException(422, "DRAFT_SLOT_INVALID")
            place_id = slot.get("place_id") or None
            if place_id is not None and place_id not in known_ids:
                raise HTTPException(422, "DRAFT_PLACE_NOT_RESEARCHED")
            normalized.append({"title": title, "time_of_day": period, "place_id": place_id,
                               "notes": str(slot.get("notes") or "")[:500], "author": author,
                               "opening_status": "UNKNOWN", "cost_status": "UNKNOWN", "travel_time_status": "UNKNOWN"})
        output.append({"date": day["date"], "slots": normalized})
    by_date = {day["date"]: day for day in output}
    return {"revision": int((task.get("draft_artifact") or {}).get("revision", 0))+1,
            "status": "DRAFT", "days": [by_date.get(day["date"], day) for day in empty_draft(journey)["days"]]}


def discover_goal_places(session, journey, task: dict, *, query: str, public_action: str = "", source: str = "photon") -> dict[str, Any]:
    """One model-selected query against a named public source; preserve zero-result evidence."""
    query = str(query).strip()
    if not 2 <= len(query) <= 120:
        raise HTTPException(422, "PUBLIC_QUERY_INVALID")
    if not settings.real_city_enabled or settings.real_city_mode != "live":
        return {"tool": "discover_places", "status": "PROVIDER_DISABLED", "reason_code": "REAL_CITY_DISABLED", "places": []}
    source = str(source or "photon").lower().strip()
    if source not in {"photon", "nominatim"}:
        raise HTTPException(422, "PUBLIC_SOURCE_NOT_SUPPORTED")
    query_key = " ".join(query.casefold().split())
    signature = f"{source}:{query_key}"
    prior = task.setdefault("public_queries", [])
    if signature in prior or (source == "photon" and query_key in prior):
        return {"tool": "discover_places", "status": "QUERY_ALREADY_ATTEMPTED", "provider": source, "places": []}
    if task.get(f"{source}_unavailable"):
        return {"tool": "discover_places", "status": "PROVIDER_UNAVAILABLE", "provider": source,
                "reason_code": f"{source.upper()}_UNAVAILABLE", "places": []}
    prior.append(signature)
    config = ExternalProviderSettings()
    started = time.perf_counter()
    observed_status = None
    def observe(response):
        nonlocal observed_status
        observed_status = response.status_code
    result = {"tool": "discover_places", "provider": source, "status": "NO_RESULTS", "places": [],
              "public_action": public_action[:120], "query": query, "provider_provenance": "LIVE_PROVIDER"}
    city_label = public_city_label(journey, session)
    try:
        with httpx.Client(timeout=min(15.0, float(settings.real_city_timeout_seconds)),
                          trust_env=trust_environment_for_public_providers(), follow_redirects=False,
                          event_hooks={"response": [observe]}) as client:
            # Do not pass CityNexus internal location codes to a public search API.
            provider = (PhotonCityGeocoder(client=client, base_url=config.photon_base_url,
                         user_agent=config.photon_user_agent or None) if source == "photon"
                        else NominatimGeocoder(client=client, user_agent=settings.city_search_user_agent or None))
            candidates = provider.search(query, city=city_label, limit=8)
        places, areas = [], []
        for place in candidates:
            if not all(math.isfinite(v) for v in (place.latitude, place.longitude)):
                continue
            if not (-90 <= place.latitude <= 90 and -180 <= place.longitude <= 180):
                continue
            identity = place.external_id.split(":", 1)[-1].split("/")
            osm_type = {"N":"node", "W":"way", "R":"relation"}.get(identity[0], identity[0])
            if len(identity) != 2 or osm_type not in {"node", "way", "relation"} or not identity[1].isdigit():
                continue
            lead = {"id": place.external_id, "name": place.name, "category": place.category,
                           "latitude": place.latitude, "longitude": place.longitude,
                           "source_url": f"https://www.openstreetmap.org/{osm_type}/{identity[1]}",
                           "provider": source, "provider_provenance": "LIVE_PROVIDER",
                           "opening_status": "UNKNOWN", "cost_status": "UNKNOWN"}
            if place.category.casefold() in {"administrative", "city", "town", "village", "county", "boundary"}:
                areas.append(lead)
            else:
                places.append(lead)
        existing = {p["id"]: p for p in task.get("research_places") or []}
        existing.update({p["id"]: p for p in places})
        task["research_places"] = list(existing.values())[:80]
        known_areas = {p["id"]: p for p in task.get("research_areas") or []}
        known_areas.update({p["id"]: p for p in areas})
        task["research_areas"] = list(known_areas.values())[:20]
        result.update(status="RESULTS" if places else "NO_RESULTS", places=places, areas=areas)
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError, IndexError, RuntimeError):
        task[f"{source}_unavailable"] = True
        result.update(status="PROVIDER_UNAVAILABLE", reason_code=f"{source.upper()}_UNAVAILABLE", provider_provenance="UNVERIFIED")
    result["elapsed_ms"] = round((time.perf_counter()-started)*1000)
    result["http_status"] = observed_status
    session.add(ProviderCall(id=str(uuid4()), provider_key=source, operation="goal_place_discovery",
        request_json=json.dumps({"query": query, "city": city_label or None, "public_city_label": city_label, "limit": 8}, ensure_ascii=False),
        response_json=json.dumps({"status": result["status"], "http_status": observed_status,
                                  "count": len(result["places"])}, ensure_ascii=False),
        status="SUCCESS" if result["status"] in {"RESULTS", "NO_RESULTS"} else "FAILURE",
        latency_ms=result["elapsed_ms"], created_at=datetime.now(timezone.utc).isoformat()))
    return result


def discover_nearby_goal_places(session, journey, task: dict, *, center_place_id: str,
                               query: str, radius_m: int = 1500, limit: int = 8,
                               public_action: str = "") -> dict[str, Any]:
    """One Overpass area request anchored to an actual source result owned by this task."""
    centers = [*(task.get("research_places") or []), *(task.get("research_areas") or [])]
    center = next((p for p in centers if p.get("id") == center_place_id
                   and p.get("provider_provenance") == "LIVE_PROVIDER"), None)
    if center is None:
        raise HTTPException(403, "CENTER_NOT_IN_GOAL_TASK_SCOPE")
    if type(radius_m) is not int or not 250 <= radius_m <= 5000 or type(limit) is not int or not 1 <= limit <= 8:
        raise HTTPException(422, "PUBLIC_AREA_BOUNDS_INVALID")
    query = str(query).strip()
    if not 2 <= len(query) <= 120:
        raise HTTPException(422, "PUBLIC_QUERY_INVALID")
    latitude, longitude = center.get("latitude"), center.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)) or not (
        math.isfinite(latitude) and math.isfinite(longitude) and -90 <= latitude <= 90 and -180 <= longitude <= 180
    ):
        raise HTTPException(422, "PUBLIC_AREA_COORDINATES_INVALID")
    result = {"tool": "discover_nearby_places", "provider": "overpass", "places": [],
              "public_action": public_action[:120], "provider_provenance": "UNVERIFIED"}
    if not settings.real_city_enabled or settings.real_city_mode != "live":
        return {**result, "status": "PROVIDER_DISABLED", "reason_code": "REAL_CITY_DISABLED"}
    signature = f"overpass:{center_place_id}:{radius_m}:{' '.join(query.casefold().split())}"
    prior = task.setdefault("public_queries", [])
    if signature in prior:
        return {**result, "status": "QUERY_ALREADY_ATTEMPTED"}
    if task.get("overpass_unavailable"):
        return {**result, "status": "PROVIDER_UNAVAILABLE", "reason_code": "OVERPASS_UNAVAILABLE"}
    prior.append(signature)
    city_label = public_city_label(journey, session)
    started = time.perf_counter()
    attempts = []
    try:
        with httpx.Client(timeout=min(15.0, float(settings.real_city_timeout_seconds)),
                          trust_env=trust_environment_for_public_providers(), follow_redirects=False) as client:
            candidates, attempts = OverpassPOIProvider(client=client).search_with_evidence(
                query, latitude=latitude, longitude=longitude, radius_m=radius_m, limit=limit, max_attempts=1)
        places = []
        for point in candidates[:limit]:
            osm_id = str((point.metadata or {}).get("osm_id") or "")
            parts = osm_id.split("/")
            if len(parts) != 2 or parts[0] not in {"node", "way", "relation"} or not parts[1].isdigit():
                continue
            if not (math.isfinite(point.latitude) and math.isfinite(point.longitude)
                    and -90 <= point.latitude <= 90 and -180 <= point.longitude <= 180):
                continue
            places.append({"id": point.external_id, "name": point.name, "category": point.category,
                           "latitude": point.latitude, "longitude": point.longitude,
                           "source_url": f"https://www.openstreetmap.org/{osm_id}", "provider": "overpass",
                           "provider_provenance": "LIVE_PROVIDER", "opening_status": "UNKNOWN", "cost_status": "UNKNOWN"})
        existing = {p["id"]: p for p in task.get("research_places") or []}
        existing.update({p["id"]: p for p in places})
        task["research_places"] = list(existing.values())[:80]
        result.update(status="RESULTS" if places else "NO_RESULTS", places=places, provider_provenance="LIVE_PROVIDER")
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError, RuntimeError) as error:
        attempts = getattr(error, "provider_attempts", [])
        task["overpass_unavailable"] = True
        result.update(status="PROVIDER_UNAVAILABLE", reason_code="OVERPASS_UNAVAILABLE")
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    result["http_status"] = attempts[-1].get("http_status") if attempts else None
    request = {"query": query, "public_city_label": city_label, "center_place_id": center_place_id,
               "center_source_url": center["source_url"], "latitude": latitude, "longitude": longitude,
               "radius_m": radius_m, "limit": limit, "max_attempts": 1}
    session.add(ProviderCall(id=str(uuid4()), provider_key="overpass", operation="goal_area_discovery",
        request_json=json.dumps(request, ensure_ascii=False),
        response_json=json.dumps({"status": result["status"], "http_status": result["http_status"],
                                 "places": result["places"], "attempt_count": len(attempts)}, ensure_ascii=False),
        status="SUCCESS" if result["status"] in {"RESULTS", "NO_RESULTS"} else "FAILURE",
        latency_ms=result["elapsed_ms"], created_at=datetime.now(timezone.utc).isoformat()))
    return result


def goal_tool_definitions() -> tuple[dict, ...]:
    slot = {"type":"object", "properties": {
        "title":{"type":"string", "maxLength":160},
        "time_of_day":{"type":"string", "enum":["morning","afternoon","evening","flexible"]},
        "place_id":{"type":"string", "description":"ID returned by a research tool; omit for a general suggestion or todo."},
        "notes":{"type":"string", "maxLength":500}}, "required":["title","time_of_day"], "additionalProperties":False}
    return (
        {"type": "function", "function": {"name": "discover_nearby_places", "description":
            "Find actual OSM POIs near a place or public region center already returned by this task's research. "
            "Unlike a name geocoder, Overpass searches a bounded area by category keyword (museum, park, restaurant, library, hotel, theatre, nightlife, attraction). "
            "Use a server-returned center ID, never invented coordinates. One request, no mirror retry; missing opening and cost remain unknown.",
            "parameters": {"type": "object", "properties": {
                "center_place_id": {"type": "string"}, "query": {"type": "string", "minLength": 2, "maxLength": 120},
                "radius_m": {"type": "integer", "minimum": 250, "maximum": 5000},
                "limit": {"type": "integer", "minimum": 1, "maximum": 8},
                "public_action": {"type": "string", "maxLength": 120}},
                "required": ["center_place_id", "query"], "additionalProperties": False}}},
        {"type":"function", "function":{"name":"discover_places", "description":
            "Choose one real public geocoder, photon or nominatim, to search named public places. "
            "After a zero-result query you may change provider or keyword within approved tool budget. "
            "Never send private traveler details; either source may have incomplete OSM coverage. "
            "An empty result is not proof that the area has no attractions.",
            "parameters":{"type":"object", "properties":{"query":{"type":"string","minLength":2,"maxLength":120},
                "public_action":{"type":"string","maxLength":120,"description":"Short user-facing operation summary, without private reasoning."},
                "source":{"type":"string","enum":["photon","nominatim"],"description":"Public geocoder for this one authorized search; defaults to photon."}},
                "required":["query"],"additionalProperties":False}}},
        {"type":"function", "function":{"name":"save_draft_itinerary", "description":
            "Save an editable tentative multi-day itinerary or useful named research todos. Use only researched IDs for named places. "
            "Generic suggestions need no place ID. Opening, price and transfer facts remain unknown. This never creates or activates a formal plan.",
            "parameters":{"type":"object", "properties":{"days":{"type":"array", "maxItems":14, "items":{
                "type":"object", "properties":{"date":{"type":"string"},"slots":{"type":"array","maxItems":6,"items":slot}},
                "required":["date","slots"],"additionalProperties":False}}}, "required":["days"],"additionalProperties":False}}},
    )
