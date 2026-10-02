from app.agent.runtime import _tool_result_advances_state


def test_replan_proposal_advances_observation_epoch():
    assert _tool_result_advances_state(
        "request_replan",
        {"tool": "request_replan", "proposal": {"id": "proposal-1"}},
    )


def test_failed_or_empty_replan_does_not_reset_repetition_guard():
    assert not _tool_result_advances_state(
        "request_replan", {"tool": "request_replan", "error": "NO_FEASIBLE_PLAN"}
    )
    assert not _tool_result_advances_state(
        "request_replan", {"tool": "request_replan", "proposal": None}
    )
