"""Private trip intent, using JourneyIntent and the existing planner preferences."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from uuid import uuid4

from sqlalchemy import select

from app.db.models import JourneyIntent, JourneyTripContext, RealPlaceCandidate
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
    rhythm = extract_day_rhythm(text)
    if rhythm:
        preferences["day_rhythm"] = rhythm.as_dict()
        mapped.append({"input": "作息", "preference": "day_rhythm"})
    # Keep open-ended text; only the explicit mappings above reach deterministic constraints.
    data.update({"mapped_preferences": mapped, "unmapped_interests": unmapped_interests,
                 "free_text_status": "PRESERVED_NOT_FULLY_COMPILED" if text or unmapped_interests else "EMPTY"})
    now = datetime.now(timezone.utc).isoformat()
    row = current_brief(session, journey.id, member.traveler_id)
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
    days = [str(first + timedelta(days=i)) for i in range(min(7, (last-first).days+1))]
    from app.execution.bootstrap_discovery import _candidate_payload, _scope_expired, _bootstrap_scope_entries
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
        payload = _candidate_payload(candidate, member_id=str(member.id), traveler_id=str(member.traveler_id))
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


def map_place_projection(session, journey, member):
    """Private saved coordinates survive fact expiry; never renew planning receipts."""
    from app.execution.bootstrap_discovery import _candidate_payload, _scope_expired, _bootstrap_scope_entries
    points = []
    for candidate in session.scalars(select(RealPlaceCandidate).where(
        RealPlaceCandidate.journey_id == journey.id,
        RealPlaceCandidate.provider_key.in_(("photon", "overpass")),
    ).order_by(RealPlaceCandidate.captured_at.desc(), RealPlaceCandidate.id).limit(100)).all():
        evidence = json.loads(candidate.evidence_json or "{}")
        scopes = [scope for scope in _bootstrap_scope_entries(evidence)
            if scope.get("member_id") == str(member.id) and scope.get("traveler_id") == str(member.traveler_id)]
        if not scopes:
            continue
        payload = _candidate_payload(candidate, member_id=str(member.id), traveler_id=str(member.traveler_id))
        payload["observation_expired"] = _scope_expired(scopes[0])
        payload["captured_at"] = scopes[0].get("captured_at") or candidate.captured_at
        if payload["observation_expired"]:
            payload["selection_state"] = "OPENING_UNVERIFIED"
            payload["selection_action"] = None
            payload["selection_blockers"] = ["OBSERVATION_EXPIRED"]
        points.append(payload)
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
