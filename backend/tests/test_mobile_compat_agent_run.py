from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.core.audit import record_audit
from app.core.config import settings
from app.agent.gateway import AgentToolGateway
from app.agent.mission import create_mission
from app.agent.orchestrator import HermesJourneyAgent
from app.db.models import AgentRun, AgentRunStep, Journey, JourneyMember
from app.db.session import SessionLocal


def _traveler(client: TestClient, label: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/travelers",
        json={"display_name": label, "timezone": "Asia/Shanghai", "locale": "zh-CN"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_mobile_compat_run_uses_signed_member_binding_and_safe_projection(monkeypatch):
    previous = {
        "secret": settings.traveler_auth_secret,
        "ai_enabled": settings.ai_enabled,
        "hermes_api_url": settings.hermes_api_url,
        "hermes_api_key": settings.hermes_api_key,
        "hermes_model": settings.hermes_model,
    }
    object.__setattr__(settings, "traveler_auth_secret", "mobile-compat-test-secret-0123456789abcdef")
    object.__setattr__(settings, "ai_enabled", True)
    object.__setattr__(settings, "hermes_api_url", "http://127.0.0.1:7863/v1/chat/completions")
    object.__setattr__(settings, "hermes_api_key", "test-key-not-used-by-fixture")
    object.__setattr__(settings, "hermes_model", "cn:glm-5.3-flash")
    calls: list[dict] = []
    monkeypatch.setattr(main_module, "native_hermes_status", lambda: {"ready": False})

    class _RecordedRun:
        runtime_identity = "HERMES_COMPAT_ENDPOINT"

        def run(self, session, *, journey, mission, **kwargs):
            calls.append(kwargs)
            run_id = kwargs["run_id"]
            binding = kwargs["signed_member_binding"]
            now = datetime.now(timezone.utc).isoformat()
            run = AgentRun(
                id=run_id,
                mission_id=mission.id,
                journey_id=journey.id,
                provider_key="hermes",
                model_key="cn:glm-5.3-flash",
                status="RUNNING",
                created_at=now,
                started_at=now,
            )
            session.add(run)
            record_audit(
                session,
                action="agent.mobile_compat.run_bound",
                entity_type="AgentRun",
                entity_id=run.id,
                journey_id=journey.id,
                actor_type="TRAVELER",
                actor_id=binding["traveler_id"],
                after={
                    "run_id": run.id,
                    "mission_id": mission.id,
                    "traveler_id": binding["traveler_id"],
                    "member_id": binding["member_id"],
                    "request_id": binding["request_id"],
                    "provider_consent": True,
                    "runtime_identity": self.runtime_identity,
                },
            )
            session.commit()
            session.add(
                AgentRunStep(
                    id=str(uuid4()),
                    run_id=run.id,
                    sequence_no=1,
                    tool_name="inspect_journey",
                    arguments_json=json.dumps({"private_argument": "hidden-args"}),
                    result_json=json.dumps({"private_fact": "hidden-result"}),
                    decision="READ",
                    status="COMPLETED",
                    created_at=now,
                    completed_at=now,
                )
            )
            run.status = "COMPLETED"
            run.completed_at = now
            mission.status = "COMPLETED"
            mission.completed_at = now
            session.commit()
            return {"run_id": run.id, "status": run.status}

        def close(self):
            return None

    def _configured_runtime(**kwargs):
        assert kwargs["force_compat"] is True
        assert kwargs["allow_budget_retry"] is False
        assert kwargs["tool_allowlist"] == frozenset(
            {"inspect_journey", "inspect_twin", "list_replans"}
        )
        return _RecordedRun()

    monkeypatch.setattr(main_module, "configured_journey_agent", _configured_runtime)
    try:
        with TestClient(main_module.app) as client:
            owner = _traveler(client, f"Compat owner {uuid4().hex[:6]}")
            collaborator = _traveler(client, f"Compat collaborator {uuid4().hex[:6]}")
            outsider = _traveler(client, f"Compat outsider {uuid4().hex[:6]}")
            journey_response = client.post(
                "/api/v1/journeys",
                json={
                    "traveler_id": owner["id"],
                    "title": "Mobile compatibility Agent run",
                    "city_code": f"CN-MCA-{uuid4().hex[:8].upper()}",
                    "timezone": "Asia/Shanghai",
                    "start_at": "2026-10-18T10:00:00+08:00",
                    "end_at": "2026-10-19T18:00:00+08:00",
                    "budget": {"amount_minor": 10000, "currency": "CNY"},
                },
            )
            assert journey_response.status_code == 201, journey_response.text
            journey_id = journey_response.json()["id"]
            route = f"/api/v1/journeys/{journey_id}/agent/mobile-compat-runs"
            draft_response = client.post(
                route,
                headers={"Authorization": f"Bearer {owner['access_token']}"},
                json={"request_id": str(uuid4()), "provider_consent": True},
            )
            assert draft_response.status_code == 409

            with SessionLocal() as session:
                journey = session.get(Journey, journey_id)
                assert journey is not None
                owner_member = session.scalar(
                    select(JourneyMember).where(
                        JourneyMember.journey_id == journey_id,
                        JourneyMember.traveler_id == owner["id"],
                    )
                )
                assert owner_member is not None
                session.add(
                    JourneyMember(
                        id=str(uuid4()),
                        journey_id=journey_id,
                        traveler_id=collaborator["id"],
                        role="COLLABORATOR",
                        invited_by=owner["id"],
                        expires_at=None,
                        joined_at="2026-10-16T00:00:00+00:00",
                        removed_at=None,
                        preferences_json="{}",
                        created_at="2026-10-16T00:00:00+00:00",
                        updated_at="2026-10-16T00:00:00+00:00",
                    )
                )
                session.commit()

            with SessionLocal() as session:
                journey = session.get(Journey, journey_id)
                assert journey is not None
                journey.status = "ACTIVE"
                session.commit()

            blocked_dispatches: list[str] = []
            monkeypatch.setattr(
                AgentToolGateway,
                "dispatch",
                lambda _self, tool_name, _payload: blocked_dispatches.append(tool_name),
            )
            blocked_run_id = str(uuid4())
            with SessionLocal() as session:
                journey = session.get(Journey, journey_id)
                assert journey is not None
                mission = create_mission(
                    session,
                    journey,
                    command="Check this journey",
                    requested_autonomy="EXECUTE_WITHIN_BOUNDS",
                    trigger_event_id=None,
                    use_model_draft=False,
                )
                session.commit()
                runtime = HermesJourneyAgent(
                    client=object(),
                    model_chain=(settings.hermes_model,),
                    allow_budget_retry=False,
                    tool_allowlist=frozenset(
                        {"inspect_journey", "inspect_twin", "list_replans"}
                    ),
                )
                runtime._complete = lambda _messages: {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "unapproved-search",
                            "type": "function",
                            "function": {
                                "name": "search_city_services",
                                "arguments": "not-json",
                            },
                        }
                    ],
                }
                runtime.run(
                    session,
                    journey=journey,
                    mission=mission,
                    max_steps=1,
                    run_id=blocked_run_id,
                )
                blocked_step = session.scalar(
                    select(AgentRunStep).where(
                        AgentRunStep.run_id == blocked_run_id
                    )
                )
                assert blocked_step is not None
                assert blocked_step.tool_name == "search_city_services"
                assert blocked_step.status == "TOOL_ERROR"
                assert blocked_step.decision == "REJECT_TOOL"
                assert blocked_step.arguments_json == "{}"
                assert blocked_dispatches == []

            request_id = str(uuid4())
            owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
            collaborator_headers = {"Authorization": f"Bearer {collaborator['access_token']}"}
            outsider_headers = {"Authorization": f"Bearer {outsider['access_token']}"}
            payload = {"request_id": request_id, "provider_consent": True}

            assert client.post(route, json=payload).status_code == 401
            assert client.post(route, headers=outsider_headers, json=payload).status_code == 403
            response = client.post(route, headers=owner_headers, json=payload)
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["runtime_identity"] == "HERMES_COMPAT_ENDPOINT"
            assert data["verification"] == "WB2API_TOOL_CALL_RECORDED"
            assert data["tool_steps"] == [
                {
                    "sequence_no": 1,
                    "tool_name": "inspect_journey",
                    "status": "COMPLETED",
                    "created_at": data["tool_steps"][0]["created_at"],
                    "completed_at": data["tool_steps"][0]["completed_at"],
                }
            ]
            assert "private_argument" not in response.text
            assert "hidden-result" not in response.text
            assert response.headers["cache-control"] == "private, no-store, max-age=0"
            assert len(calls) == 1
            assert calls[0]["max_steps"] == 1
            assert calls[0]["signed_member_binding"]["member_id"]

            duplicate = client.post(route, headers=owner_headers, json=payload)
            assert duplicate.status_code == 200, duplicate.text
            assert duplicate.json()["run_id"] == data["run_id"]
            assert len(calls) == 1

            latest_path = f"{route}/latest"
            owner_latest = client.get(latest_path, headers=owner_headers)
            assert owner_latest.status_code == 200, owner_latest.text
            assert owner_latest.json()["run"]["run_id"] == data["run_id"]
            collaborator_latest = client.get(latest_path, headers=collaborator_headers)
            assert collaborator_latest.status_code == 200, collaborator_latest.text
            assert collaborator_latest.json()["run"] is None

            run_path = f"{route}/{request_id}"
            assert client.get(run_path, headers=collaborator_headers).status_code == 404
            assert client.get(run_path, headers=outsider_headers).status_code == 403
    finally:
        for key, value in previous.items():
            field = "traveler_auth_secret" if key == "secret" else key
            object.__setattr__(settings, field, value)
