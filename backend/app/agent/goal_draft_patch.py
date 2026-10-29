"""Narrow, task-local replacement of one DRAFT itinerary time block."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, time
import re
from typing import Any

from fastapi import HTTPException

from app.agent.goal_artifacts import empty_draft, normalize_draft


_TIME_OF_DAY = frozenset({"morning", "afternoon", "evening", "flexible"})
_MAX_SLOTS_PER_DAY = 6
_HHMM = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_PROTECTED_MARKER_KEYS = ("reservation_id", "booking_id", "commitment_ids", "protected_commitment_ids")
_PROTECTED_ROLES = frozenset({"ARRIVAL", "DEPARTURE", "CHECK_IN", "CHECK_OUT", "LUGGAGE_DROP"})


def protected_draft_slot_markers(slot: Any) -> dict[str, Any]:
    """Return explicit structured protection markers; never infer protection from a title."""
    if not isinstance(slot, dict):
        return {}
    markers: dict[str, Any] = {}
    sources = [(None, slot)]
    metadata = slot.get("metadata")
    if isinstance(metadata, dict):
        sources.append(("metadata", metadata))
    for prefix, source in sources:
        for key in ("locked", "protected", *_PROTECTED_MARKER_KEYS):
            value = source.get(key)
            if value is True or (key not in {"locked", "protected"} and value):
                target_key = f"{prefix}.{key}" if prefix else key
                markers[target_key] = deepcopy(value)
        role = str(source.get("role") or "")
        if role in _PROTECTED_ROLES:
            target_key = f"{prefix}.role" if prefix else "role"
            markers[target_key] = role
    return markers


def is_protected_draft_slot(slot: Any) -> bool:
    return bool(protected_draft_slot_markers(slot))


def _hhmm_from_slot(slot: dict[str, Any]) -> str | None:
    for key in ("start_time", "start_at", "scheduled_start"):
        raw = slot.get(key)
        if not isinstance(raw, str):
            continue
        value = raw.strip()
        try:
            parsed = datetime.fromisoformat(value) if "T" in value else time.fromisoformat(value)
        except ValueError:
            continue
        return parsed.strftime("%H:%M")
    return None


def _prepared_slot_start(
    task: dict[str, Any], current: dict[str, Any], day_index: int, slot_index: int
) -> str | None:
    prepared = task.get("prepared_plan")
    if not isinstance(prepared, dict):
        return None
    result = prepared.get("result")
    if not isinstance(result, dict) or result.get("draft_revision") != current.get("revision"):
        return None
    schedule = prepared.get("schedule")
    if not isinstance(schedule, list):
        return None
    for row in schedule:
        if (isinstance(row, dict) and row.get("day_index") == day_index
                and row.get("slot_index") == slot_index):
            start_time = row.get("start_time")
            return start_time if isinstance(start_time, str) and _HHMM.fullmatch(start_time) else None
    return None


def replace_draft_slots(
    journey,
    task: dict[str, Any],
    *,
    date: str,
    time_of_day: str,
    slots: list[dict[str, Any]],
    start_not_before: str | None = None,
) -> dict[str, Any]:
    """Replace editable slots in one date/time block, preserving protected slots and all other blocks.

    The shared normalizer validates only the incoming block, including researched
    Place scope and region-conflict checks. Existing slots are deep-copied instead
    of being round-tripped through the model tool schema. An optional lower bound
    is persisted on this exact date/time block in the draft artifact.
    """
    if not isinstance(date, str) or not date:
        raise HTTPException(422, "DRAFT_DATE_NOT_FOUND")
    if not isinstance(time_of_day, str) or time_of_day not in _TIME_OF_DAY:
        raise HTTPException(422, "DRAFT_TIME_OF_DAY_INVALID")
    if not isinstance(slots, list) or len(slots) > _MAX_SLOTS_PER_DAY:
        raise HTTPException(422, "DRAFT_SLOTS_INVALID")
    if start_not_before is not None and (
        not isinstance(start_not_before, str) or not _HHMM.fullmatch(start_not_before)
    ):
        raise HTTPException(422, "DRAFT_START_NOT_BEFORE_INVALID")

    current = task.get("draft_artifact")
    if not isinstance(current, dict):
        current = empty_draft(journey)
    current_days = current.get("days")
    if not isinstance(current_days, list):
        raise HTTPException(422, "DRAFT_DAYS_INVALID")

    matching_days = [day for day in current_days if isinstance(day, dict) and day.get("date") == date]
    if len(matching_days) != 1:
        raise HTTPException(422, "DRAFT_DATE_NOT_FOUND")
    current_day = matching_days[0]
    day_index = next(index for index, day in enumerate(current_days) if day is current_day)
    current_slots = current_day.get("slots")
    if not isinstance(current_slots, list):
        raise HTTPException(422, "DRAFT_SLOTS_INVALID")

    for slot in slots:
        if not isinstance(slot, dict) or slot.get("time_of_day") != time_of_day:
            raise HTTPException(422, "DRAFT_SLOT_INVALID")

    def belongs_to_block(slot: Any) -> bool:
        return isinstance(slot, dict) and slot.get("time_of_day") == time_of_day

    if not any(belongs_to_block(slot) for slot in current_slots):
        raise HTTPException(422, "DRAFT_TIME_OF_DAY_NOT_FOUND")

    if start_not_before is not None:
        protected_conflicts = []
        for slot_index, slot in enumerate(current_slots):
            if not belongs_to_block(slot) or not is_protected_draft_slot(slot):
                continue
            start_time = _hhmm_from_slot(slot) or _prepared_slot_start(task, current, day_index, slot_index)
            if start_time is not None and start_time < start_not_before:
                protected_conflicts.append({
                    "date": date,
                    "time_of_day": time_of_day,
                    "title": str(slot.get("title") or "")[:160],
                    "start_time": start_time,
                    "start_not_before": start_not_before,
                    "protected_markers": protected_draft_slot_markers(slot),
                })
        if protected_conflicts:
            return {
                "status": "NEEDS_USER_CHOICE",
                "reason_code": "PROTECTED_ACTIVITY_BEFORE_START_NOT_BEFORE",
                "date": date,
                "time_of_day": time_of_day,
                "start_not_before": start_not_before,
                "conflicts": protected_conflicts,
            }

    preserved_slots = [deepcopy(slot) for slot in current_slots if not belongs_to_block(slot)]
    protected_slots = [slot for slot in current_slots if belongs_to_block(slot) and is_protected_draft_slot(slot)]
    if len(preserved_slots) + len(protected_slots) + len(slots) > _MAX_SLOTS_PER_DAY:
        raise HTTPException(422, "DRAFT_SLOTS_INVALID")

    # normalize_draft enforces journey date, slot fields, task-owned Place IDs,
    # and region conflict rules for the replacement area only.
    normalized = normalize_draft(
        journey,
        task,
        [{"date": date, "slots": deepcopy(slots)}],
        author="MODEL_SUGGESTION",
    )
    normalized_day = next(day for day in normalized["days"] if day["date"] == date)
    replacement_slots = normalized_day["slots"]

    replacement_block = []
    replacement_index = 0
    for slot in current_slots:
        if not belongs_to_block(slot):
            continue
        if is_protected_draft_slot(slot):
            replacement_block.append(deepcopy(slot))
        elif replacement_index < len(replacement_slots):
            replacement_block.append(replacement_slots[replacement_index])
            replacement_index += 1
    replacement_block.extend(replacement_slots[replacement_index:])

    first_replaced = next(
        (index for index, slot in enumerate(current_slots) if belongs_to_block(slot)),
        None,
    )
    if first_replaced is None:
        merged_slots = [deepcopy(slot) for slot in current_slots] + replacement_block
    else:
        prefix = [
            deepcopy(slot)
            for index, slot in enumerate(current_slots[:first_replaced])
            if not belongs_to_block(slot)
        ]
        suffix = [
            deepcopy(slot)
            for slot in current_slots[first_replaced + 1 :]
            if not belongs_to_block(slot)
        ]
        merged_slots = prefix + replacement_block + suffix

    result = deepcopy(current)
    target_day = next(day for day in result["days"] if isinstance(day, dict) and day.get("date") == date)
    target_day["slots"] = merged_slots
    if start_not_before is not None:
        date_constraints = result.get("date_constraints")
        if date_constraints is None:
            date_constraints = {}
            result["date_constraints"] = date_constraints
        if not isinstance(date_constraints, dict):
            raise HTTPException(422, "DRAFT_DATE_CONSTRAINTS_INVALID")
        block_constraints = date_constraints.get(date)
        if block_constraints is None:
            block_constraints = {}
            date_constraints[date] = block_constraints
        if not isinstance(block_constraints, dict):
            raise HTTPException(422, "DRAFT_DATE_CONSTRAINTS_INVALID")
        current_constraint = block_constraints.get(time_of_day)
        if current_constraint is None:
            current_constraint = {}
        if not isinstance(current_constraint, dict):
            raise HTTPException(422, "DRAFT_DATE_CONSTRAINTS_INVALID")
        block_constraints[time_of_day] = {
            **current_constraint,
            "start_not_before": start_not_before,
        }
    try:
        result["revision"] = int(current.get("revision", 0)) + 1
    except (TypeError, ValueError):
        raise HTTPException(422, "DRAFT_REVISION_INVALID") from None
    return result


def _slot_booking_identities(slot: Any) -> set[tuple[str, str]]:
    """Extract only explicit reservation/booking/commitment IDs from a stored slot."""
    identities: set[tuple[str, str]] = set()
    for marker, value in protected_draft_slot_markers(slot).items():
        key = marker.rsplit(".", 1)[-1]
        if key not in _PROTECTED_MARKER_KEYS:
            continue
        values = value if key in {"commitment_ids", "protected_commitment_ids"} and isinstance(
            value, (list, tuple, set)
        ) else [value]
        for item in values:
            if isinstance(item, (str, int)) and not isinstance(item, bool) and str(item).strip():
                identities.add((key, str(item)))
    return identities


def _slot_role_identities(slot: Any) -> set[str]:
    return {
        str(value)
        for marker, value in protected_draft_slot_markers(slot).items()
        if marker.rsplit(".", 1)[-1] == "role" and str(value) in _PROTECTED_ROLES
    }


def _slot_boolean_protections(slot: Any) -> frozenset[str]:
    return frozenset(
        marker.rsplit(".", 1)[-1]
        for marker, value in protected_draft_slot_markers(slot).items()
        if marker.rsplit(".", 1)[-1] in {"locked", "protected"} and value is True
    )


def _raise_protected_draft_choice(conflicts: list[dict[str, Any]]) -> None:
    reason_code = "DRAFT_PROTECTED_ACTIVITY_REQUIRES_USER_CHOICE"
    refused = HTTPException(status_code=409, detail=reason_code)
    refused.reason_code = reason_code  # type: ignore[attr-defined]
    refused.error_details = {  # type: ignore[attr-defined]
        "choice_required": True,
        "conflicts": conflicts,
    }
    raise refused


def reconcile_user_draft(journey, task: dict[str, Any], days: Any) -> dict[str, Any]:
    """Normalize a full USER save while retaining server-owned constraints and protections.

    Booking identity is matched only through explicit structured IDs. Titles and
    other presentation text are never used to infer that two activities are the
    same reservation. A booked activity that is omitted or moved must be resolved
    by the traveller before the full draft can be saved.
    """
    current = task.get("draft_artifact")
    if not isinstance(current, dict):
        current = empty_draft(journey)
    normalized = normalize_draft(journey, task, days, author="USER")
    if "date_constraints" in current:
        normalized["date_constraints"] = deepcopy(current["date_constraints"])

    current_days = current.get("days")
    if not isinstance(current_days, list):
        return normalized

    incoming_slots: list[dict[str, Any]] = []
    for day in days:
        if not isinstance(day, dict) or not isinstance(day.get("slots"), list):
            continue
        for slot_index, slot in enumerate(day["slots"]):
            if not isinstance(slot, dict):
                continue
            incoming_slots.append({
                "date": day.get("date"),
                "time_of_day": slot.get("time_of_day", "flexible"),
                "slot_index": slot_index,
                "slot": slot,
                "booking_ids": _slot_booking_identities(slot),
                "roles": _slot_role_identities(slot),
                "boolean_protections": _slot_boolean_protections(slot),
            })

    protected_records: list[dict[str, Any]] = []
    for day in current_days:
        if not isinstance(day, dict) or not isinstance(day.get("slots"), list):
            continue
        for slot_index, slot in enumerate(day["slots"]):
            markers = protected_draft_slot_markers(slot)
            if not markers:
                continue
            protected_records.append({
                "date": day.get("date"),
                "time_of_day": slot.get("time_of_day") if isinstance(slot, dict) else None,
                "slot_index": slot_index,
                "slot": slot,
                "markers": markers,
                "booking_ids": _slot_booking_identities(slot),
                "roles": _slot_role_identities(slot),
                "boolean_protections": _slot_boolean_protections(slot),
            })

    conflicts: list[dict[str, Any]] = []
    replacements: dict[tuple[str, int], dict[str, Any]] = {}
    matched_records: set[tuple[Any, int]] = set()
    claimed_incoming: dict[tuple[Any, int], tuple[Any, int]] = {}

    def location(record: dict[str, Any]) -> dict[str, Any]:
        return {"date": record.get("date"), "time_of_day": record.get("time_of_day")}

    def conflict_record(record: dict[str, Any], kind: str, requested: Any = None) -> dict[str, Any]:
        return {
            "kind": kind,
            **location(record),
            "title": str(record["slot"].get("title") or "")[:160]
            if isinstance(record.get("slot"), dict) else "",
            "protected_markers": deepcopy(record["markers"]),
            "requested": requested,
            "choice_required": True,
        }

    # A booking's explicit ID is the only acceptable identity for a full-save
    # reconciliation. Missing and duplicate IDs are surfaced before any mutation.
    for record in protected_records:
        if not record["booking_ids"]:
            continue
        hits = [
            item for item in incoming_slots
            if record["booking_ids"] & item["booking_ids"]
        ]
        if not hits:
            conflicts.append(conflict_record(record, "BOOKING_OMITTED"))
            continue
        if len(hits) != 1:
            conflicts.append(conflict_record(
                record,
                "BOOKING_DUPLICATED",
                [location(item) for item in hits],
            ))
            continue
        incoming = hits[0]
        incoming_key = (incoming["date"], incoming["slot_index"])
        record_key = (record["date"], record["slot_index"])
        if incoming_key in claimed_incoming:
            conflicts.append(conflict_record(
                record,
                "BOOKING_IDENTITY_AMBIGUOUS",
                location(incoming),
            ))
            continue
        claimed_incoming[incoming_key] = record_key
        if location(record) != location(incoming):
            conflicts.append(conflict_record(record, "BOOKING_MOVED", location(incoming)))
            continue
        replacements[incoming_key] = deepcopy(record["slot"])
        matched_records.add(record_key)

    # A lone locked/protected flag has no unique ID. Match only the same
    # structured flag in the same date/block, without looking at the title.
    # This keeps an ordinary full save from duplicating a returned locked row.
    for record in protected_records:
        if record["booking_ids"] or record["roles"] or not record["boolean_protections"]:
            continue
        record_key = (record["date"], record["slot_index"])
        same_block_hits = [
            item for item in incoming_slots
            if item["boolean_protections"] == record["boolean_protections"]
            and location(record) == location(item)
            and (item["date"], item["slot_index"]) not in claimed_incoming
        ]
        if same_block_hits:
            incoming = same_block_hits[0]
            incoming_key = (incoming["date"], incoming["slot_index"])
            claimed_incoming[incoming_key] = record_key
            replacements[incoming_key] = deepcopy(record["slot"])
            matched_records.add(record_key)
            continue

        current_same_marker = [
            item for item in protected_records
            if item["boolean_protections"] == record["boolean_protections"]
            and not item["booking_ids"] and not item["roles"]
        ]
        moved_hits = [
            item for item in incoming_slots
            if item["boolean_protections"] == record["boolean_protections"]
            and (item["date"], item["slot_index"]) not in claimed_incoming
        ]
        if len(current_same_marker) == 1 and len(moved_hits) == 1:
            conflicts.append(conflict_record(record, "PROTECTED_MARKER_MOVED", location(moved_hits[0])))

    # Explicit role markers (arrival/check-in/etc.) are protected facts too.
    # If echoed at a different date/block, ask instead of silently relocating them.
    role_counts: dict[str, int] = {}
    for record in protected_records:
        if record["booking_ids"]:
            continue
        for role in record["roles"]:
            role_counts[role] = role_counts.get(role, 0) + 1
    for record in protected_records:
        if record["booking_ids"] or len(record["roles"]) != 1:
            continue
        role = next(iter(record["roles"]))
        if role_counts.get(role) != 1:
            continue
        hits = [item for item in incoming_slots if role in item["roles"]]
        if not hits:
            continue  # preserve it at its original location below
        if len(hits) != 1:
            conflicts.append(conflict_record(
                record,
                "PROTECTED_ROLE_DUPLICATED",
                [location(item) for item in hits],
            ))
            continue
        incoming = hits[0]
        incoming_key = (incoming["date"], incoming["slot_index"])
        record_key = (record["date"], record["slot_index"])
        if incoming_key in claimed_incoming:
            conflicts.append(conflict_record(
                record,
                "PROTECTED_ROLE_IDENTITY_AMBIGUOUS",
                location(incoming),
            ))
            continue
        if location(record) != location(incoming):
            conflicts.append(conflict_record(record, "PROTECTED_ROLE_MOVED", location(incoming)))
            continue
        replacements[incoming_key] = deepcopy(record["slot"])
        matched_records.add(record_key)

    if conflicts:
        _raise_protected_draft_choice(conflicts)

    normalized_days = {day["date"]: day for day in normalized["days"]}
    for (date, slot_index), canonical_slot in replacements.items():
        target_day = normalized_days.get(date)
        if target_day is None or slot_index >= len(target_day["slots"]):
            continue
        target_day["slots"][slot_index] = deepcopy(canonical_slot)

    # Marker-only protections have no unique identity. Preserve the canonical
    # server-owned slot at its original date/block/index; never copy new markers
    # from the incoming payload into the normalized artifact.
    for record in protected_records:
        record_key = (record["date"], record["slot_index"])
        if record_key in matched_records:
            continue
        target_day = normalized_days.get(record["date"])
        if target_day is None:
            _raise_protected_draft_choice([conflict_record(record, "PROTECTED_DATE_UNAVAILABLE")])
        slots = target_day["slots"]
        slots.insert(min(record["slot_index"], len(slots)), deepcopy(record["slot"]))

    if any(len(day["slots"]) > _MAX_SLOTS_PER_DAY for day in normalized["days"]):
        raise HTTPException(422, "DRAFT_SLOTS_INVALID")
    return normalized


def draft_patch_definition() -> dict[str, Any]:
    """OpenAI Chat Completions function schema for the narrow patch tool."""
    slot = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "maxLength": 160},
            "time_of_day": {"type": "string", "enum": sorted(_TIME_OF_DAY)},
            "place_id": {
                "type": "string",
                "description": "ID returned by this task's research; omit for a general suggestion or todo.",
            },
            "notes": {"type": "string", "maxLength": 500},
        },
        "required": ["title", "time_of_day"],
        "additionalProperties": False,
    }
    return {
        "type": "function",
        "function": {
            "name": "replace_draft_slots",
            "description": (
                "Replace only one existing date and time-of-day block in the current editable draft. "
                "Send replacement slots for editable activities only; the server carries forward existing "
                "slots with structured locked, reservation, or commitment markers. All other dates and "
                "time blocks are preserved. An optional start_not_before value applies only to this block. "
                "If a protected slot has a known earlier time, the result requires the traveller to choose; "
                "do not claim that the conflict was resolved. "
                "The final day may contain at most six slots. This does not create or activate a formal plan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "An existing draft date within the Journey."},
                    "time_of_day": {"type": "string", "enum": sorted(_TIME_OF_DAY)},
                    "start_not_before": {
                        "type": "string",
                        "pattern": r"^(?:[01]\d|2[0-3]):[0-5]\d$",
                        "description": "Optional earliest start time for editable activities in only this date/time block.",
                    },
                    "slots": {"type": "array", "maxItems": _MAX_SLOTS_PER_DAY, "items": slot},
                },
                "required": ["date", "time_of_day", "slots"],
                "additionalProperties": False,
            },
        },
    }


# Descriptive alias retained for callers that prefer the operation name.
replace_draft_slots_tool_definition = draft_patch_definition
