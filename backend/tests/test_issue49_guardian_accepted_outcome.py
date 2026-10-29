from __future__ import annotations

import json
from uuid import uuid4

import pytest
from test_issue47_private_reads import stack  # noqa: F401 -- dependency of sim
from test_issue47_simulation import sim  # noqa: F401 -- shared fixture
from test_issue49_guardian_outcome import (
    _add_agent,
    _add_guardian,
    _add_proposal,
    _other_event,
    _progress,
    _set_model_config,
    _start_scene,
)

from app.db.models import AgentRunStep, Event, Journey
from app.simulation.models import SimulationRun


def _accepted_attempt(
    session,
    journey,
    event_id,
    plan_id,
    *,
    agent_status="PARTIAL",
    agent_created_at="2026-10-26T10:00:00+00:00",
    guardian_created_at="2026-10-26T10:00:01+00:00",
    guardian_agent_id=None,
):
    event = session.get(Event, event_id)
    assert event is not None
    event.status = "RESOLVED"

    proposal = _add_proposal(
        session,
        journey.id,
        plan_id,
        event_id,
        created_at="2026-10-26T10:00:00+00:00",
    )
    proposal.status = "ACCEPTED"
    agent = _add_agent(
        session,
        journey,
        event_id,
        status=agent_status,
        created_at=agent_created_at,
    )
    proposal.source_agent_run_id = agent.id
    session.flush()
    guardian = _add_guardian(
        session,
        journey.id,
        event_id,
        created_at=guardian_created_at,
        status="PARTIAL",
        action_status="PROPOSAL_PRESENTED",
        agent_run_id=guardian_agent_id or agent.id,
        proposal_id=proposal.id,
    )
    return proposal, agent, guardian


@pytest.mark.parametrize("clear_pending_event", [False, True])
def test_same_run_accepted_proposal_wins_over_partial_and_projects_safe_steps(
    sim, monkeypatch, clear_pending_event
):
    _set_model_config(monkeypatch, configured=True)
    client, ids, factory, headers, path, run = _start_scene(sim)
    event_id = run["state"]["pending_event_id"]
    session_factory = factory()
    session = next(session_factory)
    journey = session.get(Journey, ids["journey"])
    proposal, agent, _guardian = _accepted_attempt(
        session, journey, event_id, ids["plan"]
    )
    session.add(
        AgentRunStep(
            id=str(uuid4()),
            run_id=agent.id,
            sequence_no=1,
            tool_name="request_replan",
            arguments_json=json.dumps({"prompt": "PRIVATE_PROMPT", "api_key": "PRIVATE_KEY"}),
            result_json=json.dumps({"private_result": "PRIVATE_RESULT"}),
            status="COMPLETED",
            created_at="2026-10-26T10:00:03+00:00",
            completed_at="2026-10-26T10:00:04.250+00:00",
        )
    )
    if clear_pending_event:
        simulation_run = session.get(SimulationRun, run["run_id"])
        state = json.loads(simulation_run.state_json)
        state["pending_event_id"] = None
        simulation_run.state_json = json.dumps(state)
        simulation_run.status = "ACTIVE"
    session.commit()
    proposal_id, agent_id = proposal.id, agent.id
    session_factory.close()

    body = _progress(client, headers, path)

    assert body["guardian_outcome"] == {"code": "PROPOSAL_ACCEPTED"}
    assert body["readiness"]["pending_event_id"] == (
        None if clear_pending_event else event_id
    )
    assert next(event for event in body["events"] if event["id"] == event_id)[
        "status"
    ] == "RESOLVED"
    accepted_proposal_view = next(
        proposal_view
        for proposal_view in body["proposals"]
        if proposal_view["id"] == proposal_id
    )
    assert accepted_proposal_view["status"] == "ACCEPTED"

    step = body["steps"][0]
    assert step["simulation_run_id"] == run["run_id"]
    assert step["event_id"] == event_id
    assert step["agent_run_id"] == agent_id
    assert step["stage"] == "TOOL_CALL"
    assert step["tool_name"] == "request_replan"
    assert step["status"] == "COMPLETED"
    assert step["duration_ms"] == 1250
    assert step["failure_classification"] is None
    assert "arguments_json" not in step and "result_json" not in step
    assert all(
        secret not in json.dumps(body)
        for secret in ("PRIVATE_PROMPT", "PRIVATE_KEY", "PRIVATE_RESULT")
    )


def test_accepted_proposal_from_event_outside_this_run_history_is_ignored(
    sim, monkeypatch
):
    _set_model_config(monkeypatch, configured=True)
    client, ids, factory, headers, path, _run = _start_scene(sim)
    session_factory = factory()
    session = next(session_factory)
    journey = session.get(Journey, ids["journey"])
    foreign_event = _other_event(journey.id)
    foreign_event.payload_json = json.dumps({"simulation_run_id": "another-run"})
    session.add(foreign_event)
    session.flush()
    foreign_event.status = "RESOLVED"
    proposal = _add_proposal(
        session,
        journey.id,
        ids["plan"],
        foreign_event.id,
        created_at="2026-10-26T10:00:00+00:00",
    )
    proposal.status = "ACCEPTED"
    agent = _add_agent(
        session,
        journey,
        foreign_event.id,
        status="PARTIAL",
        created_at="2026-10-26T10:00:01+00:00",
    )
    proposal.source_agent_run_id = agent.id
    session.flush()
    _add_guardian(
        session,
        journey.id,
        foreign_event.id,
        created_at="2026-10-26T10:00:02+00:00",
        status="PARTIAL",
        action_status="PROPOSAL_PRESENTED",
        agent_run_id=agent.id,
        proposal_id=proposal.id,
    )
    session.commit()
    session_factory.close()

    body = _progress(client, headers, path)

    assert body["guardian_outcome"] == {"code": "UNKNOWN"}
    assert body["guardian_runs"] == []
    assert body["proposals"] == []


def test_old_accepted_proposal_reference_does_not_override_latest_guardian(
    sim, monkeypatch
):
    _set_model_config(monkeypatch, configured=True)
    client, ids, factory, headers, path, run = _start_scene(sim)
    event_id = run["state"]["pending_event_id"]
    session_factory = factory()
    session = next(session_factory)
    journey = session.get(Journey, ids["journey"])
    proposal, agent, _old_guardian = _accepted_attempt(
        session, journey, event_id, ids["plan"]
    )
    _add_guardian(
        session,
        journey.id,
        event_id,
        created_at="2026-10-26T10:00:04+00:00",
        status="PARTIAL",
        action_status="UNRESOLVED",
        agent_run_id=agent.id,
        proposal_id=None,
    )
    session.commit()
    proposal_id = proposal.id
    session_factory.close()

    body = _progress(client, headers, path)

    assert body["guardian_outcome"] == {"code": "AGENT_UNRESOLVED"}
    assert body["guardian_runs"][-1]["proposal_id"] is None
    assert any(
        item["id"] == proposal_id and item["status"] == "ACCEPTED"
        for item in body["proposals"]
    )


def test_accepted_proposal_source_agent_must_match_current_guardian_agent(
    sim, monkeypatch
):
    _set_model_config(monkeypatch, configured=True)
    client, ids, factory, headers, path, run = _start_scene(sim)
    event_id = run["state"]["pending_event_id"]
    session_factory = factory()
    session = next(session_factory)
    journey = session.get(Journey, ids["journey"])
    foreign_event = _other_event(journey.id)
    foreign_event.payload_json = json.dumps({"simulation_run_id": "another-run"})
    session.add(foreign_event)
    session.flush()
    proposal, current_agent, guardian = _accepted_attempt(
        session,
        journey,
        event_id,
        ids["plan"],
        agent_created_at="2026-10-26T10:00:03+00:00",
        guardian_created_at="2026-10-26T10:00:02+00:00",
    )
    foreign_agent = _add_agent(
        session,
        journey,
        foreign_event.id,
        status="PARTIAL",
        created_at="2026-10-26T10:00:01+00:00",
    )
    session.flush()
    proposal.source_agent_run_id = foreign_agent.id
    session.commit()
    current_agent_id, foreign_agent_id = current_agent.id, foreign_agent.id
    guardian_agent_id, source_agent_id = guardian.agent_run_id, proposal.source_agent_run_id
    session_factory.close()

    body = _progress(client, headers, path)

    assert current_agent_id != foreign_agent_id
    assert guardian_agent_id == current_agent_id
    assert source_agent_id == foreign_agent_id
    assert body["guardian_outcome"] == {"code": "AGENT_UNRESOLVED"}


def test_accepted_partial_run_is_not_overruled_by_an_earlier_failed_step(
    sim, monkeypatch
):
    _set_model_config(monkeypatch, configured=True)
    client, ids, factory, headers, path, run = _start_scene(sim)
    event_id = run["state"]["pending_event_id"]
    session_factory = factory()
    session = next(session_factory)
    journey = session.get(Journey, ids["journey"])
    _proposal, agent, _guardian = _accepted_attempt(
        session, journey, event_id, ids["plan"]
    )
    session.add_all(
        [
            AgentRunStep(
                id=str(uuid4()),
                run_id=agent.id,
                sequence_no=1,
                tool_name="external_model_call",
                arguments_json=json.dumps({"api_key": "PRIVATE_KEY"}),
                result_json=json.dumps({"prompt": "PRIVATE_PROMPT"}),
                status="FAILED_EXTERNAL",
                created_at="2026-10-26T10:00:02+00:00",
                completed_at="2026-10-26T10:00:03+00:00",
            ),
            AgentRunStep(
                id=str(uuid4()),
                run_id=agent.id,
                sequence_no=2,
                tool_name="request_replan",
                arguments_json=json.dumps({"places": ["server-place-a", "server-place-b"]}),
                result_json=json.dumps({"proposal_created": True}),
                status="COMPLETED",
                created_at="2026-10-26T10:00:04+00:00",
                completed_at="2026-10-26T10:00:05+00:00",
            ),
        ]
    )
    session.commit()
    session_factory.close()

    body = _progress(client, headers, path)

    assert body["guardian_outcome"] == {"code": "PROPOSAL_ACCEPTED"}
    assert body["agent_runs"][0]["status"] == "PARTIAL"
    assert [step["status"] for step in body["steps"]] == [
        "FAILED_EXTERNAL",
        "COMPLETED",
    ]
    assert body["steps"][0]["failure_classification"] == "MODEL_REQUEST_FAILED"
    assert "PRIVATE_KEY" not in json.dumps(body)
    assert "PRIVATE_PROMPT" not in json.dumps(body)


def test_external_step_failure_without_accepted_native_result_remains_failure(
    sim, monkeypatch
):
    _set_model_config(monkeypatch, configured=True)
    client, ids, factory, headers, path, run = _start_scene(sim)
    event_id = run["state"]["pending_event_id"]
    session_factory = factory()
    session = next(session_factory)
    journey = session.get(Journey, ids["journey"])
    agent = _add_agent(
        session,
        journey,
        event_id,
        status="PARTIAL",
        created_at="2026-10-26T10:00:00+00:00",
    )
    session.flush()
    _add_guardian(
        session,
        journey.id,
        event_id,
        created_at="2026-10-26T10:00:01+00:00",
        status="PARTIAL",
        action_status="RETRYABLE_FAILURE",
        agent_run_id=agent.id,
    )
    session.add(
        AgentRunStep(
            id=str(uuid4()),
            run_id=agent.id,
            sequence_no=1,
            tool_name="external_model_call",
            arguments_json=json.dumps({"api_key": "PRIVATE_KEY"}),
            result_json=json.dumps({"prompt": "PRIVATE_PROMPT"}),
            status="FAILED_EXTERNAL",
            created_at="2026-10-26T10:00:02+00:00",
            completed_at="2026-10-26T10:00:03+00:00",
        )
    )
    session.commit()
    session_factory.close()

    body = _progress(client, headers, path)

    assert body["guardian_outcome"] == {
        "code": "EXTERNAL_FAILED",
        "error_code": "MODEL_REQUEST_FAILED",
    }
    assert body["agent_runs"][0]["status"] == "PARTIAL"
    assert body["steps"][0]["failure_classification"] == "MODEL_REQUEST_FAILED"
    assert "PRIVATE_KEY" not in json.dumps(body)
    assert "PRIVATE_PROMPT" not in json.dumps(body)


def test_real_external_failure_is_not_hidden_by_an_accepted_proposal(sim, monkeypatch):
    _set_model_config(monkeypatch, configured=True)
    client, ids, factory, headers, path, run = _start_scene(sim)
    event_id = run["state"]["pending_event_id"]
    session_factory = factory()
    session = next(session_factory)
    journey = session.get(Journey, ids["journey"])
    _proposal, agent, _guardian = _accepted_attempt(
        session,
        journey,
        event_id,
        ids["plan"],
        agent_status="FAILED_EXTERNAL",
    )
    session.add(
        AgentRunStep(
            id=str(uuid4()),
            run_id=agent.id,
            sequence_no=1,
            tool_name="external_model_call",
            arguments_json=json.dumps({"api_key": "PRIVATE_KEY"}),
            result_json=json.dumps({"prompt": "PRIVATE_PROMPT"}),
            status="FAILED_EXTERNAL",
            created_at="2026-10-26T10:00:03+00:00",
            completed_at="2026-10-26T10:00:04+00:00",
        )
    )
    session.commit()
    session_factory.close()

    body = _progress(client, headers, path)

    assert body["guardian_outcome"] == {
        "code": "EXTERNAL_FAILED",
        "error_code": "MODEL_REQUEST_FAILED",
    }
    assert body["steps"][0]["failure_classification"] == "MODEL_REQUEST_FAILED"
    assert "PRIVATE_KEY" not in json.dumps(body)
    assert "PRIVATE_PROMPT" not in json.dumps(body)


def test_presented_proposal_remains_proposal_ready(sim, monkeypatch):
    _set_model_config(monkeypatch, configured=False)
    client, ids, factory, headers, path, run = _start_scene(sim)
    event_id = run["state"]["pending_event_id"]
    session_factory = factory()
    session = next(session_factory)
    journey = session.get(Journey, ids["journey"])
    proposal = _add_proposal(
        session,
        journey.id,
        ids["plan"],
        event_id,
        created_at="2026-10-26T10:00:00+00:00",
    )
    _add_guardian(
        session,
        journey.id,
        event_id,
        created_at="2026-10-26T10:00:01+00:00",
        action_status="PROPOSAL_PRESENTED",
        proposal_id=proposal.id,
    )
    session.commit()
    session_factory.close()

    body = _progress(client, headers, path)

    assert body["guardian_outcome"] == {"code": "PROPOSAL_READY"}
