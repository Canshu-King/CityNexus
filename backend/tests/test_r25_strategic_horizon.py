from __future__ import annotations

from app.agent.runtime import _server_completion_contract


def test_r25_defer_is_a_typed_non_mutating_conclusion_after_comparing_proposal() -> None:
    trace = [
        {
            "tool_name": "request_replan",
            "status": "COMPLETED",
            "result": {"proposal": {"id": "proposal-current-window"}},
        },
        {
            "tool_name": "conclude_recovery",
            "status": "COMPLETED",
            "result": {
                "requested_outcome": "NO_ACTION",
                "horizon_decision": "DEFER",
                "reason": "Preserve optional budget for a higher-value later window.",
            },
        },
    ]

    assert _server_completion_contract(trace, run_status="COMPLETED") == {
        "kind": "NO_ACTION",
        "source": "server_trace",
    }


def test_r25_plain_no_action_still_requires_no_server_proposal() -> None:
    trace = [
        {
            "tool_name": "conclude_recovery",
            "status": "COMPLETED",
            "result": {"requested_outcome": "NO_ACTION"},
        }
    ]
    assert _server_completion_contract(trace, run_status="COMPLETED")["kind"] == "NO_ACTION"
