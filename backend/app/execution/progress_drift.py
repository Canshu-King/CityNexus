"""Server-owned progress-drift semantics for the continuous Journey Operator.

This module derives drift only from authoritative execution milestones. It does
not mutate plans, create Events, or choose a recovery strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


_AUTHORITATIVE_EXECUTION = {
    "OPERATOR_CONFIRMED_EXECUTION",
    "DEVICE_LOCATION_VERIFIED_EXECUTION",
}


@dataclass(frozen=True)
class ProgressDrift:
    drift_min: int
    planned_at: str
    actual_at: str
    truth_kind: str
    authoritative: bool


@dataclass(frozen=True)
class ProgressRiskDecision:
    state: str
    material: bool
    reason: str
    remaining_slack_min: int | None


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("DRIFT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
    return parsed.astimezone(timezone.utc)


def drift_from_milestone(
    *,
    planned_at: str,
    actual_at: str,
    truth_kind: str,
) -> ProgressDrift:
    planned = _aware(planned_at)
    actual = _aware(actual_at)
    drift_min = int((actual - planned).total_seconds() // 60)
    kind = str(truth_kind or "").upper()
    return ProgressDrift(
        drift_min=drift_min,
        planned_at=planned.isoformat(),
        actual_at=actual.isoformat(),
        truth_kind=kind,
        authoritative=kind in _AUTHORITATIVE_EXECUTION,
    )


def classify_progress_risk(
    *,
    drift: ProgressDrift,
    protected_commitment: bool,
    slack_before_min: int | None,
    safety_buffer_min: int = 5,
    route_grounded: bool = True,
    commitment_contested: bool = False,
) -> ProgressRiskDecision:
    """Classify the consequence of grounded execution drift.

    slack_before_min is the server-derived absorbable schedule slack before
    applying this real execution drift. Unknown mobility or contested
    commitment truth prevents a precise risk conclusion.
    """

    if not drift.authoritative:
        return ProgressRiskDecision(
            state="UNKNOWN_PROGRESS",
            material=False,
            reason="EXECUTION_MILESTONE_NOT_AUTHORITATIVE",
            remaining_slack_min=None,
        )

    if commitment_contested:
        return ProgressRiskDecision(
            state="REALITY_CONTESTED",
            material=False,
            reason="DOWNSTREAM_COMMITMENT_TRUTH_CONTESTED",
            remaining_slack_min=None,
        )

    if not route_grounded or slack_before_min is None:
        return ProgressRiskDecision(
            state="ROUTE_UNKNOWN",
            material=False,
            reason="DOWNSTREAM_SLACK_NOT_GROUNDED",
            remaining_slack_min=None,
        )

    remaining = int(slack_before_min) - max(0, int(drift.drift_min))

    if drift.drift_min < 0:
        return ProgressRiskDecision(
            state="AHEAD",
            material=False,
            reason="EXECUTION_AHEAD_OF_PLAN",
            remaining_slack_min=int(slack_before_min),
        )

    if drift.drift_min == 0:
        return ProgressRiskDecision(
            state="ON_SCHEDULE",
            material=False,
            reason="EXECUTION_MATCHES_PLAN",
            remaining_slack_min=int(slack_before_min),
        )

    if protected_commitment and remaining < int(safety_buffer_min):
        return ProgressRiskDecision(
            state="COMMITMENT_AT_RISK",
            material=True,
            reason="PROTECTED_COMMITMENT_SLACK_BELOW_SAFETY_BUFFER",
            remaining_slack_min=remaining,
        )

    if remaining < 0:
        return ProgressRiskDecision(
            state="RECOVERABLE_DRIFT",
            material=True,
            reason="NEXT_SCHEDULE_WINDOW_NO_LONGER_FITS",
            remaining_slack_min=remaining,
        )

    if remaining < int(safety_buffer_min) * 2:
        return ProgressRiskDecision(
            state="RECOVERABLE_DRIFT",
            material=False,
            reason="LOW_REMAINING_SLACK",
            remaining_slack_min=remaining,
        )

    return ProgressRiskDecision(
        state="MINOR_DRIFT",
        material=False,
        reason="DRIFT_ABSORBED_BY_REMAINING_SLACK",
        remaining_slack_min=remaining,
    )


def execution_drift_fingerprint(
    *,
    journey_id: str,
    activity_id: str,
    milestone: str,
    actual_at: str,
    affected_target_id: str | None,
) -> str:
    """Stable semantic identity for a material drift generation."""
    import hashlib
    import json

    payload: dict[str, Any] = {
        "journey_id": str(journey_id),
        "activity_id": str(activity_id),
        "milestone": str(milestone).upper(),
        "actual_at": _aware(actual_at).isoformat(),
        "affected_target_id": str(affected_target_id or ""),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
