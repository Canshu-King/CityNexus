"""Signed HTTP recovery of persisted failed classroom attempts; no external calls."""
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_issue47_private_reads import stack  # noqa: F401
from test_issue47_simulation import sim  # noqa: F401
from test_issue49_guardian_outcome import _add_agent, _add_guardian, _other_event, _start_scene

from app.agent import guardian
from app.agent.mission import create_mission
from app.agent.runtime import AgentRuntimeUnavailable
from app.db.models import AgentRun, GuardianRun, Journey
from app.simulation.models import SimulationCommand, SimulationRun


def _standing(factory, journey_id):
    db = factory()
    session = next(db)
    mission = create_mission(session, session.get(Journey, journey_id),
        command="TEST_FIXTURE 闭馆后先给替代方案，等待我确认",
        requested_autonomy="PROPOSE_ONLY", trigger_event_id=None,
        is_standing=True, use_model_draft=False)
    mission.status = "ACTIVE"
    session.commit()
    db.close()


def test_503_attempt_settles_without_automatic_second_model_and_can_be_retried(sim, monkeypatch, record_property):
    client, ids, factory, headers, path, run = _start_scene(sim)
    _standing(factory, ids["journey"])
    calls = []

    class FailingModel:
        def run(self, session, *, journey, mission, max_steps):
            calls.append(mission.id)
            stamp = datetime.now(timezone.utc).isoformat()
            session.add(AgentRun(id=str(uuid4()), mission_id=mission.id, journey_id=journey.id,
                provider_key="TEST_DOUBLE", model_key="NOT_LIVE", status="FAILED_EXTERNAL",
                created_at=stamp, started_at=stamp, completed_at=stamp,
                failure_reason="TEST_FIXTURE HTTP 503"))
            session.commit()
            raise AgentRuntimeUnavailable("TEST_FIXTURE HTTP 503")
        def close(self):
            pass

    class MustNotAutomaticallyCall:
        def run(self, *args, **kwargs):
            pytest.fail("An explicit classroom retry may not silently call another model")

    monkeypatch.setattr(guardian, "configured_journey_agent_candidates",
                        lambda: [FailingModel(), MustNotAutomaticallyCall()])
    body = {"expected_sequence": run["sequence"], "model_consent": True}
    response = client.post(path + "/guardian", headers={**headers, "Idempotency-Key": "failed-once"}, json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "PAUSED_MODEL_UNAVAILABLE"
    assert "guardian_lease_expires_at" not in result["state"]
    assert len(calls) == 1
    replay = client.post(path + "/guardian", headers={**headers, "Idempotency-Key": "failed-once"}, json=body)
    assert replay.json() == result
    assert len(calls) == 1
    retry = client.post(path + "/guardian", headers={**headers, "Idempotency-Key": "explicit-retry"},
        json={"expected_sequence": result["sequence"], "model_consent": True})
    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "PAUSED_MODEL_UNAVAILABLE"
    assert len(calls) == 2
    read = client.get(path + "/progress", headers=headers)
    assert read.status_code == 200
    assert read.json()["guardian_outcome"]["code"] == "EXTERNAL_FAILED"
    assert len(calls) == 2
    record_property("evidence_kind", "ISOLATED_HTTP_WITH_DECLARED_MODEL_DOUBLE")
    record_property("run_id", run["run_id"])
    record_property("event_id", run["state"]["pending_event_id"])


@pytest.mark.parametrize("failure", ["current", "old_attempt", "other_event", "running"])
def test_recover_uses_only_this_attempts_terminal_failure_and_replays_idempotently(sim, failure):
    client, ids, factory, headers, path, run = _start_scene(sim)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(seconds=3)).isoformat()
    db = factory()
    session = next(db)
    stored = session.get(SimulationRun, run["run_id"])
    stored.status = "GUARDIAN_RUNNING"
    state = json.loads(stored.state_json)
    state["guardian_attempt_started_at"] = start
    state["guardian_lease_expires_at"] = (now + timedelta(minutes=29)).isoformat()
    stored.state_json = json.dumps(state)
    event_id = state["pending_event_id"]
    if failure == "other_event":
        other = _other_event(ids["journey"])
        session.add(other)
        event_id = other.id
    agent = _add_agent(session, session.get(Journey, ids["journey"]), event_id,
        status="RUNNING" if failure == "running" else "FAILED_EXTERNAL",
        created_at=(now - timedelta(minutes=1) if failure == "old_attempt" else now).isoformat())
    envelope = _add_guardian(session, ids["journey"], state["pending_event_id"],
        created_at=now.isoformat(), status="RUNNING", action_status="PLANNING", agent_run_id=agent.id)
    envelope.completed_at = None
    envelope_id = envelope.id
    session.add(SimulationCommand(id=str(uuid4()), journey_id=ids["journey"], run_id=stored.id,
        actor_id=ids["owner"], idempotency_key="original-pending", request_sha256="fixture",
        result_json=json.dumps({"status": "GUARDIAN_RUNNING", "sequence": run["sequence"]}), created_at=start))
    session.commit()
    db.close()
    body = {"expected_sequence": run["sequence"]}
    assert client.post(path + "/recover", headers={"Idempotency-Key": "anonymous"}, json=body).status_code == 401
    progress = client.get(path + "/progress", headers=headers).json()
    assert progress["recovery"]["available"] is (failure == "current")
    assert client.get(path, headers=headers).json()["status"] == "GUARDIAN_RUNNING"
    response = client.post(path + "/recover", headers={**headers, "Idempotency-Key": "recover-failed"}, json=body)
    if failure != "current":
        assert response.status_code == 409, response.text
        assert client.get(path, headers=headers).json()["status"] == "GUARDIAN_RUNNING"
        return
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "PAUSED_MODEL_UNAVAILABLE"
    assert result["history"][-1]["error_code"] == "MODEL_REQUEST_FAILED"
    assert "guardian_lease_expires_at" not in result["state"]
    replay = client.post(path + "/recover", headers={**headers, "Idempotency-Key": "recover-failed"}, json=body)
    assert replay.json() == result
    assert client.get(path, headers=headers).json()["sequence"] == result["sequence"]
    db = factory()
    session = next(db)
    receipt = session.scalar(select(SimulationCommand).where(SimulationCommand.idempotency_key == "original-pending"))
    assert json.loads(receipt.result_json)["status"] == "PAUSED_MODEL_UNAVAILABLE"
    envelope = session.get(GuardianRun, envelope_id)
    assert envelope.status == "INTERRUPTED"
    assert envelope.action_status == "RETRYABLE_FAILURE"
    assert envelope.cooldown_until is None
    db.close()
