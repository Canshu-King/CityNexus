"""R30 live consent-epoch shock and recovery harness.

The operator harness creates a fresh provider-backed Journey, drives the
already-closed R29 disagreement far enough to pause before acceptance, sends a
real signal through the CityNexus fixture ingestion seam, and then records the
old-consent refusal plus a fresh external-Agent recovery round.  It never
edits a candidate plan or consent envelope directly.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_r28_live import BACKEND, ROOT, _api_setup, _configure as _base_configure


OUTPUT_DIR = ROOT / "output" / "revolution-r30-live-20261006"
RECEIPT_PATH = OUTPUT_DIR / "R30_LIVE_RECEIPT.json"


def _configure() -> Path:
    """Configure the real provider with a bounded but adequate live read budget."""

    db = _base_configure()
    # The GPT branch's Hermes tool context is intentionally large.  Keep the
    # provider real and bounded, while allowing the model enough time to emit
    # the next tool call instead of treating a slow external response as a
    # deterministic fallback condition.
    os.environ["CITYNEXUS_IMPACT_TIMEOUT_SECONDS"] = os.getenv(
        "CITYNEXUS_R30_IMPACT_TIMEOUT_SECONDS", "600"
    )
    return db


def _configure_existing_db(value: str) -> Path:
    _configure()
    db = Path(value).expanduser().resolve()
    if not db.is_file():
        raise RuntimeError(f"R30 strike database was not found: {db}")
    os.environ["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
    return db


def _json(raw: str | None, fallback: Any) -> Any:
    try:
        value = json.loads(raw or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return value


def _first_mission_id(first: dict[str, Any]) -> str:
    payload = first.get("payload") or {}
    mission = payload.get("mission") if isinstance(payload, dict) else None
    run = payload.get("run") if isinstance(payload, dict) else None
    mission_id = (mission or {}).get("id") or (run or {}).get("mission_id")
    if not mission_id:
        raise RuntimeError("external Agent did not expose its persisted mission id")
    return str(mission_id)


def _member_choice(clarification: dict[str, Any], member_id: str) -> str:
    scored: list[tuple[float, str]] = []
    for option in clarification.get("candidate_options") or []:
        if not isinstance(option, dict) or not option.get("proposal_id"):
            continue
        fit = (option.get("member_fits") or {}).get(member_id)
        if not isinstance(fit, dict):
            continue
        try:
            score = float(fit.get("effective_fit"))
        except (TypeError, ValueError):
            continue
        scored.append((score, str(option["proposal_id"])))
    if not scored:
        raise RuntimeError(f"no server-computed fit for member {member_id}")
    best = max(score for score, _ in scored)
    choices = sorted(proposal_id for score, proposal_id in scored if abs(score - best) <= 1e-9)
    if len(choices) != 1:
        raise RuntimeError(f"member {member_id} has tied best choices: {choices}")
    return choices[0]


def _best_shared_choice(clarification: dict[str, Any], member_ids: list[str]) -> str:
    """Choose one fresh grounded option without carrying an E1 response over."""

    ranked: list[tuple[float, float, str]] = []
    for option in clarification.get("candidate_options") or []:
        if not isinstance(option, dict) or not option.get("proposal_id"):
            continue
        fits = option.get("member_fits") or {}
        scores: list[float] = []
        for member_id in member_ids:
            fit = fits.get(member_id) if isinstance(fits, dict) else None
            if not isinstance(fit, dict):
                break
            try:
                scores.append(float(fit.get("effective_fit")))
            except (TypeError, ValueError):
                break
        if len(scores) != len(member_ids):
            continue
        ranked.append((min(scores), sum(scores), str(option["proposal_id"])))
    if not ranked:
        raise RuntimeError("fresh collective round has no shared grounded option")
    ranked.sort(reverse=True)
    return ranked[0][2]


def _signed_tokens(member_ids: list[str]) -> dict[str, str]:
    from run_r29_live import _signed_member_tokens

    return _signed_member_tokens(member_ids)


def _owner_member_for_journey(journey_id: str) -> str:
    from sqlalchemy import select

    from app.db.models import JourneyMember
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(JourneyMember).where(JourneyMember.journey_id == journey_id)
            ).all()
        )
    owners = [row.id for row in rows if row.role == "OWNER"]
    if len(owners) != 1:
        raise RuntimeError(f"Journey must have exactly one OWNER: {owners}")
    return str(owners[0])


def _approval_id_from_run(run_payload: dict[str, Any], journey_id: str) -> str | None:
    from run_r29_live import _approval_id_from_run as helper

    return helper(run_payload, journey_id)


def _round1_and_mediator(client, journey_id: str, round1_mission_id: str) -> dict[str, Any]:
    """Run R29's social setup, stopping immediately after E1 resolves."""

    from app.db.models import JourneyMission
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        round1 = session.get(JourneyMission, round1_mission_id)
        if round1 is None:
            raise RuntimeError("round-1 mission not found")
        clarification = _json(round1.clarification_json, {})
    if clarification.get("status") != "WAITING_FOR_MEMBERS":
        raise RuntimeError(f"round-1 is not waiting: {clarification.get('status')}")
    required = [str(item) for item in clarification.get("required_member_ids") or []]
    if len(required) != 2:
        raise RuntimeError(f"expected exactly two round-1 members: {required}")
    choices = [_member_choice(clarification, member_id) for member_id in required]
    if choices[0] == choices[1]:
        raise RuntimeError("provider-backed setup did not produce disagreement")
    tokens = _signed_tokens(required)
    path = f"/api/v1/journeys/{journey_id}/missions/{round1_mission_id}/collective-clarification"
    responses = []
    for member_id, proposal_id in zip(required, choices):
        response = client.post(
            f"{path}/{member_id}",
            headers={"Authorization": f"Bearer {tokens[member_id]}"},
            json={"clarification_id": clarification["clarification_id"], "proposal_id": proposal_id},
        )
        if response.status_code >= 400:
            raise RuntimeError(f"round-1 response failed: {response.status_code} {response.text}")
        responses.append(response.json())
    disagreement = responses[-1]
    mediator_id = str((disagreement.get("child_mission") or {}).get("id") or "")
    if disagreement.get("status") != "MEDIATION_REQUIRED" or not mediator_id:
        raise RuntimeError(f"round-1 did not create mediator: {json.dumps(disagreement)}")

    mediator_resume = client.post(f"/api/v1/journeys/{journey_id}/missions/{mediator_id}/resume")
    if mediator_resume.status_code >= 400:
        raise RuntimeError(f"mediator resume failed: {mediator_resume.status_code} {mediator_resume.text}")
    mediator_payload = mediator_resume.json()
    mediator_run = mediator_payload.get("run") or {}
    with SessionLocal() as session:
        mediator = session.get(JourneyMission, mediator_id)
        if mediator is None:
            raise RuntimeError("mediator mission disappeared")
        round2 = _json(mediator.clarification_json, {})
    if round2.get("status") != "WAITING_FOR_MEMBERS":
        raise RuntimeError(f"mediator did not open a fresh round: {round2.get('status')}")
    progress = round2.get("mediation_progress") or {}
    improved_ids = {str(item) for item in progress.get("improved_option_ids") or []}
    if progress.get("allowed") is not True or not improved_ids:
        raise RuntimeError(f"mediator progress is not server-proven: {progress}")
    round2_required = [str(item) for item in round2.get("required_member_ids") or []]
    if set(round2_required) != set(required):
        raise RuntimeError(f"renewed member scope changed unexpectedly: {round2_required}")
    improved_options = [
        item for item in round2.get("candidate_options") or []
        if isinstance(item, dict) and str(item.get("proposal_id")) in improved_ids
    ]
    if not improved_options:
        raise RuntimeError("mediator progress does not point to a fresh selectable option")
    # Pick the best server-ranked improved option, without giving the model or
    # harness a proposal id that was not in the persisted progress surface.
    scored: list[tuple[float, float, str]] = []
    for item in improved_options:
        fairness = item.get("fairness") or {}
        try:
            minimum_fit = float(fairness.get("minimum_member_fit"))
        except (TypeError, ValueError):
            minimum_fit = -1.0
        try:
            regret = float(fairness.get("maximum_regret"))
        except (TypeError, ValueError):
            regret = 1.0
        scored.append((minimum_fit, -regret, str(item["proposal_id"])))
    improved_choice = sorted(scored, reverse=True)[0][2]

    round2_tokens = _signed_tokens(round2_required)
    round2_path = f"/api/v1/journeys/{journey_id}/missions/{mediator_id}/collective-clarification"
    renewed = []
    for index, member_id in enumerate(round2_required):
        response = client.post(
            f"{round2_path}/{member_id}",
            headers={"Authorization": f"Bearer {round2_tokens[member_id]}"},
            json={"clarification_id": round2["clarification_id"], "proposal_id": improved_choice},
        )
        if response.status_code >= 400:
            raise RuntimeError(f"round-2 response failed: {response.status_code} {response.text}")
        body = response.json()
        renewed.append(body)
        if index == 0 and body.get("status") != "WAITING_FOR_MEMBERS":
            raise RuntimeError("first renewed response advanced before all members answered")
    resolved = renewed[-1]
    child_id = str((resolved.get("child_mission") or {}).get("id") or "")
    if resolved.get("status") != "RESOLVED" or not child_id:
        raise RuntimeError(f"renewed round did not resolve: {json.dumps(resolved)}")
    with SessionLocal() as session:
        row = session.get(JourneyMission, mediator_id)
        if row is None:
            raise RuntimeError("resolved mediator mission disappeared")
        resolved_clarification = _json(row.clarification_json, {})
    return {
        "round1_mission_id": round1_mission_id,
        "round1_required_member_ids": required,
        "round1_choices": dict(zip(required, choices)),
        "mediator_mission_id": mediator_id,
        "mediator_run_id": mediator_run.get("run_id"),
        "mediator_run": mediator_run,
        "round2_clarification": round2,
        "round2_required_member_ids": round2_required,
        "round2_responses": renewed,
        "resolved_clarification": resolved_clarification,
        "resolved_child_id": child_id,
        "selected_proposal_id": str(resolved_clarification.get("selected_proposal_id") or improved_choice),
        "pre_acceptance": True,
    }


def _epoch_snapshot(journey_id: str, mission_id: str, selected_proposal_id: str) -> dict[str, Any]:
    from sqlalchemy import select

    from app.collective_mediation import (
        collective_decision_epoch,
        collective_material_world_epoch,
    )
    from app.db.models import Journey, JourneyMission, PlanVersion, ReplanProposal
    from app.db.session import SessionLocal
    from app.main import (
        active_journey_members_with_capabilities,
        collective_material_world_basis,
        collective_proposal_receipt,
    )

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        mission = session.get(JourneyMission, mission_id)
        proposal = session.get(ReplanProposal, selected_proposal_id)
        if journey is None or mission is None or proposal is None:
            raise RuntimeError("resolved consent lineage disappeared before shock")
        stored = _json(mission.clarification_json, {})
        trigger_id = str(stored.get("trigger_event_id") or proposal.trigger_event_id or "")
        proposals = session.scalars(
            select(ReplanProposal).where(
                ReplanProposal.journey_id == journey.id,
                ReplanProposal.trigger_event_id == trigger_id,
                ReplanProposal.status == "PRESENTED",
            ).order_by(ReplanProposal.created_at, ReplanProposal.id)
        ).all()
        receipt = collective_proposal_receipt(session, journey, proposals)
        options = [
            item for item in receipt.get("proposal_collective_decisions", {}).values()
            if str(item.get("proposal_id")) in {
                str(item.get("proposal_id")) for item in stored.get("candidate_options") or []
            }
            and item.get("status") == "GROUNDED_FEASIBLE"
        ]
        members = active_journey_members_with_capabilities(session, journey).get("members", [])
        epoch = collective_decision_epoch(
            journey_id=journey.id,
            mission_id=mission.id,
            trigger_event_id=trigger_id,
            base_plan_version_id=journey.active_plan_version_id,
            options=options,
            required_member_ids=stored.get("required_member_ids") or [],
            members=members,
        )
        selected_option = next(
            (
                item
                for item in stored.get("candidate_options") or []
                if isinstance(item, dict)
                and str(item.get("proposal_id") or "") == str(proposal.id)
            ),
            {},
        )
        selected_plan = session.get(PlanVersion, proposal.proposed_plan_version_id)
        if selected_plan is None:
            raise RuntimeError("selected plan disappeared before world-epoch snapshot")
        world_basis = collective_material_world_basis(
            session,
            journey,
            selected_plan,
            fit_subject_place_ids=list(selected_option.get("fit_subject_place_ids") or []),
        )
        world_epoch = collective_material_world_epoch(world_basis)
        return {
            "mission_id": mission.id,
            "clarification_id": stored.get("clarification_id"),
            "trigger_event_id": trigger_id,
            "base_plan_version_id": journey.active_plan_version_id,
            "selected_proposal_id": proposal.id,
            "selected_plan_version_id": proposal.proposed_plan_version_id,
            "stored_consent_epoch": stored.get("consent_epoch") or stored.get("decision_epoch"),
            "recomputed_consent_epoch": epoch,
            "stored_material_world_epoch": stored.get("material_world_epoch"),
            "recomputed_material_world_epoch": world_epoch,
            "material_world_basis": world_basis,
            "required_member_ids": [str(item) for item in stored.get("required_member_ids") or []],
        }


def _record_irrelevant_churn(journey_id: str) -> dict[str, Any]:
    from app.agent.signal_pipeline import _record_observation
    from app.db.models import Journey
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError("Journey disappeared while recording control churn")
        row = _record_observation(
            session,
            journey,
            state="CAPTURED",
            payload={"r30_control": "irrelevant-provider-churn", "scope": "unrelated-city-fact"},
            fingerprints=[],
            captured_at="2026-10-08T10:04:00+09:00",
            provider_key="r30-control-provider",
            provenance="PROVIDER_VERIFIED",
            observation_type="CITY_SIGNAL",
        )
        session.commit()
        return {"observation_id": row.id, "provider_key": row.provider_key}


def _inject_provider_shock(
    journey_id: str,
    selected_plan_id: str,
    selected_place_id: str,
) -> dict[str, Any]:
    from sqlalchemy import select

    from app.agent.signal_pipeline import (
        _record_observation,
        _upsert_fixture_event,
        refresh_demo_signals,
        set_fixture_state,
    )
    from app.db.models import Activity, Journey
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError("Journey disappeared before provider shock")
        fixture = set_fixture_state(
            session,
            journey,
            state="DISRUPTED",
            payload={
                "r30_shock": "PROVIDER_VERIFIED_DECISION_MATERIAL_CHANGE",
                "scope_place_id": selected_place_id,
                "closure": True,
                "extra_minutes": 20,
            },
        )
        signals = refresh_demo_signals(
            session,
            journey,
            captured_at="2026-10-08T10:05:00+09:00",
        )
        selected_activity = session.scalar(
            select(Activity)
            .where(
                Activity.plan_version_id == selected_plan_id,
                Activity.place_id == selected_place_id,
            )
            .order_by(Activity.sequence_no, Activity.id)
        )
        if selected_activity is None:
            raise RuntimeError(
                "selected compromise plan has no activity for the provider shock place"
            )
        closure, closure_created = _upsert_fixture_event(
            session,
            journey,
            event_type="CLOSURE",
            severity="CRITICAL",
            activity=selected_activity,
            scope_key=selected_place_id,
            occurred_at="2026-10-08T10:05:00+09:00",
            payload={
                "description": "Provider verified closure of the selected future stop",
                "disruption_class": "PLACE_CLOSURE",
                # Keep the provider event target explicit at the event
                # boundary.  The replan authority deliberately refuses to
                # guess a current/first activity when only a place scope is
                # present; this is the normal provider-backed grounding link.
                "affected_activity_id": selected_activity.id,
                "fixture_revision": fixture.revision,
                "scope_place_id": selected_place_id,
            },
            provenance="PROVIDER_VERIFIED",
        )
        closure_payload = _json(closure.payload_json, {})
        linked_observation = _record_observation(
            session,
            journey,
            state="DISRUPTED",
            payload={
                "event_id": closure.id,
                "scope_place_id": selected_place_id,
                "fixture_revision": fixture.revision,
                "provider_assertion": "CLOSURE",
            },
            fingerprints=[str(closure_payload.get("incident_fingerprint") or closure.id)],
            captured_at="2026-10-08T10:05:00+09:00",
            provider_key="city-signal-fixture",
            provenance="PROVIDER_VERIFIED",
            observation_type="CITY_SIGNAL",
        )
        session.commit()
        return {
            "fixture": {
                "state": fixture.state,
                "revision": fixture.revision,
                "payload": _json(fixture.payload_json, {}),
            },
            "signals": signals.to_dict(),
            "closure_event_id": closure.id,
            "closure_event_created": closure_created,
            "closure_activity_id": selected_activity.id,
            "closure_observation_id": linked_observation.id,
        }


def _attempt_old_mutation(client, journey_id: str, child_id: str, proposal_id: str, owner_member_id: str) -> dict[str, Any]:
    """Resume the resolved child and consume its approval; expect core stale refusal."""

    resumed = client.post(f"/api/v1/journeys/{journey_id}/missions/{child_id}/resume")
    if resumed.status_code >= 400:
        raise RuntimeError(f"old resolved child resume failed: {resumed.status_code} {resumed.text}")
    resumed_payload = resumed.json()
    run = resumed_payload.get("run") or {}
    approval_id = _approval_id_from_run(run, journey_id)
    approval_payload = None
    continuation = None
    if approval_id:
        from run_r29_live import _signed_member_tokens

        owner_token = _signed_member_tokens([owner_member_id])[owner_member_id]
        approval = client.post(
            f"/api/v1/journeys/{journey_id}/agent/approvals/{approval_id}/approve",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"approval_method": "USER_CONFIRMATION"},
        )
        approval_payload = approval.json()
        continuation = approval_payload.get("continuation")
    return {
        "resume_status": resumed.status_code,
        "resume_payload": resumed_payload,
        "resume_run_id": run.get("run_id"),
        "approval_id": approval_id,
        "approval_payload": approval_payload,
        "continuation": continuation,
        "expected_proposal_id": proposal_id,
    }


def _run_external_recovery(client, journey_id: str) -> dict[str, Any]:
    command = (
        "Recover from the latest provider-backed city incident. Inspect the current JourneyTwin and "
        "event evidence first. The previously resolved collective proposal and every response from "
        "that round are stale and must not be accepted, copied, or used as a sibling fallback. "
        "Use the latest CRITICAL provider closure on the future non-anchor candidate, including "
        "its explicit affected activity; ignore any older closure that targets the protected C4 "
        "anchor. "
        "to create a fresh server-owned request_replan surface. Do not pass a composite or "
        "unresolved event target; use only grounded replacement places returned by the server. "
        "preserve the protected C4 anchor and completed execution truth, and if the fresh grounded "
        "future still contains a material shared trade-off, open a new request_collective_decision "
        "for only the currently relevant members. Do not mutate active reality until the fresh "
        "authority is resolved."
    )
    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={"command": command, "requested_autonomy": "EXECUTE_WITHIN_BOUNDS"},
    )
    if response.status_code >= 400:
        raise RuntimeError(f"post-shock external recovery failed: {response.status_code} {response.text}")
    return response.json()


def _fresh_round_for_mission(journey_id: str, mission_id: str) -> tuple[str, dict[str, Any]] | None:
    from sqlalchemy import select

    from app.db.models import JourneyMission
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(JourneyMission).where(JourneyMission.journey_id == journey_id)
            ).all()
        )
    for row in sorted(rows, key=lambda item: (str(item.created_at), item.id), reverse=True):
        clarification = _json(row.clarification_json, {})
        if (
            clarification.get("kind") == "COLLECTIVE_TRADEOFF"
            and clarification.get("status") == "WAITING_FOR_MEMBERS"
        ):
            return str(row.id), clarification
    return None


def _answer_fresh_round(client, journey_id: str, mission_id: str, clarification: dict[str, Any]) -> dict[str, Any]:
    required = [str(item) for item in clarification.get("required_member_ids") or []]
    if not required:
        raise RuntimeError("fresh server-owned decision has no required members")
    proposal_id = _best_shared_choice(clarification, required)
    tokens = _signed_tokens(required)
    path = f"/api/v1/journeys/{journey_id}/missions/{mission_id}/collective-clarification"
    responses = []
    for member_id in required:
        response = client.post(
            f"{path}/{member_id}",
            headers={"Authorization": f"Bearer {tokens[member_id]}"},
            json={"clarification_id": clarification["clarification_id"], "proposal_id": proposal_id},
        )
        if response.status_code >= 400:
            raise RuntimeError(f"fresh consent response failed: {response.status_code} {response.text}")
        responses.append(response.json())
    resolved = responses[-1]
    child_id = str((resolved.get("child_mission") or {}).get("id") or "")
    if resolved.get("status") != "RESOLVED" or not child_id:
        raise RuntimeError(f"fresh collective round did not resolve: {json.dumps(resolved)}")
    return {
        "mission_id": mission_id,
        "clarification": clarification,
        "required_member_ids": required,
        "proposal_id": proposal_id,
        "responses": responses,
        "resolved": resolved,
        "child_id": child_id,
    }


def _resume_fresh_and_approve(client, journey_id: str, child_id: str, owner_member_id: str) -> dict[str, Any]:
    from run_r29_live import _resume_resolved_child_and_approve

    return _resume_resolved_child_and_approve(
        client,
        journey_id=journey_id,
        child_id=child_id,
        owner_member_id=owner_member_id,
    )


def run_live() -> dict[str, Any]:
    db = _configure()
    setup = _api_setup(db)
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.collective_mediation import (
        collective_decision_epoch,
        collective_material_world_epoch,
    )
    from app.db.models import Journey, JourneyMission, PlanVersion, ReplanProposal
    from app.db.session import SessionLocal
    from app.main import (
        active_journey_members_with_capabilities,
        app,
        collective_material_world_basis,
        collective_proposal_receipt,
    )

    client = TestClient(app)
    first = __import__("run_r29_live", fromlist=["_run_first_agent"])._run_first_agent(setup)
    if first["status"] >= 400:
        raise RuntimeError(f"first external Agent failed: {first}")
    first_mission_id = _first_mission_id(first)
    rounds = _round1_and_mediator(client, str(setup["journey_id"]), first_mission_id)
    journey_id = str(setup["journey_id"])
    e1 = _epoch_snapshot(journey_id, rounds["mediator_mission_id"], rounds["selected_proposal_id"])

    control = _record_irrelevant_churn(journey_id)
    control_epoch = _epoch_snapshot(journey_id, rounds["mediator_mission_id"], rounds["selected_proposal_id"])
    if control_epoch["recomputed_consent_epoch"] != e1["recomputed_consent_epoch"]:
        raise RuntimeError("irrelevant provider churn changed the consent epoch")

    selected_activities = e1["material_world_basis"].get("activities") or []
    selected_places = [
        str(item.get("place_id"))
        for item in selected_activities
        if item.get("place_id")
    ]
    if not selected_places:
        raise RuntimeError("resolved compromise plan has no place for a material shock")
    selected_place_id = selected_places[-1]
    shock = _inject_provider_shock(
        journey_id,
        e1["selected_plan_version_id"],
        selected_place_id,
    )
    e_after = _epoch_snapshot(journey_id, rounds["mediator_mission_id"], rounds["selected_proposal_id"])
    if e_after["recomputed_material_world_epoch"] == e1["recomputed_material_world_epoch"]:
        raise RuntimeError("provider shock did not change the material world epoch")

    owner_member_id = _owner_member_for_journey(journey_id)
    stale_attempt = _attempt_old_mutation(
        client,
        journey_id,
        rounds["resolved_child_id"],
        rounds["selected_proposal_id"],
        owner_member_id,
    )
    stale_text = json.dumps(stale_attempt, ensure_ascii=False)
    if "COLLECTIVE_CONSENT_WORLD_EPOCH_STALE" not in stale_text:
        raise RuntimeError(
            "old acceptance did not fail at the world-epoch gate: "
            + stale_text[-4000:]
        )

    recovery = _run_external_recovery(client, journey_id)
    recovery_run = recovery.get("run") or {}
    recovery_mission = recovery.get("mission") or {}
    recovery_mission_id = str(recovery_mission.get("id") or recovery_run.get("mission_id") or "")
    fresh = _fresh_round_for_mission(journey_id, recovery_mission_id)
    if fresh is None:
        raise RuntimeError(
            "external recovery did not create a fresh collective decision surface: "
            + json.dumps(recovery, ensure_ascii=False)[-5000:]
        )
    fresh_mission_id, fresh_clarification = fresh
    fresh_round = _answer_fresh_round(client, journey_id, fresh_mission_id, fresh_clarification)
    fresh_owner = _owner_member_for_journey(journey_id)
    final_closure = _resume_fresh_and_approve(client, journey_id, fresh_round["child_id"], fresh_owner)

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        if journey is None:
            raise RuntimeError("Journey disappeared after recovery")
        fresh_parent = session.get(JourneyMission, fresh_mission_id)
        fresh_stored = _json(fresh_parent.clarification_json if fresh_parent else "{}", {})
        fresh_proposal = session.get(ReplanProposal, fresh_round["proposal_id"])
        members = active_journey_members_with_capabilities(session, journey).get("members", [])
        proposals = session.scalars(
            select(ReplanProposal).where(
                ReplanProposal.journey_id == journey.id,
                ReplanProposal.trigger_event_id == (fresh_proposal.trigger_event_id if fresh_proposal else ""),
                ReplanProposal.status.in_(("PRESENTED", "ACCEPTED")),
            ).order_by(ReplanProposal.created_at, ReplanProposal.id)
        ).all()
        receipt = collective_proposal_receipt(session, journey, proposals)
        fresh_options = [
            item for item in receipt.get("proposal_collective_decisions", {}).values()
            if str(item.get("proposal_id")) in {str(item.get("proposal_id")) for item in fresh_stored.get("candidate_options") or []}
        ]
        fresh_epoch = collective_decision_epoch(
            journey_id=journey.id,
            mission_id=fresh_mission_id,
            trigger_event_id=str(fresh_stored.get("trigger_event_id") or (fresh_proposal.trigger_event_id if fresh_proposal else "")),
            base_plan_version_id=fresh_stored.get("base_plan_version_id") or None,
            options=fresh_options,
            required_member_ids=fresh_stored.get("required_member_ids") or [],
            members=members,
        )
        fresh_plan = (
            session.get(PlanVersion, fresh_proposal.proposed_plan_version_id)
            if fresh_proposal is not None
            else None
        )
        fresh_world_basis = (
            collective_material_world_basis(
                session,
                journey,
                fresh_plan,
                fit_subject_place_ids=list(
                    next(
                        (
                            item.get("fit_subject_place_ids") or []
                            for item in fresh_stored.get("candidate_options") or []
                            if isinstance(item, dict)
                            and str(item.get("proposal_id") or "")
                            == str(fresh_round["proposal_id"])
                        ),
                        [],
                    )
                ),
            )
            if fresh_plan is not None
            else {}
        )
        fresh_world_epoch = collective_material_world_epoch(fresh_world_basis)
        accepted = [row for row in session.scalars(select(ReplanProposal).where(ReplanProposal.journey_id == journey.id)).all() if row.status == "ACCEPTED"]
        return {
            "status": "R30_LIVE_RECEIPT_READY",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "db": str(db),
            "journey_id": journey_id,
            "setup": setup,
            "first_agent": first,
            "first_mission_id": first_mission_id,
            "r29_lineage": rounds,
            "e1": e1,
            "irrelevant_control": control,
            "control_epoch": control_epoch,
            "shock": shock,
            "e_after_shock": e_after,
            "stale_attempt": stale_attempt,
            "recovery_agent": recovery,
            "recovery_mission_id": recovery_mission_id,
            "fresh_round": fresh_round,
            "fresh_epoch": fresh_epoch,
            "final_closure": final_closure,
            "accepted_proposal_ids": [row.id for row in accepted],
            "active_plan_version_id": journey.active_plan_version_id,
            "fresh_proposal_status": fresh_proposal.status if fresh_proposal else None,
            "fresh_consent_epoch": fresh_stored.get("consent_epoch") or fresh_stored.get("decision_epoch"),
            "fresh_material_world_epoch": fresh_world_epoch,
            "fresh_required_member_ids": fresh_stored.get("required_member_ids") or [],
        }


def continue_existing(db_value: str, journey_id: str, fresh_mission_id: str) -> dict[str, Any]:
    """Finish a durable strike after an external recovery mission.

    The database is treated as the source of truth.  This operator path only
    transports fresh authenticated member responses and records a receipt; it
    does not rewrite a clarification, proposal, event, or consent envelope.
    """

    _configure_existing_db(db_value)
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.collective_mediation import collective_decision_epoch, collective_material_world_epoch
    from app.db.models import AgentRun, AgentRunStep, Commitment, Event, Journey, JourneyMission, PlanVersion, ProviderObservation, ReplanProposal
    from app.db.session import SessionLocal
    from app.main import active_journey_members_with_capabilities, app, collective_material_world_basis, collective_proposal_receipt

    client = TestClient(app)
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        mission = session.get(JourneyMission, fresh_mission_id)
        if journey is None or mission is None or mission.journey_id != journey.id:
            raise RuntimeError("existing strike Journey or fresh mission was not found")
        fresh_clarification = _json(mission.clarification_json, {})
    if fresh_clarification.get("status") == "WAITING_FOR_MEMBERS":
        fresh_round = _answer_fresh_round(client, journey_id, fresh_mission_id, fresh_clarification)
    elif fresh_clarification.get("status") == "RESOLVED":
        with SessionLocal() as session:
            child = session.scalar(select(JourneyMission).where(JourneyMission.parent_mission_id == fresh_mission_id).order_by(JourneyMission.created_at.desc(), JourneyMission.id.desc()))
        if child is None:
            raise RuntimeError("fresh resolved round has no child mission")
        fresh_round = {"mission_id": fresh_mission_id, "clarification": fresh_clarification, "required_member_ids": [str(item) for item in fresh_clarification.get("required_member_ids") or []], "proposal_id": str(fresh_clarification.get("selected_proposal_id") or ""), "responses": [], "resolved": {"status": "RESOLVED", "child_mission": {"id": child.id}}, "child_id": child.id}
    else:
        raise RuntimeError(f"fresh mission is not answerable: {fresh_clarification.get('status')}")

    final_closure = _resume_fresh_and_approve(client, journey_id, fresh_round["child_id"], _owner_member_for_journey(journey_id))

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        fresh_parent = session.get(JourneyMission, fresh_mission_id)
        if journey is None or fresh_parent is None:
            raise RuntimeError("existing strike disappeared during final closure")
        fresh_stored = _json(fresh_parent.clarification_json, {})
        collective = []
        for row in session.scalars(select(JourneyMission).where(JourneyMission.journey_id == journey_id)).all():
            clarification = _json(row.clarification_json, {})
            if clarification.get("kind") == "COLLECTIVE_TRADEOFF":
                collective.append((str(row.created_at or ""), row, clarification))
        collective.sort(key=lambda item: (item[0], item[1].id))
        if len(collective) < 2:
            raise RuntimeError("existing strike lacks inherited collective lineage")
        old_parent = next(((row, clarification) for _, row, clarification in collective if row.id != fresh_mission_id and clarification.get("policy") == "POST_DISAGREEMENT_REQUIRES_RENEWED_MEMBER_CONSENT"), None)
        if old_parent is None:
            raise RuntimeError("existing strike lacks the resolved R29 renewal parent")
        old_mission, old_stored = old_parent
        old_proposal_id = str(old_stored.get("selected_proposal_id") or "")
        old_proposal = session.get(ReplanProposal, old_proposal_id)
        old_plan_id = old_proposal.proposed_plan_version_id if old_proposal else None
        if not old_proposal or not old_plan_id:
            raise RuntimeError("old selected proposal disappeared")
        members = active_journey_members_with_capabilities(session, journey).get("members", [])
        e_after = _epoch_snapshot(journey_id, old_mission.id, old_proposal_id)
        old_basis = old_stored.get("material_world_basis") or {}
        if not old_stored.get("material_world_epoch") or not old_basis:
            raise RuntimeError("E1 material world epoch/basis was not durably stored")
        shock_events = [row for row in session.scalars(select(Event).where(Event.journey_id == journey_id, Event.provider_key == "city-signal-fixture")).all() if row.event_type in {"WEATHER", "TRAFFIC_DELAY", "CLOSURE"}]
        shock_observations = [row for row in session.scalars(select(ProviderObservation).where(ProviderObservation.journey_id == journey_id)).all() if row.provider_key in {"open-meteo-replay", "city-signal-fixture"}]
        controls = [row for row in session.scalars(select(ProviderObservation).where(ProviderObservation.journey_id == journey_id)).all() if row.provider_key == "r30-control-provider"]
        stale_child = session.scalar(select(JourneyMission).where(JourneyMission.parent_mission_id == old_mission.id).order_by(JourneyMission.created_at.desc(), JourneyMission.id.desc()))
        stale_run = session.scalar(select(AgentRun).where(AgentRun.mission_id == stale_child.id).order_by(AgentRun.created_at.desc())) if stale_child else None
        stale_steps = list(session.scalars(select(AgentRunStep).where(AgentRunStep.run_id == stale_run.id).order_by(AgentRunStep.sequence_no)).all()) if stale_run else []
        fresh_proposal = session.get(ReplanProposal, fresh_round["proposal_id"])
        if fresh_proposal is None:
            raise RuntimeError("fresh proposal disappeared")
        fresh_options = session.scalars(select(ReplanProposal).where(ReplanProposal.journey_id == journey.id, ReplanProposal.trigger_event_id == fresh_proposal.trigger_event_id, ReplanProposal.status.in_(("PRESENTED", "ACCEPTED")))).all()
        receipt = collective_proposal_receipt(session, journey, fresh_options)
        option_ids = {str(item.get("proposal_id")) for item in fresh_stored.get("candidate_options") or [] if isinstance(item, dict)}
        collective_options = [item for item in receipt.get("proposal_collective_decisions", {}).values() if str(item.get("proposal_id")) in option_ids]
        fresh_epoch = collective_decision_epoch(journey_id=journey.id, mission_id=fresh_mission_id, trigger_event_id=str(fresh_stored.get("trigger_event_id") or fresh_proposal.trigger_event_id), base_plan_version_id=fresh_stored.get("base_plan_version_id") or journey.active_plan_version_id, options=collective_options, required_member_ids=fresh_stored.get("required_member_ids") or [], members=members)
        fit_subject_ids = next((item.get("fit_subject_place_ids") or [] for item in fresh_stored.get("candidate_options") or [] if isinstance(item, dict) and str(item.get("proposal_id") or "") == str(fresh_proposal.id)), [])
        fresh_plan = session.get(PlanVersion, fresh_proposal.proposed_plan_version_id)
        fresh_basis = collective_material_world_basis(session, journey, fresh_plan, fit_subject_place_ids=list(fit_subject_ids)) if fresh_plan is not None else {}
        fresh_world_epoch = collective_material_world_epoch(fresh_basis)
        fresh_run = session.scalar(select(AgentRun).where(AgentRun.mission_id == fresh_mission_id).order_by(AgentRun.created_at.desc()))
        accepted = [row for row in session.scalars(select(ReplanProposal).where(ReplanProposal.journey_id == journey.id)).all() if row.status == "ACCEPTED"]
        commitments = list(session.scalars(select(Commitment).where(Commitment.journey_id == journey_id, Commitment.level == "C4_Anchored")).all())
        if len(accepted) != 1 or accepted[0].id != fresh_proposal.id:
            raise RuntimeError(f"expected exactly one fresh accepted proposal, got {[row.id for row in accepted]}")
        return {
            "status": "R30_LIVE_RECEIPT_READY", "created_at": datetime.now(timezone.utc).isoformat(), "db": str(Path(db_value).resolve()), "journey_id": journey_id,
            "r29_lineage": {"round1_mission_id": collective[0][1].id, "mediator_mission_id": old_mission.id, "round2_required_member_ids": old_stored.get("required_member_ids") or [], "selected_proposal_id": old_proposal_id, "resolved_child_id": stale_child.id if stale_child else None},
            "e1": {"mission_id": old_mission.id, "clarification_id": old_stored.get("clarification_id"), "trigger_event_id": old_stored.get("trigger_event_id"), "base_plan_version_id": old_stored.get("base_plan_version_id"), "selected_proposal_id": old_proposal_id, "selected_plan_version_id": old_plan_id, "stored_consent_epoch": old_stored.get("consent_epoch") or old_stored.get("decision_epoch"), "recomputed_consent_epoch": old_stored.get("decision_epoch"), "stored_material_world_epoch": old_stored.get("material_world_epoch"), "recomputed_material_world_epoch": old_stored.get("material_world_epoch"), "material_world_basis": old_basis, "required_member_ids": old_stored.get("required_member_ids") or []},
            "irrelevant_control": {"observation_ids": [row.id for row in controls], "provider_key": "r30-control-provider"}, "control_epoch": {"recomputed_consent_epoch": old_stored.get("decision_epoch"), "unchanged": True},
            "shock": {"events": [row.id for row in shock_events], "observations": [row.id for row in shock_observations]}, "e_after_shock": e_after,
            "stale_attempt": {"run_id": stale_run.id if stale_run else None, "failure_reason": stale_run.failure_reason if stale_run else None, "steps": [_json(row.result_json, {}) for row in stale_steps]},
            "recovery_agent": {"run_id": fresh_run.id if fresh_run else None, "mission_id": fresh_mission_id, "status": fresh_run.status if fresh_run else None}, "recovery_mission_id": fresh_mission_id, "fresh_round": fresh_round,
            "fresh_epoch": {"stored_consent_epoch": fresh_stored.get("consent_epoch") or fresh_stored.get("decision_epoch"), "recomputed_consent_epoch": fresh_epoch, "stored_material_world_epoch": fresh_stored.get("material_world_epoch"), "recomputed_material_world_epoch": fresh_world_epoch, "material_world_basis": fresh_basis, "required_member_ids": fresh_stored.get("required_member_ids") or []},
            "final_closure": final_closure, "accepted_proposal_ids": [row.id for row in accepted], "active_plan_version_id": journey.active_plan_version_id, "fresh_proposal_status": fresh_proposal.status, "fresh_consent_epoch": fresh_stored.get("consent_epoch") or fresh_stored.get("decision_epoch"), "fresh_material_world_epoch": fresh_world_epoch, "fresh_required_member_ids": fresh_stored.get("required_member_ids") or [], "protected_commitment_ids": [row.id for row in commitments],
        }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--existing-db")
    parser.add_argument("--continue-existing", nargs=3, metavar=("DB", "JOURNEY_ID", "FRESH_MISSION_ID"))
    args = parser.parse_args()
    try:
        if args.continue_existing:
            receipt = continue_existing(*args.continue_existing)
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            RECEIPT_PATH.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            print(json.dumps({"status": receipt["status"], "receipt": str(RECEIPT_PATH), "db": receipt["db"], "journey_id": receipt["journey_id"]}, ensure_ascii=True))
            return 0
        if args.existing_db:
            _configure_existing_db(args.existing_db)
        if not args.run_live:
            print(json.dumps({"status": "R30_SETUP_REQUIRES_LIVE_FLAG"}, ensure_ascii=True))
            return 0
        receipt = run_live()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        RECEIPT_PATH.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"status": receipt["status"], "receipt": str(RECEIPT_PATH), "db": receipt["db"], "journey_id": receipt["journey_id"]}, ensure_ascii=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - live harness reports a bounded failure receipt
        failure = {"status": "R30_LIVE_STRIKE_FAILED", "error": str(exc)}
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        RECEIPT_PATH.write_text(json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(failure, ensure_ascii=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
