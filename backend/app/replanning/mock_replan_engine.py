from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from app.capabilities import accessibility_state
from app.replanning.candidate_evidence import verified_interest_preference_fit


@dataclass(frozen=True)
class ReplacementChoice:
    place_id: str
    title: str
    duration_min: int
    cost_minor: int
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionPartition:
    terminal_prefix_ids: tuple[str, ...]
    current_activity_id: str | None
    c4_anchor_ids: tuple[str, ...]
    mutable_suffix_ids: tuple[str, ...]


def partition_execution(
    activities: Iterable[Any],
    *,
    current_activity_id: str | None,
    c4_anchors: Iterable[tuple[str, str]],
) -> ExecutionPartition:
    """Partition an active plan into immutable/current/C4/mutable sets."""

    rows = sorted(activities, key=lambda item: (int(item.sequence_no), str(item.id)))
    anchors = {
        (str(key), datetime.fromisoformat(str(start)).isoformat()) for key, start in c4_anchors
    }
    terminal: list[str] = []
    protected: list[str] = []
    mutable: list[str] = []
    current: str | None = None
    for item in rows:
        activity_id = str(item.id)
        status = str(getattr(item, "status", ""))
        semantic = str(
            getattr(item, "place_id", None) or getattr(item, "city_service_id", None) or activity_id
        )
        start_at = datetime.fromisoformat(str(item.start_at)).isoformat()
        if status in {"COMPLETED", "SKIPPED", "CANCELLED"}:
            terminal.append(activity_id)
        elif activity_id == current_activity_id:
            current = activity_id
        elif (semantic, start_at) in anchors:
            protected.append(activity_id)
        else:
            mutable.append(activity_id)
    return ExecutionPartition(tuple(terminal), current, tuple(protected), tuple(mutable))


def _json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value


def _capability_candidate_fit(
    preferences: Iterable[Any], meta: dict[str, Any], tags: set[str]
) -> tuple[bool, float, tuple[str, ...]]:
    """Apply capability constraints to ranking without inventing evidence."""

    score = 0.0
    reasons: list[str] = []
    accessibility = meta.get("accessibility") or meta.get("accessibility_evidence")
    for item in preferences:
        if str(getattr(item, "category", "")) != "capability":
            continue
        code = str(getattr(item, "preference_key", "")).upper()
        params = _json(getattr(item, "value_json", "{}"), {})
        if not isinstance(params, dict):
            params = {}
        severity = str(params.get("severity") or getattr(item, "severity", "SOFT")).upper()
        if code in {"STEP_FREE_REQUIRED", "AVOID_STAIRS"}:
            state = accessibility_state(accessibility)
            if severity == "HARD" and state != "ACCESSIBILITY_VERIFIED":
                return False, 0.0, ("ACCESSIBILITY_EVIDENCE_REQUIRED",)
            if state == "ACCESSIBILITY_VERIFIED":
                score += 1.0
                reasons.append("ACCESSIBILITY_VERIFIED")
        elif code == "MAX_WALKING_PER_LEG_M":
            limit = params.get("max_m")
            distance = meta.get("walking_distance_m", meta.get("distance_m"))
            if severity == "HARD":
                try:
                    if distance is None:
                        return False, 0.0, ("WALKING_EVIDENCE_REQUIRED",)
                    if int(distance) > int(limit):
                        return False, 0.0, ("MAX_WALKING_PER_LEG_EXCEEDED",)
                    score += 1.0
                except (TypeError, ValueError):
                    return False, 0.0, ("WALKING_EVIDENCE_REQUIRED",)
        elif code == "INDOOR_PREFERRED" and "indoor" in tags:
            score += 0.25
            reasons.append("INDOOR_PREFERRED")
        elif code in {"QUIET_ENVIRONMENT", "SENSORY_LOW_STIMULATION"} and (
            "quiet" in tags or "low-stimulation" in tags or "sensory-friendly" in tags
        ):
            score += 0.25
            reasons.append("LOW_STIMULATION_PREFERRED")
    return True, score, tuple(reasons)


#: Decimal places used when comparing coordinates.  ~5 places is about one
#: metre, which is finer than any two distinct venues are ever recorded.
_COORD_QUANTUM = 5


def _coordinates(place: Any) -> tuple[float, float] | None:
    try:
        return (
            round(float(getattr(place, "latitude")), _COORD_QUANTUM),
            round(float(getattr(place, "longitude")), _COORD_QUANTUM),
        )
    except (TypeError, ValueError, AttributeError):
        return None


def _identity_tokens(place: Any) -> set[str]:
    """Opaque identifiers that name the physical venue behind a Place row.

    A domain wrapper and the provider row it wraps are *different* Place rows
    with different ``id`` values, so comparing ids alone cannot tell that they
    are one venue.  The wrapper stores the provider identity inside its
    ``external_id`` (``CN-XIAMEN:real-place-<hex>``), so tokenising both rows'
    identifiers recovers the shared identity.  Short human labels such as a
    city code are deliberately ignored: only tokens that carry a digit and are
    long enough to be machine identifiers can name a venue.
    """

    tokens: set[str] = set()
    raw_id = str(getattr(place, "id", "") or "")
    if raw_id:
        tokens.add(raw_id)
    raw = str(getattr(place, "external_id", "") or "")
    for separator in (":", "/", "|", ",", "#"):
        raw = raw.replace(separator, " ")
    for token in raw.split():
        if len(token) >= 8 and any(character.isdigit() for character in token):
            tokens.add(token)
    return tokens


def is_same_physical_venue(left: Any, right: Any) -> bool:
    """Whether two Place rows describe one and the same real-world venue.

    Used to keep a closed venue out of its own replacement family.  A domain
    wrapper row and the provider row it wraps have different ids but identical
    coordinates and cross-referencing identifiers; treating them as different
    places let a replan "replace" a closed restaurant with that same
    restaurant under a new id, so the plan looked recovered while the traveller
    was still sent to a closed venue.
    """

    if left is None or right is None:
        return False
    if str(getattr(left, "id", "")) == str(getattr(right, "id", "")):
        return True
    left_coordinates = _coordinates(left)
    right_coordinates = _coordinates(right)
    if left_coordinates is not None and left_coordinates == right_coordinates:
        return True
    return bool(_identity_tokens(left) & _identity_tokens(right))


def choose_closure_replacement(
    *,
    affected_place: Any,
    candidate_places: Iterable[Any],
    occupied_place_ids: set[str],
    max_duration_min: int,
) -> ReplacementChoice | None:
    """Choose one deterministic same-slot replacement for a closed flexible place.

    This is a mock candidate-family generator, not the feasibility authority.
    The returned candidate must still pass the shared deterministic gate.
    """

    choices = rank_closure_replacements(
        affected_place=affected_place,
        candidate_places=candidate_places,
        occupied_place_ids=occupied_place_ids,
        max_duration_min=max_duration_min,
    )
    return choices[0] if choices else None


def rank_closure_replacements(
    *,
    affected_place: Any,
    candidate_places: Iterable[Any],
    occupied_place_ids: set[str],
    max_duration_min: int,
    traveler_preferences: Iterable[Any] = (),
    occupied_places: Iterable[Any] | None = None,
) -> tuple[ReplacementChoice, ...]:
    """Return every distinct same-slot replacement in deterministic rank order."""

    traveler_preferences = list(traveler_preferences)
    affected_tags = set(_json(getattr(affected_place, "tags_json", "[]"), []))
    occupied_places = list(occupied_places or ())
    ranked: list[tuple[tuple[Any, ...], ReplacementChoice]] = []
    for place in candidate_places:
        place_id = str(place.id)
        # A closed venue must never be offered as its own replacement, and a
        # venue already used elsewhere in the plan must not be reused.  Both
        # checks are physical, because one venue can be stored under several
        # id namespaces (domain wrapper vs provider row).
        if place_id in occupied_place_ids or is_same_physical_venue(place, affected_place):
            continue
        if any(is_same_physical_venue(place, other) for other in occupied_places):
            continue
        meta = _json(getattr(place, "metadata_json", "{}"), {})
        tags = set(_json(getattr(place, "tags_json", "[]"), []))
        duration = int(meta.get("duration_min", 60))
        cost_evidence = meta.get("cost_evidence") or {}
        if (
            str(cost_evidence.get("status")) in {"KNOWN", "ESTIMATED"}
            and cost_evidence.get("amount_minor") is not None
        ):
            cost = int(cost_evidence["amount_minor"])
        else:
            cost = int(meta.get("cost_minor", 0))
        if duration <= 0 or duration > max_duration_min:
            continue
        capability_ok, capability_fit, capability_reasons = _capability_candidate_fit(
            traveler_preferences, meta, tags
        )
        if not capability_ok:
            continue
        overlap = len(affected_tags & tags)
        indoor = 1 if "indoor" in tags else 0
        choice = ReplacementChoice(
            place_id=place_id,
            title=str(place.name),
            duration_min=duration,
            cost_minor=cost,
            reason_codes=(
                "DISRUPTED_ACTIVITY_REPLACED",
                "MINIMAL_SCHEDULE_CHANGE",
                *(("INDOOR_ALTERNATIVE",) if indoor else ()),
                *capability_reasons,
            ),
        )
        preference_fit = verified_interest_preference_fit(traveler_preferences, candidate_tags=tags)
        # Highest tag overlap, then indoor, then lower cost, then stable ID.
        rank = (
            -overlap,
            -indoor,
            -(0.5 if preference_fit is None else preference_fit) - capability_fit,
            cost,
            place_id,
        )
        ranked.append((rank, choice))
    ranked.sort(key=lambda item: item[0])
    return tuple(choice for _, choice in ranked)
