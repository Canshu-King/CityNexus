from app.agent.runtime import _same_state_replay, _tool_result_advances_state


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



def test_same_state_inspection_replays_server_truth_without_tool_error():
    replay = _same_state_replay(
        "inspect_journey",
        {
            "tool": "inspect_journey",
            "journey_id": "journey-1",
            "status": "ACTIVE",
        },
        replayed_from_sequence_no=3,
        state_epoch=0,
    )

    assert replay is not None
    assert replay["tool"] == "inspect_journey"
    assert replay["status"] == "ACTIVE"
    assert replay["_runtime_replay"] == {
        "same_state_replay": True,
        "state_changed": False,
        "state_epoch": 0,
        "replayed_from_sequence_no": 3,
    }
    assert "error" not in replay


def test_same_state_mutation_is_not_semantically_replayed():
    assert (
        _same_state_replay(
            "accept_replan",
            {"tool": "accept_replan", "executed": True},
            replayed_from_sequence_no=5,
            state_epoch=1,
        )
        is None
    )


def test_failed_inspection_is_not_replayed_as_truth():
    assert (
        _same_state_replay(
            "inspect_twin",
            {"tool": "inspect_twin", "error": "unavailable"},
            replayed_from_sequence_no=2,
            state_epoch=0,
        )
        is None
    )
