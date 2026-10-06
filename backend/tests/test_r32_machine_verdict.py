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
            "external_call_outcomes": [
                {
                    "thread": "AnyIO worker thread",
                    "causal_slot": "A",
                    "provider_call_invoked": True,
                    "provider_returned": True,
                },
                {
                    "thread": "AnyIO worker thread",
                    "causal_slot": "B",
                    "provider_call_invoked": True,
                    "provider_returned": True,
                },
            ],
        },
        "setup": {"active_plan_id": "plan-0"},
        "runtime_preflight": {
            "runtime_type": "HermesJourneyAgent",
            "provider_key": "hermes",
            "model_key": "cn:glm-5.3-flash",
            "hermes_api_url_configured": True,
            "hermes_api_key_configured": True,
            "semantic_ai_api_key_configured": False,
            "native_hermes_configured": False,
            "native_hermes_ready": False,
            "selected_openai_compatible_hermes": True,
        },
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


def _successful_autonomous_mutation_checkpoint() -> dict:
    checkpoint = _checkpoint()
    checkpoint["authority_setup"] = {
        "requested_member_preference": {
            "category": "interest",
            "key": "garden",
            "value": True,
            "weight": 1.0,
        },
        "member_preferences": [
            {"member_id": "member-a", "status_code": 200},
            {"member_id": "member-b", "status_code": 200},
        ],
        "owner_policy": {
            "mode": "AUTONOMOUS",
            "auto_accept_replan": True,
            "max_auto_replan_cost_delta_minor": 25000,
            "max_auto_loss_minor": 25000,
            "max_auto_schedule_drift_min": 240,
        },
        "timing": "PRE_SHOCK_STANDING_AUTHORITY",
        "human_action_after_shock": False,
    }
    checkpoint["final"]["journey"]["active_plan_version_id"] = "plan-r2"
    checkpoint["final"]["proposals"] = [
        {
            "id": "proposal-r2",
            "trigger_event_id": "event-a",
            "proposed_plan_version_id": "plan-r2",
            "status": "ACCEPTED",
            "recovery_epoch_id": "r2",
            "source_agent_run_id": "agent-b",
        }
    ]
    checkpoint["final"]["receipts"] = [
        {
            "id": "receipt-r2",
            "proposal_id": "proposal-r2",
            "plan_version_id": "plan-r2",
            "authority_mode": "UNANIMOUS_DOMINANCE",
            "recovery_epoch_id": "r2",
            "source_agent_run_id": "agent-b",
            "classification": "UNANIMOUS_DOMINANCE",
            "invalidated_at": None,
        }
    ]
    checkpoint["final"]["steps"].append(
        {
            "run_id": "agent-b",
            "tool_name": "accept_replan",
            "status": "COMPLETED",
            "result": {
                "executed": True,
                "collective_authority_receipt_id": "receipt-r2",
            },
        }
    )
    checkpoint["final"]["audits"] = [
        {
            "action": "replan.accepted",
            "entity_id": "proposal-r2",
            "after": {
                "collective_authority": {
                    "receipt_id": "receipt-r2",
                    "receipt": {
                        "receipt_id": "receipt-r2",
                        "authority_mode": "UNANIMOUS_DOMINANCE",
                        "recovery_epoch_id": "r2",
                        "source_agent_run_id": "agent-b",
                        "provenance": {
                            "decision_epoch": {
                                "source": (
                                    "ALGORITHMIC_UNANIMOUS_SEMANTIC_EPOCH"
                                )
                            }
                        },
                    },
                    "candidate_surface_scope": "RECOVERY_EPOCH_TRIGGER",
                    "candidate_surface_recovery_epoch_id": "r2",
                    "candidate_surface_trigger_event_id": "event-a",
                }
            },
        }
    ]
    return checkpoint


def test_complete_b_r2_unanimous_mutation_path_can_prove_core():
    result = verdict(
        _successful_autonomous_mutation_checkpoint(),
        regression={"exit_code": 0, "passed": 132, "failed": 0},
    )

    assert result["overall"] == "PROVEN"
    assert (
        result["dimensions"]["arrival_order_not_authority"]["verdict"]
        == "PROVEN"
    )
    assert (
        result["dimensions"]["authority_provenance_mode_accurate"]["verdict"]
        == "PROVEN"
    )
    assert (
        result["dimensions"]["current_surface_epoch_pure"]["verdict"]
        == "PROVEN"
    )
    assert "approval_not_retargeted" in result["coverage_not_proven"]
    assert (
        "no_duplicate_continuation_side_effect"
        in result["coverage_not_proven"]
    )


def test_pending_server_approval_is_not_fabricated_human_authority():
    checkpoint = _successful_autonomous_mutation_checkpoint()
    checkpoint["final"]["steps"] = [
        row
        for row in checkpoint["final"]["steps"]
        if row.get("tool_name") != "accept_replan"
    ]
    checkpoint["final"]["audits"] = []
    checkpoint["final"]["receipts"] = []
    checkpoint["final"]["proposals"][0]["status"] = "PRESENTED"
    checkpoint["final"]["journey"]["active_plan_version_id"] = "plan-0"
    checkpoint["final"]["approvals"] = [
        {
            "id": "approval-pending",
            "status": "PENDING",
            "recovery_epoch_id": "r2",
            "created_at": "2026-10-06T00:02:00+00:00",
            "approved_at": None,
            "consumed_at": None,
        }
    ]

    result = verdict(
        checkpoint,
        regression={"exit_code": 0, "passed": 132, "failed": 0},
    )

    assert (
        result["dimensions"][
            "no_post_shock_human_authority_fabrication"
        ]["verdict"]
        == "NOT_PROVEN"
    )
    assert result["overall"] == "NOT_PROVEN"


def test_unanimous_receipt_cannot_borrow_stale_agent_a_lineage():
    checkpoint = _successful_autonomous_mutation_checkpoint()
    checkpoint["final"]["receipts"][0][
        "source_agent_run_id"
    ] = "agent-a"

    result = verdict(
        checkpoint,
        regression={"exit_code": 0, "passed": 132, "failed": 0},
    )

    assert (
        result["dimensions"]["authority_provenance_mode_accurate"]["verdict"]
        == "CONTRADICTED"
    )
    assert result["overall"] == "CONTRADICTED"


def test_anyio_worker_thread_does_not_define_agent_identity():
    checkpoint = _checkpoint()
    result = verdict(
        checkpoint,
        regression={"exit_code": 0, "passed": 145, "failed": 0},
    )

    assert (
        result["dimensions"]["agent_a_external_and_bound_r1"]["verdict"]
        == "PROVEN"
    )
    assert (
        result["dimensions"]["agent_b_external_and_bound_r2"]["verdict"]
        == "PROVEN"
    )


def test_clean_precausal_abort_is_not_a_product_contradiction():
    checkpoint = {
        "schema": "citynexus.r32.live-strike.v2.failure.v2",
        "status": "NOT_PROVEN",
        "failure": {
            "phase": "A_EXTERNAL_RESPONSE_BOUNDARY",
            "message": "Agent A did not reach the boundary",
        },
        "source_receipt": {
            "git_head": "deadbeef",
            "tracked_dirty_before_strike": False,
            "source_sha256": {"backend/run_r32_live.py": "abc"},
        },
        "runtime": {
            "provider_calls_were_real": False,
            "concurrent_external_barrier_proven": False,
            "external_call_outcomes": [],
        },
        "setup": {},
        "authority_setup": {},
        "r1": {},
        "r2": {},
        "current_epoch_id": None,
        "agent_a_run_at_barrier": None,
        "agent_b_run_at_barrier": None,
        "agent_responses": {},
        "stale_binding_assertion": {},
        "final": {
            "journey": {},
            "epochs": [],
            "runs": [],
            "steps": [],
            "events": [],
            "proposals": [],
            "receipts": [],
            "approvals": [],
            "pending_actions": [],
            "audits": [],
            "plans": [],
        },
        "truth_boundary": {
            "shock_source": "SERVER_OWNED_PROVIDER_REPLAY_FIXTURE",
            "physical_travel_proven": False,
        },
    }

    result = verdict(
        checkpoint,
        regression={"exit_code": 0, "passed": 142, "failed": 0},
    )

    assert result["overall"] == "NOT_PROVEN"
    assert result["contradicted"] == []
    assert len(result["evaluator_receipt"]["sha256"]) == 64


def test_failure_marker_cannot_hide_observed_authority_contradiction():
    checkpoint = _successful_autonomous_mutation_checkpoint()
    checkpoint["status"] = "NOT_PROVEN"
    checkpoint["failure"] = {
        "phase": "POST_MUTATION_CHECKPOINT",
        "message": "later harness observation failed",
    }
    checkpoint["final"]["receipts"][0][
        "source_agent_run_id"
    ] = "agent-a"

    result = verdict(
        checkpoint,
        regression={"exit_code": 0, "passed": 142, "failed": 0},
    )

    assert result["overall"] == "CONTRADICTED"
    assert (
        result["dimensions"]["authority_provenance_mode_accurate"]["verdict"]
        == "CONTRADICTED"
    )


def test_r32_configuration_clears_ambient_semantic_ai(
    monkeypatch, tmp_path
):
    import os
    import run_r32_live

    monkeypatch.setattr(
        run_r32_live,
        "_base_configure",
        lambda: tmp_path / "r32-isolated.sqlite3",
    )
    monkeypatch.setenv("CITYNEXUS_AI_API_KEY", "ambient-citynexus-ai")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ambient-deepseek")
    monkeypatch.setenv("CITYNEXUS_AI_ENABLED", "true")
    monkeypatch.setenv(
        "CITYNEXUS_HERMES_NATIVE_API_URL",
        "http://127.0.0.1:9999",
    )
    monkeypatch.setenv("CITYNEXUS_HERMES_API_SERVER_KEY", "ambient-native")

    db = run_r32_live._configure_r32()

    assert db == tmp_path / "r32-isolated.sqlite3"
    assert os.environ["CITYNEXUS_AI_API_KEY"] == ""
    assert os.environ["DEEPSEEK_API_KEY"] == ""
    assert os.environ["CITYNEXUS_AI_ENABLED"] == "false"
    assert os.environ["CITYNEXUS_HERMES_NATIVE_API_URL"] == ""
    assert os.environ["CITYNEXUS_HERMES_API_SERVER_KEY"] == ""


def test_dirty_source_state_cannot_be_proven():
    checkpoint = _checkpoint()
    checkpoint["source_receipt"]["tracked_dirty_before_strike"] = True

    result = verdict(
        checkpoint,
        regression={"exit_code": 0, "passed": 132, "failed": 0},
    )

    assert result["dimensions"]["strike_source_state_traceable"]["verdict"] == "CONTRADICTED"
    assert result["overall"] == "CONTRADICTED"
