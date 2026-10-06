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
    provider_calls_real = runtime.get("provider_calls_were_real") is True
    a_external = (
        provider_calls_real
        and a.get("provider_key") == "hermes"
        and any(row.get("run_id") == a.get("id") for row in steps)
    )
    b_external = (
        provider_calls_real
        and b.get("provider_key") == "hermes"
        and any(row.get("run_id") == b.get("id") for row in steps)
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

    # Current executable Agent surface: legacy setup rows are historical input
    # but every currently PRESENTED Agent-discovered proposal must belong to
    # the one OPEN recovery epoch.  If B opened a collective clarification,
    # every candidate option in that surface must resolve to one of those rows.
    current_agent_presented = [
        row
        for row in proposals
        if row.get("source_agent_run_id")
        and row.get("status") == "PRESENTED"
    ]
    current_agent_ids = {
        str(row.get("id"))
        for row in current_agent_presented
        if row.get("recovery_epoch_id") == current_id
    }
    b_payload = (
        (checkpoint.get("agent_responses") or {})
        .get("agent_b", {})
        .get("payload", {})
    )
    clarification = (b_payload.get("mission") or {}).get("clarification") or {}
    option_ids = {
        str(item.get("proposal_id"))
        for item in clarification.get("candidate_options") or []
        if isinstance(item, dict) and item.get("proposal_id")
    }
    surface_epoch_pure = (
        True
        if current_agent_presented
        and all(
            row.get("recovery_epoch_id") == current_id
            for row in current_agent_presented
        )
        and option_ids
        and option_ids.issubset(current_agent_ids)
        else None
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
            continuation_exact_once = len(approval_ids) == len(set(approval_ids))

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
    zero_legal_transition = (
        not mutations
        and (final.get("journey") or {}).get("active_plan_version_id")
        == (checkpoint.get("setup") or {}).get("active_plan_id")
    )
    regression_green = bool(
        regression
        and regression.get("exit_code") == 0
        and regression.get("passed", 0) >= 129
        and regression.get("failed") == 0
    )

    dimensions = {
        "recovery_epoch_server_owned": _dim(
            bool(r1id and r2id and r1id != r2id),
            "R1/R2 are distinct persisted server-created ids",
        ),
        "r1_opened_from_shock_a": _dim(
            bool(r1.get("triggering_event_ids") and r1.get("fingerprint")),
            "R1 has provider Event lineage and a recovery fingerprint",
        ),
        "agent_a_external_and_bound_r1": _dim(
            bool(
                a_external
                and a.get("recovery_epoch_id") == r1id
                and checkpoint.get("agent_a_bound_before_shock_b")
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
            bool(
                b_external
                and b.get("recovery_epoch_id") == r2id
                and checkpoint.get("agent_b_bound_after_shock_b")
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
            None,
            "no authority-bearing competing arrival was exercised",
        ),
        "approval_not_retargeted": _dim(
            approval_not_retargeted,
            (
                "requires a stale R1 approval; absence of approvals is not "
                "positive evidence"
            ),
        ),
        "exactly_one_or_zero_legal_plan_transition": _dim(
            True if zero_legal_transition else None,
            (
                "zero executed mutation with unchanged active plan is a legal "
                "convergence outcome for this path"
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
            None if not receipts else None,
            (
                "requires an authority receipt plus its mutation/gate "
                "provenance in this strike"
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

    values = [item["verdict"] for item in dimensions.values()]
    overall = (
        "CONTRADICTED"
        if "CONTRADICTED" in values
        else "PROVEN"
        if all(value == "PROVEN" for value in values)
        else "NOT_PROVEN"
    )
    return {
        "schema": "citynexus.r32.machine-verdict.v2",
        "overall": overall,
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
