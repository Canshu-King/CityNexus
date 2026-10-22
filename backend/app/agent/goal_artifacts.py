"""Task-scoped public research and editable suggestions; canonical plans stay separate."""
from __future__ import annotations

import json
import math
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.db.models import ProviderCall
from app.agent.goal_place_identity import attach_canonical_places
from app.integrations.discovery.real_city import PhotonCityGeocoder, NominatimGeocoder, OverpassPOIProvider, _resolver_city_label
from app.integrations.provider_config import ExternalProviderSettings, trust_environment_for_public_providers
from app.region_matching import public_address as _public_address, public_address_from_tags as _public_address_from_tags
from app.region_matching import public_region_status as _public_region_status

_LIVE_GOAL_RESEARCH_PROVIDERS = frozenset({"photon", "nominatim", "overpass", "amap"})
_OSM_REFERENCE_TYPES = {"N": "node", "W": "way", "R": "relation",
                        "node": "node", "way": "way", "relation": "relation"}
_REGION_STATUSES = frozenset({"MATCHED", "CONFLICT", "UNKNOWN"})


def _structured_public_region_label(session, journey) -> str:
    if session is None:
        return ""
    from app.planning.travel_brief import current_brief
    row = current_brief(session, journey.id, journey.traveler_id)
    if row is None:
        return ""
    try:
        brief = json.loads(row.semantic_envelope_json or "{}")
    except (TypeError, ValueError):
        return ""
    if not isinstance(brief, dict):
        return ""
    label = brief.get("public_region_label")
    if isinstance(label, str):
        label = label.strip()
        if 0 < len(label) <= 60 and not any(ord(char) < 32 for char in label):
            return label
    return ""


def _source_label(value: Any, *, limit: int = 80) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > limit or any(ord(char) < 32 for char in normalized):
        return None
    return normalized


def _public_location_kind(osm_key: str | None, osm_value: str | None,
                          location_type: str | None) -> tuple[str, str]:
    key = (osm_key or "").casefold()
    value = (osm_value or "").casefold()
    locator = (location_type or "").casefold()
    if key in {"place", "boundary"} or value in {
        "administrative", "city", "town", "village", "county", "boundary",
        "district", "hamlet", "suburb", "locality", "neighbourhood", "state", "province", "postcode",
    }:
        return "AREA", "REGION"
    if locator == "street" and key == "highway":
        return "AREA", "STREET"
    if locator in {"district", "street", "house"} and value in {"", "unknown"}:
        return "AREA", {"district": "REGION", "street": "STREET", "house": "ADDRESS"}[locator]
    return "POI", "POI"


def public_city_label(journey, session=None) -> str:
    """Resolve a public region from the owner's structured brief or stable city code."""
    structured_label = _structured_public_region_label(session, journey)
    if structured_label:
        return structured_label
    code = str(journey.city_code).strip()
    if code.upper().startswith("CN-RV-"):
        # Older journeys may have no structured region. Never infer one from title.
        return ""
    try:
        return _resolver_city_label(code)
    except ValueError:
        return ""


def goal_research_lead(task: dict[str, Any], place_id: str) -> dict[str, Any] | None:
    """Find a live public lead already owned by this signed goal task."""
    for collection in ("research_places", "research_areas"):
        places = task.get(collection)
        if not isinstance(places, list):
            continue
        for place in places:
            if (isinstance(place, dict) and place.get("id") == place_id
                    and place.get("provider_provenance") == "LIVE_PROVIDER"
                    and place.get("provider") in _LIVE_GOAL_RESEARCH_PROVIDERS):
                return place
    return None


def _validated_osm_reference(place_id: str, provider: str, stored_url: Any) -> str | None:
    prefix, separator, object_ref = place_id.partition(":")
    if not separator or prefix != provider or provider not in _LIVE_GOAL_RESEARCH_PROVIDERS:
        return None
    match = re.fullmatch(r"([^/]+)/([1-9][0-9]*)", object_ref)
    if match is None:
        return None
    osm_type = _OSM_REFERENCE_TYPES.get(match.group(1))
    if osm_type is None:
        return None
    expected_url = f"https://www.openstreetmap.org/{osm_type}/{match.group(2)}"
    return expected_url if stored_url == expected_url else None


def cached_goal_place_sources(task: dict[str, Any], place_id: str) -> dict[str, Any]:
    """Return task-local OSM references and known fields without creating observations or networking."""
    lead = goal_research_lead(task, place_id)
    if lead is None:
        raise HTTPException(403, "PLACE_NOT_IN_GOAL_TASK_SCOPE")

    provider = str(lead.get("provider") or "")
    if provider == "amap":
        return {"tool": "research_place_sources", "status": "CACHED_ONLY", "place_id": place_id,
                "authority": "NON_AUTHORITATIVE", "region_status": lead.get("region_status", "UNKNOWN"),
                "public_address": lead.get("public_address") or {}, "reference_status": "PRESENT",
                "cached_references": [{"reference_type": "AMAP_POI", "provider": "amap", "url": lead.get("source_url"), "authority_status": "NON_AUTHORITATIVE"}],
                "cached_facts": {key: lead[key] for key in ("name", "category", "provider", "provider_object_id", "adcode", "coordinate_system", "latitude", "longitude", "opening_status", "cost_status") if key in lead},
                "not_acquired_fields": ["opening_hours", "cost", "availability"], "source_discovery_attempted": False, "acquisition_attempted": False}
    source_url = _validated_osm_reference(place_id, provider, lead.get("source_url"))
    references = ([{"reference_type": "OSM_OBJECT", "provider": provider, "url": source_url,
                    "authority_status": "NON_AUTHORITATIVE"}] if source_url else [])
    known_facts: dict[str, Any] = {"place_id": place_id, "provider": provider,
                                   "provider_provenance": "LIVE_PROVIDER"}
    for key in ("name", "category"):
        value = lead.get(key)
        if isinstance(value, str) and value.strip():
            known_facts[key] = value.strip()[:160]
    latitude, longitude = lead.get("latitude"), lead.get("longitude")
    if (type(latitude) in {int, float} and type(longitude) in {int, float}
            and math.isfinite(latitude) and math.isfinite(longitude)
            and -90 <= latitude <= 90 and -180 <= longitude <= 180):
        known_facts["latitude"] = latitude
        known_facts["longitude"] = longitude
    for key in ("opening_status", "cost_status"):
        value = lead.get(key)
        known_facts[key] = value.strip()[:40] if isinstance(value, str) and value.strip() else "UNKNOWN"
    for key in ("location_type", "osm_key", "osm_value"):
        value = _source_label(lead.get(key), limit=80 if key != "location_type" else 40)
        if value:
            known_facts[key] = value
    public_address = _public_address(lead.get("public_address"))
    region_status = lead.get("region_status")
    if region_status not in _REGION_STATUSES:
        region_status = "UNKNOWN"

    not_acquired_fields = []
    for field, stored_key, status_key in (
        ("opening_hours", "opening_hours", "opening_status"),
        ("cost", "cost_evidence", "cost_status"),
        ("availability", "availability", None),
        ("travel_time", "travel_time", None),
    ):
        value = lead.get(stored_key)
        missing = value is None or value == "" or value == {} or value == []
        if status_key and str(lead.get(status_key) or "UNKNOWN").upper() == "UNKNOWN":
            missing = True
        if missing:
            not_acquired_fields.append(field)
    return {
        "tool": "research_place_sources",
        "status": "CACHED_ONLY",
        "place_id": place_id,
        "authority": "NON_AUTHORITATIVE",
        "cached_references": references,
        "reference_status": "PRESENT" if references else "NOT_VERIFIED",
        "cached_facts": known_facts,
        "region_status": region_status,
        "public_address": public_address,
        "not_acquired_fields": not_acquired_fields,
        "source_discovery_attempted": False,
        "acquisition_attempted": False,
    }


def empty_draft(journey) -> dict[str, Any]:
    first = datetime.fromisoformat(journey.start_at).date()
    last = datetime.fromisoformat(journey.end_at).date()
    dates = [(first + timedelta(days=i)).isoformat() for i in range(min(14, max(1, (last-first).days+1)))]
    return {"revision": 0, "status": "DRAFT", "days": [{"date": date, "slots": []} for date in dates]}


def normalize_draft(journey, task: dict, days: Any, *, author: str) -> dict[str, Any]:
    valid_dates = {day["date"] for day in empty_draft(journey)["days"]}
    if not isinstance(days, list) or not 1 <= len(days) <= 14:
        raise HTTPException(422, "DRAFT_DAYS_INVALID")
    research_leads = [*(task.get("research_places") or []), *(task.get("research_areas") or [])]
    known_ids = set(task.get("candidate_place_ids") or []) | {p["id"] for p in research_leads}
    conflicting_ids = {p["id"] for p in research_leads if p.get("region_status") == "CONFLICT"}
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
            if place_id in conflicting_ids:
                raise HTTPException(422, "DRAFT_PLACE_REGION_CONFLICT")
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
    if source == "amap":
        from app.agent.goal_amap import discover_amap_goal_places
        return discover_amap_goal_places(session, journey, task, query=query, public_action=public_action)
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
    result = {"tool": "discover_places", "provider": source, "status": "NO_RESULTS", "places": [], "areas": [],
              "public_action": public_action[:120], "query": query, "provider_provenance": "LIVE_PROVIDER"}
    city_label = public_city_label(journey, session)
    region_label = _structured_public_region_label(session, journey)
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
            metadata = getattr(place, "metadata", {})
            metadata = metadata if isinstance(metadata, dict) else {}
            osm_key = _source_label(metadata.get("osm_key"))
            osm_value = _source_label(metadata.get("osm_value"))
            location_type = _source_label(getattr(place, "location_type", None), limit=40)
            address = _public_address(metadata)
            collection, location_kind = _public_location_kind(osm_key, osm_value or place.category, location_type)
            lead = {"id": place.external_id, "name": place.name, "category": place.category,
                    "latitude": place.latitude, "longitude": place.longitude,
                    "source_url": f"https://www.openstreetmap.org/{osm_type}/{identity[1]}",
                    "provider": source, "provider_provenance": "LIVE_PROVIDER",
                    "location_type": location_type, "location_kind": location_kind,
                    "osm_key": osm_key, "osm_value": osm_value, "public_address": address,
                    "region_status": _public_region_status(region_label, address),
                    "opening_status": "UNKNOWN", "cost_status": "UNKNOWN"}
            if collection == "AREA":
                areas.append(lead)
            else:
                places.append(lead)
        existing = {p["id"]: p for p in task.get("research_places") or []}
        existing.update({p["id"]: p for p in places})
        task["research_places"] = list(existing.values())[:80]
        known_areas = {p["id"]: p for p in task.get("research_areas") or []}
        known_areas.update({p["id"]: p for p in areas})
        task["research_areas"] = list(known_areas.values())[:20]
        attach_canonical_places(session, journey, task, places)
        result.update(status="RESULTS" if places or areas else "NO_RESULTS", places=places, areas=areas)
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError, IndexError, RuntimeError):
        task[f"{source}_unavailable"] = True
        result.update(status="PROVIDER_UNAVAILABLE", reason_code=f"{source.upper()}_UNAVAILABLE", provider_provenance="UNVERIFIED")
    result["elapsed_ms"] = round((time.perf_counter()-started)*1000)
    result["http_status"] = observed_status
    session.add(ProviderCall(id=str(uuid4()), provider_key=source, operation="goal_place_discovery",
        request_json=json.dumps({"query": query, "city": city_label or None, "public_city_label": city_label, "limit": 8}, ensure_ascii=False),
        response_json=json.dumps({"status": result["status"], "http_status": observed_status,
                                  "count": len(result["places"]), "area_count": len(result["areas"])}, ensure_ascii=False),
        status="SUCCESS" if result["status"] in {"RESULTS", "NO_RESULTS"} else "FAILURE",
        latency_ms=result["elapsed_ms"], created_at=datetime.now(timezone.utc).isoformat()))
    return result


def discover_nearby_goal_places(session, journey, task: dict, *, center_place_id: str,
                               query: str, radius_m: int = 1500, limit: int = 8,
                               public_action: str = "") -> dict[str, Any]:
    """One Overpass area request anchored to an actual source result owned by this task."""
    centers = [*(task.get("research_places") or []), *(task.get("research_areas") or [])]
    center = next((p for p in centers if isinstance(p, dict) and p.get("id") == center_place_id
                   and p.get("provider_provenance") == "LIVE_PROVIDER"
                   and str(p.get("region_status") or "UNKNOWN").upper() != "CONFLICT"), None)
    if center is None:
        raise HTTPException(403, "CENTER_NOT_IN_GOAL_TASK_SCOPE")
    if type(radius_m) is not int or not 250 <= radius_m <= 5000 or type(limit) is not int or not 1 <= limit <= 8:
        raise HTTPException(422, "PUBLIC_AREA_BOUNDS_INVALID")
    query = str(query).strip()
    if not 2 <= len(query) <= 120:
        raise HTTPException(422, "PUBLIC_QUERY_INVALID")
    if center.get("provider") == "amap":
        from app.agent.goal_amap import discover_amap_goal_places
        return discover_amap_goal_places(session, journey, task, query=query, public_action=public_action,
                                         center=center, radius_m=radius_m, limit=limit)
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
    region_label = _structured_public_region_label(session, journey)
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
            metadata = point.metadata if isinstance(point.metadata, dict) else {}
            address = _public_address_from_tags(metadata.get("tags"))
            places.append({"id": point.external_id, "name": point.name, "category": point.category,
                           "latitude": point.latitude, "longitude": point.longitude,
                           "source_url": f"https://www.openstreetmap.org/{osm_id}", "provider": "overpass",
                           "provider_provenance": "LIVE_PROVIDER", "location_type": None,
                           "location_kind": "POI", "osm_key": None, "osm_value": None,
                           "public_address": address, "region_status": _public_region_status(region_label, address),
                           "opening_status": "UNKNOWN", "cost_status": "UNKNOWN"})
        existing = {p["id"]: p for p in task.get("research_places") or []}
        existing.update({p["id"]: p for p in places})
        task["research_places"] = list(existing.values())[:80]
        attach_canonical_places(session, journey, task, places)
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
            "Choose a configured real public source: amap for domestic Chinese POIs, photon or nominatim for OSM geographic leads. "
            "After a zero-result query you may change provider or keyword within approved tool budget. "
            "Never send private traveler details; either source may have incomplete OSM coverage. "
            "An empty result is not proof that the area has no attractions.",
            "parameters":{"type":"object", "properties":{"query":{"type":"string","minLength":2,"maxLength":120},
                "public_action":{"type":"string","maxLength":120,"description":"Short user-facing operation summary, without private reasoning."},
                "source":{"type":"string","enum":["photon","nominatim","amap"],"description":"Prefer amap for Chinese places when amap_configured is true. Otherwise use OSM sources."}},
                "required":["query"],"additionalProperties":False}}},
        {"type":"function", "function":{"name":"save_draft_itinerary", "description":
            "Save an editable tentative multi-day itinerary or useful named research todos. Use only researched IDs for named places. "
            "Generic suggestions need no place ID. Opening, price and transfer facts remain unknown. This never creates or activates a formal plan.",
            "parameters":{"type":"object", "properties":{"days":{"type":"array", "maxItems":14, "items":{
                "type":"object", "properties":{"date":{"type":"string"},"slots":{"type":"array","maxItems":6,"items":slot}},
                "required":["date","slots"],"additionalProperties":False}}}, "required":["days"],"additionalProperties":False}}},
    )
