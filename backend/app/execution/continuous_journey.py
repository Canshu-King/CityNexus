"""Continuous Journey Day Operator projection.

This module is deliberately read-only. It turns existing execution truth,
presence, readiness and next-move facts into one traveller-facing day flow.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _aware(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def continuous_journey_state(
    *,
    journey_status: str,
    activity_status: str | None,
    presence_state: str | None,
    readiness_state: str | None,
    must_leave_by: str | None,
    activity_end_at: str | None,
    next_activity_id: str | None,
    operator_needs_attention: bool = False,
    now: datetime,
) -> dict[str, Any]:
    """Project the next human-facing milestone without creating execution truth."""

    if str(journey_status).upper() == "COMPLETED":
        return {
            "state": "DAY_COMPLETE",
            "recommended_action": "NONE",
            "can_confirm": False,
        }

    if operator_needs_attention:
        return {
            "state": "NEEDS_ATTENTION",
            "recommended_action": "REVIEW_OPERATOR",
            "can_confirm": False,
        }

    status = str(activity_status or "").upper()
    presence = str(presence_state or "").upper()
    readiness = str(readiness_state or "").upper()

    if status == "EN_ROUTE":
        if presence in {"NEAR_TARGET", "VERIFIED_AT_TARGET"}:
            return {
                "state": "ARRIVAL_READY",
                "recommended_action": "CONFIRM_ARRIVAL",
                "can_confirm": True,
            }
        return {
            "state": "ON_THE_WAY",
            "recommended_action": "CONTINUE_ROUTE",
            "can_confirm": True,
        }

    if status == "ARRIVED":
        return {
            "state": "READY_TO_BEGIN",
            "recommended_action": "CONFIRM_BEGIN",
            "can_confirm": True,
        }

    if status == "IN_PROGRESS":
        end_at = _aware(activity_end_at)
        if end_at is not None and now.astimezone(timezone.utc) >= end_at:
            return {
                "state": "READY_TO_COMPLETE",
                "recommended_action": "CONFIRM_COMPLETE",
                "can_confirm": True,
            }
        return {
            "state": "IN_ACTIVITY",
            "recommended_action": "CONTINUE_ACTIVITY",
            "can_confirm": True,
        }

    if status == "COMPLETED":
        if next_activity_id:
            return {
                "state": "BETWEEN_STOPS",
                "recommended_action": "PREPARE_NEXT_STOP",
                "can_confirm": False,
            }
        return {
            "state": "DAY_COMPLETE",
            "recommended_action": "NONE",
            "can_confirm": False,
        }

    leave_at = _aware(must_leave_by)
    if readiness == "BLOCKED":
        return {
            "state": "NEEDS_ATTENTION",
            "recommended_action": "CHECK_BLOCKER",
            "can_confirm": False,
        }
    if leave_at is not None and now.astimezone(timezone.utc) >= leave_at:
        return {
            "state": "LEAVE_NOW",
            "recommended_action": "CONFIRM_DEPARTURE",
            "can_confirm": True,
        }
    if readiness in {"READY", "READY_WITH_UNCERTAINTY", "ACTION_NEEDED", "NOT_DUE"}:
        return {
            "state": "PREPARING_TO_LEAVE",
            "recommended_action": "WAIT_OR_CHECK_ROUTE",
            "can_confirm": True,
        }

    return {
        "state": "NEXT_STOP_PREPARING",
        "recommended_action": "CHECK_NEXT_STEP",
        "can_confirm": False,
    }


def milestone_notification_key(
    *, journey_id: str, activity_id: str, state: str
) -> str:
    """Stable, human-milestone dedupe key."""
    return f"journey-flow:{journey_id}:{activity_id}:{str(state).upper()}"
