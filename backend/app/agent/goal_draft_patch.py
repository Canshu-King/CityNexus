"""Narrow, task-local replacement of one DRAFT itinerary time block."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import HTTPException

from app.agent.goal_artifacts import empty_draft, normalize_draft


_TIME_OF_DAY = frozenset({"morning", "afternoon", "evening", "flexible"})
_MAX_SLOTS_PER_DAY = 6


def replace_draft_slots(
    journey,
    task: dict[str, Any],
    *,
    date: str,
    time_of_day: str,
    slots: list[dict[str, Any]],
) -> dict[str, Any]:
    """Replace one date/time block while preserving every other slot verbatim.

    The shared normalizer validates only the incoming block, including researched
    Place scope and region-conflict checks. Existing slots are deep-copied instead
    of being round-tripped through the model tool schema.
    """
    if not isinstance(date, str) or not date:
        raise HTTPException(422, "DRAFT_DATE_NOT_FOUND")
    if not isinstance(time_of_day, str) or time_of_day not in _TIME_OF_DAY:
        raise HTTPException(422, "DRAFT_TIME_OF_DAY_INVALID")
    if not isinstance(slots, list) or len(slots) > _MAX_SLOTS_PER_DAY:
        raise HTTPException(422, "DRAFT_SLOTS_INVALID")

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

    preserved_slots = [deepcopy(slot) for slot in current_slots if not belongs_to_block(slot)]
    if len(preserved_slots) + len(slots) > _MAX_SLOTS_PER_DAY:
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

    first_replaced = next(
        (index for index, slot in enumerate(current_slots) if belongs_to_block(slot)),
        None,
    )
    if first_replaced is None:
        merged_slots = [deepcopy(slot) for slot in current_slots] + replacement_slots
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
        merged_slots = prefix + replacement_slots + suffix

    result = deepcopy(current)
    target_day = next(day for day in result["days"] if isinstance(day, dict) and day.get("date") == date)
    target_day["slots"] = merged_slots
    try:
        result["revision"] = int(current.get("revision", 0)) + 1
    except (TypeError, ValueError):
        raise HTTPException(422, "DRAFT_REVISION_INVALID") from None
    return result


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
                "Send the full replacement block; all other dates and time blocks are preserved. "
                "The final day may contain at most six slots. This does not create or activate a formal plan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "An existing draft date within the Journey."},
                    "time_of_day": {"type": "string", "enum": sorted(_TIME_OF_DAY)},
                    "slots": {"type": "array", "maxItems": _MAX_SLOTS_PER_DAY, "items": slot},
                },
                "required": ["date", "time_of_day", "slots"],
                "additionalProperties": False,
            },
        },
    }


# Descriptive alias retained for callers that prefer the operation name.
replace_draft_slots_tool_definition = draft_patch_definition
