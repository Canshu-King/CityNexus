"""Pure, run-scoped itinerary activity coverage summaries.

This projection counts canonical place IDs already present on the supplied
active-plan activities. It does not look up or certify place/source evidence.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import datetime, tzinfo
from typing import Any
from zoneinfo import ZoneInfo


_TERMINAL_NON_COVERING = frozenset({"CANCELLED", "SKIPPED"})
_FREE_TIME_TYPES = frozenset({"FREE_TIME"})


def _value(activity: Any, key: str, default: Any = None) -> Any:
    if isinstance(activity, Mapping):
        return activity.get(key, default)
    return getattr(activity, key, default)


def _code(value: Any) -> str:
    value = getattr(value, "value", value)
    return str(value or "").strip().upper()


def _place_id(value: Any) -> str | None:
    if value is None:
        return None
    place_id = str(value).strip()
    return place_id or None


def _zone(value: str | tzinfo) -> tzinfo:
    if isinstance(value, str):
        return ZoneInfo(value)
    if isinstance(value, tzinfo):
        return value
    raise TypeError("journey_timezone must be an IANA timezone name or tzinfo")


def _local_date(value: Any, zone: tzinfo) -> str:
    if isinstance(value, datetime):
        stamp = value
    elif isinstance(value, str) and value.strip():
        raw = value.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            stamp = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError(f"invalid activity start_at: {value!r}") from exc
    else:
        raise ValueError("each activity must have a datetime start_at")

    # A naive timestamp from the existing Activity shape is a Journey-local
    # wall time. Aware timestamps are converted before grouping by calendar day.
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=zone)
    return stamp.astimezone(zone).date().isoformat()


def _has_place_required_gap(activity: Any) -> bool:
    raw = _value(activity, "metadata_json", {})
    if isinstance(raw, Mapping):
        metadata = raw
    elif isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            parsed = {}
        metadata = parsed if isinstance(parsed, Mapping) else {}
    else:
        metadata = {}

    gaps = metadata.get("preparation_gaps", ())
    if isinstance(gaps, str):
        gaps = (gaps,)
    if not isinstance(gaps, Iterable):
        return False
    return any(_code(gap) == "PLACE_REQUIRED" for gap in gaps)


def _is_placeholder(activity: Any, activity_type: str, place_id: str | None) -> bool:
    if place_id is not None:
        return False
    if activity_type in _FREE_TIME_TYPES:
        # A normal free-time block is not a missing station. Keep an explicitly
        # unresearched place slot visible when its preparation gap says so.
        return _has_place_required_gap(activity)
    return True


def _non_empty_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_iso_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        datetime.fromisoformat(raw)
    except ValueError:
        return False
    return True


def _execution_truth(activity: Any) -> Mapping[str, Any] | None:
    raw = _value(activity, "metadata_json", {})
    if isinstance(raw, Mapping):
        metadata = raw
    elif isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return None
        if not isinstance(parsed, Mapping):
            return None
        metadata = parsed
    else:
        return None
    truth = metadata.get("execution_truth")
    return truth if isinstance(truth, Mapping) else None


def _truth_matches_completion_history(
    truth: Mapping[str, Any],
    completion: Mapping[str, Any],
    *,
    run_id: str,
    run_sequence: int,
    run_actor_id: str,
) -> bool:
    sequence = completion.get("sequence")
    evidence = truth.get("evidence")
    evidence_sequence = evidence.get("sequence") if isinstance(evidence, Mapping) else None
    if (
        truth.get("kind") != "SIMULATED_STATE_TRANSITION"
        or truth.get("transition") != "COMPLETED"
        or truth.get("actor_type") != "TRAVELER"
        or _non_empty_text(truth.get("actor_id")) != run_actor_id
        or not isinstance(evidence, Mapping)
        or _non_empty_text(evidence.get("simulation_run_id")) != run_id
        or evidence.get("location_source") != "SIMULATED_GPS"
        or isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or sequence < 0
        or sequence > run_sequence
        or isinstance(evidence_sequence, bool)
        or not isinstance(evidence_sequence, int)
        or evidence_sequence != sequence
    ):
        return False

    virtual_now = completion.get("virtual_now")
    captured_at = truth.get("captured_at")
    if (
        not isinstance(virtual_now, str)
        or not isinstance(captured_at, str)
        or captured_at != virtual_now
        or not _is_iso_timestamp(virtual_now)
        or not _is_iso_timestamp(completion.get("recorded_at"))
        or not _is_iso_timestamp(evidence.get("recorded_at"))
    ):
        return False
    return True


def resolve_run_completed_activity_ids(
    *,
    run_id: str,
    run_sequence: int,
    run_actor_id: str,
    history: Iterable[Mapping[str, Any]],
    source_activities: Iterable[Any],
    active_activities: Iterable[Any],
) -> set[str]:
    """Keep native completion IDs and authenticate only copied active rows.

    ``source_activities`` are already scoped by the caller to this Journey's
    real-place activities whose IDs appear in both run state and completion
    history. Their IDs retain the existing direct coverage behavior. A copied
    activity in the active plan is added only when its complete execution truth
    matches an authenticated source row.
    """
    source_rows: dict[str, Any] = {}
    completed_ids: set[str] = set()
    for activity in source_activities or ():
        activity_id = _non_empty_text(_value(activity, "id"))
        if activity_id is None:
            continue
        completed_ids.add(activity_id)
        source_rows.setdefault(activity_id, activity)

    if (
        isinstance(run_sequence, bool)
        or not isinstance(run_sequence, int)
        or run_sequence < 0
    ):
        return completed_ids
    normalized_run_id = _non_empty_text(run_id)
    normalized_actor_id = _non_empty_text(run_actor_id)
    if normalized_run_id is None or normalized_actor_id is None:
        return completed_ids

    completions_by_activity_id: dict[str, list[Mapping[str, Any]]] = {}
    for item in history or ():
        if not isinstance(item, Mapping) or item.get("event") != "SIM_ACTIVITY_COMPLETED":
            continue
        activity_id = _non_empty_text(item.get("activity_id"))
        if activity_id is not None:
            completions_by_activity_id.setdefault(activity_id, []).append(item)

    authenticated_sources: dict[str, Mapping[str, Any]] = {}
    for activity_id, source in source_rows.items():
        if _code(_value(source, "status")) != "COMPLETED":
            continue
        truth = _execution_truth(source)
        if truth is None:
            continue
        if any(
            _truth_matches_completion_history(
                truth,
                completion,
                run_id=normalized_run_id,
                run_sequence=run_sequence,
                run_actor_id=normalized_actor_id,
            )
            for completion in completions_by_activity_id.get(activity_id, ())
        ):
            authenticated_sources[activity_id] = truth

    for active in active_activities or ():
        active_id = _non_empty_text(_value(active, "id"))
        if active_id is None or active_id in completed_ids:
            continue
        active_type = _code(_value(active, "activity_type"))
        active_place_id = _place_id(_value(active, "place_id"))
        active_start = _non_empty_text(_value(active, "start_at"))
        active_end = _non_empty_text(_value(active, "end_at"))
        if (
            _code(_value(active, "status")) != "COMPLETED"
            or not active_type
            or active_type in _FREE_TIME_TYPES
            or active_place_id is None
            or active_start is None
            or active_end is None
        ):
            continue
        active_truth = _execution_truth(active)
        if active_truth is None:
            continue
        for source_id, source_truth in authenticated_sources.items():
            source = source_rows[source_id]
            if (
                active_truth == source_truth
                and active_id != source_id
                and _code(_value(source, "activity_type")) == active_type
                and _place_id(_value(source, "place_id")) == active_place_id
                and _non_empty_text(_value(source, "start_at")) == active_start
                and _non_empty_text(_value(source, "end_at")) == active_end
            ):
                completed_ids.add(active_id)
                break

    return completed_ids


def summarize_activity_coverage(
    activities: Iterable[Any],
    completed_activity_ids: Iterable[Any],
    *,
    journey_timezone: str | tzinfo,
    target_places_per_day: int = 2,
    required_dates: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Summarize named-place coverage by Journey-local date.

    A named stop is a non-FREE_TIME activity with a canonical ``place_id``;
    duplicate activities for the same place count once. Run completions come
    only from ``completed_activity_ids``. A different activity already in
    ``COMPLETED`` status is reported as inherited state, never as run work.

    Null-place TODOs are reported as placeholders (including FREE_TIME slots
    explicitly marked with ``PLACE_REQUIRED``). They do not satisfy the named
    place target. SKIPPED and CANCELLED activities do not provide coverage.
    ``required_dates`` lets the caller include Journey-local dates with no
    activities at all. Callers may use the target gap as a UI hint without
    imposing a Journey-wide planning rule.
    """
    if isinstance(target_places_per_day, bool) or not isinstance(target_places_per_day, int):
        raise TypeError("target_places_per_day must be an integer")
    if target_places_per_day < 0:
        raise ValueError("target_places_per_day must be non-negative")

    zone = _zone(journey_timezone)
    run_ids = {
        str(activity_id).strip()
        for activity_id in (completed_activity_ids or ())
        if activity_id is not None and str(activity_id).strip()
    }

    days: dict[str, dict[str, Any]] = {
        activity_date: {
            "named": [],
            "run_completed": [],
            "inherited_completed": [],
            "placeholders": [],
        }
        for activity_date in required_dates
    }
    for activity in activities or ():
        activity_id_value = _value(activity, "id")
        if activity_id_value is None or not str(activity_id_value).strip():
            raise ValueError("each activity must have a non-empty id")
        activity_id = str(activity_id_value).strip()
        activity_date = _local_date(_value(activity, "start_at"), zone)
        activity_type = _code(_value(activity, "activity_type"))
        status = _code(_value(activity, "status"))
        place_id = _place_id(_value(activity, "place_id"))
        row = days.setdefault(
            activity_date,
            {
                "named": [],
                "run_completed": [],
                "inherited_completed": [],
                "placeholders": [],
            },
        )

        if status in _TERMINAL_NON_COVERING:
            continue
        if _is_placeholder(activity, activity_type, place_id):
            row["placeholders"].append(activity_id)
        if place_id is None or activity_type in _FREE_TIME_TYPES:
            continue
        row["named"].append(
            {
                "activity_id": activity_id,
                "place_id": place_id,
                "status": status,
                "run_completed": activity_id in run_ids,
            }
        )

    summaries: list[dict[str, Any]] = []
    for activity_date in sorted(days):
        row = days[activity_date]
        named = row["named"]
        run_place_ids = {
            item["place_id"] for item in named if item["run_completed"]
        }
        inherited = [
            item
            for item in named
            if item["status"] == "COMPLETED"
            and not item["run_completed"]
            and item["place_id"] not in run_place_ids
        ]
        run_completed = [item for item in named if item["run_completed"]]
        distinct_place_ids = list(dict.fromkeys(item["place_id"] for item in named))
        run_completed_place_ids = list(
            dict.fromkeys(item["place_id"] for item in run_completed)
        )
        inherited_place_ids = list(dict.fromkeys(item["place_id"] for item in inherited))

        summaries.append(
            {
                "date": activity_date,
                "distinct_place_count": len(distinct_place_ids),
                "distinct_place_ids": distinct_place_ids,
                "named_activity_ids": [item["activity_id"] for item in named],
                "run_completed_place_count": len(run_completed_place_ids),
                "run_completed_activity_ids": [
                    item["activity_id"] for item in run_completed
                ],
                "inherited_completed_place_count": len(inherited_place_ids),
                "inherited_completed_activity_ids": [
                    item["activity_id"] for item in inherited
                ],
                "placeholder_count": len(row["placeholders"]),
                "placeholder_activity_ids": list(dict.fromkeys(row["placeholders"])),
                "missing_for_target": max(
                    0, target_places_per_day - len(distinct_place_ids)
                ),
            }
        )
    return summaries
