from app.intelligence.decision_sensitivity import (
    clarification_epoch_fingerprint,
    decision_sensitivity_receipt,
)


def _window(key: str, place_id: str, status: str, cost: int, fit: float = 0.5):
    return {
        "window_id": key,
        "status": status,
        "window_boundary": {"opens_at": "2026-10-04T10:00:00+00:00", "closes_at": "2026-10-04T12:00:00+00:00"},
        "candidate": {
            "place_id": place_id,
            "category": "garden" if key == "w1" else "museum",
            "cost_evidence": {"status": "KNOWN_PAID", "amount_minor": cost},
            "preference_fit": fit,
        },
    }


def test_r26_only_two_feasible_conflicting_actions_are_decision_sensitive():
    receipt = decision_sensitivity_receipt(
        [_window("w1", "place-a", "GROUNDED_FEASIBLE", 700), _window("w2", "place-b", "GROUNDED_FEASIBLE", 800)],
        traveler_twin_context={"explicit_preferences": [], "learned_soft_preferences": []},
    )
    assert receipt["decision_sensitive"] is True
    assert receipt["reason"] == "DECISION_SENSITIVE_HUMAN_VALUE"
    assert [item["top_action"] for item in receipt["counterfactuals"]] == ["TAKE_NOW", "DEFER"]


def test_r26_known_cost_and_route_but_infeasible_window_cannot_enable_defer():
    receipt = decision_sensitivity_receipt(
        [_window("w1", "place-a", "GROUNDED_INFEASIBLE", 700), _window("w2", "place-b", "GROUNDED_FEASIBLE", 800)],
    )
    assert receipt["decision_sensitive"] is False
    assert receipt["reason"] == "INSUFFICIENT_GROUNDED_FEASIBLE_OPTIONS"


def test_r26_explicit_preference_suppresses_question_and_fingerprint_is_epoch_bound():
    windows = [_window("w1", "place-a", "GROUNDED_FEASIBLE", 700), _window("w2", "place-b", "GROUNDED_FEASIBLE", 800)]
    receipt = decision_sensitivity_receipt(windows, current_mission_preferences={"garden": "positive"})
    assert receipt["decision_sensitive"] is False
    first = clarification_epoch_fingerprint(
        journey_id="j", active_plan_version_id="p1", current_activity_id="a1", windows=windows
    )
    second = clarification_epoch_fingerprint(
        journey_id="j", active_plan_version_id="p2", current_activity_id="a1", windows=windows
    )
    assert first != second
