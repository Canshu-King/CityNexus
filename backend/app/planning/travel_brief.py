"""Private trip intent, using JourneyIntent and the existing planner preferences."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from uuid import uuid4

from sqlalchemy import select

from app.db.models import Activity, JourneyIntent, JourneyTripContext, Place, RealPlaceCandidate
from app.planning.day_rhythm import extract_day_rhythm

INTEREST_KEYS = {
    "park/garden": "outdoor", "cafe": "food", "museum/gallery": "cultural", "library": "library",
    "local_food": "food", "night_market": "food", "old_town": "cultural",
    "heritage": "cultural", "architecture": "cultural", "nature": "outdoor",
    "coast": "outdoor", "shopping": "shopping", "nightlife": "nightlife",
    "photography": "photography", "family": "family",
}


def current_brief(session, journey_id, traveler_id):
    return session.scalar(select(JourneyIntent).where(
        JourneyIntent.journey_id == str(journey_id),
        JourneyIntent.created_by_traveler_id == str(traveler_id),
        JourneyIntent.intent_kind == "TRAVEL_BRIEF",
        JourneyIntent.status == "RECORDED",
    ).order_by(JourneyIntent.updated_at.desc(), JourneyIntent.id.desc()).limit(1))


def _public_region_label(session, journey) -> str | None:
    row = current_brief(session, journey.id, journey.traveler_id)
    if row is None:
        return None
    try:
        value = json.loads(row.semantic_envelope_json or "{}").get("public_region_label")
    except (TypeError, ValueError, AttributeError):
        return None
    return value.strip() if isinstance(value, str) and value.strip() else None


def save_brief(session, journey, member, payload):
    data = payload.model_dump()
    text = data["goal"].strip()
    preferences = {INTEREST_KEYS[key]: True for key in data["interests"] if key in INTEREST_KEYS}
    mapped = [{"input": key, "preference": INTEREST_KEYS[key]} for key in data["interests"] if key in INTEREST_KEYS]
    # Unsupported expressions still belong to the user and remain in the brief.
    # They must not disappear or be asserted as planner constraints we cannot honor.
    unmapped_interests = [key for key in data["interests"] if key not in INTEREST_KEYS]
    if data["energy"] == "easy" or any(word in text for word in ("少走路", "少走", "轻松", "低步行")):
        preferences["low_walking"] = True
        mapped.append({"input": "轻松少走", "preference": "low_walking"})
    for words, key in ((("美食", "吃饭"), "food"), (("博物馆", "艺术"), "cultural")):
        if any(word in text for word in words):
            preferences[key] = True
            mapped.append({"input": next(word for word in words if word in text), "preference": key})
    now = datetime.now(timezone.utc).isoformat()
    row = current_brief(session, journey.id, member.traveler_id)
    public_region_label = data.get("public_region_label")
    if isinstance(public_region_label, str):
        public_region_label = public_region_label.strip() or None
    if public_region_label is None and row is not None:
        try:
            previous_data = json.loads(row.semantic_envelope_json or "{}")
        except (TypeError, ValueError):
            previous_data = {}
        previous_region = previous_data.get("public_region_label")
        if isinstance(previous_region, str):
            previous_region = previous_region.strip()
            if 0 < len(previous_region) <= 60 and not any(ord(char) < 32 for char in previous_region):
                public_region_label = previous_region
    data["public_region_label"] = public_region_label
    rhythm = extract_day_rhythm(text)
    if rhythm:
        preferences["day_rhythm"] = rhythm.as_dict()
        mapped.append({"input": "作息", "preference": "day_rhythm"})
    # Keep open-ended text; only the explicit mappings above reach deterministic constraints.
    data.update({"mapped_preferences": mapped, "unmapped_interests": unmapped_interests,
                 "free_text_status": "PRESERVED_NOT_FULLY_COMPILED" if text or unmapped_interests else "EMPTY"})
    if row is None:
        row = JourneyIntent(id=str(uuid4()), journey_id=journey.id,
            created_by_traveler_id=member.traveler_id, created_by_member_id=member.id,
            intent_kind="TRAVEL_BRIEF", source_text=text, semantic_fingerprint=f"travel-brief:{member.id}",
            created_at=now, updated_at=now)
        session.add(row)
    row.source_text = text
    row.scope_kind = "JOURNEY"
    row.scope_start_at, row.scope_end_at = journey.start_at, journey.end_at
    row.source = "USER_TRAVEL_BRIEF"
    row.status, row.evaluation_state = "RECORDED", "PLANNING_INPUT"
    row.preference_hints_json = json.dumps(preferences, ensure_ascii=False)
    row.semantic_envelope_json = json.dumps(data, ensure_ascii=False)
    row.updated_at = now
    session.flush()
    return row


def preference_items(session, traveler_id, journey_id):
    row = current_brief(session, journey_id, traveler_id)
    if row is None:
        return []
    return [SimpleNamespace(category="interest" if key not in {"day_rhythm", "low_walking"} else "pace", preference_key=key,
        value_json=json.dumps(value), weight=1.0, source="USER_TRAVEL_BRIEF")
        for key, value in json.loads(row.preference_hints_json).items()]


def brief_projection(session, journey, member):
    row = current_brief(session, journey.id, member.traveler_id)
    context = session.get(JourneyTripContext, journey.id)
    zone = ZoneInfo(journey.timezone)
    first = datetime.fromisoformat(journey.start_at).astimezone(zone).date()
    last = datetime.fromisoformat(journey.end_at).astimezone(zone).date()
    # The intake accepts up to 14 days; do not silently discard days 8 through 14.
    days = [str(first + timedelta(days=i)) for i in range(min(14, (last-first).days+1))]
    from app.execution.bootstrap_discovery import _candidate_payload, _scope_expired, _bootstrap_scope_entries
    region_label = _public_region_label(session, journey)
    candidates = []
    # Existing per-member observations, without querying or materializing a provider.
    for candidate in session.scalars(select(RealPlaceCandidate).where(
        RealPlaceCandidate.journey_id == journey.id,
        RealPlaceCandidate.provider_key.in_(("photon", "overpass")),
    ).order_by(RealPlaceCandidate.captured_at.desc(), RealPlaceCandidate.id).limit(100)).all():
        evidence = json.loads(candidate.evidence_json or "{}")
        scopes = [scope for scope in _bootstrap_scope_entries(evidence)
            if scope.get("member_id") == str(member.id) and scope.get("traveler_id") == str(member.traveler_id)]
        if not scopes or _scope_expired(scopes[0]):
            continue
        payload = _candidate_payload(candidate, member_id=str(member.id), traveler_id=str(member.traveler_id),
                                     public_region_label=region_label)
        payload["receipt_id"] = scopes[0]["receipt_id"]
        candidates.append(payload)
        if len(candidates) >= 12:
            break
    result = {
        "journey_id": journey.id, "intent": ({"id": row.id, **json.loads(row.semantic_envelope_json),
            "updated_at": row.updated_at, "source": row.source} if row else None),
        "trip": {"dates": days, "party_size": context.party_size if context else 1,
            "budget": {"amount_minor": journey.budget_amount_minor, "currency": journey.budget_currency},
            "planning_mode": journey.planning_mode},
        "candidates": candidates, "preview_kind": "UNVERIFIED_SUGGESTION_DRAFT",
        "transport_status": "UNKNOWN", "plan_version_id": None,
        "status": "READY_TO_COMPOSE" if sum(item["selection_state"] == "READY_FOR_NATIVE_PLAN" for item in candidates) >= 2 else "PARTIAL",
    }
    return result


def _provider_attribution(provider_key):
    """An Amap point must not borrow the OpenStreetMap copyright that _candidate_payload defaults to."""
    from app.integrations.discovery.photon_poi import OSM_ATTRIBUTION, OSM_ATTRIBUTION_URL
    if str(provider_key or "").lower() == "amap":
        return "© 高德地图（AMAP）", None
    return OSM_ATTRIBUTION, OSM_ATTRIBUTION_URL


def _plan_activity_point(activity, place):
    """A stop the traveller already accepted, projected from the place row that carries it."""
    metadata = json.loads(place.metadata_json or "{}")
    opening = json.loads(place.opening_hours_json or "{}")
    cost = metadata.get("cost_evidence") if isinstance(metadata.get("cost_evidence"), dict) else {}
    source_url = next((str(url) for url in (metadata.get("source_urls") or []) if url), None) \
        or (str(opening["source_url"]) if opening.get("source_url") else None)
    attribution, attribution_url = _provider_attribution(place.provider_key)
    return {
        "candidate_id": str(place.id), "place_id": str(place.id),
        "name": place.name, "category": place.category,
        "provider_key": place.provider_key, "provider": place.provider_key,
        "external_id": place.external_id,
        "latitude": place.latitude, "longitude": place.longitude,
        "coordinate_system": str(place.coordinate_system or "WGS84"),
        "source_coordinate_system": place.source_coordinate_system,
        "source_url": source_url, "source_attribution": attribution, "source_attribution_url": attribution_url,
        "region_status": str(metadata.get("region_status") or "UNKNOWN"),
        "selection_state": "READY_FOR_NATIVE_PLAN", "selection_action": None, "selection_blockers": [],
        "opening_state": str(opening.get("status") or "UNKNOWN"),
        "price_state": str(cost.get("status") or "UNKNOWN"),
        "observation_expired": False, "captured_at": place.updated_at,
        "scheduled_start_at": activity.start_at, "activity_title": activity.title,
        "origin": "PLAN_ACTIVITY",
    }


def map_place_projection(session, journey, member):
    """Private saved coordinates survive fact expiry; never renew planning receipts."""
    from app.execution.bootstrap_discovery import _candidate_payload, _scope_expired, _bootstrap_scope_entries
    region_label = _public_region_label(session, journey)
    points = []
    seen_places = set()
    for candidate in session.scalars(select(RealPlaceCandidate).where(
        RealPlaceCandidate.journey_id == journey.id,
        RealPlaceCandidate.provider_key.in_(("photon", "overpass")),
    ).order_by(RealPlaceCandidate.captured_at.desc(), RealPlaceCandidate.id).limit(100)).all():
        if candidate.materialized_place_id:
            seen_places.add(str(candidate.materialized_place_id))
        evidence = json.loads(candidate.evidence_json or "{}")
        scopes = [scope for scope in _bootstrap_scope_entries(evidence)
            if scope.get("member_id") == str(member.id) and scope.get("traveler_id") == str(member.traveler_id)]
        if not scopes:
            continue
        payload = _candidate_payload(candidate, member_id=str(member.id), traveler_id=str(member.traveler_id),
                                     public_region_label=region_label)
        payload["observation_expired"] = _scope_expired(scopes[0])
        payload["captured_at"] = scopes[0].get("captured_at") or candidate.captured_at
        if payload["observation_expired"]:
            payload["selection_state"] = "OPENING_UNVERIFIED"
            payload["selection_action"] = None
            payload["selection_blockers"] = ["OBSERVATION_EXPIRED"]
        points.append(payload)
    # The bootstrap arm above only knows the traveller's own private observations.  A plan built by the
    # Agent materialises its stops into `places` and no candidate row survives there with a member scope,
    # so an accepted itinerary used to render as 「0 处地点 / 暂无研究地点」 next to a schedule of six stops.
    if journey.active_plan_version_id:
        rows = session.execute(select(Activity, Place).join(Place, Place.id == Activity.place_id)
            .where(Activity.plan_version_id == str(journey.active_plan_version_id),
                   Activity.place_id.is_not(None))
            .order_by(Activity.start_at, Activity.sequence_no)).all()
        for activity, place in rows:
            if str(place.id) in seen_places:
                continue
            seen_places.add(str(place.id))
            points.append(_plan_activity_point(activity, place))
    return {"journey_id": str(journey.id), "candidates": points}


def stamp_plan_intent(session, journey, plans):
    row = current_brief(session, journey.id, journey.traveler_id)
    if row:
        for plan in plans:
            explanation = json.loads(plan.explanation_json or "{}")
            explanation["travel_brief"] = {"intent_id": row.id, "updated_at": row.updated_at,
                "source": row.source,
                "free_text_status": json.loads(row.semantic_envelope_json)["free_text_status"],
                "sha256": hashlib.sha256(row.semantic_envelope_json.encode()).hexdigest()}
            plan.explanation_json = json.dumps(explanation, ensure_ascii=False)
