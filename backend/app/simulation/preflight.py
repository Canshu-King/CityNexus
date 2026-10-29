"""Inspect acquired public facts without making provider requests."""

import hashlib
import json
import math
import random
import re
from collections.abc import Mapping
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import (
    Journey,
    JourneyMember,
    Place,
    PlanVersion,
    ProviderCall,
    RealPlaceCandidate,
)
from app.traveler_principal import _member_is_in_force, member_has_capability
from app.replanning.provider_snapshots import LIVE_PROVIDER_CAPTURE, MobilitySnapshot


_MUNICIPAL_ADCODES = {"110000", "120000", "310000", "500000"}


def _valid_wgs84_points(value):
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return False
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return False
        longitude, latitude = point
        if type(longitude) not in (int, float) or type(latitude) not in (int, float):
            return False
        if not math.isfinite(longitude) or not math.isfinite(latitude):
            return False
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            return False
    return True


def _normalized_crs(value):
    return str(value or "").strip().upper().replace("-", "").replace("_", "")


def _valid_snapshot_geometry_fact(item):
    if not isinstance(item, Mapping):
        return False
    provider = str(item.get("provider") or "").strip()
    geometry_provider = str(item.get("geometry_provider") or "").strip()
    if (
        item.get("fact_quality") != LIVE_PROVIDER_CAPTURE
        or bool(item.get("degraded"))
        or not provider
        or provider.lower() in {"unknown", "none", "null"}
        or geometry_provider != provider
        or not _valid_wgs84_points(item.get("route_geometry"))
    ):
        return False
    route_provenance = item.get("route_provenance")
    if route_provenance not in (None, LIVE_PROVIDER_CAPTURE):
        return False
    for field in ("geometry_crs", "domain_crs", "coordinate_system"):
        if item.get(field) is not None and _normalized_crs(item.get(field)) != "WGS84":
            return False
    if item.get("source_crs") is not None and _normalized_crs(item.get("source_crs")) not in {
        "WGS84",
        "GCJ02",
    }:
        return False
    return True


def _valid_city_identity(session, identity):
    if (
        identity is None
        or identity.provider != "amap"
        or not re.fullmatch(r"[0-9]{6}", str(identity.provider_adcode or ""))
        or not str(identity.public_name or "").strip()
        or not re.fullmatch(r"[0-9a-fA-F]{64}", str(identity.source_sha256 or ""))
    ):
        return False
    try:
        bound_at = datetime.fromisoformat(identity.bound_at)
    except (TypeError, ValueError):
        return False
    if bound_at.tzinfo is None or bound_at > datetime.now(timezone.utc):
        return False
    source = session.get(ProviderCall, identity.source_call_id)
    if (
        source is None
        or source.provider_key != "amap-web-service"
        or source.operation != "goal_amap_district"
        or source.status != "SUCCESS"
        or hashlib.sha256(str(source.response_json or "").encode()).hexdigest().lower()
        != identity.source_sha256.lower()
    ):
        return False
    try:
        request = json.loads(source.request_json or "{}")
        response = json.loads(source.response_json or "{}")
    except (TypeError, ValueError):
        return False
    if not isinstance(request, Mapping) or not str(request.get("region") or "").strip():
        return False
    districts = response.get("districts", []) if isinstance(response, Mapping) else []
    if not isinstance(districts, list):
        return False
    return any(
        isinstance(row, Mapping)
        and str(row.get("adcode") or "") == identity.provider_adcode
        and row.get("name") == identity.public_name
        and (
            row.get("level") == "city"
            or row.get("level") == "province"
            and identity.provider_adcode in _MUNICIPAL_ADCODES
        )
        for row in districts
    )


def _valid_public_poi(item):
    if not isinstance(item, Mapping):
        return False
    latitude = item.get("latitude")
    longitude = item.get("longitude")
    return (
        bool(str(item.get("place_id") or "").strip())
        and item.get("coordinate_system") == "WGS84"
        and type(latitude) in (int, float)
        and type(longitude) in (int, float)
        and math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def _valid_public_route(item, poi_ids):
    if not isinstance(item, Mapping):
        return False
    provider = item.get("provider")
    origin = str(item.get("origin_place_id") or "")
    destination = str(item.get("destination_place_id") or "")
    captured_at = item.get("captured_at")
    try:
        captured = datetime.fromisoformat(captured_at)
    except (TypeError, ValueError):
        return False
    return (
        item.get("provenance") == "CAPTURED_PROVIDER_SNAPSHOT"
        and item.get("fact_quality") == LIVE_PROVIDER_CAPTURE
        and item.get("route_provenance") == LIVE_PROVIDER_CAPTURE
        and provider == "amap-web-service"
        and item.get("geometry_provider") == provider
        and item.get("geometry_crs") == "WGS84"
        and _valid_wgs84_points(item.get("route_geometry"))
        and "source_call_id" not in item
        and "provider_call_id" not in item
        and origin != destination
        and origin in poi_ids
        and destination in poi_ids
        and type(item.get("minutes")) is int
        and item.get("minutes") >= 0
        and re.fullmatch(r"[0-9a-fA-F]{64}", str(item.get("snapshot_sha256") or ""))
        and captured.tzinfo is not None
        and captured <= datetime.now(timezone.utc)
        and (
            item.get("source_crs") is None
            or _normalized_crs(item.get("source_crs")) in {"WGS84", "GCJ02"}
        )
    )


def cities_for(session, actor_id, seed, *, journey_ids=None, include_public=True):
    from app.simulation.city_catalog import (
        SimulationCityIdentity,
        SimulationPublicCitySnapshot,
        acquired_amap_places,
        city_contains,
    )

    allowed = {
        seat.journey_id
        for seat in session.scalars(
            select(JourneyMember).where(JourneyMember.traveler_id == actor_id)
        )
        if _member_is_in_force(seat) and member_has_capability(session, seat, "JOURNEY_READ")
    }
    if journey_ids is not None:
        allowed &= set(journey_ids)
    journeys = {
        jid: journey
        for jid in sorted(allowed)
        if (journey := session.get(Journey, jid)) is not None
    }
    allowed = set(journeys)
    binding_by_journey = {}
    binding_candidates = {}
    for jid, journey in journeys.items():
        identity = session.get(SimulationCityIdentity, jid)
        if not _valid_city_identity(session, identity):
            continue
        binding_by_journey[jid] = identity
        binding_candidates.setdefault((journey.traveler_id, journey.city_code), []).append(identity)
    bindings = {}
    binding_conflicts = set()
    for owner_city, candidates in binding_candidates.items():
        adcodes = {identity.provider_adcode for identity in candidates}
        if len(adcodes) > 1:
            binding_conflicts.add(owner_city)
            continue
        bindings[owner_city] = min(candidates, key=lambda identity: identity.journey_id)
    amap_sources = acquired_amap_places(session)
    cities = {}
    places = {}
    for owner_id, city_code in binding_conflicts:
        cities[(owner_id, city_code)] = {"city_code": city_code, "poi": {}, "routes": {}}
    for lead in session.scalars(
        select(RealPlaceCandidate).where(RealPlaceCandidate.journey_id.in_(allowed))
    ):
        meta = json.loads(lead.metadata_json or "{}")
        if meta.get("discovery_mode") != "live" or not lead.materialized_place_id:
            continue
        journey = journeys.get(lead.journey_id)
        binding = binding_by_journey.get(lead.journey_id)
        owner_city = (journey.traveler_id, lead.city_code) if journey else None
        city_binding = bindings.get(owner_city)
        if (
            journey is None
            or journey.city_code != lead.city_code
            or binding is None
            or city_binding is None
            or owner_city in binding_conflicts
            or binding.provider_adcode != city_binding.provider_adcode
            or lead.provider_key != "amap"
        ):
            continue
        source = amap_sources.get(lead.external_id.removeprefix("amap:"))
        if source is None or not city_contains(city_binding.provider_adcode, source["adcode"]):
            continue
        place = session.get(Place, lead.materialized_place_id)
        if (
            not place
            or place.city_code != lead.city_code
            or place.provider_key != lead.provider_key
            or place.external_id != lead.external_id
            or place.coordinate_system != "WGS84"
            or not all(math.isfinite(v) for v in (place.latitude, place.longitude))
            or not (-90 <= place.latitude <= 90 and -180 <= place.longitude <= 180)
        ):
            continue
        try:
            acquired = datetime.fromisoformat(lead.captured_at)
            if acquired.tzinfo is None or acquired > datetime.now(timezone.utc):
                continue
        except (ValueError, TypeError):
            continue
        owner_city = (journey.traveler_id, place.city_code)
        bucket = cities.setdefault(owner_city, {"city_code": place.city_code, "poi": {}, "routes": {}})
        bucket["poi"][place.id] = {
            "place_id": place.id,
            "name": place.name,
            "provider": place.provider_key,
            "external_id": place.external_id,
            "latitude": place.latitude,
            "longitude": place.longitude,
            "coordinate_system": "WGS84",
            "captured_at": lead.captured_at,
            "expires_at": lead.expires_at,
            "provenance": "CAPTURED_PROVIDER_SNAPSHOT",
        }
        places.setdefault(place.id, set()).add((journey.traveler_id, place.city_code))
    for plan in session.scalars(select(PlanVersion).where(PlanVersion.journey_id.in_(allowed))):
        raw = plan.mobility_evidence_json or "{}"
        try:
            evidence = json.loads(raw)
            if not isinstance(evidence, Mapping):
                continue
            snapshot = MobilitySnapshot.from_evidence(evidence)
        except (AttributeError, TypeError, ValueError, KeyError):
            continue
        journey = journeys.get(plan.journey_id)
        if journey is None:
            continue
        owner_city = (journey.traveler_id, journey.city_code)
        if owner_city not in cities or snapshot.snapshot_id != plan.mobility_snapshot_id:
            continue
        raw_geometry_valid = {}
        if isinstance(evidence, Mapping):
            evidence_facts = [
                *[item for item in evidence.get("facts", []) if isinstance(item, Mapping)],
                *[item for item in evidence.get("selected_facts", []) if isinstance(item, Mapping)],
            ]
            for item in evidence_facts:
                pair = (
                    str(item.get("origin_key") or ""),
                    str(item.get("destination_key") or ""),
                )
                if pair[0] and pair[1]:
                    raw_geometry_valid[pair] = _valid_snapshot_geometry_fact(item)
        for fact in snapshot.facts.values():
            origin = fact.origin_key.split("@")[0]
            destination = fact.destination_key.split("@")[0]
            raw_pair = (fact.origin_key, fact.destination_key)
            if raw_geometry_valid.get(raw_pair) is not True:
                continue
            if (
                origin == destination
                or (journey.traveler_id, journey.city_code) not in places.get(origin, set())
                or (journey.traveler_id, journey.city_code) not in places.get(destination, set())
                or owner_city in binding_conflicts
                or owner_city not in bindings
                or fact.fact_quality != LIVE_PROVIDER_CAPTURE
                or fact.degraded
                or not fact.captured_at
            ):
                continue
            cities[owner_city]["routes"][(origin, destination)] = {
                "origin_place_id": origin,
                "destination_place_id": destination,
                "minutes": fact.minutes,
                "provider": fact.provider_key,
                "captured_at": fact.captured_at,
                "fact_quality": fact.fact_quality,
                # MobilitySnapshot stores the WGS84-normalized point pairs and these two
                # provenance fields; it does not persist the original provider call id or CRS.
                "route_geometry": [list(point) for point in fact.route_geometry],
                "geometry_crs": "WGS84",
                "geometry_provider": fact.geometry_provider,
                "route_provenance": fact.route_provenance,
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "provenance": "CAPTURED_PROVIDER_SNAPSHOT",
            }
    results = []
    for owner_city, bucket in sorted(cities.items()):
        name = bucket["city_code"]
        poi = list(bucket["poi"].values())
        routes = list(bucket["routes"].values())
        missing = []
        binding = bindings.get(owner_city)
        if owner_city in binding_conflicts:
            missing.append("CITY_IDENTITY_BINDING_CONFLICT")
        if binding is None:
            missing.append("VERIFIED_CITY_ADCODE_REQUIRED")
        if len(poi) < 5:
            missing.append("AT_LEAST_5_ACQUIRED_POI_REQUIRED")
        if len(routes) < 3:
            missing.append("AT_LEAST_3_CAPTURED_ROUTES_REQUIRED")
        results.append(
            {
                "city_code": name,
                "provider_city_adcode": binding.provider_adcode if binding else None,
                "status": "ELIGIBLE_CAPTURED_SNAPSHOT" if not missing else "BLOCKED",
                "missing": missing,
                "poi": poi,
                "routes": routes,
            }
        )
    if include_public:
        for row in session.scalars(select(SimulationPublicCitySnapshot)):
            try:
                public = json.loads(row.snapshot_json)
            except (TypeError, ValueError):
                public = {}
            if not isinstance(public, Mapping):
                public = {}
            raw_poi = public.get("poi", []) if isinstance(public, Mapping) else []
            poi = (
                [item for item in raw_poi if _valid_public_poi(item)]
                if isinstance(raw_poi, list)
                else []
            )
            poi_ids = {str(item["place_id"]) for item in poi}
            raw_routes = public.get("routes", []) if isinstance(public, Mapping) else []
            routes = []
            seen_routes = set()
            if isinstance(raw_routes, list):
                for item in raw_routes:
                    if not _valid_public_route(item, poi_ids):
                        continue
                    pair = (item["origin_place_id"], item["destination_place_id"])
                    if pair in seen_routes:
                        continue
                    seen_routes.add(pair)
                    routes.append(item)
            public_code = str(public.get("provider_city_adcode") or "")
            missing = []
            if (
                not re.fullmatch(r"[0-9]{6}", public_code)
                or public_code != row.provider_adcode
            ):
                missing.append("VERIFIED_CITY_ADCODE_REQUIRED")
            if public.get("provenance") != "CAPTURED_PROVIDER_SNAPSHOT":
                missing.append("CAPTURED_PROVIDER_SNAPSHOT_REQUIRED")
            if (
                hashlib.sha256(str(row.snapshot_json or "").encode()).hexdigest()
                != row.snapshot_sha256
            ):
                missing.append("PUBLISHED_SNAPSHOT_HASH_MISMATCH")
            if len(poi) < 5:
                missing.append("AT_LEAST_5_ACQUIRED_POI_REQUIRED")
            if len(routes) < 3:
                missing.append("AT_LEAST_3_CAPTURED_ROUTES_REQUIRED")
            results.append(
                {
                    **public,
                    "poi": poi,
                    "routes": routes,
                    "city_code": None,
                    "status": "ELIGIBLE_CAPTURED_SNAPSHOT" if not missing else "BLOCKED",
                    "missing": missing,
                    "catalog": "EXPLICITLY_PUBLISHED_PUBLIC",
                    "snapshot_sha256": row.snapshot_sha256,
                }
            )
    eligible = sorted(
        {
            item["provider_city_adcode"]
            for item in results
            if not item["missing"]
            and re.fullmatch(r"[0-9]{6}", str(item.get("provider_city_adcode") or ""))
        }
    )
    return {
        "seed": seed,
        "status": "READY" if len(eligible) >= 3 else "BLOCKED",
        "required_city_count": 3,
        "eligible_city_count": len(eligible),
        "cities": results,
        "selected_city_code": random.Random(seed).choice(eligible) if len(eligible) >= 3 else None,
        "selected_provider_adcode": random.Random(seed).choice(eligible)
        if len(eligible) >= 3
        else None,
        "missing": [] if len(eligible) >= 3 else ["THREE_ACQUIRED_CITIES_REQUIRED"],
        "provider_requests": 0,
    }
