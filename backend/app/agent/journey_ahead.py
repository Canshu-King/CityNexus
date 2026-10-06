"""Journey Ahead product projection over predictive resilience evidence.

This module does not create incidents or authority. It only classifies a
future-risk horizon into a traveller-facing preventive Operator state.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable


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


def actionable_future_risks(
    activity_risks: Iterable[dict[str, Any]],
    *,
    now: datetime,
) -> list[dict[str, Any]]:
    """Return grounded, still-future risks ordered by urgency then severity."""

    rows: list[dict[str, Any]] = []
    stamp = now.astimezone(timezone.utc)
    for item in activity_risks:
        start = _aware(item.get("start_at"))
        if start is None or start <= stamp:
            continue
        score = int(item.get("risk_score") or 0)
        grounded = bool(
            item.get("grounded") is True
            or str(item.get("authority") or "").upper() in {
                "PROVIDER_GROUNDED",
                "FROZEN_PROVIDER_EVIDENCE",
                "SYSTEM_DERIVED_PROVIDER_FACT",
            }
        )
        lead_minutes = int((start - stamp).total_seconds() // 60)
        rows.append(
            {
                **item,
                "risk_score": score,
                "lead_time_minutes": lead_minutes,
                "grounded": grounded,
            }
        )
    rows.sort(key=lambda item: (item["lead_time_minutes"], -item["risk_score"]))
    return rows


def journey_ahead_state(
    *,
    activity_risks: Iterable[dict[str, Any]],
    now: datetime,
    prevention_status: str | None = None,
    provider_degraded: bool = False,
    brain_blocked: bool = False,
    journey_completed: bool = False,
) -> dict[str, Any]:
    """Classify the future horizon without asserting a disruption has happened."""

    if journey_completed:
        return {
            "state": "CLEAR",
            "headline": "Journey complete.",
            "top_risk": None,
            "recommended_action": "NONE",
        }

    rows = actionable_future_risks(activity_risks, now=now)
    top = rows[0] if rows else None

    if provider_degraded:
        return {
            "state": "PROVIDER_DEGRADED",
            "headline": "I can’t fully check the rest of the journey right now.",
            "top_risk": top,
            "recommended_action": "KEEP_WATCHING",
        }
    if brain_blocked and top is not None:
        return {
            "state": "FUTURE_RISK_UNCERTAIN",
            "headline": "I found a future risk, but my planning AI is unavailable.",
            "top_risk": top,
            "recommended_action": "WAIT_FOR_BRAIN",
        }

    prevention = str(prevention_status or "").upper()
    if prevention in {"PLANNING", "DISCOVERING", "INVESTIGATING"}:
        return {
            "state": "PREVENTION_PLANNING",
            "headline": "I’m preparing a safer option for later.",
            "top_risk": top,
            "recommended_action": "WAIT",
        }
    if prevention in {"READY", "WAITING_FOR_APPROVAL"}:
        return {
            "state": "WAITING_FOR_APPROVAL" if prevention == "WAITING_FOR_APPROVAL" else "PREVENTION_READY",
            "headline": (
                "I found a preventive change and need your approval."
                if prevention == "WAITING_FOR_APPROVAL"
                else "A preventive option is ready."
            ),
            "top_risk": top,
            "recommended_action": "REVIEW_PREVENTION",
        }
    if prevention in {"APPLIED", "COMPLETED", "RECOVERED"}:
        return {
            "state": "PREVENTION_APPLIED",
            "headline": "I handled the future risk and I’m still watching ahead.",
            "top_risk": top,
            "recommended_action": "NONE",
        }

    if top is None:
        return {
            "state": "CLEAR",
            "headline": "I’m watching the rest of your journey.",
            "top_risk": None,
            "recommended_action": "NONE",
        }

    score = int(top["risk_score"])
    lead = int(top["lead_time_minutes"])
    grounded = bool(top["grounded"])

    if not grounded or score < 40:
        state = "WATCHING_FUTURE"
        action = "KEEP_WATCHING"
    elif lead > 240:
        state = "WATCHING_FUTURE"
        action = "KEEP_WATCHING"
    elif lead >= 30:
        state = "FUTURE_RISK_FOUND"
        action = "PREPARE_RECOVERY"
    else:
        state = "FUTURE_RISK_FOUND"
        action = "HAND_OFF_TO_NEAR_TERM_GUARDIAN"

    return {
        "state": state,
        "headline": (
            "I found a credible risk later in the journey."
            if state == "FUTURE_RISK_FOUND"
            else "I’m watching a possible risk later in the journey."
        ),
        "top_risk": top,
        "recommended_action": action,
    }
