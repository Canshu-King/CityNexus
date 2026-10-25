"""Regression for #47 comment 6401253491: old proposals must not lock a new scene."""

from dataclasses import replace
import json
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_issue47_private_reads import stack  # noqa: F401
from test_issue47_simulation import sim  # noqa: F401
from test_issue49_guardian_outcome import _add_proposal, _other_event, _start_scene

from app.agent import guardian
from app.agent.mission import create_mission
from app.db.models import AgentRun, GuardianRun, Journey
from app.simulation import api


def test_disabled_ai_does_not_call_guardian_or_consume_sequence(sim, monkeypatch):
    client, _, factory, headers, path, run = _start_scene(sim)
    monkeypatch.setattr(api, "settings", replace(api.settings, ai_enabled=False))

    def must_not_call(*args, **kwargs):
        pytest.fail("Disabled AI must not start Guardian or a runtime")

    monkeypatch.setattr(guardian, "scan_guardian", must_not_call)
    response = client.post(
        path + "/guardian",
        headers={**headers, "Idempotency-Key": uuid4().hex},
        json={"expected_sequence": run["sequence"], "model_consent": True},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "SIMULATION_AI_DISABLED"
    after = client.get(path, headers=headers).json()
    assert after["sequence"] == run["sequence"]
    assert after["status"] == "PAUSED_FOR_GUARDIAN"
    readiness = client.get(path + "/progress", headers=headers).json()["readiness"]
    assert readiness["ai_enabled"] is False
    assert "AI_DISABLED" in readiness["missing"]
    db = factory()
    session = next(db)
    assert session.scalar(select(AgentRun.id)) is None
    db.close()


@pytest.mark.parametrize("binding", ["current", "other_event", "missing", "dismissed"])
def test_only_presented_current_scene_proposal_waits_for_acceptance(sim, monkeypatch, binding):
    client, ids, factory, headers, path, run = _start_scene(sim)
    db = factory()
    session = next(db)
    other = _other_event(ids["journey"])
    session.add(other)
    proposal = _add_proposal(
        session, ids["journey"], ids["plan"],
        other.id if binding == "other_event" else run["state"]["pending_event_id"],
        created_at="2026-10-26T10:00:01+00:00",
    )
    if binding == "dismissed":
        proposal.status = "DISMISSED"
    proposal_id = str(uuid4()) if binding == "missing" else proposal.id
    session.commit()
    db.close()

    def scan(session, journey, **kwargs):
        assert kwargs["trigger_event_id"] == run["state"]["pending_event_id"]
        return {"status": "PARTIAL", "action_status": "PROPOSAL_PRESENTED", "proposal_id": proposal_id}

    monkeypatch.setattr(guardian, "scan_guardian", scan)
    response = client.post(
        path + "/guardian", headers={**headers, "Idempotency-Key": uuid4().hex},
        json={"expected_sequence": run["sequence"], "model_consent": True},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == ("PAUSED_FOR_ACCEPTANCE" if binding == "current" else "PAUSED_MODEL_UNAVAILABLE")
    result = body["history"][-1]["guardian"]
    assert result["proposal_id"] == (proposal_id if binding == "current" else None)
    if binding != "current":
        assert result["error_code"] == "GUARDIAN_PROPOSAL_EVENT_MISMATCH"
    progress = client.get(path + "/progress", headers=headers).json()
    assert all(p["event_id"] == run["state"]["pending_event_id"] for p in progress["proposals"])


def test_actual_guardian_rejects_runtime_proposal_from_other_event(sim, monkeypatch):
    client, ids, factory, headers, path, run = _start_scene(sim)
    db = factory()
    session = next(db)
    journey = session.get(Journey, ids["journey"])
    standing = create_mission(
        session, journey, command="闭馆后先给我方案", requested_autonomy="PROPOSE_ONLY",
        trigger_event_id=None, is_standing=True, use_model_draft=False,
    )
    standing.status = "ACTIVE"
    other = _other_event(journey.id)
    session.add(other)
    proposal = _add_proposal(session, journey.id, ids["plan"], other.id,
                             created_at="2026-10-26T10:00:01+00:00")
    proposal_id = proposal.id
    session.commit()
    db.close()

    calls = []

    class RuntimeDouble:
        def run(self, session, *, journey, mission, max_steps):
            calls.append(mission.id)
            assert mission.trigger_event_id == run["state"]["pending_event_id"]
            agent = AgentRun(
                id=str(uuid4()), mission_id=mission.id, journey_id=journey.id,
                provider_key="TEST_DOUBLE", model_key="NOT_LIVE", status="PARTIAL",
                created_at="2026-10-26T10:00:02+00:00",
                started_at="2026-10-26T10:00:02+00:00",
            )
            session.add(agent)
            session.commit()
            return {"run_id": agent.id, "tool_steps": [{
                "tool_name": "request_replan", "result": {"proposal": {"id": proposal_id}},
            }]}

    monkeypatch.setattr(guardian, "configured_journey_agent_candidates", lambda: [RuntimeDouble()])
    response = client.post(
        path + "/guardian", headers={**headers, "Idempotency-Key": uuid4().hex},
        json={"expected_sequence": run["sequence"], "model_consent": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "PAUSED_MODEL_UNAVAILABLE"
    progress = client.get(path + "/progress", headers=headers).json()
    db = factory()
    session = next(db)
    recorded = session.scalar(select(GuardianRun).where(GuardianRun.journey_id == ids["journey"]))
    assert calls, recorded.evidence_json
    assert json.loads(recorded.evidence_json)["rejected_proposal"] == {
        "id": proposal_id, "reason_code": "GUARDIAN_PROPOSAL_EVENT_MISMATCH",
    }
    assert len(progress["agent_runs"]) == 1
    db.close()
    assert progress["guardian_runs"][0]["proposal_id"] is None
    assert progress["guardian_runs"][0]["action_status"] == "RETRYABLE_FAILURE"
    assert progress["proposals"] == []
