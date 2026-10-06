"""Machine verdict for the R32 live strike checkpoint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _dim(value: bool | None, evidence: str) -> dict[str, Any]:
    return {"verdict": "PROVEN" if value is True else "CONTRADICTED" if value is False else "NOT_PROVEN", "evidence": evidence}


def verdict(
    checkpoint: dict[str, Any],
    *,
    regression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Judge only evidence that the strike actually exercised.

    Empty artifact classes are never positive evidence.  A missing stale
    approval, receipt, proposal, or continuation means that boundary is
    NOT_PROVEN in this strike, not vacuously PROVEN.
    """

    final = checkpoint.get("final") or {}
    epochs = final.get("epochs") or []
    runs = final.get("runs") or []
    steps = final.get("steps") or []
    proposals = final.get("proposals") or []
    receipts = final.get("receipts") or []
    approvals = final.get("approvals") or []
    pending = final.get("pending_actions") or []
    events = final.get("events") or []
    audits = final.get("audits") or []
    authority_setup = checkpoint.get("authority_setup") or {}

    r1 = checkpoint.get("r1") or {}
    r2 = checkpoint.get("r2") or {}
    r1id, r2id = r1.get("id"), r2.get("id")
    current_id = checkpoint.get("current_epoch_id")
    a = checkpoint.get("agent_a_run_at_barrier") or {}
    b = checkpoint.get("agent_b_run_at_barrier") or {}
    stale = checkpoint.get("stale_binding_assertion") or {}

    a_final = next(
        (row for row in runs if row.get("id") == a.get("id")), {}
    )
    b_final = next(
        (row for row in runs if row.get("id") == b.get("id")), {}
    )
    r1row = next(
        (row for row in epochs if row.get("id") == r1id), {}
    )
    r2row = next(
        (row for row in epochs if row.get("id") == r2id), {}
    )

    stale_steps = [
        row
        for row in steps
        if row.get("run_id") == a.get("id")
        and (row.get("result") or {}).get("code")
        == "RECOVERY_EPOCH_SUPERSEDED"
    ]
    runtime = checkpoint.get("runtime") or {}
    source_receipt = checkpoint.get("source_receipt") or {}

    provider_calls_raw = runtime.get("provider_calls_were_real")
    provider_calls_real: bool | None = (
        True
        if provider_calls_raw is True
        else False
        if provider_calls_raw is False
        else None
    )
    barrier_raw = runtime.get("concurrent_external_barrier_proven")
    concurrent_barrier: bool | None = (
        True if barrier_raw is True else False if barrier_raw is False else None
    )
    source_traceable: bool | None = None
    if source_receipt:
        source_traceable = bool(
            source_receipt.get("git_head")
            and source_receipt.get("source_sha256")
            and source_receipt.get("tracked_dirty_before_strike") is False
        )

    a_external: bool | None = None
    if (
        provider_calls_real is not None
        and concurrent_barrier is not None
        and a.get("id")
    ):
        a_external = bool(
            provider_calls_real
            and concurrent_barrier
            and a.get("provider_key") == "hermes"
            and any(row.get("run_id") == a.get("id") for row in steps)
        )
    b_external: bool | None = None
    if (
        provider_calls_real is not None
        and concurrent_barrier is not None
        and b.get("id")
    ):
        b_external = bool(
            provider_calls_real
            and concurrent_barrier
            and b.get("provider_key") == "hermes"
            and any(row.get("run_id") == b.get("id") for row in steps)
        )

    standing_authority_preconfigured: bool | None = None
    if authority_setup:
        requested_preference = (
            authority_setup.get("requested_member_preference") or {}
        )
        preference_receipts = (
            authority_setup.get("member_preferences") or []
        )
        owner_policy = authority_setup.get("owner_policy") or {}
        standing_authority_preconfigured = bool(
            authority_setup.get("timing")
            == "PRE_SHOCK_STANDING_AUTHORITY"
            and authority_setup.get("human_action_after_shock") is False
            and requested_preference.get("key") == "garden"
            and requested_preference.get("value") is True
            and len(preference_receipts) == 2
            and all(
                item.get("status_code") == 200
                for item in preference_receipts
            )
            and owner_policy.get("mode") == "AUTONOMOUS"
            and owner_policy.get("auto_accept_replan") is True
            and int(
                owner_policy.get(
                    "max_auto_replan_cost_delta_minor", -1
                )
            )
            >= 0
            and int(owner_policy.get("max_auto_loss_minor", -1)) >= 0
            and int(
                owner_policy.get("max_auto_schedule_drift_min", -1)
            )
            >= 0
        )

    r1_event_ids = set(r1.get("triggering_event_ids") or [])
    r2_event_ids = set(r2.get("triggering_event_ids") or [])
    new_r2_event_ids = r2_event_ids - r1_event_ids
    event_by_id = {
        str(row.get("id")): row
        for row in events
        if row.get("id")
    }
    material_r2_events = []
    for event_id in sorted(new_r2_event_ids):
        row = event_by_id.get(str(event_id)) or {}
        payload = row.get("payload") or {}
        if (
            row.get("event_type")
            and row.get("severity")
            and (
                payload.get("incident_fingerprint")
                or row.get("affected_activity_id")
                or payload.get("scope_place_id")
            )
        ):
            material_r2_events.append(event_id)
    shock_b_material = bool(
        r1.get("fingerprint")
        and r2.get("fingerprint")
        and r1.get("fingerprint") != r2.get("fingerprint")
        and material_r2_events
    )

    stale_proposals = [
        row
        for row in proposals
        if row.get("recovery_epoch_id") == r1id
    ]
    stale_receipts = [
        row
        for row in receipts
        if row.get("recovery_epoch_id") == r1id
    ]
    stale_approvals = [
        row
        for row in approvals
        if row.get("recovery_epoch_id") == r1id
    ]

    # Current executable Agent surface.  A post-mutation strike proves this
    # from the exact gate facts persisted in replan.accepted; a waiting
    # collective round proves it from its server-derived option set.
    current_agent_rows = [
        row
        for row in proposals
        if row.get("source_agent_run_id")
        and row.get("recovery_epoch_id") == current_id
    ]
    current_agent_ids = {
        str(row.get("id"))
        for row in current_agent_rows
        if row.get("id")
    }
    b_payload = (
        (checkpoint.get("agent_responses") or {})
        .get("agent_b", {})
        .get("payload", {})
    )
    clarification = (b_payload.get("mission") or {}).get(
        "clarification"
    ) or {}
    option_ids = {
        str(item.get("proposal_id"))
        for item in clarification.get("candidate_options") or []
        if isinstance(item, dict) and item.get("proposal_id")
    }

    accepted_audits = [
        row
        for row in audits
        if row.get("action") == "replan.accepted"
    ]
    accepted_audit = accepted_audits[-1] if accepted_audits else {}
    accepted_after = accepted_audit.get("after") or {}
    accepted_collective = (
        accepted_after.get("collective_authority") or {}
    )
    accepted_proposal_id = str(
        accepted_audit.get("entity_id") or ""
    )
    accepted_proposal = next(
        (
            row
            for row in proposals
            if str(row.get("id") or "") == accepted_proposal_id
        ),
        {},
    )
    accepted_receipt_id = str(
        accepted_collective.get("receipt_id") or ""
    )
    accepted_receipt = next(
        (
            row
            for row in receipts
            if str(row.get("id") or "") == accepted_receipt_id
        ),
        {},
    )
    receipt_snapshot = accepted_collective.get("receipt") or {}
    receipt_provenance = receipt_snapshot.get("provenance") or {}

    surface_epoch_pure: bool | None = None
    if accepted_audit:
        surface_epoch_pure = bool(
            accepted_collective.get("candidate_surface_scope")
            == "RECOVERY_EPOCH_TRIGGER"
            and accepted_collective.get(
                "candidate_surface_recovery_epoch_id"
            )
            == current_id
            and accepted_collective.get(
                "candidate_surface_trigger_event_id"
            )
            == accepted_proposal.get("trigger_event_id")
            and accepted_proposal.get("recovery_epoch_id")
            == current_id
            and accepted_proposal.get("source_agent_run_id")
            == b.get("id")
        )
    elif option_ids:
        current_presented_ids = {
            str(row.get("id"))
            for row in current_agent_rows
            if row.get("status") == "PRESENTED"
        }
        surface_epoch_pure = bool(
            current_presented_ids
            and option_ids.issubset(current_presented_ids)
            and all(
                row.get("recovery_epoch_id") == current_id
                for row in proposals
                if str(row.get("id") or "") in option_ids
            )
        )

    # A stale approval only proves non-retargeting if one actually existed.
    # A post-R2 consumption of an R1 approval is a contradiction.
    approval_not_retargeted: bool | None = None
    if stale_approvals:
        r2_opened = str(r2row.get("opened_at") or "")
        late_consumption = any(
            row.get("status") == "CONSUMED"
            and row.get("consumed_at")
            and r2_opened
            and str(row.get("consumed_at")) >= r2_opened
            for row in stale_approvals
        )
        approval_not_retargeted = not late_consumption

    continuation_exact_once: bool | None = None
    if pending:
        approval_ids = [
            str(row.get("approval_id") or "")
            for row in pending
        ]
        if all(approval_ids):
            continuation_exact_once = (
                len(approval_ids) == len(set(approval_ids))
            )

    mutations = [
        row
        for row in steps
        if row.get("tool_name")
        in {
            "accept_replan",
            "activate_standby",
            "replace_activity",
            "reschedule_activity",
        }
        and (row.get("result") or {}).get("executed") is True
    ]
    active_plan_id = (final.get("journey") or {}).get(
        "active_plan_version_id"
    )
    setup_plan_id = (checkpoint.get("setup") or {}).get(
        "active_plan_id"
    )
    zero_legal_transition = (
        not mutations and active_plan_id == setup_plan_id
    )
    one_legal_transition = bool(
        len(mutations) == 1
        and accepted_proposal
        and active_plan_id
        == accepted_proposal.get("proposed_plan_version_id")
        and mutations[0].get("run_id") == b.get("id")
    )
    legal_transition_cardinality = (
        True
        if zero_legal_transition or one_legal_transition
        else False
        if mutations or active_plan_id != setup_plan_id
        else None
    )

    authority_provenance_mode_accurate: bool | None = None
    arrival_order_not_authority: bool | None = None
    if mutations:
        expected_decision_source = (
            "ALGORITHMIC_UNANIMOUS_SEMANTIC_EPOCH"
        )
        authority_provenance_mode_accurate = bool(
            len(mutations) == 1
            and accepted_receipt
            and accepted_receipt.get("authority_mode")
            == "UNANIMOUS_DOMINANCE"
            and accepted_receipt.get("recovery_epoch_id") == current_id
            and accepted_receipt.get("source_agent_run_id")
            == b.get("id")
            and accepted_receipt.get("invalidated_at") is None
            and accepted_receipt.get("proposal_id")
            == accepted_proposal_id
            and receipt_snapshot.get("recovery_epoch_id")
            == current_id
            and (
                receipt_provenance.get("decision_epoch") or {}
            ).get("source")
            == expected_decision_source
            and accepted_collective.get(
                "candidate_surface_recovery_epoch_id"
            )
            == current_id
        )
        arrival_order_not_authority = bool(
            authority_provenance_mode_accurate
            and a_final.get("status") == "SUPERSEDED"
            and not any(
                row.get("run_id") == a.get("id")
                and (row.get("result") or {}).get("executed") is True
                for row in steps
            )
            and mutations[0].get("run_id") == b.get("id")
        )

    no_post_shock_human_authority_fabrication: bool | None = None
    if authority_setup:
        no_post_shock_human_authority_fabrication = bool(
            authority_setup.get("human_action_after_shock") is False
            and not approvals
            and not pending
            and not any(
                row.get("action")
                == "agent.collective_decision.response"
                for row in audits
            )
        )

    regression_green = bool(
        regression
        and regression.get("exit_code") == 0
        and regression.get("passed", 0) >= 129
        and regression.get("failed") == 0
    )

    dimensions = {
        "strike_source_state_traceable": _dim(
            source_traceable,
            (
                f"git_head={source_receipt.get('git_head')} "
                f"tracked_dirty_before_strike="
                f"{source_receipt.get('tracked_dirty_before_strike')}"
            ),
        ),
        "concurrent_external_barrier": _dim(
            concurrent_barrier,
            (
                "A and B must each invoke the real external provider before "
                "their first model response is released to Runtime"
            ),
        ),
        "standing_authority_preconfigured": _dim(
            standing_authority_preconfigured,
            (
                "member values and a finite AUTONOMOUS delegation envelope "
                "must be configured through product APIs before Shock A"
            ),
        ),
        "no_post_shock_human_authority_fabrication": _dim(
            no_post_shock_human_authority_fabrication,
            (
                "this standing-autonomy strike must not synthesize approvals "
                "or member clarification responses after either shock"
            ),
        ),        "recovery_epoch_server_owned": _dim(
            bool(r1id and r2id and r1id != r2id),
            "R1/R2 are distinct persisted server-created ids",
        ),
        "r1_opened_from_shock_a": _dim(
            bool(r1.get("triggering_event_ids") and r1.get("fingerprint")),
            "R1 has provider Event lineage and a recovery fingerprint",
        ),
        "agent_a_external_and_bound_r1": _dim(
            (
                None
                if a_external is None
                else bool(
                    a_external
                    and a.get("recovery_epoch_id") == r1id
                    and checkpoint.get("agent_a_bound_before_shock_b")
                )
            ),
            (
                f"Agent A provider={a.get('provider_key')} "
                f"epoch={a.get('recovery_epoch_id')}; "
                "real external runtime evidence required"
            ),
        ),
        "shock_b_material_not_storage_churn": _dim(
            shock_b_material,
            (
                "R2 adds decision-material semantic Event facts: "
                + ",".join(material_r2_events)
            ),
        ),
        "r1_superseded_by_r2": _dim(
            bool(
                r1row.get("status") == "SUPERSEDED"
                and r1row.get("superseded_by_recovery_epoch_id") == r2id
                and r2row.get("status") == "OPEN"
            ),
            "R1 SUPERSEDED -> R2 OPEN",
        ),
        "agent_b_external_and_bound_r2": _dim(
            (
                None
                if b_external is None
                else bool(
                    b_external
                    and b.get("recovery_epoch_id") == r2id
                    and checkpoint.get("agent_b_bound_after_shock_b")
                )
            ),
            (
                f"Agent B provider={b.get('provider_key')} "
                f"epoch={b.get('recovery_epoch_id')}; "
                "independent external run required"
            ),
        ),
        "stale_agent_authority_refused": _dim(
            bool(stale.get("typed") or stale_steps),
            "old-run Gateway assertion or live run trace refused stale R1",
        ),
        "stale_result_typed_superseded": _dim(
            bool(stale.get("typed") or stale_steps),
            "typed RECOVERY_EPOCH_SUPERSEDED evidence",
        ),
        "agent_a_terminal_live_outcome": _dim(
            (
                True
                if a_final.get("status") == "SUPERSEDED"
                and stale_steps
                else None
            ),
            (
                f"A durable status={a_final.get('status')}; "
                "requires a live typed supersession step"
            ),
        ),
        "r1_candidates_removed_from_current_surface": _dim(
            (
                all(row.get("status") != "PRESENTED" for row in stale_proposals)
                if stale_proposals
                else None
            ),
            "requires at least one R1 proposal before Shock B",
        ),
        "r1_receipts_invalidated": _dim(
            (
                all(
                    row.get("invalidated_at")
                    and row.get("invalidation_code")
                    == "RECOVERY_EPOCH_SUPERSEDED"
                    for row in stale_receipts
                )
                if stale_receipts
                else None
            ),
            "requires at least one R1 authority receipt before Shock B",
        ),
        "current_surface_epoch_pure": _dim(
            surface_epoch_pure,
            (
                "every current Agent PRESENTED proposal and every B collective "
                "candidate must belong to the current OPEN epoch"
            ),
        ),
        "semantic_dedupe_not_uuid_dedupe": _dim(
            None,
            (
                "this strike did not create an equivalent cross-run future; "
                "deterministic regression remains supporting evidence only"
            ),
        ),
        "arrival_order_not_authority": _dim(
            arrival_order_not_authority,
            (
                "if mutation occurs it must be authorized from B/R2; A/R1 "
                "arrival or completion order may not confer authority"
            ),
        ),
        "approval_not_retargeted": _dim(
            approval_not_retargeted,
            (
                "requires a stale R1 approval; absence of approvals is not "
                "positive evidence"
            ),
        ),
        "exactly_one_or_zero_legal_plan_transition": _dim(
            legal_transition_cardinality,
            (
                f"executed_mutations={len(mutations)}; "
                f"active_plan={active_plan_id}; "
                f"accepted_proposal={accepted_proposal_id or None}"
            ),
        ),
        "no_duplicate_continuation_side_effect": _dim(
            continuation_exact_once,
            (
                "requires an exercised pending continuation; an empty set is "
                "not exactly-once evidence"
            ),
        ),
        "inherited_r28_exactly_once": _dim(
            True if regression_green else None,
            (
                f"focused regression: "
                f"{regression.get('passed') if regression else None} passed, "
                f"exit {regression.get('exit_code') if regression else None}"
            ),
        ),
        "authority_provenance_mode_accurate": _dim(
            authority_provenance_mode_accurate,
            (
                "an executed collective mutation must carry a current R2 "
                "UNANIMOUS_DOMINANCE receipt sourced from Agent B's proposal "
                "and algorithmic decision-epoch provenance"
            ),
        ),
        "truth_boundary_honest": _dim(
            bool(
                (checkpoint.get("truth_boundary") or {}).get("shock_source")
                == "SERVER_OWNED_PROVIDER_REPLAY_FIXTURE"
                and not (checkpoint.get("truth_boundary") or {}).get(
                    "physical_travel_proven"
                )
            ),
            "provider replay fixture; physical travel not claimed",
        ),
    }

    required_dimensions = {
        "strike_source_state_traceable",
        "concurrent_external_barrier",
        "standing_authority_preconfigured",
        "no_post_shock_human_authority_fabrication",
        "recovery_epoch_server_owned",
        "r1_opened_from_shock_a",
        "agent_a_external_and_bound_r1",
        "shock_b_material_not_storage_churn",
        "r1_superseded_by_r2",
        "agent_b_external_and_bound_r2",
        "stale_agent_authority_refused",
        "stale_result_typed_superseded",
        "agent_a_terminal_live_outcome",
        "exactly_one_or_zero_legal_plan_transition",
        "inherited_r28_exactly_once",
        "truth_boundary_honest",
    }
    if current_agent_rows or option_ids or mutations:
        required_dimensions.add("current_surface_epoch_pure")
    if mutations:
        required_dimensions.update(
            {
                "arrival_order_not_authority",
                "authority_provenance_mode_accurate",
            }
        )

    all_values = [
        item["verdict"] for item in dimensions.values()
    ]
    required_values = [
        dimensions[key]["verdict"]
        for key in sorted(required_dimensions)
    ]
    overall = (
        "CONTRADICTED"
        if "CONTRADICTED" in all_values
        else "PROVEN"
        if all(value == "PROVEN" for value in required_values)
        else "NOT_PROVEN"
    )
    return {
        "schema": "citynexus.r32.machine-verdict.v3",
        "overall": overall,
        "required_dimensions": sorted(required_dimensions),
        "coverage_not_proven": [
            key
            for key, item in dimensions.items()
            if key not in required_dimensions
            and item["verdict"] == "NOT_PROVEN"
        ],
        "dimensions": dimensions,
        "not_proven": [
            key
            for key, item in dimensions.items()
            if item["verdict"] == "NOT_PROVEN"
        ],
        "contradicted": [
            key
            for key, item in dimensions.items()
            if item["verdict"] == "CONTRADICTED"
        ],
        "agent_statuses": {
            "a": a_final.get("status"),
            "b": b_final.get("status"),
        },
        "stale_evidence_mode": (
            "LIVE_AGENT_STEP"
            if stale_steps
            else "SEPARATE_GATEWAY_BINDING_ASSERTION"
        ),
        "regression": regression,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--regression", type=Path, help="Actual focused regression receipt JSON; never assumed by default")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    regression = json.loads(args.regression.read_text(encoding="utf-8")) if args.regression else None
    result = verdict(json.loads(args.checkpoint.read_text(encoding="utf-8")), regression=regression)
    output = args.output or args.checkpoint.with_name("R32_MACHINE_VERDICT.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(output), "overall": result["overall"], "not_proven": result["not_proven"], "contradicted": result["contradicted"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
