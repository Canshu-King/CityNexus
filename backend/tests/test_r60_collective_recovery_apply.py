from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.collective_mediation as collective_mediation
import app.main as main_module
from app.collective_authority import AUTHENTICATED_MEMBER_CONSENT
from app.core.config import settings
from app.db.models import (
    AuditLog,
    CollectiveAuthorityReceipt,
    Event,
    IdempotencyKey,
    Journey,
    JourneyMember,
    JourneyMission,
    JourneyRoleCapability,
    PlanVersion,
    ReplanProposal,
    RecoveryEpoch,
    Traveler,
)
from app.db.session import SessionLocal
from app.traveler_principal import issue_traveler_token
from app.recovery_epoch import recovery_reality_basis, recovery_reality_fingerprint


client = TestClient(main_module.app)
_TEST_SECRET = "r60-collective-apply-secret-0123456789abcdef"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_r60_apply_world() -> dict[str, str | list[dict[str, object]]]:
    now = _now()
    owner_id, admin_id = str(uuid4()), str(uuid4())
    journey_id = str(uuid4())
    owner_member_id, admin_member_id = str(uuid4()), str(uuid4())
    base_id, selected_plan_id, sibling_plan_id = (str(uuid4()) for _ in range(3))
    event_id = str(uuid4())
    selected_proposal_id, sibling_proposal_id = str(uuid4()), str(uuid4())
    room_id, child_id = str(uuid4()), str(uuid4())
    receipt_id, recovery_epoch_id = str(uuid4()), str(uuid4())
    incident_key = f"r60-incident-{journey_id}"
    decision_epoch = "r60-current-decision-epoch"
    material_world_epoch = "r60-current-world-epoch"
    surface_fingerprint = "r60-current-candidate-surface"
    options: list[dict[str, object]] = [
        {
            "proposal_id": selected_proposal_id,
            "plan_id": selected_plan_id,
            "status": "GROUNDED_FEASIBLE",
            "label": "Garden recovery",
            "fit_subject_place_ids": ["place-r60-garden"],
            "fit_subject_tags": ["garden"],
            "member_fits": {},
            "fairness": {"minimum_member_fit": 0.5, "maximum_regret": 0.3, "unacceptable_member_ids": []},
        },
        {
            "proposal_id": sibling_proposal_id,
            "plan_id": sibling_plan_id,
            "status": "GROUNDED_FEASIBLE",
            "label": "Museum recovery",
            "fit_subject_place_ids": ["place-r60-museum"],
            "fit_subject_tags": ["museum"],
            "member_fits": {},
            "fairness": {"minimum_member_fit": 0.4, "maximum_regret": 0.4, "unacceptable_member_ids": []},
        },
    ]
    future_end = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
    with SessionLocal() as session:
        session.add_all(
            [
                Traveler(id=owner_id, display_name="R60 owner", locale="en-US", timezone="UTC", created_at=now, updated_at=now),
                Traveler(id=admin_id, display_name="R60 admin", locale="en-US", timezone="UTC", created_at=now, updated_at=now),
            ]
        )
        session.flush()
        journey = Journey(
            id=journey_id,
            traveler_id=owner_id,
            title="R60 collective apply",
            city_code="NARA",
            timezone="UTC",
            start_at=now,
            end_at=future_end,
            budget_currency="JPY",
            budget_amount_minor=10000,
            planning_mode="balanced",
            status="ACTIVE",
            active_plan_version_id=None,
            current_activity_id=None,
            created_at=now,
            updated_at=now,
        )
        session.add(journey)
        session.flush()
        session.add_all(
            [
                JourneyMember(id=owner_member_id, journey_id=journey_id, traveler_id=owner_id, role="OWNER", invited_by=owner_id, joined_at=now, preferences_json='{"preferences":[{"key":"garden"}]}', created_at=now, updated_at=now),
                JourneyMember(id=admin_member_id, journey_id=journey_id, traveler_id=admin_id, role="ADMIN", invited_by=owner_id, joined_at=now, preferences_json='{"preferences":[{"key":"museum"}]}', created_at=now, updated_at=now),
            ]
        )
        for plan_id, version_no, status in (
            (base_id, 1, "ACTIVE"),
            (selected_plan_id, 2, "CANDIDATE"),
            (sibling_plan_id, 3, "CANDIDATE"),
        ):
            session.add(
                PlanVersion(
                    id=plan_id,
                    journey_id=journey_id,
                    version_no=version_no,
                    planning_mode="balanced",
                    status=status,
                    lifecycle="ACTIVE",
                    source="INITIAL" if plan_id == base_id else "REPLAN",
                    parent_plan_version_id=base_id if plan_id != base_id else None,
                    total_cost_minor=0,
                    currency="JPY",
                    estimated_duration_min=60,
                    utility_score=0.0,
                    score_breakdown_json="{}",
                    explanation_json="{}",
                    mobility_evidence_json="{}",
                    created_at=now,
                )
            )
        session.flush()
        journey.active_plan_version_id = base_id
        session.add(
            Event(
                id=event_id,
                journey_id=journey_id,
                provider_key="journey-group-presence",
                provenance="SYSTEM_DERIVED",
                event_type="TRAFFIC_DELAY",
                severity="MAJOR",
                status="DETECTED",
                occurred_at=now,
                detected_at=now,
                payload_json="{}",
                created_at=now,
            )
        )
        session.flush()
        recovery_fingerprint = recovery_reality_fingerprint(
            recovery_reality_basis(session, journey)
        )
        session.add(
            RecoveryEpoch(
                id=recovery_epoch_id,
                journey_id=journey_id,
                generation=1,
                active_plan_version_id_at_open=base_id,
                material_world_epoch_at_open=recovery_fingerprint,
                recovery_reality_fingerprint=recovery_fingerprint,
                triggering_event_ids_json=json.dumps([event_id]),
                status="OPEN",
                opened_at=now,
            )
        )
        session.flush()
        for proposal_id, plan_id in (
            (selected_proposal_id, selected_plan_id),
            (sibling_proposal_id, sibling_plan_id),
        ):
            session.add(
                ReplanProposal(
                    id=proposal_id,
                    journey_id=journey_id,
                    trigger_event_id=event_id,
                    base_plan_version_id=base_id,
                    proposed_plan_version_id=plan_id,
                    status="PRESENTED",
                    hard_constraints_passed=True,
                    locked_commitments_preserved=True,
                    utility_score=0.0,
                    score_breakdown_json="{}",
                    diff_json="{}",
                    explanation_json="{}",
                    created_at=now,
                    recovery_epoch_id=recovery_epoch_id,
                )
            )
        clarification = {
            "kind": "COLLECTIVE_TRADEOFF",
            "policy": "MATERIAL_TRADEOFF_REQUIRES_ALL_RELEVANT_MEMBER_RESPONSES",
            "status": "RESOLVED",
            "clarification_id": "r60-resolved-clarification",
            "decision_epoch": decision_epoch,
            "material_world_epoch": material_world_epoch,
            "candidate_surface_fingerprint": surface_fingerprint,
            "trigger_event_id": event_id,
            "base_plan_version_id": base_id,
            "candidate_options": options,
            "required_member_ids": [owner_member_id, admin_member_id],
            "decision_relevant_member_ids": [owner_member_id, admin_member_id],
            "responses": {
                owner_member_id: {"proposal_id": selected_proposal_id},
                admin_member_id: {"proposal_id": selected_proposal_id},
            },
            "selected_proposal_id": selected_proposal_id,
            "authority_receipt_id": receipt_id,
        }
        room = JourneyMission(
            id=room_id,
            journey_id=journey_id,
            traveler_id=owner_id,
            trigger_event_id=event_id,
            user_text="Resolve the current group recovery.",
            requested_autonomy="EXECUTE_WITHIN_BOUNDS",
            status="ANSWERED",
            resolved_intent_json=json.dumps(
                {"group_recovery": {"incident_key": incident_key, "hermes_run_id": "r60-test-run"}},
                sort_keys=True,
            ),
            clarification_json=json.dumps(clarification, sort_keys=True),
            max_cost_delta_minor=2000,
            max_loss_minor=1000,
            max_schedule_drift_min=30,
            protected_activity_ids_json="[]",
            mutable_activity_ids_json="[]",
            allowed_action_classes_json='["REPLAN"]',
            created_at=now,
            started_at=now,
            completed_at=now,
        )
        session.add(room)
        session.flush()
        session.add(
            JourneyMission(
                id=child_id,
                journey_id=journey_id,
                traveler_id=owner_id,
                trigger_event_id=event_id,
                parent_mission_id=room_id,
                user_text="Continue with the group decision.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="ANSWERED",
                resolved_intent_json=json.dumps(
                    {
                        "collective_decision": {
                            "clarification_id": clarification["clarification_id"],
                            "decision_epoch": decision_epoch,
                            "material_world_epoch": material_world_epoch,
                            "candidate_surface_fingerprint": surface_fingerprint,
                            "authority_receipt_id": receipt_id,
                            "selected_proposal_id": selected_proposal_id,
                        }
                    },
                    sort_keys=True,
                ),
                clarification_json="{}",
                created_at=now,
                started_at=now,
                completed_at=now,
            )
        )
        session.flush()
        session.add(
            CollectiveAuthorityReceipt(
                id=receipt_id,
                journey_id=journey_id,
                proposal_id=selected_proposal_id,
                plan_version_id=selected_plan_id,
                authority_mode=AUTHENTICATED_MEMBER_CONSENT,
                decision_epoch=decision_epoch,
                material_world_epoch=material_world_epoch,
                candidate_surface_fingerprint=surface_fingerprint,
                source_mission_id=room_id,
                recovery_epoch_id=recovery_epoch_id,
                required_member_ids_json=json.dumps([owner_member_id, admin_member_id]),
                response_audit_ids_json="[]",
                principal_actor_ids_json=json.dumps([owner_id, admin_id]),
                classification="HUMAN_TRADEOFF_REQUIRED",
                issued_at=now,
            )
        )
        session.commit()
    return {
        "journey_id": journey_id,
        "owner_id": owner_id,
        "admin_id": admin_id,
        "owner_member_id": owner_member_id,
        "admin_member_id": admin_member_id,
        "base_id": base_id,
        "selected_plan_id": selected_plan_id,
        "sibling_plan_id": sibling_plan_id,
        "selected_proposal_id": selected_proposal_id,
        "sibling_proposal_id": sibling_proposal_id,
        "event_id": event_id,
        "room_id": room_id,
        "child_id": child_id,
        "receipt_id": receipt_id,
        "recovery_epoch_id": recovery_epoch_id,
        "incident_key": incident_key,
        "decision_epoch": decision_epoch,
        "material_world_epoch": material_world_epoch,
        "surface_fingerprint": surface_fingerprint,
        "options": options,
    }


def _enable_r60_apply_path(
    monkeypatch, seeded, *, stale: bool = False, mock_resolution: bool = True
) -> None:
    owner_member_id = str(seeded["owner_member_id"])
    admin_member_id = str(seeded["admin_member_id"])
    selected_proposal_id = str(seeded["selected_proposal_id"])
    selected_plan_id = str(seeded["selected_plan_id"])
    receipt_id = str(seeded["receipt_id"])
    recovery_epoch_id = str(seeded["recovery_epoch_id"])
    monkeypatch.setattr(main_module, "group_presence_projection", lambda *_args, **_kwargs: {"state": "GROUP_SPLIT_ADVISORY"})
    monkeypatch.setattr(
        main_module,
        "group_recovery_projection",
        lambda _presence: {
            "can_request_planning": True,
            "affected_member": {"member_id": admin_member_id},
            "shared_commitment": {"activity_id": "r60-rendezvous"},
        },
    )
    monkeypatch.setattr(main_module, "group_recovery_incident_key", lambda **_kwargs: str(seeded["incident_key"]))
    if stale:
        def stale_resolution(*_args, **_kwargs):
            raise HTTPException(409, "STALE_COLLECTIVE_DECISION")

        monkeypatch.setattr(main_module, "_collective_resolution_for_child", stale_resolution)
    elif mock_resolution:
        monkeypatch.setattr(
            main_module,
            "_collective_resolution_for_child",
            lambda _session, _journey, proposal, _mission_id: {
                "status": "RESOLVED",
                "selected_proposal_id": str(proposal.id),
                "selected_candidate_id": selected_plan_id,
                "selected_plan_version_id": selected_plan_id,
                "authority_receipt_id": receipt_id,
                "decision_epoch": str(seeded["decision_epoch"]),
                "material_world_epoch": str(seeded["material_world_epoch"]),
                "candidate_surface_fingerprint": str(seeded["surface_fingerprint"]),
                "recovery_epoch_id": recovery_epoch_id,
            },
        )
    monkeypatch.setattr(
        main_module,
        "validate_recovery_epoch_binding",
        lambda session, _journey_id, epoch_id: session.get(RecoveryEpoch, str(epoch_id)),
    )
    monkeypatch.setattr(main_module, "_proposal_mobility_snapshot", lambda _proposal: object())
    monkeypatch.setattr(
        main_module,
        "validate_plan_feasibility",
        lambda *_args, **_kwargs: SimpleNamespace(passed=True, failures=[]),
    )
    monkeypatch.setattr(
        main_module,
        "collective_authority_preflight",
        lambda *_args, **_kwargs: {
            "allowed": True,
            "classification": "HUMAN_TRADEOFF_REQUIRED",
            "authority_receipt_id": receipt_id,
            "resolved_decision_epoch": str(seeded["decision_epoch"]),
            "current_decision_epoch": str(seeded["decision_epoch"]),
            "resolved_material_world_epoch": str(seeded["material_world_epoch"]),
            "current_material_world_epoch": str(seeded["material_world_epoch"]),
            "candidate_surface_fingerprint": str(seeded["surface_fingerprint"]),
            "recovery_epoch_id": recovery_epoch_id,
        },
    )
    monkeypatch.setattr(main_module, "_revalidate_locked_commitments", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_module, "_twin_snapshot", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(main_module, "_compile_transactional_recovery_if_needed", lambda _session, result: result)


def _apply_headers(traveler_id: str, *, idempotency_key: str = "r60-apply-once-001") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {issue_traveler_token(traveler_id)}",
        "Idempotency-Key": idempotency_key,
    }


def test_r60_apply_requires_signed_in_force_mutation_member_and_empty_body(monkeypatch) -> None:
    previous_secret = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", _TEST_SECRET)
    seeded = _seed_r60_apply_world()
    _enable_r60_apply_path(monkeypatch, seeded)
    path = f"/api/v1/journeys/{seeded['journey_id']}/group-recovery/apply"
    try:
        unauthenticated = client.post(path, json={})
        assert unauthenticated.status_code == 401

        forged = client.post(
            path,
            headers=_apply_headers(str(seeded["owner_id"])),
            json={"proposal_id": str(seeded["sibling_proposal_id"]), "member_id": str(seeded["admin_member_id"]), "traveler_id": str(seeded["admin_id"])},
        )
        assert forged.status_code == 422

        with SessionLocal() as session:
            read_only = session.get(JourneyMember, str(seeded["admin_member_id"]))
            assert read_only is not None
            read_only.role = "COLLABORATOR"
            session.commit()
        read_only_response = client.post(
            path,
            headers=_apply_headers(str(seeded["admin_id"])),
            json={},
        )
        assert read_only_response.status_code == 403
        assert "JOURNEY_UPDATE" in str(read_only_response.json())
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)


def test_r60_signed_apply_spends_only_server_selected_recovery_once(monkeypatch) -> None:
    previous_secret = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", _TEST_SECRET)
    seeded = _seed_r60_apply_world()
    _enable_r60_apply_path(monkeypatch, seeded)
    path = f"/api/v1/journeys/{seeded['journey_id']}/group-recovery/apply"
    headers = _apply_headers(str(seeded["owner_id"]))
    try:
        arbitrary_proposal = client.post(
            path,
            headers=headers,
            json={"proposal_id": str(seeded["sibling_proposal_id"])},
        )
        assert arbitrary_proposal.status_code == 422

        generic_accept = client.post(
            f"/api/v1/replans/{seeded['selected_proposal_id']}/accept",
            headers={"Idempotency-Key": "r60-generic-must-refuse"},
        )
        assert generic_accept.status_code == 409
        assert "GROUP_RECOVERY_REQUIRES_AUTHENTICATED_APPLY" in str(generic_accept.json())

        first = client.post(path, headers=headers, json={})
        assert first.status_code == 200, first.text
        body = first.json()
        assert body["group_recovery_apply"]["result"] == "APPLIED"
        assert body["group_recovery_apply"]["selected_proposal_id"] == seeded["selected_proposal_id"]
        assert body["journey"]["active_plan_version_id"] == seeded["selected_plan_id"]

        replay = client.post(path, headers=headers, json={})
        assert replay.status_code == 200, replay.text
        assert replay.json()["replayed"] is True
        assert replay.json()["journey"]["active_plan_version_id"] == seeded["selected_plan_id"]

        with SessionLocal() as session:
            journey = session.get(Journey, str(seeded["journey_id"]))
            base = session.get(PlanVersion, str(seeded["base_id"]))
            selected = session.get(PlanVersion, str(seeded["selected_plan_id"]))
            proposal = session.get(ReplanProposal, str(seeded["selected_proposal_id"]))
            sibling = session.get(ReplanProposal, str(seeded["sibling_proposal_id"]))
            event = session.get(Event, str(seeded["event_id"]))
            audits = session.scalars(
                select(AuditLog).where(
                    AuditLog.journey_id == str(seeded["journey_id"]),
                    AuditLog.action == "replan.accepted",
                )
            ).all()
            idempotency = session.scalars(
                select(IdempotencyKey).where(
                    IdempotencyKey.operation == "replan.accept",
                    IdempotencyKey.key.like("replan.accept:gr-%"),
                )
            ).all()
            assert journey is not None and journey.active_plan_version_id == str(seeded["selected_plan_id"])
            assert base is not None and base.status == "SUPERSEDED"
            assert selected is not None and selected.status == "ACTIVE"
            assert proposal is not None and proposal.status == "ACCEPTED"
            assert sibling is not None and sibling.status == "INVALIDATED"
            assert event is not None and event.status == "RESOLVED"
            assert len(audits) == 1
            spend = json.loads(audits[0].after_json or "{}")["group_recovery_spend"]
            assert audits[0].actor_type == "AUTHENTICATED_TRAVELER"
            assert audits[0].actor_id == str(seeded["owner_id"])
            assert spend["journey_member_id"] == str(seeded["owner_member_id"])
            assert spend["member_role"] == "OWNER"
            assert spend["before_plan_version_id"] == str(seeded["base_id"])
            assert spend["after_plan_version_id"] == str(seeded["selected_plan_id"])
            assert spend["authority_receipt_id"] == str(seeded["receipt_id"])
            assert len(idempotency) == 1
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)


def test_r60_stale_apply_preserves_old_answers_and_reuses_one_successor_room(monkeypatch) -> None:
    previous_secret = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", _TEST_SECRET)
    policy_key = {"role": "ADMIN", "capability": "JOURNEY_UPDATE"}
    with SessionLocal() as session:
        original_policy = session.get(JourneyRoleCapability, policy_key)
        original_policy_values = (
            {
                "scope_message_key": original_policy.scope_message_key,
                "created_at": original_policy.created_at,
            }
            if original_policy is not None
            else None
        )
        if original_policy is None:
            session.add(
                JourneyRoleCapability(
                    role="ADMIN",
                    capability="JOURNEY_UPDATE",
                    scope_message_key="test.r60.admin.update",
                    created_at=_now(),
                )
            )
            session.commit()
    seeded = _seed_r60_apply_world()
    _enable_r60_apply_path(monkeypatch, seeded, mock_resolution=False)
    options = seeded["options"]
    option_by_id = {str(item["proposal_id"]): item for item in options}

    # Bind the durable receipt to the actually current two-updater epoch. The
    # test then removes ADMIN's mutation capability before the signed apply.
    with SessionLocal() as session:
        journey = session.get(Journey, str(seeded["journey_id"]))
        room = session.get(JourneyMission, str(seeded["room_id"]))
        child = session.get(JourneyMission, str(seeded["child_id"]))
        receipt = session.get(CollectiveAuthorityReceipt, str(seeded["receipt_id"]))
        assert journey is not None and room is not None and child is not None and receipt is not None
        clarification = json.loads(room.clarification_json or "{}")
        for option in clarification["candidate_options"]:
            plan = session.get(PlanVersion, str(option["plan_id"]))
            assert plan is not None
            option["material_world_epoch"] = collective_mediation.collective_material_world_epoch(
                main_module.collective_material_world_basis(
                    session,
                    journey,
                    plan,
                    fit_subject_place_ids=list(option.get("fit_subject_place_ids") or []),
                )
            )
        selected_option = next(
            item for item in clarification["candidate_options"]
            if item["proposal_id"] == str(seeded["selected_proposal_id"])
        )
        relevant_ids = clarification["decision_relevant_member_ids"]
        members = main_module.active_journey_members_with_capabilities(session, journey)["members"]
        current_epoch = collective_mediation.collective_decision_epoch(
            journey_id=journey.id,
            mission_id=room.id,
            trigger_event_id=str(seeded["event_id"]),
            base_plan_version_id=str(seeded["base_id"]),
            options=clarification["candidate_options"],
            required_member_ids=clarification["required_member_ids"],
            decision_relevant_member_ids=relevant_ids,
            members=members,
        )
        clarification["decision_epoch"] = current_epoch
        clarification["material_world_epoch"] = selected_option["material_world_epoch"]
        room.clarification_json = json.dumps(clarification, sort_keys=True)
        child_intent = json.loads(child.resolved_intent_json or "{}")
        child_intent["collective_decision"]["decision_epoch"] = current_epoch
        child_intent["collective_decision"]["material_world_epoch"] = selected_option["material_world_epoch"]
        child.resolved_intent_json = json.dumps(child_intent, sort_keys=True)
        receipt.decision_epoch = current_epoch
        receipt.material_world_epoch = selected_option["material_world_epoch"]
        session.commit()

        policy = session.get(JourneyRoleCapability, policy_key)
        assert policy is not None
        session.delete(policy)
        session.commit()

    def current_receipt(_session, _journey, _proposals):
        return {
            "proposal_collective_decisions": option_by_id,
            "candidate_fit_matrix": [{"candidate_id": "r60-current-surface"}],
            "collective_mediation": {
                "classification": "HUMAN_TRADEOFF_REQUIRED",
                "decision_relevant_member_ids": [
                    str(seeded["owner_member_id"]),
                    str(seeded["admin_member_id"]),
                ],
            },
        }

    monkeypatch.setattr(main_module, "collective_proposal_receipt", current_receipt)
    monkeypatch.setattr(
        collective_mediation,
        "collective_decision_epoch",
        lambda **kwargs: f"r60-reconsent-{kwargs['mission_id']}-{len(kwargs['options'])}",
    )
    path = f"/api/v1/journeys/{seeded['journey_id']}/group-recovery/apply"
    headers = _apply_headers(str(seeded["owner_id"]), idempotency_key="r60-stale-click-001")
    try:
        stale = client.post(path, headers=headers, json={})
        assert stale.status_code == 409, stale.text
        assert "COLLECTIVE_CONSENT_STALE_RECONSENT_REQUIRED" in str(stale.json())

        with SessionLocal() as session:
            journey = session.get(Journey, str(seeded["journey_id"]))
            old_room = session.get(JourneyMission, str(seeded["room_id"]))
            old_receipt = session.get(CollectiveAuthorityReceipt, str(seeded["receipt_id"]))
            assert journey is not None and journey.active_plan_version_id == str(seeded["base_id"])
            assert old_room is not None
            old = json.loads(old_room.clarification_json or "{}")
            assert old["status"] == "STALE"
            assert set(old["responses"]) == {
                str(seeded["owner_member_id"]),
                str(seeded["admin_member_id"]),
            }
            assert old_receipt is not None and old_receipt.invalidated_at is not None
            successor_rows = session.scalars(
                select(JourneyMission).where(
                    JourneyMission.parent_mission_id == str(seeded["room_id"])
                )
            ).all()
            successor = next(
                row for row in successor_rows
                if json.loads(row.resolved_intent_json or "{}").get("group_recovery", {}).get(
                    "reconsent_for_clarification_id"
                ) == old["clarification_id"]
            )
            first_successor_id = successor.id
            fresh = json.loads(successor.clarification_json or "{}")
            assert fresh["status"] == "WAITING_FOR_MEMBERS"
            assert fresh["required_member_ids"] == [str(seeded["owner_member_id"])]
            assert fresh["decision_epoch"] != old["decision_epoch"]
            assert fresh["responses"] == {}

        repeated = client.post(path, headers=headers, json={})
        assert repeated.status_code == 409
        assert "COLLECTIVE_CONSENT_RECONSENT_IN_PROGRESS" in str(repeated.json())
        with SessionLocal() as session:
            successors = session.scalars(
                select(JourneyMission).where(
                    JourneyMission.parent_mission_id == str(seeded["room_id"])
                )
            ).all()
            current = [
                row for row in successors
                if json.loads(row.resolved_intent_json or "{}").get("group_recovery", {}).get(
                    "reconsent_for_clarification_id"
                ) == "r60-resolved-clarification"
            ]
            assert len(current) == 1
            assert current[0].id == first_successor_id
    finally:
        with SessionLocal() as session:
            current_policy = session.get(JourneyRoleCapability, policy_key)
            if current_policy is not None:
                session.delete(current_policy)
            if original_policy_values is not None:
                session.add(
                    JourneyRoleCapability(
                        role="ADMIN",
                        capability="JOURNEY_UPDATE",
                        scope_message_key=original_policy_values["scope_message_key"],
                        created_at=original_policy_values["created_at"],
                    )
                )
            session.commit()
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)


def test_r60_only_consent_staleness_opens_reconsent_not_execution_failure() -> None:
    assert (
        main_module._group_recovery_reconsent_code("STALE_COLLECTIVE_DECISION")
        == "STALE_COLLECTIVE_DECISION"
    )
    assert (
        main_module._group_recovery_reconsent_code(
            {"code": "RECOVERY_EPOCH_SUPERSEDED"}
        )
        == "RECOVERY_EPOCH_SUPERSEDED"
    )
    assert (
        main_module._group_recovery_reconsent_code(
            "COLLECTIVE_AUTHORITY_RECEIPT_STALE_WORLD_EPOCH"
        )
        == "COLLECTIVE_AUTHORITY_RECEIPT_STALE_WORLD_EPOCH"
    )

    # These failures say the concrete future is no longer executable. Human
    # consent cannot repair them and must not be laundered into a fresh vote.
    assert (
        main_module._group_recovery_reconsent_code(
            "replan is no longer feasible: protected commitment violated"
        )
        is None
    )
    assert (
        main_module._group_recovery_reconsent_code(
            "replan mobility evidence is missing or invalid; regenerate proposal"
        )
        is None
    )
    assert (
        main_module._group_recovery_reconsent_code(
            "accepted replan cannot remap an active C4 commitment"
        )
        is None
    )


def test_r60_unexecutable_proposal_requires_replan_without_invalidating_consent(
    monkeypatch,
) -> None:
    previous_secret = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", _TEST_SECRET)
    seeded = _seed_r60_apply_world()
    _enable_r60_apply_path(monkeypatch, seeded)

    def fail_execution(*_args, **_kwargs):
        raise HTTPException(
            409,
            "replan is no longer feasible: protected commitment violated",
        )

    monkeypatch.setattr(main_module, "_accept_replan_impl", fail_execution)
    path = f"/api/v1/journeys/{seeded['journey_id']}/group-recovery/apply"
    try:
        response = client.post(
            path,
            headers=_apply_headers(
                str(seeded["owner_id"]),
                idempotency_key="r60-invalid-plan-not-revote",
            ),
            json={},
        )
        assert response.status_code == 409, response.text
        detail = response.json()["error"]["details"]
        assert detail["code"] == "GROUP_RECOVERY_REPLAN_REQUIRED"
        assert detail["reconsent"]["available"] is False
        assert detail["plan_unchanged"] is True

        with SessionLocal() as session:
            journey = session.get(Journey, str(seeded["journey_id"]))
            room = session.get(JourneyMission, str(seeded["room_id"]))
            receipt = session.get(
                CollectiveAuthorityReceipt, str(seeded["receipt_id"])
            )
            proposal = session.get(
                ReplanProposal, str(seeded["selected_proposal_id"])
            )
            assert journey is not None
            assert journey.active_plan_version_id == str(seeded["base_id"])
            assert room is not None
            stored = json.loads(room.clarification_json or "{}")
            assert stored["status"] == "RESOLVED"
            assert receipt is not None and receipt.invalidated_at is None
            assert proposal is not None and proposal.status == "PRESENTED"
            reconsent_audits = session.scalars(
                select(AuditLog).where(
                    AuditLog.journey_id == str(seeded["journey_id"]),
                    AuditLog.action == "journey.group_recovery.reconsent.started",
                )
            ).all()
            assert reconsent_audits == []
            replan_required = session.scalars(
                select(AuditLog).where(
                    AuditLog.journey_id == str(seeded["journey_id"]),
                    AuditLog.action == "journey.group_recovery.replan_required",
                )
            ).all()
            assert len(replan_required) == 1
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)


def test_r60_reconsent_lineage_keeps_original_group_recovery_root() -> None:
    seeded = _seed_r60_apply_world()
    successor_id = str(uuid4())
    now = _now()
    with SessionLocal() as session:
        session.add(
            JourneyMission(
                id=successor_id,
                journey_id=str(seeded["journey_id"]),
                traveler_id=str(seeded["owner_id"]),
                trigger_event_id=str(seeded["event_id"]),
                parent_mission_id=str(seeded["room_id"]),
                user_text="Fresh consent round.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="WAITING_FOR_MEMBERS",
                resolved_intent_json=json.dumps(
                    {
                        "group_recovery": {
                            "incident_key": str(seeded["incident_key"]),
                            "reconsent_for_clarification_id": "old-round",
                            "reconsent_generation": 1,
                        }
                    },
                    sort_keys=True,
                ),
                clarification_json=json.dumps(
                    {"kind": "COLLECTIVE_TRADEOFF", "status": "WAITING_FOR_MEMBERS"},
                    sort_keys=True,
                ),
                created_at=now,
                started_at=now,
            )
        )
        session.commit()

        root, context = main_module._group_recovery_lineage_context(
            session, successor_id
        )
        assert root is not None
        assert root.id == str(seeded["room_id"])
        assert context["incident_key"] == str(seeded["incident_key"])
        assert "reconsent_for_clarification_id" not in context
