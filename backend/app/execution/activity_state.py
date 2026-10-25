"""Native execution preconditions shared by HTTP and classroom execution."""

import json

from fastapi import HTTPException

from app.replanning.provider_snapshots import MobilitySnapshot


def require_subject(journey, activity):
    if journey.status != "ACTIVE" or not journey.active_plan_version_id:
        raise HTTPException(409, "journey must be ACTIVE")
    if activity is None or activity.plan_version_id != journey.active_plan_version_id:
        raise HTTPException(409, "activity is not on the active plan")
    if journey.current_activity_id != activity.id:
        raise HTTPException(409, "activity is not the current activity")


def require_transition(activity, target):
    allowed = {
        "EN_ROUTE": {"ACTIVE", "NOT_STARTED"},
        "ARRIVED": {"EN_ROUTE"},
        "IN_PROGRESS": {"ARRIVED"},
        "COMPLETED": {"IN_PROGRESS"},
    }
    predecessors = allowed.get(target, set())
    if activity.status not in predecessors:
        raise HTTPException(
            409,
            f"INVALID_ACTIVITY_TRANSITION:{activity.status}->{target}; expected={', '.join(sorted(predecessors)) or 'none'}",
        )


def require_departure_route(activity):
    override = json.loads(activity.metadata_json or "{}").get("execution_mobility_override")
    if not override:
        return
    try:
        snapshot = MobilitySnapshot.from_evidence(override.get("snapshot") or {})
        edge = override.get("actual_edge") or {}
        pair = (str(edge.get("origin_key") or ""), str(edge.get("destination_key") or ""))
        snapshot.hard_minutes(*pair)
        if snapshot.facts[pair].fact_quality != "LIVE_PROVIDER_CAPTURE":
            raise KeyError("not a live provider route")
    except (KeyError, TypeError, ValueError):
        raise HTTPException(409, "DEPART_BLOCKED_MISSING_LIVE_EXECUTION_MOBILITY")


def require_simulated_transition(session, journey, activity, target):
    require_subject(journey, activity)
    require_transition(activity, target)
    from app.execution.group_recovery_followthrough import active_group_recovery_spend

    applied = active_group_recovery_spend(session, journey)
    if applied and str(applied[2].get("rendezvous_activity_id") or "") == activity.id:
        raise HTTPException(409, "GROUP_RECOVERY_REJOIN_REQUIRES_AUTHENTICATED_EXECUTION")
    if target == "EN_ROUTE":
        require_departure_route(activity)
