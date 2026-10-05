from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
for _path in (BACKEND, SCRIPTS):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


PROVEN = "PROVEN"
NOT_PROVEN = "NOT_PROVEN"
CONTRADICTED = "CONTRADICTED"


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _verdict(status: str, reason: str, **facts: Any) -> dict[str, Any]:
    return {"status": status, "reason": reason, "facts": facts}


def _looks_external(provider_key: str | None, model_key: str | None) -> bool:
    text = f"{provider_key or ''} {model_key or ''}".lower()
    forbidden = (
        "local-test",
        "deterministic",
        "mock-model",
        "citynexus-local-agent",
        "fake-model",
    )
    return bool(provider_key and model_key) and not any(
        token in text for token in forbidden
    )



def _independent_choice_evidence(
    payload: dict[str, Any],
    required_member_ids: set[str],
    *,
    allowed_proposal_ids: set[str] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Recompute independent member maxima from the persisted decision surface."""

    allowed = (
        {str(value) for value in allowed_proposal_ids if value}
        if allowed_proposal_ids is not None
        else None
    )
    grounded_options = [
        item
        for item in payload.get("candidate_options") or []
        if isinstance(item, dict)
        and item.get("proposal_id")
        and item.get("status") == "GROUNDED_FEASIBLE"
        and (
            allowed is None
            or str(item.get("proposal_id") or "") in allowed
        )
    ]
    choices: dict[str, str] = {}
    errors: dict[str, str] = {}
    for member_id in sorted(required_member_ids):
        scored: list[tuple[float, str]] = []
        for option in grounded_options:
            fairness = option.get("fairness") or {}
            if member_id in {
                str(value)
                for value in fairness.get("unacceptable_member_ids") or []
            }:
                continue
            fits = option.get("member_fits") or {}
            fit = fits.get(member_id) if isinstance(fits, dict) else None
            if not isinstance(fit, dict):
                continue
            try:
                score = float(fit.get("effective_fit"))
            except (TypeError, ValueError):
                continue
            proposal_id = str(option.get("proposal_id") or "")
            if proposal_id:
                scored.append((score, proposal_id))
        if not scored:
            errors[member_id] = "no acceptable grounded member fit"
            continue
        best_score = max(score for score, _pid in scored)
        best_ids = sorted(
            pid
            for score, pid in scored
            if abs(score - best_score) <= 1e-9
        )
        if len(best_ids) != 1:
            errors[member_id] = "no unique grounded maximum: " + repr(
                best_ids
            )
            continue
        choices[member_id] = best_ids[0]

    if (
        required_member_ids
        and set(choices) == required_member_ids
        and not errors
        and len(set(choices.values())) != 1
    ):
        errors["__convergence__"] = (
            "members independently prefer different grounded futures: "
            + repr(choices)
        )
    return choices, errors

def _configure_checkpoint_db(checkpoint: dict[str, Any]) -> Path:
    raw = str(checkpoint.get("db") or "").strip()
    if not raw:
        raise SystemExit("R30 checkpoint has no database path")
    db = Path(raw).expanduser().resolve()
    if not db.is_file():
        raise SystemExit(f"R30 checkpoint database was not found: {db}")
    os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
    return db


def build_verdict(
    checkpoint: dict[str, Any],
    *,
    final_run_id: str | None = None,
) -> dict[str, Any]:
    # Import only after checkpoint DB binding so app.db.session connects to the
    # exact live-strike database rather than a default development database.
    from sqlalchemy import select

    from app.db.models import (
        AgentRun,
        AuditLog,
        Event,
        JourneyMission,
        ReplanProposal,
    )
    from app.db.session import SessionLocal

    interlock = checkpoint.get("interlock") or {}
    journey_id = str(checkpoint.get("journey_id") or "")
    round1_id = str(interlock.get("round1_mission_id") or "")
    mediator_id = str(interlock.get("mediator_mission_id") or "")
    selected_proposal_id = str(interlock.get("selected_proposal_id") or "")
    selected_plan_id = str(interlock.get("selected_plan_id") or "")
    e1 = str(interlock.get("decision_epoch_e1") or "")
    w1 = str(interlock.get("material_world_epoch_w1") or "")
    fit_subject_place_ids = {
        str(value)
        for value in interlock.get("fit_subject_place_ids") or []
        if value
    }

    verdicts: dict[str, dict[str, Any]] = {}

    with SessionLocal() as session:
        round1 = session.get(JourneyMission, round1_id) if round1_id else None
        mediator = session.get(JourneyMission, mediator_id) if mediator_id else None
        proposal = (
            session.get(ReplanProposal, selected_proposal_id)
            if selected_proposal_id
            else None
        )

        mediator_payload = (
            _json(mediator.clarification_json, {}) if mediator is not None else {}
        )
        durable_e1 = str(mediator_payload.get("decision_epoch") or "")
        durable_w1 = str(mediator_payload.get("material_world_epoch") or "")
        durable_selected = str(mediator_payload.get("selected_proposal_id") or "")
        epoch_binding_ok = bool(
            mediator is not None
            and mediator_payload.get("status") == "RESOLVED"
            and e1
            and w1
            and durable_e1 == e1
            and durable_w1 == w1
            and durable_selected == selected_proposal_id
            and proposal is not None
            and str(proposal.proposed_plan_version_id) == selected_plan_id
        )
        verdicts["e1_w1_durable_at_renewed_consent"] = _verdict(
            PROVEN if epoch_binding_ok else CONTRADICTED,
            "The renewed collective decision durably stores E1/W1 and the exact selected proposal."
            if epoch_binding_ok
            else "The stored renewed-consent epoch binding does not match the live interlock.",
            mediator_mission_id=mediator_id,
            clarification_status=mediator_payload.get("status"),
            decision_epoch=durable_e1,
            material_world_epoch=durable_w1,
            selected_proposal_id=durable_selected,
            selected_plan_id=selected_plan_id,
        )

        def _external_run_for_mission(mission_id: str) -> AgentRun | None:
            if not mission_id:
                return None
            rows = list(
                session.scalars(
                    select(AgentRun)
                    .where(AgentRun.mission_id == mission_id)
                    .order_by(AgentRun.created_at, AgentRun.id)
                ).all()
            )
            external = [
                row
                for row in rows
                if _looks_external(row.provider_key, row.model_key)
            ]
            return external[-1] if external else None

        round1_run = _external_run_for_mission(round1_id)
        round1_external_ok = round1_run is not None
        verdicts["real_external_round1_agent"] = _verdict(
            PROVEN if round1_external_ok else NOT_PROVEN,
            "A configured external AgentRun is persisted on the first collective mission."
            if round1_external_ok
            else "No configured external AgentRun is persisted for round 1.",
            run_id=round1_run.id if round1_run else None,
            provider_key=round1_run.provider_key if round1_run else None,
            model_key=round1_run.model_key if round1_run else None,
        )

        mediator_run = _external_run_for_mission(mediator_id)
        mediator_external_ok = mediator_run is not None
        verdicts["real_external_mediator"] = _verdict(
            PROVEN if mediator_external_ok else NOT_PROVEN,
            "A configured external AgentRun is persisted on the mediator mission."
            if mediator_external_ok
            else "No configured external mediator AgentRun is persisted.",
            run_id=mediator_run.id if mediator_run else None,
            provider_key=mediator_run.provider_key if mediator_run else None,
            model_key=mediator_run.model_key if mediator_run else None,
        )

        shock_ids = [
            str(value)
            for value in (
                (checkpoint.get("shock") or {})
                .get("signals", {})
                .get("created_event_ids", [])
            )
            if value
        ]
        shock_rows = [
            session.get(Event, event_id) for event_id in shock_ids
        ]
        targeted_shocks: list[dict[str, Any]] = []
        for row in shock_rows:
            if row is None:
                continue
            payload = _json(row.payload_json, {})
            scope_place_id = str(
                payload.get("scope_place_id")
                or payload.get("target_place_id")
                or ""
            )
            targeted_shocks.append(
                {
                    "event_id": row.id,
                    "provider_key": row.provider_key,
                    "provenance": row.provenance,
                    "event_type": row.event_type,
                    "scope_place_id": scope_place_id,
                    "incident_fingerprint": payload.get("incident_fingerprint"),
                }
            )
        trusted_shock_ok = bool(
            targeted_shocks
            and any(
                item["provider_key"] == "city-signal-fixture"
                and item["provenance"] == "PROVIDER_VERIFIED"
                and item["event_type"] == "CLOSURE"
                and item["scope_place_id"] in fit_subject_place_ids
                for item in targeted_shocks
            )
        )
        verdicts["server_owned_decision_material_shock"] = _verdict(
            PROVEN if trusted_shock_ok else CONTRADICTED,
            "Server-owned provider ingestion persisted a targeted verified closure on a consent-relevant Place."
            if trusted_shock_ok
            else "No persisted server-owned targeted closure is linked to the consented decision surface.",
            events=targeted_shocks,
            fit_subject_place_ids=sorted(fit_subject_place_ids),
        )

        denial_rows = list(
            session.scalars(
                select(AuditLog)
                .where(
                    AuditLog.journey_id == journey_id,
                    AuditLog.action == "collective.mutation.denied",
                    AuditLog.entity_type == "PlanVersion",
                    AuditLog.entity_id == selected_plan_id,
                )
                .order_by(AuditLog.created_at, AuditLog.id)
            ).all()
        )
        denial = None
        denial_after: dict[str, Any] = {}
        for row in reversed(denial_rows):
            after = _json(row.after_json, {})
            if (
                isinstance(after, dict)
                and after.get("code")
                == "COLLECTIVE_CONSENT_WORLD_EPOCH_STALE"
            ):
                denial = row
                denial_after = after
                break

        resolved_e = str(denial_after.get("resolved_decision_epoch") or "")
        current_e = str(denial_after.get("current_decision_epoch") or "")
        resolved_w = str(
            denial_after.get("resolved_material_world_epoch") or ""
        )
        current_w = str(
            denial_after.get("current_material_world_epoch") or ""
        )
        world_stale_ok = bool(
            denial is not None
            and resolved_e
            and resolved_e == current_e == e1
            and resolved_w
            and resolved_w == w1
            and current_w
            and current_w != resolved_w
        )
        verdicts["world_epoch_stale_semantic_epoch_stable"] = _verdict(
            PROVEN if world_stale_ok else CONTRADICTED,
            "The durable core denial proves semantic E stayed equal while material-world W changed."
            if world_stale_ok
            else "The core denial does not cleanly prove W-staleness with semantic parity.",
            denial_audit_id=denial.id if denial else None,
            mutation_kind=denial_after.get("mutation_kind"),
            resolved_decision_epoch=resolved_e,
            current_decision_epoch=current_e,
            resolved_material_world_epoch=resolved_w,
            current_material_world_epoch=current_w,
        )

        old_authority_safe = bool(
            proposal is not None and proposal.status != "ACCEPTED"
        )
        verdicts["old_authority_not_consumed"] = _verdict(
            PROVEN if old_authority_safe else CONTRADICTED,
            "The proposal selected under E1/W1 never became ACCEPTED."
            if old_authority_safe
            else "The stale E1/W1 proposal was accepted or is missing.",
            proposal_id=selected_proposal_id,
            proposal_status=proposal.status if proposal else None,
        )

        recovery_payload = (
            (checkpoint.get("external_recovery") or {}).get("payload") or {}
        )
        recovery_run_payload = (
            recovery_payload.get("run")
            if isinstance(recovery_payload, dict)
            else None
        )
        recovery_run_id = str(
            (recovery_run_payload or {}).get("run_id") or ""
        )
        recovery_run = (
            session.get(AgentRun, recovery_run_id)
            if recovery_run_id
            else None
        )
        denial_time = _dt(denial.created_at) if denial else None
        recovery_time = _dt(recovery_run.created_at) if recovery_run else None
        recovery_external_ok = bool(
            recovery_run is not None
            and _looks_external(
                recovery_run.provider_key, recovery_run.model_key
            )
            and (
                denial_time is None
                or recovery_time is None
                or recovery_time >= denial_time
            )
        )
        verdicts["real_external_post_shock_recovery_agent"] = _verdict(
            PROVEN if recovery_external_ok else NOT_PROVEN,
            "A configured external AgentRun is persisted after the stale-authority denial."
            if recovery_external_ok
            else "No configured external post-shock recovery AgentRun is durably proven.",
            run_id=recovery_run.id if recovery_run else None,
            provider_key=recovery_run.provider_key if recovery_run else None,
            model_key=recovery_run.model_key if recovery_run else None,
            denial_created_at=denial.created_at if denial else None,
            recovery_created_at=recovery_run.created_at if recovery_run else None,
        )

        # Fresh collective authority is discovered from persisted missions, not
        # from the checkpoint's convenience pointer. Exclude the already-used
        # R29 rounds and require a later authenticated resolved round.
        mission_rows = list(
            session.scalars(
                select(JourneyMission)
                .where(JourneyMission.journey_id == journey_id)
                .order_by(JourneyMission.created_at, JourneyMission.id)
            ).all()
        )
        fresh_candidates: list[tuple[JourneyMission, dict[str, Any]]] = []
        for row in mission_rows:
            if row.id in {round1_id, mediator_id}:
                continue
            payload = _json(row.clarification_json, {})
            if not isinstance(payload, dict):
                continue
            if payload.get("kind") != "COLLECTIVE_TRADEOFF":
                continue
            if denial_time is not None:
                created = _dt(row.created_at)
                if created is not None and created < denial_time:
                    continue
            fresh_candidates.append((row, payload))

        fresh_resolved = next(
            (
                (row, payload)
                for row, payload in reversed(fresh_candidates)
                if payload.get("status") == "RESOLVED"
                and payload.get("selected_proposal_id")
            ),
            None,
        )
        if fresh_resolved is None:
            accepted_after_denial = None
            accepted_authority: dict[str, Any] = {}
            accepted_rows = list(
                session.scalars(
                    select(AuditLog)
                    .where(
                        AuditLog.journey_id == journey_id,
                        AuditLog.action == "replan.accepted",
                        AuditLog.entity_type == "ReplanProposal",
                    )
                    .order_by(AuditLog.created_at, AuditLog.id)
                ).all()
            )
            for row in reversed(accepted_rows):
                created = _dt(row.created_at)
                if (
                    denial_time is not None
                    and created is not None
                    and created < denial_time
                ):
                    continue
                after = _json(row.after_json, {})
                authority = (
                    after.get("collective_authority")
                    if isinstance(after, dict)
                    and isinstance(after.get("collective_authority"), dict)
                    else {}
                )
                accepted_after_denial = row
                accepted_authority = authority
                break

            unanimous_no_reconsent_ok = bool(
                accepted_after_denial is not None
                and accepted_authority.get("classification")
                == "UNANIMOUS_DOMINANCE"
            )
            verdicts["fresh_selective_human_authority"] = _verdict(
                PROVEN if unanimous_no_reconsent_ok else NOT_PROVEN,
                "No fresh human round was needed because the final post-shock mutation was durably authorized as current UNANIMOUS_DOMINANCE."
                if unanimous_no_reconsent_ok
                else "No post-shock resolved collective round is persisted, and no durable unanimously-dominant mutation authority proves that re-consent was unnecessary.",
                post_shock_collective_rounds=[
                    {
                        "mission_id": row.id,
                        "status": payload.get("status"),
                        "required_member_ids": payload.get(
                            "required_member_ids"
                        ),
                    }
                    for row, payload in fresh_candidates
                ],
                accepted_audit_id=(
                    accepted_after_denial.id
                    if accepted_after_denial is not None
                    else None
                ),
                accepted_proposal_id=(
                    accepted_after_denial.entity_id
                    if accepted_after_denial is not None
                    else None
                ),
                collective_authority=accepted_authority,
            )
            verdicts["e2_w2_durable_when_required"] = _verdict(
                PROVEN if unanimous_no_reconsent_ok else NOT_PROVEN,
                "E2/W2 human authority is not required when current post-shock authority is unanimously dominant."
                if unanimous_no_reconsent_ok
                else "No fresh E2/W2 authority exists and the no-reconsent unanimous exception is not durably proven.",
                not_required=unanimous_no_reconsent_ok,
            )
        else:
            fresh_mission, fresh_payload = fresh_resolved
            required = {
                str(value)
                for value in fresh_payload.get("required_member_ids") or []
            }
            responses = (
                fresh_payload.get("responses")
                if isinstance(fresh_payload.get("responses"), dict)
                else {}
            )
            response_audits = list(
                session.scalars(
                    select(AuditLog)
                    .where(
                        AuditLog.action
                        == "agent.collective_decision.response",
                        AuditLog.entity_type == "JourneyMission",
                        AuditLog.entity_id == fresh_mission.id,
                        AuditLog.actor_type == "AUTHENTICATED_TRAVELER",
                    )
                    .order_by(AuditLog.created_at, AuditLog.id)
                ).all()
            )
            authenticated_members = {
                str((_json(row.after_json, {}) or {}).get("member_id") or "")
                for row in response_audits
            }
            independent_choices: dict[str, str] = {}
            independent_choice_errors: dict[str, str] = {}
            grounded_options = [
                item
                for item in fresh_payload.get("candidate_options") or []
                if isinstance(item, dict)
                and item.get("proposal_id")
                and item.get("status") == "GROUNDED_FEASIBLE"
            ]
            for member_id in sorted(required):
                scored: list[tuple[float, str]] = []
                for option in grounded_options:
                    fairness = option.get("fairness") or {}
                    if member_id in {
                        str(value)
                        for value in fairness.get(
                            "unacceptable_member_ids"
                        )
                        or []
                    }:
                        continue
                    fits = option.get("member_fits") or {}
                    fit = (
                        fits.get(member_id)
                        if isinstance(fits, dict)
                        else None
                    )
                    if not isinstance(fit, dict):
                        continue
                    try:
                        score = float(fit.get("effective_fit"))
                    except (TypeError, ValueError):
                        continue
                    scored.append(
                        (score, str(option.get("proposal_id") or ""))
                    )
                if not scored:
                    independent_choice_errors[member_id] = (
                        "no acceptable grounded member fit"
                    )
                    continue
                best_score = max(score for score, _pid in scored)
                best_ids = sorted(
                    pid
                    for score, pid in scored
                    if pid and abs(score - best_score) <= 1e-9
                )
                if len(best_ids) != 1:
                    independent_choice_errors[member_id] = (
                        "no unique grounded maximum: " + repr(best_ids)
                    )
                    continue
                independent_choices[member_id] = best_ids[0]

            selected_fresh = str(
                fresh_payload.get("selected_proposal_id") or ""
            )
            independent_convergence_ok = bool(
                required
                and set(independent_choices) == required
                and not independent_choice_errors
                and len(set(independent_choices.values())) == 1
                and set(independent_choices.values()) == {selected_fresh}
                and all(
                    isinstance(responses.get(member_id), dict)
                    and str(
                        responses[member_id].get("proposal_id") or ""
                    )
                    == independent_choices[member_id]
                    for member_id in required
                )
            )
            fresh_auth_ok = bool(
                required
                and required.issubset(set(responses))
                and required.issubset(authenticated_members)
                and independent_convergence_ok
            )
            verdicts["fresh_selective_human_authority"] = _verdict(
                PROVEN if fresh_auth_ok else CONTRADICTED,
                "The post-shock round is authenticated and every relevant member independently has the same unique grounded best option."
                if fresh_auth_ok
                else "Fresh authority is not proven as independent authenticated member convergence.",
                mission_id=fresh_mission.id,
                required_member_ids=sorted(required),
                response_member_ids=sorted(responses),
                authenticated_member_ids=sorted(authenticated_members),
                independent_member_choices=independent_choices,
                independent_choice_errors=independent_choice_errors,
                selected_proposal_id=selected_fresh,
            )

            e2 = str(fresh_payload.get("decision_epoch") or "")
            w2 = str(fresh_payload.get("material_world_epoch") or "")
            e2w2_ok = bool(
                e2
                and w2
                and w2 != w1
                and str(fresh_payload.get("selected_proposal_id") or "")
            )
            verdicts["e2_w2_durable_when_required"] = _verdict(
                PROVEN if e2w2_ok else CONTRADICTED,
                "Fresh post-shock authority durably stores a new world epoch."
                if e2w2_ok
                else "Fresh authority is missing a durable changed E2/W2 binding.",
                mission_id=fresh_mission.id,
                decision_epoch_e1=e1,
                decision_epoch_e2=e2,
                material_world_epoch_w1=w1,
                material_world_epoch_w2=w2,
                selected_proposal_id=fresh_payload.get(
                    "selected_proposal_id"
                ),
            )

    if final_run_id:
        try:
            from r28_machine_verdict import build_verdict as build_r28_verdict

            inherited = build_r28_verdict(final_run_id)
            r28_ok = (inherited.get("summary") or {}).get("overall") == PROVEN
            verdicts["final_exactly_once_continuation"] = _verdict(
                PROVEN if r28_ok else CONTRADICTED,
                "The final recovery run preserves R28 same-run approval and exactly-once continuation."
                if r28_ok
                else "The final recovery run violates an inherited R28 continuation invariant.",
                final_run_id=final_run_id,
                r28_summary=inherited.get("summary"),
                r28_binding=inherited.get("binding"),
            )
        except SystemExit as exc:
            verdicts["final_exactly_once_continuation"] = _verdict(
                CONTRADICTED,
                "The supplied final recovery run cannot be verified by the inherited R28 machine verifier.",
                final_run_id=final_run_id,
                error=str(exc),
            )
    else:
        verdicts["final_exactly_once_continuation"] = _verdict(
            NOT_PROVEN,
            "No final recovery AgentRun id was supplied yet.",
        )

    # The unrelated-observation control is deliberately not inferred from lack
    # of DB churn. A focused deterministic control or durable live control must
    # explicitly prove it.
    control = checkpoint.get("unrelated_observation_control")
    control_ok = bool(
        isinstance(control, dict)
        and control.get("before_epoch")
        and control.get("before_epoch") == control.get("after_epoch")
        and control.get("unrelated") is True
    )
    verdicts["unrelated_observation_does_not_invalidate"] = _verdict(
        PROVEN if control_ok else NOT_PROVEN,
        "An explicit control proves unrelated evidence churn leaves W unchanged."
        if control_ok
        else "No explicit unrelated-observation epoch-equivalence control is present in the live checkpoint.",
        control=control,
    )

    counts = {PROVEN: 0, NOT_PROVEN: 0, CONTRADICTED: 0}
    for item in verdicts.values():
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    overall = (
        PROVEN
        if counts[CONTRADICTED] == 0 and counts[NOT_PROVEN] == 0
        else CONTRADICTED
        if counts[CONTRADICTED] > 0
        else NOT_PROVEN
    )
    return {
        "schema_version": "R30_MACHINE_VERDICT_V1",
        "inputs": {
            "journey_id": journey_id,
            "round1_mission_id": round1_id,
            "mediator_mission_id": mediator_id,
            "selected_proposal_id_e1w1": selected_proposal_id,
            "selected_plan_id_e1w1": selected_plan_id,
            "final_recovery_run_id": final_run_id,
        },
        "verdicts": verdicts,
        "summary": {**counts, "overall": overall},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the machine-derived Revolution R30 consent-epoch "
            "shock-recovery verdict."
        )
    )
    parser.add_argument(
        "--checkpoint",
        required=True,
        help="R30_LIVE_CHECKPOINT.json produced by run_r30_live.py",
    )
    parser.add_argument(
        "--final-run-id",
        help="Final post-shock recovery AgentRun id after any fresh authority",
    )
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint).expanduser().resolve()
    if not checkpoint_path.is_file():
        raise SystemExit(f"R30 checkpoint not found: {checkpoint_path}")
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    _configure_checkpoint_db(checkpoint)

    report = build_verdict(
        checkpoint,
        final_run_id=args.final_run_id,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if report["summary"]["overall"] == PROVEN else 1)


if __name__ == "__main__":
    main()
