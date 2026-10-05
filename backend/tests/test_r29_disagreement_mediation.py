from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.collective_mediation as collective_mediation
import app.main as main_module
from app.core.config import settings
from app.agent.gateway import AgentToolGateway, _journey_has_unresolved_collective_mediation
from app.agent.runtime import _acceptance_requested, _collective_mediation_requested
from app.db.models import (
    Activity,
    AuditLog,
    Event,
    Journey,
    JourneyMember,
    JourneyMission,
    Place,
    PlanVersion,
    ProviderObservation,
    ReplanProposal,
    Traveler,
)
from app.db.session import SessionLocal
from app.schemas import AgentToolCall
from app.traveler_principal import issue_traveler_token


client = TestClient(main_module.app)
_TEST_SECRET = "r29-disagreement-test-secret-0123456789abcdef"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_r29_disagreement_mediation_is_not_authority_to_accept_a_side() -> None:
    mission = JourneyMission(
        id=str(uuid4()),
        journey_id=str(uuid4()),
        traveler_id=str(uuid4()),
        user_text=(
            "Mediate the unresolved shared Journey disagreement without choosing a winner."
        ),
        requested_autonomy="EXECUTE_WITHIN_BOUNDS",
        resolved_intent_json=json.dumps(
            {
                "collective_mediation": {
                    "kind": "DISAGREEMENT_MEDIATION",
                    "round": 1,
                    "required_member_ids": ["member-owner", "member-admin"],
                    "member_choices": [
                        {"member_id": "member-owner", "proposal_id": "proposal-garden"},
                        {"member_id": "member-admin", "proposal_id": "proposal-museum"},
                    ],
                }
            },
            sort_keys=True,
        ),
        status="CREATED",
        created_at=_now(),
    )

    assert _collective_mediation_requested(mission) is True
    assert _acceptance_requested(mission) is False


def test_r29_plan_only_mediator_stays_non_mutating() -> None:
    mission = JourneyMission(
        id=str(uuid4()),
        journey_id=str(uuid4()),
        traveler_id=str(uuid4()),
        user_text="Mediate the disagreement.",
        requested_autonomy="PLAN_ONLY",
        resolved_intent_json=json.dumps(
            {"collective_mediation": {"kind": "DISAGREEMENT_MEDIATION", "round": 1}}
        ),
        status="CREATED",
        created_at=_now(),
    )

    assert _collective_mediation_requested(mission) is True
    assert _acceptance_requested(mission) is False


def test_r29_mediation_progress_gate_rejects_same_option_surface() -> None:
    from app.collective_mediation import mediation_progress_gate

    option = {
        "proposal_id": "proposal-old",
        "fit_subject_place_ids": ["place-garden"],
        "fit_subject_tags": ["garden"],
        "fairness": {
            "minimum_member_fit": 0.0,
            "maximum_regret": 1.0,
            "unacceptable_member_ids": ["member-admin"],
        },
    }
    result = mediation_progress_gate(
        [option],
        [{**option, "proposal_id": "proposal-copy"}],
    )
    assert result["allowed"] is False
    assert result["code"] == "MEDIATION_NO_PROGRESS"


def test_r29_mediation_progress_gate_rejects_same_shape_even_with_new_id_and_better_scores() -> None:
    from app.collective_mediation import mediation_progress_gate

    previous = {
        "proposal_id": "proposal-old",
        "fit_subject_place_ids": ["place-garden"],
        "fit_subject_tags": ["garden"],
        "fairness": {
            "minimum_member_fit": 0.0,
            "maximum_regret": 1.0,
            "unacceptable_member_ids": ["member-admin"],
        },
    }
    regenerated = {
        **previous,
        "proposal_id": "proposal-new-row",
        "fairness": {
            "minimum_member_fit": 0.8,
            "maximum_regret": 0.1,
            "unacceptable_member_ids": [],
        },
    }
    result = mediation_progress_gate([previous], [regenerated])
    assert result["allowed"] is False
    assert result["code"] == "MEDIATION_NO_PROGRESS"
    assert result["new_option_count"] == 0


def test_r29_mediation_progress_does_not_use_union_of_different_losers() -> None:
    from app.collective_mediation import mediation_progress_gate

    previous = [
        {
            "proposal_id": "proposal-garden",
            "fit_subject_place_ids": ["place-garden"],
            "fit_subject_tags": ["garden"],
            "fairness": {
                "minimum_member_fit": 0.0,
                "maximum_regret": 1.0,
                "unacceptable_member_ids": ["member-admin"],
            },
        },
        {
            "proposal_id": "proposal-museum",
            "fit_subject_place_ids": ["place-museum"],
            "fit_subject_tags": ["museum"],
            "fairness": {
                "minimum_member_fit": 0.0,
                "maximum_regret": 1.0,
                "unacceptable_member_ids": ["member-owner"],
            },
        },
    ]
    still_sacrifices_one_member = {
        "proposal_id": "proposal-new",
        "fit_subject_place_ids": ["place-gallery"],
        "fit_subject_tags": ["gallery"],
        "fairness": {
            "minimum_member_fit": 0.0,
            "maximum_regret": 1.0,
            "unacceptable_member_ids": ["member-owner"],
        },
    }
    result = mediation_progress_gate(previous, [still_sacrifices_one_member])
    assert result["allowed"] is False
    assert result["previous_best_unacceptable_count"] == 1


def test_r29_mediation_progress_rejects_one_metric_gain_with_fairness_regression() -> None:
    from app.collective_mediation import mediation_progress_gate

    previous = {
        "proposal_id": "proposal-old",
        "fit_subject_place_ids": ["place-old"],
        "fit_subject_tags": ["old"],
        "fairness": {
            "minimum_member_fit": 0.4,
            "maximum_regret": 0.3,
            "unacceptable_member_ids": [],
        },
    }
    misleading = {
        "proposal_id": "proposal-new",
        "fit_subject_place_ids": ["place-new"],
        "fit_subject_tags": ["new"],
        "fairness": {
            "minimum_member_fit": 0.41,
            "maximum_regret": 0.9,
            "unacceptable_member_ids": [],
        },
    }
    result = mediation_progress_gate([previous], [misleading])
    assert result["allowed"] is False
    assert result["code"] == "MEDIATION_NO_PROGRESS"
    assert result["progress_policy"] == "NON_REGRESSING_PARETO_BOUNDARY_WITH_STRICT_IMPROVEMENT"


def test_r29_mediation_progress_gate_accepts_new_fairer_option() -> None:
    from app.collective_mediation import mediation_progress_gate

    previous = {
        "proposal_id": "proposal-old",
        "fit_subject_place_ids": ["place-garden"],
        "fit_subject_tags": ["garden"],
        "fairness": {
            "minimum_member_fit": 0.0,
            "maximum_regret": 1.0,
            "unacceptable_member_ids": ["member-admin"],
        },
    }
    improved = {
        "proposal_id": "proposal-new",
        "fit_subject_place_ids": ["place-craft-garden"],
        "fit_subject_tags": ["craft", "garden"],
        "fairness": {
            "minimum_member_fit": 0.5,
            "maximum_regret": 0.25,
            "unacceptable_member_ids": [],
        },
    }
    result = mediation_progress_gate([previous], [improved])
    assert result["allowed"] is True
    assert result["improved_option_ids"] == ["proposal-new"]


def _seed_r29_disagreement_http_fixture() -> dict[str, str | list[dict[str, object]]]:
    now = _now()
    owner_id, admin_id = str(uuid4()), str(uuid4())
    journey_id, parent_id, event_id = str(uuid4()), str(uuid4()), str(uuid4())
    owner_member_id, admin_member_id = str(uuid4()), str(uuid4())
    base_id, garden_plan_id, museum_plan_id = (str(uuid4()) for _ in range(3))
    garden_proposal_id, museum_proposal_id = str(uuid4()), str(uuid4())
    options = [
        {
            "proposal_id": garden_proposal_id,
            "plan_id": garden_plan_id,
            "status": "GROUNDED_FEASIBLE",
            "fit_subject_place_ids": ["place-garden"],
            "fit_subject_tags": ["garden"],
            "member_fits": {},
            "fairness": {
                "minimum_member_fit": 0.0,
                "maximum_regret": 1.0,
                "unacceptable_member_ids": [admin_member_id],
            },
        },
        {
            "proposal_id": museum_proposal_id,
            "plan_id": museum_plan_id,
            "status": "GROUNDED_FEASIBLE",
            "fit_subject_place_ids": ["place-museum"],
            "fit_subject_tags": ["museum"],
            "member_fits": {},
            "fairness": {
                "minimum_member_fit": 0.0,
                "maximum_regret": 1.0,
                "unacceptable_member_ids": [owner_member_id],
            },
        },
    ]
    with SessionLocal() as session:
        session.add_all([
            Traveler(id=owner_id, display_name="R29 owner", locale="en-US", timezone="UTC", created_at=now, updated_at=now),
            Traveler(id=admin_id, display_name="R29 admin", locale="en-US", timezone="UTC", created_at=now, updated_at=now),
        ])
        session.flush()
        session.add(Journey(
            id=journey_id, traveler_id=owner_id, title="R29 disagreement", city_code="NARA",
            timezone="UTC", start_at=now, end_at=(datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(), budget_currency="JPY", budget_amount_minor=10000,
            planning_mode="balanced", status="ACTIVE", active_plan_version_id=None,
            current_activity_id=None, created_at=now, updated_at=now,
        ))
        session.add_all([
            JourneyMember(id=owner_member_id, journey_id=journey_id, traveler_id=owner_id, role="OWNER", invited_by=owner_id, joined_at=now, preferences_json=json.dumps({"preferences": [{"key": "garden"}]}), created_at=now, updated_at=now),
            JourneyMember(id=admin_member_id, journey_id=journey_id, traveler_id=admin_id, role="ADMIN", invited_by=owner_id, joined_at=now, preferences_json=json.dumps({"preferences": [{"key": "museum"}]}), created_at=now, updated_at=now),
        ])
        session.flush()
        for plan_id, version_no, status in ((base_id, 1, "ACTIVE"), (garden_plan_id, 2, "CANDIDATE"), (museum_plan_id, 3, "CANDIDATE")):
            session.add(PlanVersion(
                id=plan_id, journey_id=journey_id, version_no=version_no, planning_mode="balanced",
                status=status, lifecycle="ACTIVE", source="INITIAL" if plan_id == base_id else "REPLAN", parent_plan_version_id=base_id if plan_id != base_id else None,
                total_cost_minor=0, currency="JPY", estimated_duration_min=60, utility_score=0.0,
                score_breakdown_json="{}", explanation_json="{}", mobility_evidence_json="{}", created_at=now,
            ))
        session.flush()
        session.get(Journey, journey_id).active_plan_version_id = base_id
        session.add(Event(
            id=event_id, journey_id=journey_id, provider_key="system", provenance="SYSTEM_DERIVED",
            event_type="OPPORTUNITY_WINDOW", severity="INFO", status="DETECTED", occurred_at=now,
            detected_at=now, payload_json="{}", created_at=now,
        ))
        for proposal_id, plan_id in ((garden_proposal_id, garden_plan_id), (museum_proposal_id, museum_plan_id)):
            session.add(ReplanProposal(
                id=proposal_id, journey_id=journey_id, trigger_event_id=event_id, base_plan_version_id=base_id,
                proposed_plan_version_id=plan_id, status="PRESENTED", hard_constraints_passed=True,
                locked_commitments_preserved=True, utility_score=0.0, score_breakdown_json="{}",
                diff_json="{}", explanation_json="{}", created_at=now,
            ))
        session.add(JourneyMission(
            id=parent_id, journey_id=journey_id, traveler_id=owner_id, trigger_event_id=event_id,
            user_text="Resolve this shared decision.", requested_autonomy="EXECUTE_WITHIN_BOUNDS",
            status="WAITING_FOR_MEMBERS", max_cost_delta_minor=1000, max_loss_minor=1000,
            max_schedule_drift_min=30, protected_activity_ids_json="[]", mutable_activity_ids_json="[]",
            allowed_action_classes_json="[\"REPLAN\"]", clarification_json=json.dumps({
                "kind": "COLLECTIVE_TRADEOFF", "status": "WAITING_FOR_MEMBERS", "clarification_id": "r29-clarification",
                "decision_epoch": "r29-epoch", "trigger_event_id": event_id, "base_plan_version_id": base_id,
                "candidate_options": options, "required_member_ids": [owner_member_id, admin_member_id], "responses": {},
            }, sort_keys=True), created_at=now, started_at=now,
        ))
        session.commit()
    return {
        "journey_id": journey_id, "parent_id": parent_id, "event_id": event_id,
        "owner_id": owner_id, "admin_id": admin_id, "owner_member_id": owner_member_id,
        "admin_member_id": admin_member_id, "base_id": base_id, "options": options,
        "garden_proposal_id": garden_proposal_id, "museum_proposal_id": museum_proposal_id,
    }


def test_r29_conflicting_authenticated_responses_create_mediation_child(monkeypatch) -> None:
    previous_secret = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", _TEST_SECRET)
    seeded = _seed_r29_disagreement_http_fixture()
    options = seeded["options"]

    def receipt(_session, _journey, _proposals):
        return {
            "proposal_collective_decisions": {item["proposal_id"]: item for item in options},
            "collective_mediation": {
                "classification": "HUMAN_TRADEOFF_REQUIRED",
                "decision_relevant_member_ids": [seeded["owner_member_id"], seeded["admin_member_id"]],
            },
        }

    monkeypatch.setattr(main_module, "collective_proposal_receipt", receipt)
    monkeypatch.setattr(collective_mediation, "collective_decision_epoch", lambda **_kwargs: "r29-epoch")
    try:
        owner_token = issue_traveler_token(str(seeded["owner_id"]))
        admin_token = issue_traveler_token(str(seeded["admin_id"]))
        path = f"/api/v1/journeys/{seeded['journey_id']}/missions/{seeded['parent_id']}/collective-clarification"
        first = client.post(
            f"{path}/{seeded['owner_member_id']}",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"clarification_id": "r29-clarification", "proposal_id": seeded["garden_proposal_id"]},
        )
        assert first.status_code == 200, first.text
        assert first.json()["status"] == "WAITING_FOR_MEMBERS"
        second = client.post(
            f"{path}/{seeded['admin_member_id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"clarification_id": "r29-clarification", "proposal_id": seeded["museum_proposal_id"]},
        )
        assert second.status_code == 200, second.text
        payload = second.json()
        assert payload["status"] == "MEDIATION_REQUIRED"
        assert payload["child_mission"] is not None
        child_id = payload["child_mission"]["id"]
        with SessionLocal() as session:
            journey = session.get(Journey, seeded["journey_id"])
            parent = session.get(JourneyMission, seeded["parent_id"])
            child = session.get(JourneyMission, child_id)
            proposal_rows = session.scalars(select(ReplanProposal).where(ReplanProposal.journey_id == journey.id)).all()
            audits = session.scalars(select(AuditLog).where(AuditLog.action == "agent.collective_decision.mediation_started")).all()
            assert journey.active_plan_version_id == seeded["base_id"]
            assert all(row.status != "ACCEPTED" for row in proposal_rows)
            assert parent.status == "ANSWERED"
            intent = json.loads(child.resolved_intent_json)
            mediation = intent["collective_mediation"]
            assert mediation["kind"] == "DISAGREEMENT_MEDIATION"
            assert {item["proposal_id"] for item in mediation["member_choices"]} == {seeded["garden_proposal_id"], seeded["museum_proposal_id"]}
            assert "selected_proposal_id" not in mediation
            snapshots = mediation["member_preference_snapshots"]
            assert snapshots[str(seeded["owner_member_id"])] == [{"key": "garden"}]
            assert snapshots[str(seeded["admin_member_id"])] == [{"key": "museum"}]
            assert child.max_cost_delta_minor == parent.max_cost_delta_minor
            assert child.max_loss_minor == parent.max_loss_minor
            assert child.max_schedule_drift_min == parent.max_schedule_drift_min
            assert audits
            members = session.scalars(select(JourneyMember).where(JourneyMember.journey_id == journey.id)).all()
            assert json.loads(next(item.preferences_json for item in members if item.id == seeded["owner_member_id"])) == {"preferences": [{"key": "garden"}]}
            assert json.loads(next(item.preferences_json for item in members if item.id == seeded["admin_member_id"])) == {"preferences": [{"key": "museum"}]}
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous_secret)

def test_r29_mediator_cannot_mutate_active_reality_before_fresh_collective_round() -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    mediator_id = str(uuid4())
    now = _now()
    with SessionLocal() as session:
        parent = session.get(JourneyMission, str(seeded["parent_id"]))
        parent_clarification = json.loads(parent.clarification_json or "{}")
        parent_clarification["status"] = "MEDIATION_REQUIRED"
        parent.clarification_json = json.dumps(parent_clarification, sort_keys=True)
        parent.status = "ANSWERED"
        session.add(
            JourneyMission(
                id=mediator_id,
                journey_id=str(seeded["journey_id"]),
                traveler_id=str(seeded["owner_id"]),
                trigger_event_id=str(seeded["event_id"]),
                user_text="Mediate the unresolved disagreement.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="CREATED",
                resolved_intent_json=json.dumps(
                    {
                        "collective_mediation": {
                            "kind": "DISAGREEMENT_MEDIATION",
                            "round": 1,
                            "source_mission_id": str(seeded["parent_id"]),
                        }
                    },
                    sort_keys=True,
                ),
                created_at=now,
            )
        )
        session.commit()

        request = AgentToolCall(
            request_id="r29-deny-mutation-001",
            agent_id="r29-test-agent",
            journey_id=UUID(str(seeded["journey_id"])),
            mission_id=UUID(mediator_id),
            proposal_id=UUID(str(seeded["garden_proposal_id"])),
        )
        with pytest.raises(HTTPException) as exc:
            AgentToolGateway(session).dispatch("accept_replan", request)
        assert exc.value.status_code == 409
        assert exc.value.detail == "MEDIATION_REQUIRES_FRESH_COLLECTIVE_DECISION"

        denial = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.action == "agent.collective_mediation.mutation_denied",
                AuditLog.entity_id == mediator_id,
            )
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        )
        assert denial is not None
        facts = json.loads(denial.after_json)
        assert facts["tool"] == "accept_replan"
        assert facts["reason"] == "FRESH_COLLECTIVE_DECISION_REQUIRED"

        # Starting another Agent mission, or omitting the mediator mission id,
        # cannot launder authority around the Journey-level disagreement lock.
        bypass = AgentToolCall(
            request_id="r29-deny-bypass-001",
            agent_id="r29-other-agent",
            journey_id=UUID(str(seeded["journey_id"])),
            proposal_id=UUID(str(seeded["garden_proposal_id"])),
        )
        with pytest.raises(HTTPException) as bypass_exc:
            AgentToolGateway(session).dispatch("accept_replan", bypass)
        assert bypass_exc.value.status_code == 409
        assert bypass_exc.value.detail == "MEDIATION_REQUIRES_FRESH_COLLECTIVE_DECISION"


def test_r29_core_collective_mutation_gate_blocks_direct_rest_bypass() -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    now = _now()
    mediator_id = str(uuid4())
    with SessionLocal() as session:
        parent = session.get(JourneyMission, str(seeded["parent_id"]))
        clarification = json.loads(parent.clarification_json or "{}")
        clarification["status"] = "MEDIATION_REQUIRED"
        parent.clarification_json = json.dumps(clarification, sort_keys=True)
        parent.status = "ANSWERED"
        session.add(
            JourneyMission(
                id=mediator_id,
                journey_id=str(seeded["journey_id"]),
                traveler_id=str(seeded["owner_id"]),
                trigger_event_id=str(seeded["event_id"]),
                user_text="Mediate the unresolved disagreement.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="CREATED",
                resolved_intent_json=json.dumps(
                    {
                        "collective_mediation": {
                            "kind": "DISAGREEMENT_MEDIATION",
                            "round": 1,
                            "source_mission_id": str(seeded["parent_id"]),
                        }
                    },
                    sort_keys=True,
                ),
                created_at=now,
            )
        )
        session.commit()

        journey = session.get(Journey, str(seeded["journey_id"]))
        target_plan_id = str(seeded["options"][0]["plan_id"])
        target_plan = session.get(PlanVersion, target_plan_id)
        gate = main_module.collective_mutation_gate(
            session,
            journey,
            target_plan,
            hard_feasible_plan_ids={target_plan_id},
            resolved_decision={
                "status": "RESOLVED",
                "selected_candidate_id": target_plan_id,
            },
        )
        assert gate["allowed"] is False
        assert gate["code"] == "COLLECTIVE_MEDIATION_RENEWED_CONSENT_REQUIRED"
        assert gate["classification"] == "MEDIATION_REQUIRED"


def test_r29_resolved_mediation_authorizes_only_the_selected_plan_until_consumed() -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    now = _now()
    mediator_id = str(uuid4())
    with SessionLocal() as session:
        mediator = JourneyMission(
            id=mediator_id,
            journey_id=str(seeded["journey_id"]),
            traveler_id=str(seeded["owner_id"]),
            trigger_event_id=str(seeded["event_id"]),
            parent_mission_id=str(seeded["parent_id"]),
            user_text="Mediate the unresolved disagreement.",
            requested_autonomy="EXECUTE_WITHIN_BOUNDS",
            status="ANSWERED",
            resolved_intent_json=json.dumps(
                {
                    "collective_mediation": {
                        "kind": "DISAGREEMENT_MEDIATION",
                        "round": 1,
                        "source_mission_id": str(seeded["parent_id"]),
                    }
                },
                sort_keys=True,
            ),
            clarification_json=json.dumps(
                {
                    "kind": "COLLECTIVE_TRADEOFF",
                    "status": "RESOLVED",
                    "clarification_id": "r29-renewed-resolution",
                    "selected_proposal_id": str(seeded["garden_proposal_id"]),
                },
                sort_keys=True,
            ),
            created_at=now,
            started_at=now,
            completed_at=now,
        )
        session.add(mediator)
        session.commit()

        journey = session.get(Journey, str(seeded["journey_id"]))
        garden_plan_id = str(seeded["options"][0]["plan_id"])
        museum_plan_id = str(seeded["options"][1]["plan_id"])
        museum_plan = session.get(PlanVersion, museum_plan_id)

        sibling_gate = main_module.collective_mutation_gate(
            session,
            journey,
            museum_plan,
            hard_feasible_plan_ids={museum_plan_id},
        )
        assert sibling_gate["allowed"] is False
        assert sibling_gate["code"] == "COLLECTIVE_MEDIATION_SELECTED_PLAN_REQUIRED"
        assert (
            sibling_gate["mediation"]["selected_plan_version_id"]
            == garden_plan_id
        )

        # Once the selected proposal is durably consumed, the old mediation
        # decision no longer acts as a permanent lock on future Journey work.
        selected_proposal = session.get(
            ReplanProposal, str(seeded["garden_proposal_id"])
        )
        selected_proposal.status = "ACCEPTED"
        session.commit()

        from app.collective_mediation import pending_resolved_mediation_selection

        assert pending_resolved_mediation_selection(
            session,
            str(seeded["journey_id"]),
            active_plan_version_id=journey.active_plan_version_id,
        ) is None


def test_r29_renewed_human_choice_overrides_algorithmic_compromise_ranking(monkeypatch) -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    now = _now()
    mediator_id = str(uuid4())
    selected_plan_id = str(seeded["options"][0]["plan_id"])
    sibling_plan_id = str(seeded["options"][1]["plan_id"])

    with SessionLocal() as session:
        session.add(
            JourneyMission(
                id=mediator_id,
                journey_id=str(seeded["journey_id"]),
                traveler_id=str(seeded["owner_id"]),
                trigger_event_id=str(seeded["event_id"]),
                parent_mission_id=str(seeded["parent_id"]),
                user_text="Mediate the unresolved disagreement.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="ANSWERED",
                resolved_intent_json=json.dumps(
                    {
                        "collective_mediation": {
                            "kind": "DISAGREEMENT_MEDIATION",
                            "round": 1,
                            "source_mission_id": str(seeded["parent_id"]),
                        }
                    },
                    sort_keys=True,
                ),
                clarification_json=json.dumps(
                    {
                        "kind": "COLLECTIVE_TRADEOFF",
                        "status": "RESOLVED",
                        "clarification_id": "r29-renewed-ranking",
                        "selected_proposal_id": str(seeded["garden_proposal_id"]),
                    },
                    sort_keys=True,
                ),
                created_at=now,
                started_at=now,
                completed_at=now,
            )
        )
        session.commit()

        original_projection = main_module.active_journey_members_with_capabilities

        def projection(_session, _journey, *, candidate_windows=None, **kwargs):
            if candidate_windows is None:
                return {"member_count": 2, "members": []}
            candidate_ids = [
                str((item.get("candidate") or {}).get("place_id") or item.get("window_id") or "")
                for item in candidate_windows
            ]
            return {
                "member_count": 2,
                "members": [],
                "candidate_fit_matrix": [],
                "mediation": {
                    "classification": "COMPROMISE_AVAILABLE",
                    "candidate_ids": candidate_ids,
                    # Deliberately make the algorithm prefer the sibling plan.
                    "selected_candidate_id": sibling_plan_id,
                },
            }

        monkeypatch.setattr(
            main_module,
            "active_journey_members_with_capabilities",
            projection,
        )
        try:
            journey = session.get(Journey, str(seeded["journey_id"]))
            selected_plan = session.get(PlanVersion, selected_plan_id)
            sibling_plan = session.get(PlanVersion, sibling_plan_id)

            selected_gate = main_module.collective_mutation_gate(
                session,
                journey,
                selected_plan,
                hard_feasible_plan_ids={selected_plan_id, sibling_plan_id},
            )
            assert selected_gate["allowed"] is True
            assert selected_gate["classification"] == "RENEWED_COLLECTIVE_CONSENT"

            sibling_gate = main_module.collective_mutation_gate(
                session,
                journey,
                sibling_plan,
                hard_feasible_plan_ids={selected_plan_id, sibling_plan_id},
            )
            assert sibling_gate["allowed"] is False
            assert sibling_gate["code"] == "COLLECTIVE_MEDIATION_SELECTED_PLAN_REQUIRED"
        finally:
            monkeypatch.setattr(
                main_module,
                "active_journey_members_with_capabilities",
                original_projection,
            )


def test_r29_renewed_consent_cannot_override_hard_revalidation(monkeypatch) -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    now = _now()
    mediator_id = str(uuid4())
    selected_plan_id = str(seeded["options"][0]["plan_id"])

    with SessionLocal() as session:
        session.add(
            JourneyMission(
                id=mediator_id,
                journey_id=str(seeded["journey_id"]),
                traveler_id=str(seeded["owner_id"]),
                trigger_event_id=str(seeded["event_id"]),
                parent_mission_id=str(seeded["parent_id"]),
                user_text="Mediate the unresolved disagreement.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="ANSWERED",
                resolved_intent_json=json.dumps(
                    {
                        "collective_mediation": {
                            "kind": "DISAGREEMENT_MEDIATION",
                            "round": 1,
                            "source_mission_id": str(seeded["parent_id"]),
                        }
                    },
                    sort_keys=True,
                ),
                clarification_json=json.dumps(
                    {
                        "kind": "COLLECTIVE_TRADEOFF",
                        "status": "RESOLVED",
                        "clarification_id": "r29-renewed-stale",
                        "selected_proposal_id": str(seeded["garden_proposal_id"]),
                    },
                    sort_keys=True,
                ),
                created_at=now,
                started_at=now,
                completed_at=now,
            )
        )
        session.commit()

        class _NotSelectable:
            def model_dump(self, *, mode="json"):
                return {"selectable": False}

        monkeypatch.setattr(
            main_module,
            "plan_schema",
            lambda _session, _plan: _NotSelectable(),
        )
        monkeypatch.setattr(
            main_module,
            "active_journey_members_with_capabilities",
            lambda _session, _journey, *, candidate_windows=None: (
                {"member_count": 2, "members": []}
                if candidate_windows is None
                else {
                    "member_count": 2,
                    "members": [],
                    "candidate_fit_matrix": [],
                    "mediation": {
                        "classification": "COMPROMISE_AVAILABLE",
                        "candidate_ids": [selected_plan_id],
                        "selected_candidate_id": selected_plan_id,
                    },
                }
            ),
        )

        journey = session.get(Journey, str(seeded["journey_id"]))
        selected_plan = session.get(PlanVersion, selected_plan_id)
        gate = main_module.collective_mutation_gate(
            session,
            journey,
            selected_plan,
            hard_feasible_plan_ids=set(),
        )
        assert gate["allowed"] is False
        assert gate["code"] == "COLLECTIVE_SELECTED_PLAN_REVALIDATION_REQUIRED"
        assert gate["classification"] == "RENEWED_COLLECTIVE_CONSENT_STALE"


def test_r29_superseded_resolved_consent_cannot_resurrect() -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    now = _now()
    old_mission_id = str(uuid4())
    new_mission_id = str(uuid4())

    with SessionLocal() as session:
        session.add_all([
            JourneyMission(
                id=old_mission_id,
                journey_id=str(seeded["journey_id"]),
                traveler_id=str(seeded["owner_id"]),
                trigger_event_id=str(seeded["event_id"]),
                parent_mission_id=str(seeded["parent_id"]),
                user_text="Older resolved mediation.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="ANSWERED",
                resolved_intent_json=json.dumps(
                    {
                        "collective_mediation": {
                            "kind": "DISAGREEMENT_MEDIATION",
                            "round": 1,
                            "source_mission_id": str(seeded["parent_id"]),
                        }
                    },
                    sort_keys=True,
                ),
                clarification_json=json.dumps(
                    {
                        "kind": "COLLECTIVE_TRADEOFF",
                        "status": "RESOLVED",
                        "clarification_id": "r29-old-consent",
                        "selected_proposal_id": str(seeded["garden_proposal_id"]),
                    },
                    sort_keys=True,
                ),
                created_at=now,
                started_at=now,
                completed_at=now,
            ),
            JourneyMission(
                id=new_mission_id,
                journey_id=str(seeded["journey_id"]),
                traveler_id=str(seeded["owner_id"]),
                trigger_event_id=str(seeded["event_id"]),
                parent_mission_id=old_mission_id,
                user_text="Newer resolved mediation.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="ANSWERED",
                resolved_intent_json=json.dumps(
                    {
                        "collective_mediation": {
                            "kind": "DISAGREEMENT_MEDIATION",
                            "round": 2,
                            "source_mission_id": old_mission_id,
                        }
                    },
                    sort_keys=True,
                ),
                clarification_json=json.dumps(
                    {
                        "kind": "COLLECTIVE_TRADEOFF",
                        "status": "RESOLVED",
                        "clarification_id": "r29-new-consent",
                        "selected_proposal_id": str(seeded["museum_proposal_id"]),
                    },
                    sort_keys=True,
                ),
                created_at=(datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
                started_at=(datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
                completed_at=(datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
            ),
        ])
        newer_proposal = session.get(
            ReplanProposal, str(seeded["museum_proposal_id"])
        )
        newer_proposal.status = "REJECTED"
        session.commit()

        from app.collective_mediation import pending_resolved_mediation_selection

        journey = session.get(Journey, str(seeded["journey_id"]))
        assert pending_resolved_mediation_selection(
            session,
            str(seeded["journey_id"]),
            active_plan_version_id=journey.active_plan_version_id,
        ) is None


def test_r29_journey_mediation_lock_clears_only_after_resolved_descendant() -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    mediator_id = str(uuid4())
    now = _now()
    with SessionLocal() as session:
        parent = session.get(JourneyMission, str(seeded["parent_id"]))
        clarification = json.loads(parent.clarification_json or "{}")
        clarification["status"] = "MEDIATION_REQUIRED"
        parent.clarification_json = json.dumps(clarification, sort_keys=True)
        parent.status = "ANSWERED"
        mediator = JourneyMission(
            id=mediator_id,
            journey_id=str(seeded["journey_id"]),
            traveler_id=str(seeded["owner_id"]),
            trigger_event_id=str(seeded["event_id"]),
            user_text="Mediate the unresolved disagreement.",
            requested_autonomy="EXECUTE_WITHIN_BOUNDS",
            status="WAITING_FOR_MEMBERS",
            resolved_intent_json=json.dumps(
                {
                    "collective_mediation": {
                        "kind": "DISAGREEMENT_MEDIATION",
                        "round": 1,
                        "source_mission_id": str(seeded["parent_id"]),
                    }
                },
                sort_keys=True,
            ),
            clarification_json=json.dumps(
                {"kind": "COLLECTIVE_TRADEOFF", "status": "WAITING_FOR_MEMBERS"},
                sort_keys=True,
            ),
            created_at=now,
        )
        session.add(mediator)
        session.commit()

        assert _journey_has_unresolved_collective_mediation(
            session, str(seeded["journey_id"])
        ) is True

        mediator.clarification_json = json.dumps(
            {"kind": "COLLECTIVE_TRADEOFF", "status": "RESOLVED"},
            sort_keys=True,
        )
        mediator.status = "ANSWERED"
        session.commit()

        assert _journey_has_unresolved_collective_mediation(
            session, str(seeded["journey_id"])
        ) is False


def test_r29_fair_compromise_reopens_same_members_for_renewed_consent(monkeypatch) -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    mediator_id = str(uuid4())
    new_plan_id = str(uuid4())
    new_proposal_id = str(uuid4())
    now = _now()
    old_options = list(seeded["options"])
    fair_option = {
        "proposal_id": new_proposal_id,
        "plan_id": new_plan_id,
        "status": "GROUNDED_FEASIBLE",
        "fit_subject_place_ids": ["place-craft-garden"],
        "fit_subject_tags": ["craft", "garden"],
        "member_fits": {
            str(seeded["owner_member_id"]): {"effective_fit": 0.7},
            str(seeded["admin_member_id"]): {"effective_fit": 0.7},
        },
        "fairness": {
            "minimum_member_fit": 0.7,
            "maximum_regret": 0.0,
            "unacceptable_member_ids": [],
        },
    }

    with SessionLocal() as session:
        session.add(
            PlanVersion(
                id=new_plan_id,
                journey_id=str(seeded["journey_id"]),
                version_no=4,
                planning_mode="balanced",
                status="CANDIDATE",
                lifecycle="ACTIVE",
                source="REPLAN",
                parent_plan_version_id=str(seeded["base_id"]),
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
        session.add(
            ReplanProposal(
                id=new_proposal_id,
                journey_id=str(seeded["journey_id"]),
                trigger_event_id=str(seeded["event_id"]),
                base_plan_version_id=str(seeded["base_id"]),
                proposed_plan_version_id=new_plan_id,
                status="PRESENTED",
                hard_constraints_passed=True,
                locked_commitments_preserved=True,
                utility_score=0.0,
                score_breakdown_json="{}",
                diff_json="{}",
                explanation_json="{}",
                created_at=now,
            )
        )
        session.add(
            JourneyMission(
                id=mediator_id,
                journey_id=str(seeded["journey_id"]),
                traveler_id=str(seeded["owner_id"]),
                trigger_event_id=str(seeded["event_id"]),
                user_text="Mediate the unresolved disagreement.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="CREATED",
                resolved_intent_json=json.dumps(
                    {
                        "collective_mediation": {
                            "kind": "DISAGREEMENT_MEDIATION",
                            "round": 1,
                            "source_mission_id": str(seeded["parent_id"]),
                            "required_member_ids": [
                                str(seeded["owner_member_id"]),
                                str(seeded["admin_member_id"]),
                            ],
                        }
                    },
                    sort_keys=True,
                ),
                created_at=now,
            )
        )
        session.commit()

    def receipt(_session, _journey, _proposals):
        options = [*old_options, fair_option]
        return {
            "proposal_collective_decisions": {
                str(item["proposal_id"]): item for item in options
            },
            # The new option is algorithmically fair. R29 still requires
            # renewed human consent because the previous round ended in
            # explicit disagreement.
            "collective_mediation": {
                "classification": "COMPROMISE_AVAILABLE",
                "candidate_ids": [new_plan_id],
                "selected_candidate_id": new_plan_id,
            },
        }

    monkeypatch.setattr(main_module, "collective_proposal_receipt", receipt)
    with SessionLocal() as session:
        request = AgentToolCall(
            request_id="r29-renew-consent-001",
            agent_id="r29-test-agent",
            journey_id=UUID(str(seeded["journey_id"])),
            mission_id=UUID(mediator_id),
            trigger_event_id=UUID(str(seeded["event_id"])),
        )
        result = AgentToolGateway(session).dispatch(
            "request_collective_decision",
            request,
        )
        assert result["mission_status"] == "WAITING_FOR_MEMBERS"
        clarification = result["clarification"]
        assert clarification["policy"] == "POST_DISAGREEMENT_REQUIRES_RENEWED_MEMBER_CONSENT"
        assert set(clarification["required_member_ids"]) == {
            str(seeded["owner_member_id"]),
            str(seeded["admin_member_id"]),
        }
        assert clarification["mediation_progress"]["allowed"] is True
        assert new_proposal_id in clarification["mediation_progress"]["improved_option_ids"]
        mission = session.get(JourneyMission, mediator_id)
        assert mission.status == "WAITING_FOR_MEMBERS"




def test_r30_collective_decision_epoch_tracks_semantic_option_meaning() -> None:
    members = [
        {
            "member_id": "member-a",
            "role": "OWNER",
            "capabilities": ["EDIT_PLAN"],
            "journey_scoped_explicit_preferences": [
                {"category": "interest", "key": "garden", "value": True, "weight": 1.0}
            ],
            "member_state": "MEMBER_IN_FORCE",
        },
        {
            "member_id": "member-b",
            "role": "ADMIN",
            "capabilities": ["EDIT_PLAN"],
            "journey_scoped_explicit_preferences": [
                {"category": "interest", "key": "museum", "value": True, "weight": 1.0}
            ],
            "member_state": "MEMBER_IN_FORCE",
        },
    ]
    base_option = {
        "proposal_id": "proposal-a",
        "plan_id": "plan-a",
        "status": "GROUNDED_FEASIBLE",
        "fit_subject_place_ids": ["place-garden"],
        "fit_subject_tags": ["outdoor", "garden"],
        "fit_subject_basis": "PLAN_DIFF",
        "member_fits": {
            "member-a": {
                "effective_fit": 1.0,
                "preference_tier": "EXPLICIT",
                "conflict": None,
            },
            "member-b": {
                "effective_fit": 0.0,
                "preference_tier": "NEUTRAL",
                "conflict": None,
            },
        },
        "fairness": {
            "minimum_member_fit": 0.0,
            "maximum_regret": 1.0,
            "unacceptable_member_ids": ["member-b"],
        },
    }

    def epoch(option):
        return collective_mediation.collective_decision_epoch(
            journey_id="journey-a",
            mission_id="mission-a",
            trigger_event_id="event-a",
            base_plan_version_id="base-plan",
            options=[option],
            required_member_ids=["member-b", "member-a"],
            members=members,
        )

    baseline = epoch(base_option)
    reordered = epoch(
        {
            **base_option,
            "fit_subject_place_ids": list(reversed(base_option["fit_subject_place_ids"])),
            "fit_subject_tags": list(reversed(base_option["fit_subject_tags"])),
            "debug_only": "ignored",
        }
    )
    assert reordered == baseline

    changed_place = epoch(
        {**base_option, "fit_subject_place_ids": ["place-museum"]}
    )
    assert changed_place != baseline

    changed_fit = epoch(
        {
            **base_option,
            "member_fits": {
                **base_option["member_fits"],
                "member-b": {
                    "effective_fit": 0.5,
                    "preference_tier": "LEARNED_SOFT",
                    "conflict": None,
                },
            },
        }
    )
    assert changed_fit != baseline


def test_r30_core_gate_rejects_resolved_consent_when_semantic_epoch_changed(
    monkeypatch,
) -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    now = _now()
    mediator_id = str(uuid4())
    selected_plan_id = str(seeded["options"][0]["plan_id"])

    with SessionLocal() as session:
        session.add(
            JourneyMission(
                id=mediator_id,
                journey_id=str(seeded["journey_id"]),
                traveler_id=str(seeded["owner_id"]),
                trigger_event_id=str(seeded["event_id"]),
                parent_mission_id=str(seeded["parent_id"]),
                user_text="Resolved renewed consent before a semantic shock.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="ANSWERED",
                resolved_intent_json=json.dumps(
                    {
                        "collective_mediation": {
                            "kind": "DISAGREEMENT_MEDIATION",
                            "round": 1,
                            "source_mission_id": str(seeded["parent_id"]),
                        }
                    },
                    sort_keys=True,
                ),
                clarification_json=json.dumps(
                    {
                        "kind": "COLLECTIVE_TRADEOFF",
                        "status": "RESOLVED",
                        "clarification_id": "r30-consent-before-shock",
                        "decision_epoch": "epoch-before-shock",
                        "trigger_event_id": str(seeded["event_id"]),
                        "candidate_options": seeded["options"],
                        "required_member_ids": [
                            str(seeded["owner_member_id"]),
                            str(seeded["admin_member_id"]),
                        ],
                        "selected_proposal_id": str(seeded["garden_proposal_id"]),
                    },
                    sort_keys=True,
                ),
                created_at=now,
                started_at=now,
                completed_at=now,
            )
        )
        session.commit()

        class _Selectable:
            def model_dump(self, *, mode="json"):
                return {"selectable": True}

        members = [
            {
                "member_id": str(seeded["owner_member_id"]),
                "role": "OWNER",
                "capabilities": ["EDIT_PLAN"],
                "journey_scoped_explicit_preferences": [{"key": "garden"}],
                "member_state": "MEMBER_IN_FORCE",
            },
            {
                "member_id": str(seeded["admin_member_id"]),
                "role": "ADMIN",
                "capabilities": ["EDIT_PLAN"],
                "journey_scoped_explicit_preferences": [{"key": "museum"}],
                "member_state": "MEMBER_IN_FORCE",
            },
        ]

        def projection(_session, _journey, *, candidate_windows=None):
            if candidate_windows is None:
                return {"member_count": 2, "members": members}
            return {
                "member_count": 2,
                "members": members,
                "candidate_fit_matrix": [],
                "mediation": {
                    "classification": "COMPROMISE_AVAILABLE",
                    "candidate_ids": [selected_plan_id],
                    "selected_candidate_id": selected_plan_id,
                },
            }

        monkeypatch.setattr(main_module, "plan_schema", lambda *_args, **_kwargs: _Selectable())
        monkeypatch.setattr(
            main_module, "active_journey_members_with_capabilities", projection
        )
        monkeypatch.setattr(
            main_module,
            "collective_proposal_receipt",
            lambda _session, _journey, _proposals: {
                "proposal_collective_decisions": {
                    str(item["proposal_id"]): item for item in seeded["options"]
                }
            },
        )
        monkeypatch.setattr(
            collective_mediation,
            "collective_decision_epoch",
            lambda **_kwargs: "epoch-after-shock",
        )

        journey = session.get(Journey, str(seeded["journey_id"]))
        selected_plan = session.get(PlanVersion, selected_plan_id)
        gate = main_module.collective_mutation_gate(
            session,
            journey,
            selected_plan,
            hard_feasible_plan_ids={selected_plan_id},
        )

        assert gate["allowed"] is False
        assert gate["code"] == "COLLECTIVE_CONSENT_EPOCH_STALE"
        assert gate["classification"] == "RENEWED_COLLECTIVE_CONSENT_STALE"
        assert gate["resolved_decision_epoch"] == "epoch-before-shock"
        assert gate["current_decision_epoch"] == "epoch-after-shock"



def test_r30_world_epoch_rejects_relevant_post_consent_shock(monkeypatch) -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    now = _now()
    selected_plan_id = str(seeded["options"][0]["plan_id"])
    selected_proposal_id = str(seeded["garden_proposal_id"])
    mediator_id = str(uuid4())
    candidate_activity_id = str(uuid4())
    active_activity_id = str(uuid4())
    place_id = "place-r30-selected-garden"

    with SessionLocal() as session:
        session.add(
            Place(
                id=place_id,
                provider_key="openstreetmap-replay",
                external_id="r30-selected-garden",
                city_code="NARA",
                name="R30 selected garden",
                category="garden",
                latitude=34.0,
                longitude=135.0,
                opening_hours_json=json.dumps(
                    {
                        "status": "NORMALIZED_VALID",
                        "open": "09:00",
                        "close": "18:00",
                        "intervals": [{"open": "09:00", "close": "18:00"}],
                    },
                    sort_keys=True,
                ),
                tags_json=json.dumps(["garden", "outdoor"], sort_keys=True),
                metadata_json=json.dumps(
                    {
                        "tags": {"fee": "no"},
                        "cost_evidence": {
                            "status": "KNOWN",
                            "amount_minor": 0,
                            "currency": None,
                        },
                    },
                    sort_keys=True,
                ),
                updated_at=now,
            )
        )
        session.add_all(
            [
                Activity(
                    id=candidate_activity_id,
                    plan_version_id=selected_plan_id,
                    sequence_no=1,
                    activity_type="visit",
                    title="R30 selected garden candidate row",
                    place_id=place_id,
                    city_service_id=None,
                    start_at=now,
                    end_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    travel_from_prev_min=0,
                    estimated_cost_minor=0,
                    currency="JPY",
                    status="PLANNED",
                    locked=False,
                    metadata_json="{}",
                    created_at=now,
                    updated_at=now,
                ),
                Activity(
                    id=active_activity_id,
                    plan_version_id=str(seeded["base_id"]),
                    sequence_no=1,
                    activity_type="visit",
                    title="R30 same physical garden on active plan",
                    place_id=place_id,
                    city_service_id=None,
                    start_at=now,
                    end_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    travel_from_prev_min=0,
                    estimated_cost_minor=0,
                    currency="JPY",
                    status="PLANNED",
                    locked=False,
                    metadata_json="{}",
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.flush()
        journey = session.get(Journey, str(seeded["journey_id"]))
        selected_plan = session.get(PlanVersion, selected_plan_id)
        baseline_basis = main_module.collective_material_world_basis(
            session,
            journey,
            selected_plan,
            fit_subject_place_ids=[place_id],
        )
        baseline_epoch = collective_mediation.collective_material_world_epoch(
            baseline_basis
        )
        options = [
            {
                **item,
                "fit_subject_place_ids": (
                    [place_id]
                    if str(item["proposal_id"]) == selected_proposal_id
                    else item["fit_subject_place_ids"]
                ),
            }
            for item in seeded["options"]
        ]
        session.add(
            JourneyMission(
                id=mediator_id,
                journey_id=str(seeded["journey_id"]),
                traveler_id=str(seeded["owner_id"]),
                trigger_event_id=str(seeded["event_id"]),
                parent_mission_id=str(seeded["parent_id"]),
                user_text="Resolved consent before a provider-backed shock.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="ANSWERED",
                resolved_intent_json=json.dumps(
                    {
                        "collective_mediation": {
                            "kind": "DISAGREEMENT_MEDIATION",
                            "round": 1,
                            "source_mission_id": str(seeded["parent_id"]),
                        }
                    },
                    sort_keys=True,
                ),
                clarification_json=json.dumps(
                    {
                        "kind": "COLLECTIVE_TRADEOFF",
                        "status": "RESOLVED",
                        "clarification_id": "r30-world-before-shock",
                        "decision_epoch": "semantic-stable",
                        "material_world_epoch": baseline_epoch,
                        "material_world_basis": baseline_basis,
                        "trigger_event_id": str(seeded["event_id"]),
                        "candidate_options": options,
                        "required_member_ids": [
                            str(seeded["owner_member_id"]),
                            str(seeded["admin_member_id"]),
                        ],
                        "selected_proposal_id": selected_proposal_id,
                    },
                    sort_keys=True,
                ),
                created_at=now,
                started_at=now,
                completed_at=now,
            )
        )
        session.add(
            Event(
                id=str(uuid4()),
                journey_id=str(seeded["journey_id"]),
                provider_key="city-provider",
                provenance="LIVE_PROVIDER",
                event_type="CLOSURE",
                severity="HIGH",
                status="DETECTED",
                # The trusted shock targets the active-plan Activity row, not
                # the candidate-plan row. R30 relevance must follow the shared
                # physical Place rather than requiring identical Activity UUIDs.
                affected_activity_id=active_activity_id,
                occurred_at=now,
                detected_at=now,
                payload_json=json.dumps(
                    {
                        "semantic": {
                            "assertion_status": "OBSERVED",
                            "place_id": place_id,
                        }
                    },
                    sort_keys=True,
                ),
                created_at=now,
            )
        )
        session.commit()

        class _Selectable:
            def model_dump(self, *, mode="json"):
                return {"selectable": True}

        members = [
            {
                "member_id": str(seeded["owner_member_id"]),
                "role": "OWNER",
                "capabilities": ["EDIT_PLAN"],
                "journey_scoped_explicit_preferences": [{"key": "garden"}],
                "member_state": "MEMBER_IN_FORCE",
            },
            {
                "member_id": str(seeded["admin_member_id"]),
                "role": "ADMIN",
                "capabilities": ["EDIT_PLAN"],
                "journey_scoped_explicit_preferences": [{"key": "museum"}],
                "member_state": "MEMBER_IN_FORCE",
            },
        ]

        def projection(_session, _journey, *, candidate_windows=None):
            if candidate_windows is None:
                return {"member_count": 2, "members": members}
            return {
                "member_count": 2,
                "members": members,
                "candidate_fit_matrix": [],
                "mediation": {
                    "classification": "COMPROMISE_AVAILABLE",
                    "candidate_ids": [selected_plan_id],
                    "selected_candidate_id": selected_plan_id,
                },
            }

        monkeypatch.setattr(main_module, "plan_schema", lambda *_args, **_kwargs: _Selectable())
        monkeypatch.setattr(
            main_module, "active_journey_members_with_capabilities", projection
        )
        monkeypatch.setattr(
            main_module,
            "collective_proposal_receipt",
            lambda _session, _journey, _proposals: {
                "proposal_collective_decisions": {
                    str(item["proposal_id"]): item for item in options
                }
            },
        )
        monkeypatch.setattr(
            collective_mediation,
            "collective_decision_epoch",
            lambda **_kwargs: "semantic-stable",
        )

        gate = main_module.collective_mutation_gate(
            session,
            journey,
            selected_plan,
            hard_feasible_plan_ids={selected_plan_id},
        )
        assert gate["allowed"] is False
        assert gate["code"] == "COLLECTIVE_CONSENT_WORLD_EPOCH_STALE"
        assert gate["classification"] == "RENEWED_COLLECTIVE_CONSENT_STALE"
        assert gate["resolved_material_world_epoch"] == baseline_epoch
        assert gate["current_material_world_epoch"] != baseline_epoch


def test_r30_unrelated_provider_observation_does_not_change_world_epoch() -> None:
    seeded = _seed_r29_disagreement_http_fixture()
    now = _now()
    selected_plan_id = str(seeded["options"][0]["plan_id"])

    with SessionLocal() as session:
        journey = session.get(Journey, str(seeded["journey_id"]))
        selected_plan = session.get(PlanVersion, selected_plan_id)
        before = main_module.collective_material_world_basis(
            session,
            journey,
            selected_plan,
            fit_subject_place_ids=[],
        )
        before_epoch = collective_mediation.collective_material_world_epoch(before)

        session.add(
            ProviderObservation(
                id=str(uuid4()),
                journey_id=str(seeded["journey_id"]),
                provider_key="unrelated-provider",
                observation_type="MOBILITY",
                state="CAPTURED",
                incident_fingerprint="unrelated-incident",
                provenance="LIVE_PROVIDER",
                captured_at=now,
                expires_at=None,
                payload_json=json.dumps(
                    {
                        "event_id": "not-a-selected-plan-event",
                        "mobility_snapshot": {"snapshot_id": "unrelated-snapshot"},
                    },
                    sort_keys=True,
                ),
                created_at=now,
            )
        )
        session.commit()

        after = main_module.collective_material_world_basis(
            session,
            journey,
            selected_plan,
            fit_subject_place_ids=[],
        )
        after_epoch = collective_mediation.collective_material_world_epoch(after)
        assert after_epoch == before_epoch
