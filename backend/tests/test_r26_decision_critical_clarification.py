from app.intelligence.decision_sensitivity import (
    clarification_epoch_fingerprint,
    decision_sensitivity_receipt,
)
from app.agent.runtime import _server_completion_contract


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


def test_r26_defer_without_server_mutation_is_not_resolved():
    steps = [{
        "tool_name": "conclude_recovery",
        "status": "COMPLETED",
        "result": {"requested_outcome": "NO_ACTION", "horizon_decision": "DEFER"},
    }]
    receipt = _server_completion_contract(steps, run_status="COMPLETED")
    assert receipt["kind"] == "UNRESOLVED"
    assert receipt["reason_code"] == "DEFER_WITHOUT_EXECUTION_EFFECT"


def test_r26_clarified_skip_is_a_machine_mutation():
    steps = [
        {
            "tool_name": "apply_clarified_horizon_choice",
            "status": "COMPLETED",
            "result": {
                "executed": True,
                "mutation": "ACTIVITY_SKIPPED",
                "reason": "CLARIFIED_DEFER_FOR_LATER_OPTION",
            },
        },
        {
            "tool_name": "conclude_recovery",
            "status": "COMPLETED",
            "result": {"requested_outcome": "MUTATION_EXECUTED"},
        },
    ]
    receipt = _server_completion_contract(steps, run_status="COMPLETED")
    assert receipt == {"kind": "MUTATION_EXECUTED", "source": "server_trace"}


def test_r26_take_now_child_keeps_current_activity_without_clarified_skip():
    import inspect
    from app.agent.runtime import _system_prompt

    prompt = inspect.getsource(_system_prompt)
    assert "TAKE_NOW answer" in prompt
    assert "do not call apply_clarified_horizon_choice" in prompt
