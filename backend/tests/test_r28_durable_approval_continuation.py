from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
from app.agent.runtime import _terminal_agent_status
from app.db.models import (
    ActionApproval,
    AgentPendingAction,
    AgentRun,
    AgentRunStep,
    Journey,
    JourneyMission,
    Traveler,
)
from app.db.session import SessionLocal


client = TestClient(main_module.app)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_pending_continuation() -> dict[str, str]:
    traveler_id = str(uuid4())
    journey_id = str(uuid4())
    mission_id = str(uuid4())
    run_id = str(uuid4())
    approval_id = str(uuid4())
    pending_id = str(uuid4())
    now = _now()
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="R28 traveler",
                email=None,
                locale="en-US",
                timezone="UTC",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            Journey(
                id=journey_id,
                traveler_id=traveler_id,
                title="R28 durable approval",
                city_code="TYO",
                timezone="UTC",
                start_at=now,
                end_at=(datetime.now(timezone.utc) + timedelta(hours=4)).isoformat(),
                budget_currency="JPY",
                budget_amount_minor=10000,
                planning_mode="balanced",
                status="ACTIVE",
                active_plan_version_id=None,
                current_activity_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            JourneyMission(
                id=mission_id,
                journey_id=journey_id,
                traveler_id=traveler_id,
                trigger_event_id=None,
                user_text="Resume the already selected action after I approve it.",
                requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                status="WAITING_FOR_APPROVAL",
                created_at=now,
                started_at=now,
            )
        )
        session.add(
            AgentRun(
                id=run_id,
                mission_id=mission_id,
                journey_id=journey_id,
                provider_key="hermes",
                model_key="test-model",
                status="WAITING_FOR_APPROVAL",
                outcome="Agent is waiting for the required human approval.",
                created_at=now,
                started_at=now,
                completed_at=None,
            )
        )
        session.add(
            ActionApproval(
                id=approval_id,
                traveler_id=traveler_id,
                journey_id=journey_id,
                action="ACCEPT_REPLAN",
                target_type="ReplanProposal",
                target_id=str(uuid4()),
                request_fingerprint="r28-test-fingerprint",
                status="PENDING",
                required_decision="REQUIRE_CONFIRMATION",
                created_at=now,
                expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
            )
        )
        session.add(
            AgentPendingAction(
                id=pending_id,
                approval_id=approval_id,
                run_id=run_id,
                mission_id=mission_id,
                journey_id=journey_id,
                originating_step_id=None,
                tool_name="accept_replan",
                arguments_json=(
                    '{"agent_id":"citynexus-agent","journey_id":"'
                    + journey_id
                    + '","mission_id":"'
                    + mission_id
                    + '","proposal_id":"'
                    + str(uuid4())
                    + '","request_id":"original-agent-request"}'
                ),
                status="PENDING",
                result_json="{}",
                error_json="{}",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return {
        "traveler_id": traveler_id,
        "journey_id": journey_id,
        "mission_id": mission_id,
        "run_id": run_id,
        "approval_id": approval_id,
        "pending_id": pending_id,
    }


def test_r28_terminal_status_is_durable_wait_not_completed() -> None:
    trace = [
        {
            "tool_name": "accept_replan",
            "result": {
                "executed": False,
                "decision": "REQUIRE_CONFIRMATION",
                "approval_id": str(uuid4()),
                "status": "PENDING",
            },
            "status": "COMPLETED",
        }
    ]
    run_status, mission_status = _terminal_agent_status(
        trace, has_final_text=True, clarification=False
    )
    assert run_status == "WAITING_FOR_APPROVAL"
    assert mission_status == "WAITING_FOR_APPROVAL"


def test_r28_approval_route_resumes_same_run_without_second_model_turn(monkeypatch) -> None:
    seeded = _seed_pending_continuation()
    calls: list[tuple[str, str]] = []

    def fake_dispatch(self, tool_name, request):
        calls.append((tool_name, request.request_id))
        assert str(request.approval_id) == seeded["approval_id"]
        assert request.request_id == f"agent-resume-{seeded['pending_id']}"
        approval = self.session.get(ActionApproval, seeded["approval_id"])
        assert approval is not None
        approval.status = "CONSUMED"
        approval.consumed_at = _now()
        self.session.commit()
        return {
            "tool": tool_name,
            "decision": "REQUIRE_CONFIRMATION",
            "executed": True,
            "approval_id": seeded["approval_id"],
            "status": "CONSUMED",
            "result": {"status": "ACCEPTED"},
        }

    monkeypatch.setattr("app.agent.gateway.AgentToolGateway.dispatch", fake_dispatch)

    approved = client.post(
        f"/api/v1/journeys/{seeded['journey_id']}/agent/approvals/"
        f"{seeded['approval_id']}/approve",
        json={"approval_method": "USER_CONFIRMATION"},
    )
    assert approved.status_code == 200, approved.text
    payload = approved.json()
    assert payload["status"] == "CONSUMED"
    assert payload["continuation"]["status"] == "RESUMED"
    assert payload["continuation"]["run_id"] == seeded["run_id"]
    assert len(calls) == 1

    with SessionLocal() as session:
        pending = session.get(AgentPendingAction, seeded["pending_id"])
        run = session.get(AgentRun, seeded["run_id"])
        mission = session.get(JourneyMission, seeded["mission_id"])
        approval = session.get(ActionApproval, seeded["approval_id"])
        assert pending is not None and pending.status == "RESUMED"
        assert run is not None and run.status == "COMPLETED" and run.completed_at
        assert mission is not None and mission.status == "COMPLETED" and mission.completed_at
        assert approval is not None and approval.status == "CONSUMED"
        steps = session.query(AgentRunStep).filter(AgentRunStep.run_id == seeded["run_id"]).all()
        assert len(steps) == 1
        assert steps[0].tool_name == "accept_replan"
        assert "agent-resume-" in steps[0].arguments_json

    replay = client.post(
        f"/api/v1/journeys/{seeded['journey_id']}/agent/approvals/"
        f"{seeded['approval_id']}/approve",
        json={"approval_method": "USER_CONFIRMATION"},
    )
    assert replay.status_code == 409
    assert len(calls) == 1, "approval replay must not cause a second mutation"
