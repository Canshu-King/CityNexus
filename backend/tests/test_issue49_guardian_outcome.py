"""Run-bound Guardian outcome projection regressions."""

from dataclasses import replace
from uuid import uuid4

import pytest
from test_issue47_private_reads import stack  # noqa: F401 -- shared fixture
from test_issue47_simulation import sim  # noqa: F401 -- shared fixture

from app.agent.mission import create_mission
from app.db.models import AgentRun, AgentRunStep, Event, GuardianRun, Journey, ReplanProposal
from app.simulation import api


def _start_scene(sim):
    client, ids, _, factory, headers, url, post = sim
    run = post(url, {"seed": 49}).json()
    path = url + "/" + run["run_id"]
    scene = post(
        path + "/scenes",
        {
            "expected_sequence": 0,
            "scene_id": "guardian-outcome-49",
            "event_type": "CLOSURE",
            "activity_id": ids["activities"][0],
        },
    )
    assert scene.status_code == 200, scene.text
    return client, ids, factory, headers, path, scene.json()


def _set_model_config(monkeypatch, *, configured):
    settings = api.settings
    monkeypatch.setattr(
        api,
        "settings",
        replace(
            settings,
            hermes_api_url="http://model.invalid" if configured else None,
            hermes_api_key="fixture-key" if configured else None,
            ai_api_key=None,
        ),
    )


def _other_event(journey_id):
    stamp = "2026-10-26T10:00:00+00:00"
    return Event(
        id=str(uuid4()),
        journey_id=journey_id,
        provider_key="TEST_FIXTURE",
        provenance="SIMULATED",
        event_type="WEATHER",
        severity="HIGH",
        status="DETECTED",
        occurred_at=stamp,
        detected_at=stamp,
        payload_json="{}",
        created_at=stamp,
    )


def _add_proposal(session, journey_id, plan_id, trigger_event_id, *, created_at):
    proposal = ReplanProposal(
        id=str(uuid4()),
        journey_id=journey_id,
        trigger_event_id=trigger_event_id,
        base_plan_version_id=plan_id,
        proposed_plan_version_id=plan_id,
        status="PRESENTED",
        hard_constraints_passed=True,
        locked_commitments_preserved=True,
        utility_score=1,
        score_breakdown_json="{}",
        diff_json="{}",
        explanation_json="{}",
        created_at=created_at,
    )
    session.add(proposal)
    return proposal


def _add_agent(session, journey, event_id, *, status, created_at):
    mission = create_mission(
        session,
        journey,
        command="TEST_FIXTURE guardian outcome",
        requested_autonomy="PROPOSE_ONLY",
        trigger_event_id=event_id,
        is_standing=False,
        use_model_draft=False,
    )
    agent = AgentRun(
        id=str(uuid4()),
        mission_id=mission.id,
        journey_id=journey.id,
        provider_key="TEST_FIXTURE",
        model_key="NOT_LIVE",
        status=status,
        created_at=created_at,
        started_at=created_at,
        completed_at=created_at if status != "RUNNING" else None,
    )
    session.add(agent)
    return agent


def _add_guardian(
    session,
    journey_id,
    event_id,
    *,
    created_at,
    status="COMPLETED",
    action_status="NO_ACTION",
    agent_run_id=None,
    proposal_id=None,
):
    guardian = GuardianRun(
        id=str(uuid4()),
        journey_id=journey_id,
        trigger_event_id=event_id,
        agent_run_id=agent_run_id,
        proposal_id=proposal_id,
        decision="TEST_FIXTURE",
        status=status,
        action_status=action_status,
        evidence_fingerprint=uuid4().hex,
        evidence_json="{}",
        reasoning_summary="fixture",
        created_at=created_at,
        completed_at=created_at,
    )
    session.add(guardian)
    return guardian


def _progress(client, headers, path):
    response = client.get(path + "/progress", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_other_trigger_event_cannot_supply_current_run_outcome(sim, monkeypatch):
    _set_model_config(monkeypatch, configured=True)
    client, ids, factory, headers, path, run = _start_scene(sim)
    session_factory = factory()
    session = next(session_factory)
    journey = session.get(Journey, ids["journey"])
    other = _other_event(journey.id)
    session.add(other)
    proposal = _add_proposal(
        session,
        journey.id,
        ids["plan"],
        other.id,
        created_at="2026-10-26T10:00:01+00:00",
    )
    _add_guardian(
        session,
        journey.id,
        other.id,
        created_at="2026-10-26T10:00:02+00:00",
        action_status="PROPOSAL_PRESENTED",
        proposal_id=proposal.id,
    )
    session.commit()
    session_factory.close()

    body = _progress(client, headers, path)
    assert body["readiness"]["pending_event_id"] == run["state"]["pending_event_id"]
    assert body["guardian_outcome"] == {"code": "UNKNOWN"}
    assert body["guardian_runs"] == []


def test_latest_pending_attempt_blocks_stale_proposal_and_preserves_partial(sim, monkeypatch):
    _set_model_config(monkeypatch, configured=False)
    client, ids, factory, headers, path, run = _start_scene(sim)
    event_id = run["state"]["pending_event_id"]
    session_factory = factory()
    session = next(session_factory)
    journey = session.get(Journey, ids["journey"])
    other = _other_event(journey.id)
    session.add(other)
    proposal = _add_proposal(
        session,
        journey.id,
        ids["plan"],
        event_id,
        created_at="2026-10-26T10:00:00+00:00",
    )
    stale_proposal = _add_proposal(
        session,
        journey.id,
        ids["plan"],
        other.id,
        created_at="2026-10-26T10:00:01+00:00",
    )
    agent = _add_agent(
        session,
        journey,
        event_id,
        status="PARTIAL",
        created_at="2026-10-26T10:00:03+00:00",
    )
    session.flush()
    _add_guardian(
        session,
        journey.id,
        event_id,
        created_at="2026-10-26T10:00:01+00:00",
        action_status="PROPOSAL_PRESENTED",
        proposal_id=proposal.id,
    )
    _add_guardian(
        session,
        journey.id,
        event_id,
        created_at="2026-10-26T10:00:04+00:00",
        status="PARTIAL",
        action_status="UNRESOLVED",
        agent_run_id=agent.id,
        proposal_id=stale_proposal.id,
    )
    session.commit()
    session_factory.close()

    body = _progress(client, headers, path)
    assert body["guardian_outcome"] == {"code": "AGENT_UNRESOLVED"}
    assert body["agent_runs"][0]["status"] == "PARTIAL"
    assert body["guardian_runs"][-1]["status"] == "PARTIAL"
    assert body["guardian_runs"][-1]["proposal_id"] is None


def test_absent_configuration_is_distinct_from_external_execution_failure(sim, monkeypatch):
    _set_model_config(monkeypatch, configured=False)
    client, ids, factory, headers, path, run = _start_scene(sim)
    body = _progress(client, headers, path)
    assert body["guardian_outcome"] == {"code": "MODEL_NOT_CONFIGURED"}

    event_id = run["state"]["pending_event_id"]
    session_factory = factory()
    session = next(session_factory)
    journey = session.get(Journey, ids["journey"])
    agent = _add_agent(
        session,
        journey,
        event_id,
        status="FAILED_EXTERNAL",
        created_at="2026-10-26T10:00:00+00:00",
    )
    session.flush()
    session.add(
        AgentRunStep(
            id=str(uuid4()),
            run_id=agent.id,
            sequence_no=1,
            tool_name="external_model_call",
            status="FAILED_EXTERNAL",
            created_at="2026-10-26T10:00:01+00:00",
            completed_at="2026-10-26T10:00:01+00:00",
        )
    )
    _add_guardian(
        session,
        journey.id,
        event_id,
        created_at="2026-10-26T10:00:02+00:00",
        action_status="RETRYABLE_FAILURE",
        agent_run_id=agent.id,
    )
    session.commit()
    session_factory.close()

    body = _progress(client, headers, path)
    assert body["guardian_outcome"] == {
        "code": "EXTERNAL_FAILED",
        "error_code": "MODEL_REQUEST_FAILED",
    }


@pytest.mark.parametrize(
    ("configured", "expected"),
    [(True, "UNKNOWN"), (False, "MODEL_NOT_CONFIGURED")],
)
def test_retryable_guardian_without_external_failure_evidence_is_not_external_failed(
    sim, monkeypatch, configured, expected
):
    _set_model_config(monkeypatch, configured=configured)
    client, ids, factory, headers, path, run = _start_scene(sim)
    session_factory = factory()
    session = next(session_factory)
    _add_guardian(
        session,
        ids["journey"],
        run["state"]["pending_event_id"],
        created_at="2026-10-26T10:00:00+00:00",
        action_status="RETRYABLE_FAILURE",
    )
    session.commit()
    session_factory.close()

    body = _progress(client, headers, path)
    assert body["guardian_outcome"] == {"code": expected}


def test_current_guardian_proposal_is_ready_even_without_model_configuration(sim, monkeypatch):
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
