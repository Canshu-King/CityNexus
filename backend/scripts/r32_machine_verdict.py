"""Machine verdict for the R32 live strike checkpoint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _dim(value: bool | None, evidence: str) -> dict[str, Any]:
    return {"verdict": "PROVEN" if value is True else "CONTRADICTED" if value is False else "NOT_PROVEN", "evidence": evidence}


def verdict(checkpoint: dict[str, Any], *, regression: dict[str, Any] | None = None) -> dict[str, Any]:
    final = checkpoint.get("final") or {}
    epochs = final.get("epochs") or []
    runs = final.get("runs") or []
    proposals = final.get("proposals") or []
    receipts = final.get("receipts") or []
    approvals = final.get("approvals") or []
    pending = final.get("pending_actions") or []
    r1 = checkpoint.get("r1") or {}
    r2 = checkpoint.get("r2") or {}
    r1id, r2id = r1.get("id"), r2.get("id")
    a = checkpoint.get("agent_a_run_at_barrier") or {}
    b = checkpoint.get("agent_b_run_at_barrier") or {}
    stale = checkpoint.get("stale_binding_assertion") or {}
    current_id = checkpoint.get("current_epoch_id")
    a_final = next((row for row in runs if row.get("id") == a.get("id")), {})
    b_final = next((row for row in runs if row.get("id") == b.get("id")), {})
    r1row = next((row for row in epochs if row.get("id") == r1id), {})
    r2row = next((row for row in epochs if row.get("id") == r2id), {})
    current_proposals = [row for row in proposals if row.get("recovery_epoch_id") == current_id]
    stale_proposals = [row for row in proposals if row.get("recovery_epoch_id") == r1id]
    stale_receipts = [row for row in receipts if row.get("recovery_epoch_id") == r1id]
    stale_steps = [
        row for row in final.get("steps") or []
        if row.get("run_id") == a.get("id") and row.get("result", {}).get("code") == "RECOVERY_EPOCH_SUPERSEDED"
    ]
    steps = final.get("steps") or []
    a_external = a.get("provider_key") == "hermes" and any(row.get("run_id") == a.get("id") for row in steps)
    b_external = b.get("provider_key") == "hermes" and any(row.get("run_id") == b.get("id") for row in steps)
    mutations = [row for row in steps if row.get("tool_name") in {"accept_replan", "activate_standby", "replace_activity", "reschedule_activity"} and row.get("result", {}).get("executed") is True]
    regression_green = bool(regression and regression.get("exit_code") == 0 and regression.get("passed", 0) >= 129 and regression.get("failed") == 0)
    dimensions = {
        "recovery_epoch_server_owned": _dim(bool(r1id and r2id and r1id != r2id), "R1/R2 are persisted server-created ids"),
        "r1_opened_from_shock_a": _dim(bool(r1.get("triggering_event_ids") and r1.get("fingerprint")), "R1 has provider event lineage and fingerprint"),
        "agent_a_external_and_bound_r1": _dim(bool(a_external and a.get("recovery_epoch_id") == r1id and checkpoint.get("agent_a_bound_before_shock_b")), f"Agent A provider={a.get('provider_key')} epoch={a.get('recovery_epoch_id')}; real model-selected tools persisted"),
        "shock_b_material_not_storage_churn": _dim(bool(r1.get("fingerprint") and r2.get("fingerprint") and r1.get("fingerprint") != r2.get("fingerprint")), "R1 and R2 reality fingerprints differ"),
        "r1_superseded_by_r2": _dim(bool(r1row.get("status") == "SUPERSEDED" and r1row.get("superseded_by_recovery_epoch_id") == r2id and r2row.get("status") == "OPEN"), "R1 SUPERSEDED -> R2 OPEN"),
        "agent_b_external_and_bound_r2": _dim(bool(b_external and b.get("recovery_epoch_id") == r2id and checkpoint.get("agent_b_bound_after_shock_b")), f"Agent B provider={b.get('provider_key')} epoch={b.get('recovery_epoch_id')}; independent model-selected tools persisted"),
        "stale_agent_authority_refused": _dim(bool(stale.get("typed") or stale_steps), "Gateway binding assertion or live AgentRun step refused stale R1"),
        "stale_result_typed_superseded": _dim(bool(stale.get("typed") or stale_steps), "typed RECOVERY_EPOCH_SUPERSEDED evidence"),
        "agent_a_terminal_live_outcome": _dim(True if a_final.get("status") == "SUPERSEDED" and stale_steps else None, f"A durable status={a_final.get('status')}; its natural typed stale terminal classification remains unproven"),
        "r1_candidates_removed_from_current_surface": _dim(all(row.get("status") != "PRESENTED" for row in stale_proposals) if stale_proposals else None, "R1 proposal retirement evaluated only when R1 rows exist"),
        "r1_receipts_invalidated": _dim(all(row.get("invalidated_at") and row.get("invalidation_code") == "RECOVERY_EPOCH_SUPERSEDED" for row in stale_receipts) if stale_receipts else None, "R1 receipt invalidation evaluated only when receipts exist"),
        "current_surface_epoch_pure": _dim(None, "R2 agent proposals are epoch-bound, but legacy setup proposals are unbound; a complete current-surface check was not captured"),
        "semantic_dedupe_not_uuid_dedupe": _dim(None, "R2 created two distinct semantic identities; no equivalent A/B pair exercised deduplication"),
        "arrival_order_not_authority": _dim(None, "No final mutation occurred, so arrival-order authority was not exercised"),
        "approval_not_retargeted": _dim(True if not approvals else all(row.get("recovery_epoch_id") in {None, current_id} for row in approvals), "No approval was retargeted"),
        "exactly_one_or_zero_legal_plan_transition": _dim(True if not mutations and final.get("journey", {}).get("active_plan_version_id") == checkpoint.get("setup", {}).get("active_plan_id") else None, "Zero executed model mutation and active plan equals baseline; legality of a mutation must be separately verified"),
        "no_duplicate_continuation_side_effect": _dim(not pending, "No duplicate pending continuation side effect"),
        "inherited_r28_exactly_once": _dim(True if regression_green else None, f"Focused regression: {regression.get('passed') if regression else None} passed, exit {regression.get('exit_code') if regression else None}"),
        "authority_provenance_mode_accurate": _dim(None, "No authority receipt was issued in this run"),
        "truth_boundary_honest": _dim(bool((checkpoint.get("truth_boundary") or {}).get("shock_source") == "SERVER_OWNED_PROVIDER_REPLAY_FIXTURE" and not (checkpoint.get("truth_boundary") or {}).get("physical_travel_proven")), "provider replay fixture; physical travel not claimed"),
    }
    values = [item["verdict"] for item in dimensions.values()]
    overall = "CONTRADICTED" if "CONTRADICTED" in values else "PROVEN" if all(value == "PROVEN" for value in values) else "NOT_PROVEN"
    return {"schema": "citynexus.r32.machine-verdict.v1", "overall": overall, "dimensions": dimensions, "not_proven": [key for key, item in dimensions.items() if item["verdict"] == "NOT_PROVEN"], "contradicted": [key for key, item in dimensions.items() if item["verdict"] == "CONTRADICTED"], "agent_statuses": {"a": a_final.get("status"), "b": b_final.get("status")}, "stale_evidence_mode": "LIVE_AGENT_STEP" if stale_steps else "SEPARATE_GATEWAY_BINDING_ASSERTION", "regression": regression}


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
