from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_verdict():
    path = Path(__file__).resolve().parents[1] / "scripts" / "r32_machine_verdict.py"
    spec = importlib.util.spec_from_file_location("r32_machine_verdict", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verdict


verdict = _load_verdict()


def _checkpoint() -> dict:
    r1 = "r1"
    r2 = "r2"
    a = "agent-a"
    b = "agent-b"
    return {
        "source_receipt": {
            "git_head": "deadbeef",
            "tracked_dirty_before_strike": False,
            "source_sha256": {"backend/run_r32_live.py": "abc"},
        },
        "runtime": {
            "provider_calls_were_real": True,
            "concurrent_external_barrier_proven": True,
        },
        "setup": {"active_plan_id": "plan-0"},
        "truth_boundary": {
            "shock_source": "SERVER_OWNED_PROVIDER_REPLAY_FIXTURE",
            "physical_travel_proven": False,
        },
        "r1": {
            "id": r1,
            "fingerprint": "fp-1",
            "triggering_event_ids": ["event-a"],
        },
        "r2": {
            "id": r2,
            "fingerprint": "fp-2",
            "triggering_event_ids": ["event-a", "event-b"],
        },
        "current_epoch_id": r2,
        "agent_a_bound_before_shock_b": True,
        "agent_b_bound_after_shock_b": True,
        "agent_a_run_at_barrier": {
            "id": a,
            "provider_key": "hermes",
            "recovery_epoch_id": r1,
        },
        "agent_b_run_at_barrier": {
            "id": b,
            "provider_key": "hermes",
            "recovery_epoch_id": r2,
        },
        "stale_binding_assertion": {
            "typed": True,
            "detail": {"code": "RECOVERY_EPOCH_SUPERSEDED"},
        },
        "agent_responses": {},
        "final": {
            "journey": {"active_plan_version_id": "plan-0"},
            "epochs": [
                {
                    "id": r1,
                    "status": "SUPERSEDED",
                    "superseded_by_recovery_epoch_id": r2,
                    "opened_at": "2026-10-06T00:00:00+00:00",
                },
                {
                    "id": r2,
                    "status": "OPEN",
                    "opened_at": "2026-10-06T00:01:00+00:00",
                },
            ],
            "runs": [
                {"id": a, "status": "SUPERSEDED"},
                {"id": b, "status": "COMPLETED"},
            ],
            "steps": [
                {
                    "run_id": a,
                    "tool_name": "recovery_epoch_guard",
                    "status": "SUPERSEDED",
                    "result": {"code": "RECOVERY_EPOCH_SUPERSEDED"},
                },
                {
                    "run_id": b,
                    "tool_name": "inspect_journey",
                    "status": "COMPLETED",
                    "result": {"decision": "ALLOW_AUTO"},
                },
            ],
            "events": [
                {
                    "id": "event-a",
                    "event_type": "CLOSURE",
                    "severity": "MAJOR",
                    "affected_activity_id": "activity-a",
                    "payload": {"incident_fingerprint": "incident-a"},
                },
                {
                    "id": "event-b",
                    "event_type": "WEATHER",
                    "severity": "MAJOR",
                    "affected_activity_id": "activity-b",
                    "payload": {
                        "incident_fingerprint": "incident-b",
                        "scope_place_id": "place-b",
                    },
                },
            ],
            "proposals": [],
            "receipts": [],
            "approvals": [],
            "pending_actions": [],
        },
    }


def test_empty_authority_artifacts_are_not_vacuous_proof():
    result = verdict(
        _checkpoint(),
        regression={"exit_code": 0, "passed": 132, "failed": 0},
    )

    assert result["dimensions"]["approval_not_retargeted"]["verdict"] == "NOT_PROVEN"
    assert (
        result["dimensions"]["no_duplicate_continuation_side_effect"]["verdict"]
        == "NOT_PROVEN"
    )
    assert result["dimensions"]["r1_candidates_removed_from_current_surface"]["verdict"] == "NOT_PROVEN"
    assert result["dimensions"]["r1_receipts_invalidated"]["verdict"] == "NOT_PROVEN"
    assert result["overall"] == "NOT_PROVEN"


def test_stale_r1_approval_consumed_after_r2_is_contradiction():
    checkpoint = _checkpoint()
    checkpoint["final"]["approvals"] = [
        {
            "id": "approval-r1",
            "recovery_epoch_id": "r1",
            "status": "CONSUMED",
            "created_at": "2026-10-06T00:00:30+00:00",
            "consumed_at": "2026-10-06T00:02:00+00:00",
        }
    ]

    result = verdict(
        checkpoint,
        regression={"exit_code": 0, "passed": 132, "failed": 0},
    )

    assert result["dimensions"]["approval_not_retargeted"]["verdict"] == "CONTRADICTED"
    assert result["overall"] == "CONTRADICTED"


def test_missing_new_evidence_fields_remain_not_proven_not_contradicted():
    checkpoint = _checkpoint()
    checkpoint.pop("source_receipt")
    checkpoint["runtime"].pop("concurrent_external_barrier_proven")

    result = verdict(
        checkpoint,
        regression={"exit_code": 0, "passed": 132, "failed": 0},
    )

    assert (
        result["dimensions"]["strike_source_state_traceable"]["verdict"]
        == "NOT_PROVEN"
    )
    assert (
        result["dimensions"]["concurrent_external_barrier"]["verdict"]
        == "NOT_PROVEN"
    )
    assert result["overall"] == "NOT_PROVEN"


def test_dirty_source_state_cannot_be_proven():
    checkpoint = _checkpoint()
    checkpoint["source_receipt"]["tracked_dirty_before_strike"] = True

    result = verdict(
        checkpoint,
        regression={"exit_code": 0, "passed": 132, "failed": 0},
    )

    assert result["dimensions"]["strike_source_state_traceable"]["verdict"] == "CONTRADICTED"
    assert result["overall"] == "CONTRADICTED"
