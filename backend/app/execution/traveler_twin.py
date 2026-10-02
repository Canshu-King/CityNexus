from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.capabilities import canonicalize_capabilities, capability_constraints, summarize_capabilities
from app.db.models import (
    Activity,
    Journey,
    JourneyMission,
    JourneyOutcomeEvent,
    Place,
    Preference,
    TravelerPreferenceEvidence,
    TravelerCapability,
    TravelerTwinSnapshot,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _load(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def _as_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def evidence_decay_factor(
    evidence: TravelerPreferenceEvidence, *, now: datetime | None = None
) -> float:
    """Return bounded linear freshness without mutating the evidence row.

    ``expires_at`` remains the hard expiry boundary.  Before that boundary the
    evidence gradually loses ranking weight, while its raw source, provenance,
    and authority class remain unchanged.
    """

    created = _as_utc(evidence.created_at)
    expires = _as_utc(evidence.expires_at)
    if created is None or expires is None or expires <= created:
        return 1.0
    current = now or datetime.now(timezone.utc)
    remaining = (expires - current).total_seconds()
    lifetime = (expires - created).total_seconds()
    return round(max(0.0, min(1.0, remaining / lifetime)), 6)


def _place_tags(session: Session, activity: Activity | None) -> set[str]:
    if activity is None or not activity.place_id:
        return set()
    place = session.get(Place, activity.place_id)
    if place is None:
        return set()
    tags = {str(item).strip().lower() for item in _load(place.tags_json, []) if str(item).strip()}
    category = str(place.category or "").strip().lower()
    if category:
        tags.add(category)
        tags.add(f"category:{category}")
    return tags


def _explicit_items(session: Session, traveler_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Preference)
        .where(Preference.traveler_id == str(traveler_id))
        .order_by(Preference.category, Preference.preference_key)
    ).all()
    return [
        {
            "id": row.id,
            "category": row.category,
            "dimension": row.preference_key,
            "direction": row.preference_key,
            "value": _load(row.value_json, None),
            "weight": float(row.weight),
            "source": "EXPLICIT",
            "explanation": "Explicit traveler preference.",
        }
        for row in rows
    ]


def _event_signal(session: Session, event: JourneyOutcomeEvent) -> dict[str, Any] | None:
    """Extract only decision-bearing preference evidence.

    Execution telemetry is deliberately not preference truth.  A completion or
    skip can be caused by a lock, a disruption, or simply having no alternative
    choice.  Only an explicit user statement or an explicitly marked voluntary
    choice is learnable here.
    """

    activity = session.get(Activity, event.activity_id) if event.activity_id else None
    tags = _place_tags(session, activity)
    place = session.get(Place, activity.place_id) if activity and activity.place_id else None
    payload = _load(event.payload_json, {})
    explicit = str(payload.get("preference_dimension") or "").strip().lower()
    if explicit in {"indoor", "outdoor", "low_walking", "cultural", "food"}:
        direction = str(payload.get("direction") or explicit).strip().lower()
        return {
            "dimension": explicit,
            "direction": direction,
            "evidence_class": "EXPLICIT_USER_FEEDBACK",
            "strength": 0.9,
            "confidence": 0.95,
            "explanation": "The traveler explicitly stated a preference in the outcome payload.",
        }

    voluntary = bool(payload.get("voluntary_choice") or payload.get("user_chose"))
    forced = bool(
        payload.get("forced_by_disruption")
        or payload.get("locked_activity")
        or payload.get("no_alternative")
        or payload.get("replan_removed")
    )
    if not voluntary or forced or activity is None or activity.locked:
        return None
    if event.event_type not in {"USER_ACCEPTED", "USER_REJECTED", "MANUAL_OVERRIDE"}:
        return None

    # Voluntary choices use canonical provider category/tags.  They never infer
    # capability or a personality trait, and plain execution events never reach
    # this branch.
    dimension = str(payload.get("learning_dimension") or "interest").strip().lower()
    if dimension == "interest":
        category = str(place.category or "").strip().lower() if place is not None else ""
        if not category:
            category = next((item for item in sorted(tags) if not item.startswith("category:")), None)
        if category is None:
            return None
        direction = category
    else:
        direction = str(payload.get("learning_direction") or dimension).strip().lower()
    if event.event_type in {"USER_REJECTED"}:
        direction = f"avoid:{direction}"
    return {
        "dimension": dimension,
        "direction": direction,
        "evidence_class": "VOLUNTARY_CHOICE",
        "strength": 0.55,
        "confidence": 0.7,
        "explanation": "The traveler made an explicitly voluntary choice; execution telemetry alone is not used.",
    }


def _active_evidence(session: Session, traveler_id: str) -> list[TravelerPreferenceEvidence]:
    now = datetime.now(timezone.utc)
    rows = list(
        session.scalars(
            select(TravelerPreferenceEvidence)
            .where(
                TravelerPreferenceEvidence.traveler_id == str(traveler_id),
                TravelerPreferenceEvidence.status == "ACTIVE",
            )
            .order_by(TravelerPreferenceEvidence.created_at, TravelerPreferenceEvidence.id)
        ).all()
    )
    active: list[TravelerPreferenceEvidence] = []
    for row in rows:
        expires = _as_utc(row.expires_at)
        if expires is not None and expires <= now:
            row.status = "EXPIRED"
            continue
        active.append(row)
    return active


def active_capability_rows(
    session: Session, traveler_id: str, journey_id: str | None = None
) -> list[TravelerCapability]:
    """Return active explicit capability facts for a traveler and journey."""

    rows = list(
        session.scalars(
            select(TravelerCapability)
            .where(
                TravelerCapability.traveler_id == str(traveler_id),
                TravelerCapability.active.is_(True),
                (
                    (TravelerCapability.scope == "TRAVELER")
                    | (
                        (TravelerCapability.scope == "JOURNEY")
                        & (TravelerCapability.journey_id == str(journey_id))
                    )
                    if journey_id is not None
                    else (TravelerCapability.scope == "TRAVELER")
                ),
            )
            .order_by(TravelerCapability.scope, TravelerCapability.code, TravelerCapability.id)
        ).all()
    )
    return rows


def capability_row_payload(row: TravelerCapability) -> dict[str, Any]:
    return {
        "id": row.id,
        "traveler_id": row.traveler_id,
        "journey_id": row.journey_id,
        "code": row.code,
        "class": row.capability_class,
        "severity": row.severity,
        "params": _load(row.params_json, {}),
        "scope": row.scope,
        "source": row.source,
        "provenance": row.provenance,
        "explicit": bool(row.explicit),
        "confirmed": bool(row.confirmed),
        "active": bool(row.active),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "confirmed_at": row.confirmed_at,
    }


def capability_payload(session: Session, traveler_id: str, journey_id: str | None = None) -> list[dict[str, Any]]:
    return [capability_row_payload(row) for row in active_capability_rows(session, traveler_id, journey_id)]


def capability_constraint_items(
    session: Session, traveler_id: str, journey_id: str | None = None
) -> list[dict[str, Any]]:
    return capability_constraints(capability_payload(session, traveler_id, journey_id))


def refresh_snapshot(session: Session, traveler_id: str) -> TravelerTwinSnapshot:
    explicit = _explicit_items(session, traveler_id)
    evidence = _active_evidence(session, traveler_id)
    grouped: dict[tuple[str, str], list[TravelerPreferenceEvidence]] = defaultdict(list)
    for item in evidence:
        grouped[(item.preference_dimension, item.direction)].append(item)
    learned: list[dict[str, Any]] = []
    for (dimension, direction), items in sorted(grouped.items()):
        count = sum(max(1, int(item.evidence_count)) for item in items)
        raw_strength = min(1.0, round(max(float(item.strength) for item in items), 3))
        weighted_items = [
            (item, evidence_decay_factor(item))
            for item in items
        ]
        representative, representative_decay = max(
            weighted_items,
            key=lambda pair: (
                float(pair[0].strength) * pair[1],
                float(pair[0].confidence),
                pair[0].created_at,
            ),
        )
        effective_strength = min(
            1.0,
            round(float(representative.strength) * representative_decay, 3),
        )
        confidence = min(0.95, round(max(float(item.confidence) for item in items), 3))
        evidence_class = max(
            items,
            key=lambda item: (
                float(item.strength) * evidence_decay_factor(item),
                float(item.confidence),
                item.created_at,
            ),
        ).evidence_type
        learned.append(
            {
                "dimension": dimension,
                "direction": direction,
                "strength": raw_strength,
                "effective_strength": effective_strength,
                "decay_factor": representative_decay,
                "confidence": confidence,
                "evidence_count": count,
                "source": "LEARNED_SOFT",
                "evidence_class": evidence_class,
                "explanation": representative.explanation,
                "evidence_ids": [item.id for item in items],
                "journey_ids": sorted({item.journey_id for item in items if item.journey_id}),
                "last_evidence_at": max(item.created_at for item in items),
                "expires_at": max(
                    (item.expires_at for item in items if item.expires_at),
                    default=None,
                ),
                "override_state": "EXPLICIT_WINS" if dimension in {item["dimension"] for item in explicit} else "LEARNED_ACTIVE",
            }
        )
    explicit_keys = {(item["category"], item["dimension"]) for item in explicit}
    explicit_interest_directions = {
        str(item["dimension"]).strip().lower()
        for item in explicit
        if str(item["category"]).strip().lower() == "interest"
    }
    conflicts: list[dict[str, Any]] = []
    by_dimension: dict[str, set[str]] = defaultdict(set)
    for item in learned:
        by_dimension[item["dimension"]].add(item["direction"])
    for dimension, directions in sorted(by_dimension.items()):
        if len(directions) > 1:
            conflicts.append(
                {
                    "dimension": dimension,
                    "directions": sorted(directions),
                    "resolution": "recent evidence and explicit mission win",
                }
            )
        if any(
            str(direction).removeprefix("avoid:") in explicit_interest_directions
            for direction in directions
        ) or ("mobility", dimension) in explicit_keys:
            conflicts.append(
                {
                    "dimension": dimension,
                    "directions": sorted(directions),
                    "resolution": "EXPLICIT overrides LEARNED_SOFT",
                }
            )
    conflict_by_dimension = {item["dimension"]: item for item in conflicts}
    for item in learned:
        item["conflict"] = conflict_by_dimension.get(item["dimension"])
        learned_target = str(item["direction"]).removeprefix("avoid:").strip().lower()
        if learned_target in explicit_interest_directions:
            item["override_state"] = "EXPLICIT_WINS"
    now = _now()
    explicit_capabilities = capability_payload(session, traveler_id)
    snapshot = session.get(TravelerTwinSnapshot, str(traveler_id))
    if snapshot is None:
        snapshot = TravelerTwinSnapshot(traveler_id=str(traveler_id), updated_at=now)
        session.add(snapshot)
    snapshot.explicit_preferences_json = _json(explicit)
    snapshot.learned_soft_preferences_json = _json(learned)
    snapshot.conflicts_json = _json(conflicts)
    snapshot.explicit_capabilities_json = _json(explicit_capabilities)
    snapshot.confidence = max((float(item["confidence"]) for item in learned), default=0.0)
    snapshot.evidence_count = sum(int(item["evidence_count"]) for item in learned)
    snapshot.provenance_json = _json(
        {
            "source": "journey_outcome_events",
            "evidence_ids": [item.id for item in evidence],
            "updated_at": now,
        }
    )
    snapshot.updated_at = now
    session.flush()
    return snapshot


def snapshot_payload(snapshot: TravelerTwinSnapshot) -> dict[str, Any]:
    explicit_capabilities = _load(getattr(snapshot, "explicit_capabilities_json", "[]"), [])
    return {
        "traveler_id": snapshot.traveler_id,
        "explicit_preferences": _load(snapshot.explicit_preferences_json, []),
        "explicit_capabilities": explicit_capabilities,
        "capability_summary": summarize_capabilities(explicit_capabilities),
        "learned_soft_preferences": _load(snapshot.learned_soft_preferences_json, []),
        "confidence": float(snapshot.confidence),
        "evidence_count": int(snapshot.evidence_count),
        "conflicts": _load(snapshot.conflicts_json, []),
        "provenance": _load(snapshot.provenance_json, {}),
        "updated_at": snapshot.updated_at,
    }


def learn_from_journey(session: Session, journey: Journey) -> TravelerTwinSnapshot:
    """Accumulate bounded evidence from actual outcome events for one Journey."""

    events = session.scalars(
        select(JourneyOutcomeEvent)
        .where(JourneyOutcomeEvent.journey_id == journey.id)
        .order_by(JourneyOutcomeEvent.occurred_at_actual, JourneyOutcomeEvent.id)
    ).all()
    grouped: dict[tuple[str, str], list[JourneyOutcomeEvent]] = defaultdict(list)
    for event in events:
        signal = _event_signal(session, event)
        if signal is not None:
            grouped[(str(signal["dimension"]), str(signal["direction"]))].append(event)
    now = _now()
    for (dimension, direction), rows in grouped.items():
        signal_classes = [_event_signal(session, event) for event in rows]
        signal_classes = [item for item in signal_classes if item is not None]
        if not signal_classes:
            continue
        strongest = max(signal_classes, key=lambda item: float(item["strength"]))
        existing = session.scalar(
            select(TravelerPreferenceEvidence)
            .where(
                TravelerPreferenceEvidence.traveler_id == journey.traveler_id,
                TravelerPreferenceEvidence.journey_id == journey.id,
                TravelerPreferenceEvidence.preference_dimension == dimension,
                TravelerPreferenceEvidence.direction == direction,
                TravelerPreferenceEvidence.status == "ACTIVE",
            )
            .order_by(TravelerPreferenceEvidence.created_at.desc())
        )
        explanation = str(strongest["explanation"])
        related = [item.id for item in rows]
        if existing is None:
            session.add(
                TravelerPreferenceEvidence(
                    id=str(uuid4()),
                    traveler_id=journey.traveler_id,
                    journey_id=journey.id,
                    evidence_type=str(strongest["evidence_class"]),
                    preference_dimension=dimension,
                    direction=direction,
                    strength=float(strongest["strength"]),
                    confidence=float(strongest["confidence"]),
                    source="USER_FEEDBACK" if strongest["evidence_class"] == "EXPLICIT_USER_FEEDBACK" else "VOLUNTARY_OUTCOME",
                    evidence_count=len(rows),
                    explanation=explanation,
                    related_ids_json=_json(related),
                    created_at=now,
                    expires_at=(datetime.now(timezone.utc) + timedelta(days=180)).isoformat(),
                    status="ACTIVE",
                )
            )
        else:
            existing.evidence_count = max(existing.evidence_count, len(rows))
            existing.evidence_type = str(strongest["evidence_class"])
            existing.strength = max(float(existing.strength), float(strongest["strength"]))
            existing.confidence = max(float(existing.confidence), float(strongest["confidence"]))
            existing.related_ids_json = _json(
                sorted(set(_load(existing.related_ids_json, []) + related))
            )
            existing.explanation = explanation
            existing.created_at = now
            existing.expires_at = (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()
    session.flush()
    return refresh_snapshot(session, journey.traveler_id)


def clear_learned(session: Session, traveler_id: str) -> TravelerTwinSnapshot:
    for item in _active_evidence(session, traveler_id):
        item.status = "CLEARED"
    session.flush()
    return refresh_snapshot(session, traveler_id)


def planning_preference_items(
    session: Session, traveler_id: str, journey_id: str | None = None
) -> list[Any]:
    """Return explicit and learned soft items in the shape used by the planner."""

    rows = list(
        session.scalars(
            select(Preference)
            .where(Preference.traveler_id == str(traveler_id))
            .order_by(Preference.category, Preference.preference_key)
        ).all()
    )
    explicit_dimensions = {row.preference_key for row in rows}
    items: list[Any] = rows[:]
    for capability in capability_payload(session, traveler_id, journey_id):
        items.append(
            SimpleNamespace(
                category="capability",
                preference_key=str(capability.get("code") or ""),
                value_json=_json(capability.get("params") or {}),
                weight=1.0 if capability.get("severity") == "HARD" else 0.75,
                source=str(capability.get("source") or "USER_CONFIRMED"),
            )
        )
    if journey_id:
        mission = session.scalar(
            select(JourneyMission)
            .where(
                JourneyMission.journey_id == str(journey_id),
                JourneyMission.status.in_(("ACTIVE", "RUNNING", "CREATED")),
            )
            .order_by(JourneyMission.created_at.desc(), JourneyMission.id.desc())
        )
        mission_preferences = _load(mission.preferences_json if mission else "{}", {})
        for key, value in mission_preferences.items():
            if key in {"protected_activity_ids"}:
                continue
            explicit_dimensions.add(str(key))
            if key == "indoor":
                explicit_dimensions.add("outdoor")
            elif key == "outdoor":
                explicit_dimensions.add("indoor")
            items.append(
                SimpleNamespace(
                    category="mission",
                    preference_key=str(key),
                    value_json=_json(value),
                    weight=1.0,
                    source="EXPLICIT_MISSION",
                )
            )
    snapshot = refresh_snapshot(session, traveler_id)
    for item in _load(snapshot.learned_soft_preferences_json, []):
        learned_direction = str(item.get("direction") or "").strip().lower()
        learned_target = learned_direction.removeprefix("avoid:").strip()
        if learned_direction in explicit_dimensions or learned_target in explicit_dimensions:
            continue
        items.append(
            SimpleNamespace(
                category="interest",
                preference_key=str(item.get("direction") or item.get("dimension")),
                value_json="true",
                weight=float(
                    item.get("effective_strength", item.get("strength", 0.0))
                ),
                source="LEARNED_SOFT",
            )
        )
    return items
