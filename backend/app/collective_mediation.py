"""Small deterministic projections for shared Journey mediation.

This module deliberately contains arithmetic and classification only.  It does
not select an authority, call a provider, or turn a soft preference into a
hard constraint.
"""

from __future__ import annotations

from typing import Any, Iterable

from app.replanning.candidate_evidence import verified_interest_preference_breakdown


def member_fit(*, preferences: Iterable[Any], candidate_tags: Iterable[str]) -> dict[str, Any]:
    breakdown = verified_interest_preference_breakdown(preferences, candidate_tags=candidate_tags)
    explicit = breakdown.get("current_mission_preference_fit")
    if explicit is None:
        explicit = breakdown.get("explicit_preference_fit")
    learned = breakdown.get("learned_soft_preference_fit")
    effective = breakdown.get("effective_preference_fit")
    return {
        "explicit_contribution": explicit,
        "learned_soft_contribution": learned,
        "effective_fit": 0.5 if effective is None else float(effective),
        "preference_tier": breakdown.get("effective_preference_tier", "NEUTRAL"),
        "conflict": None,
    }


def fairness_receipt(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_member: dict[str, float] = {}
    for candidate in candidates:
        for member_id, fit in (candidate.get("member_fits") or {}).items():
            best_by_member[member_id] = max(best_by_member.get(member_id, 0.0), float(fit.get("effective_fit", 0.5)))
    receipts = []
    for candidate in candidates:
        fits = candidate.get("member_fits") or {}
        values = {key: float(value.get("effective_fit", 0.5)) for key, value in fits.items()}
        regrets = {key: round(best_by_member[key] - value, 3) for key, value in values.items()}
        candidate["fairness"] = {
            "minimum_member_fit": round(min(values.values()), 3) if values else None,
            "maximum_regret": round(max(regrets.values()), 3) if regrets else None,
            "regret_by_member": regrets,
            "mean_fit": round(sum(values.values()) / len(values), 3) if values else None,
            "unacceptable_member_ids": [key for key, value in values.items() if value < 0.35],
        }
        receipts.append(candidate["fairness"])
    return receipts


def classify_group_decision(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    rejected = [item.get("candidate_id") for item in candidates if item.get("status") != "GROUNDED_FEASIBLE"]
    candidates = [item for item in candidates if item.get("status") == "GROUNDED_FEASIBLE"]
    if not candidates or not candidates[0].get("member_fits"):
        return {"classification": "INSUFFICIENT_WORLD_FACTS", "reason": "NO_GROUNDED_FEASIBLE_MEMBER_OPTIONS", "rejected_candidate_ids": rejected}
    fairness_receipt(candidates)
    if len(candidates) == 1 and not candidates[0]["fairness"]["unacceptable_member_ids"]:
        return {"classification": "UNANIMOUS_DOMINANCE", "candidate_id": candidates[0].get("candidate_id")}
    for candidate in candidates:
        current = candidate["member_fits"]
        dominates = True
        strictly_better = False
        for other in candidates:
            if other is candidate:
                continue
            for member_id, fit in current.items():
                value = float(fit.get("effective_fit", 0.5))
                other_value = float((other.get("member_fits") or {}).get(member_id, {}).get("effective_fit", 0.5))
                if value < other_value - 0.05:
                    dominates = False
                if value > other_value + 0.05:
                    strictly_better = True
        if dominates and strictly_better and not candidate["fairness"]["unacceptable_member_ids"]:
            return {"classification": "UNANIMOUS_DOMINANCE", "candidate_id": candidate.get("candidate_id")}
    compromise = [
        item for item in candidates
        if (item.get("fairness") or {}).get("minimum_member_fit", 0.0) >= 0.45
        and (item.get("fairness") or {}).get("maximum_regret", 1.0) <= 0.35
    ]
    if compromise:
        return {
            "classification": "COMPROMISE_AVAILABLE",
            "candidate_ids": [item.get("candidate_id") for item in compromise],
            "selected_candidate_id": max(
                compromise,
                key=lambda item: (
                    (item.get("fairness") or {}).get("minimum_member_fit", 0.0),
                    -(item.get("fairness") or {}).get("maximum_regret", 1.0),
                    (item.get("fairness") or {}).get("mean_fit", 0.0),
                ),
            ).get("candidate_id"),
        }
    relevant = []
    for member_id in candidates[0]["member_fits"]:
        fits = [float(item["member_fits"][member_id]["effective_fit"]) for item in candidates]
        if max(fits) - min(fits) > 0.05 or min(fits) < 0.35:
            relevant.append(member_id)
    return {"classification": "HUMAN_TRADEOFF_REQUIRED", "candidate_ids": [item.get("candidate_id") for item in candidates], "decision_relevant_member_ids": relevant}
