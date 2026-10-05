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
    AuditLog,
    Event,
    Journey,
    JourneyMember,
    JourneyMission,
    PlanVersion,
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

