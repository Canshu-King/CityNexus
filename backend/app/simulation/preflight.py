"""Inspect acquired public facts without making provider requests."""

import hashlib
import json
import math
import random
import re
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import Journey, JourneyMember, Place, PlanVersion, RealPlaceCandidate
from app.traveler_principal import _member_is_in_force, member_has_capability
from app.replanning.provider_snapshots import MobilitySnapshot


def cities_for(session, actor_id, seed):
    allowed = {
        seat.journey_id
        for seat in session.scalars(
            select(JourneyMember).where(JourneyMember.traveler_id == actor_id)
        )
        if _member_is_in_force(seat) and member_has_capability(session, seat, "JOURNEY_READ")
    }
    cities = {}
    places = {}
    for lead in session.scalars(
        select(RealPlaceCandidate).where(RealPlaceCandidate.journey_id.in_(allowed))
    ):
        meta = json.loads(lead.metadata_json or "{}")
        if meta.get("discovery_mode") != "live" or not lead.materialized_place_id:
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
        bucket = cities.setdefault(
            place.city_code, {"city_code": place.city_code, "poi": {}, "routes": {}}
        )
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
        places[place.id] = place.city_code
    for plan in session.scalars(select(PlanVersion).where(PlanVersion.journey_id.in_(allowed))):
        raw = plan.mobility_evidence_json or "{}"
        try:
            snapshot = MobilitySnapshot.from_evidence(json.loads(raw))
        except (TypeError, ValueError, KeyError):
            continue
        journey = session.get(Journey, plan.journey_id)
        if journey.city_code not in cities or snapshot.snapshot_id != plan.mobility_snapshot_id:
            continue
        for fact in snapshot.facts.values():
            origin = fact.origin_key.split("@")[0]
            destination = fact.destination_key.split("@")[0]
            if (
                origin == destination
                or places.get(origin) != journey.city_code
                or places.get(destination) != journey.city_code
                or fact.fact_quality != "LIVE_PROVIDER_CAPTURE"
                or fact.degraded
                or not fact.route_geometry
                or not fact.captured_at
            ):
                continue
            cities[journey.city_code]["routes"][(origin, destination)] = {
                "origin_place_id": origin,
                "destination_place_id": destination,
                "minutes": fact.minutes,
                "provider": fact.provider_key,
                "captured_at": fact.captured_at,
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "provenance": "CAPTURED_PROVIDER_SNAPSHOT",
            }
    results = []
    for name, bucket in sorted(cities.items()):
        poi = list(bucket["poi"].values())
        routes = list(bucket["routes"].values())
        missing = []
        if not re.fullmatch(r"(?:CN-)?[0-9]{6}", name):
            missing.append("VERIFIED_CITY_ADCODE_REQUIRED")
        if len(poi) < 5:
            missing.append("AT_LEAST_5_ACQUIRED_POI_REQUIRED")
        if len(routes) < 3:
            missing.append("AT_LEAST_3_CAPTURED_ROUTES_REQUIRED")
        results.append(
            {
                "city_code": name,
                "status": "ELIGIBLE_CAPTURED_SNAPSHOT" if not missing else "BLOCKED",
                "missing": missing,
                "poi": poi,
                "routes": routes,
            }
        )
    eligible = [item["city_code"] for item in results if not item["missing"]]
    return {
        "seed": seed,
        "status": "READY" if len(eligible) >= 3 else "BLOCKED",
        "required_city_count": 3,
        "eligible_city_count": len(eligible),
        "cities": results,
        "selected_city_code": random.Random(seed).choice(eligible) if len(eligible) >= 3 else None,
        "missing": [] if len(eligible) >= 3 else ["THREE_ACQUIRED_CITIES_REQUIRED"],
        "provider_requests": 0,
    }
