"""Isolated SQLite integration; upstream model is a declared failing test double."""
# ruff: noqa: F811 -- pytest resolves imported shared fixtures by name

import json
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_issue47_private_reads import stack  # noqa: F401
from test_issue47_simulation import sim  # noqa: F401

from app import main, traveler_principal
from app.agent import autorun, guardian
from app.agent.mission import create_mission
from app.agent.runtime import AgentRuntimeUnavailable
from app.db.models import (
    AgentRun,
    AgentRunStep,
    Event,
    Journey,
    JourneyRoleCapability,
    ReplanProposal,
)
from app.execution.clock import execution_clock
from app.simulation import api, clock
from app.simulation.models import SimulationRun


def start_scene(sim):
    _, ids, _, _, _, url, post = sim
    run = post(url, {"seed": 49}).json()
    path = url + "/" + run["run_id"]
    scene = post(
        path + "/scenes",
        {
            "expected_sequence": 0,
            "scene_id": "closed-49",
            "event_type": "CLOSURE",
            "activity_id": ids["activities"][0],
        },
    )
    assert scene.status_code == 200, scene.text
    return path, scene.json()


@pytest.mark.parametrize(
    "caller,status",
    [
        (None, 401),
        ("stranger", 403),
        ("removed", 403),
        ("expired", 403),
        ("no_read", 403),
        ("member", 200),
        ("owner", 200),
    ],
)
def test_progress_private_read_matrix(sim, caller, status):
    client, ids, _, _, _, _, _ = sim
    path, run = start_scene(sim)
    headers = (
        {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(ids[caller])}
        if caller
        else {}
    )
    response = client.get(path + "/progress", headers=headers)
    assert response.status_code == status
    if status == 200:
        assert "no-store" in response.headers["Cache-Control"]
        assert response.json()["run_id"] == run["run_id"]
    else:
        assert run["run_id"] not in response.text


def test_readiness_is_configuration_not_execution_and_unknown_run_is_404(sim, monkeypatch):
    client, _, _, _, headers, url, _ = sim
    path, _ = start_scene(sim)
    monkeypatch.setattr(
        api,
        "settings",
        replace(api.settings, hermes_api_url=None, hermes_api_key=None, ai_api_key=None),
    )
    response = client.get(path + "/progress", headers=headers).json()
    assert response["agent_runs"] == response["steps"] == []
    assert response["readiness"]["missing"] == [
        "MODEL_CREDENTIALS_MISSING",
        "STANDING_MISSION_REQUIRED",
    ]
    assert response["readiness"]["network_checked"] is False
    assert response["clock_policy"] == {
        "business": "PERSISTED_VIRTUAL",
        "security_and_audit": "WALL",
    }
    assert client.get(url + "/" + str(uuid4()) + "/progress", headers=headers).status_code == 404


def test_guardian_inflight_steps_are_persisted_scoped_and_never_leak_raw_text(sim, monkeypatch):
    client, ids, _, factory, headers, _, post = sim
    path, run = start_scene(sim)
    event_id = run["state"]["pending_event_id"]
    db = factory()
    session = next(db)
    journey = session.get(Journey, ids["journey"])
    mission = create_mission(
        session,
        journey,
        command="闭馆后给我选择，先确认。",
        requested_autonomy="PROPOSE_ONLY",
        trigger_event_id=None,
        is_standing=True,
        use_model_draft=False,
    )
    mission.status = "ACTIVE"
    stamp = datetime.now(timezone.utc).isoformat()
    # A more severe, unrelated event must not hijack this SimulationRun's trigger.
    unrelated = Event(
        id=str(uuid4()),
        journey_id=journey.id,
        provider_key="TEST_FIXTURE",
        provenance="TEST_FIXTURE",
        event_type="WEATHER",
        severity="CRITICAL",
        status="DETECTED",
        occurred_at=stamp,
        detected_at=stamp,
        payload_json='{"secret":"DO_NOT_PROJECT"}',
        created_at=stamp,
    )
    session.add(unrelated)
    session.commit()
    db.close()
    observations = []

    class FailingModelDouble:
        provider_key = "TEST_DOUBLE"

        def run(self, session, *, journey, mission, max_steps):
            assert mission.trigger_event_id == event_id
            assert execution_clock.now(journey.timezone).isoformat() == run["virtual_now"]
            agent = AgentRun(
                id=str(uuid4()),
                mission_id=mission.id,
                journey_id=journey.id,
                provider_key="TEST_DOUBLE",
                model_key="NOT_LIVE",
                status="RUNNING",
                created_at=stamp,
                started_at=stamp,
            )
            session.add(agent)
            session.flush()
            session.add(
                AgentRunStep(
                    id=str(uuid4()),
                    run_id=agent.id,
                    sequence_no=1,
                    tool_name="inspect_journey",
                    status="COMPLETED",
                    arguments_json='{"key":"DO_NOT_PROJECT"}',
                    result_json='{"reasoning":"DO_NOT_PROJECT"}',
                    created_at=stamp,
                    completed_at=stamp,
                )
            )
            session.commit()
            # Independent HTTP read before Guardian assigns agent_run_id at completion.
            progress = client.get(path + "/progress", headers=headers)
            assert progress.status_code == 200
            assert "DO_NOT_PROJECT" not in progress.text
            body = progress.json()
            assert body["status"] == "GUARDIAN_RUNNING"
            assert body["guardian_runs"][0]["event_id"] == event_id
            assert body["agent_runs"][0]["id"] == agent.id
            assert body["steps"][0]["tool_name"] == "inspect_journey"
            observations.append(body)
            agent.status = "FAILED_EXTERNAL"
            agent.failure_reason = "DO_NOT_PROJECT"
            session.add(
                AgentRunStep(
                    id=str(uuid4()),
                    run_id=agent.id,
                    sequence_no=2,
                    tool_name="external_model_call",
                    status="FAILED_EXTERNAL",
                    result_json='{"error":"DO_NOT_PROJECT"}',
                    created_at=stamp,
                    completed_at=stamp,
                )
            )
            session.commit()
            raise AgentRuntimeUnavailable("DO_NOT_PROJECT")

        def close(self):
            pass

    monkeypatch.setattr(
        guardian, "configured_journey_agent_candidates", lambda: [FailingModelDouble()]
    )
    key = uuid4().hex
    body = {"expected_sequence": 1, "model_consent": True}
    result = post(path + "/guardian", body, key)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "PAUSED_MODEL_UNAVAILABLE"
    assert len(observations) == 1
    assert post(path + "/guardian", body, key).json() == result.json()
    assert len(observations) == 1
    progress = client.get(path + "/progress", headers=headers)
    assert "DO_NOT_PROJECT" not in progress.text
    assert progress.json()["steps"][-1]["error_code"] == "MODEL_REQUEST_FAILED"
    assert len(progress.json()["events"]) == 1


def test_missing_mission_guardian_is_still_linked_to_injected_event(sim):
    client, _, _, _, headers, _, post = sim
    path, run = start_scene(sim)
    result = post(path + "/guardian", {"expected_sequence": 1, "model_consent": True})
    assert result.status_code == 200
    assert result.json()["status"] == "PAUSED_REQUIRES_MISSION"
    progress = client.get(path + "/progress", headers=headers).json()
    assert progress["guardian_runs"][0]["event_id"] == run["state"]["pending_event_id"]
    assert progress["guardian_runs"][0]["action_status"] == "MISSION_REQUIRED"
    assert progress["agent_runs"] == []


def test_mismatched_scene_cannot_start_guardian_or_consume_sequence(sim):
    client, _, _, factory, headers, _, post = sim
    path, run = start_scene(sim)
    db = factory()
    session = next(db)
    event = session.get(Event, run["state"]["pending_event_id"])
    data = json.loads(event.payload_json)
    data["simulation_run_id"] = str(uuid4())
    event.payload_json = json.dumps(data)
    session.commit()
    db.close()
    result = post(path + "/guardian", {"expected_sequence": 1, "model_consent": True})
    assert result.status_code == 409
    assert result.json()["detail"] == "SIMULATION_SCENE_EVENT_MISMATCH"
    assert client.get(path, headers=headers).json()["sequence"] == 1


def test_autorun_scope_uses_persisted_time_and_restores_wall_clock(sim, monkeypatch):
    _, ids, _, factory, _, url, post = sim
    run = post(url, {"seed": 49}).json()
    monkeypatch.setattr(autorun, "settings", replace(autorun.settings, simulation_enabled=True))
    seen = []

    def pulse(session, journey):
        assert clock.simulation_scope_active()
        seen.append(execution_clock.now(journey.timezone).isoformat())
        return {"status": "CLOCK_TEST_DOUBLE"}

    monkeypatch.setattr(autorun, "_pulse_journey_in_context", pulse)
    db = factory()
    session = next(db)
    journey = session.get(Journey, ids["journey"])
    assert autorun.pulse_journey(session, journey)["status"] == "CLOCK_TEST_DOUBLE"
    assert seen == [run["virtual_now"]]
    assert not clock.simulation_scope_active()
    assert abs((execution_clock.now() - datetime.now(timezone.utc)).total_seconds()) < 3
    session.get(SimulationRun, run["run_id"]).status = "PAUSED_FOR_GUARDIAN"
    session.commit()
    assert autorun.pulse_journey(session, journey)["status"] == "SIMULATION_PAUSED"
    assert len(seen) == 1
    db.close()


def test_signed_acceptance_passes_actor_to_native_writer_and_denies_others(sim, monkeypatch):
    client, ids, _, factory, headers, url, post = sim
    run = post(url, {"seed": 49}).json()
    db = factory()
    session = next(db)
    stamp = datetime.now(timezone.utc).isoformat()
    proposal = ReplanProposal(
        id=str(uuid4()),
        journey_id=ids["journey"],
        base_plan_version_id=ids["plan"],
        proposed_plan_version_id=ids["plan"],
        status="PRESENTED",
        hard_constraints_passed=True,
        locked_commitments_preserved=True,
        utility_score=1,
        score_breakdown_json="{}",
        diff_json="{}",
        explanation_json="{}",
        created_at=stamp,
    )
    session.add(proposal)
    session.add(
        JourneyRoleCapability(
            role="OWNER", capability="JOURNEY_UPDATE", scope_message_key="test", created_at=stamp
        )
    )
    session.commit()
    accept_url = "/api/v1/replans/" + proposal.id + "/accept"
    db.close()
    client.app.add_api_route(
        "/api/v1/replans/{proposal_id}/accept", main.accept_replan, methods=["POST"]
    )
    calls = []

    def writer(proposal_id, key, session, **kwargs):
        assert clock.simulation_scope_active()
        assert execution_clock.now() == datetime.fromisoformat(run["virtual_now"])
        calls.append(kwargs)
        return {"writer": "TEST_DOUBLE"}

    monkeypatch.setattr(main, "_accept_replan_impl", writer)
    assert client.post(accept_url, headers={"Idempotency-Key": "49"}).status_code == 401
    member = {
        "Authorization": "Bearer " + traveler_principal.issue_traveler_token(ids["member"]),
        "Idempotency-Key": "49",
    }
    assert client.post(accept_url, headers=member).status_code == 403
    assert not calls
    response = client.post(accept_url, headers={**headers, "Idempotency-Key": "49"})
    assert response.status_code == 200, response.text
    assert calls == [{"actor_type": "AUTHENTICATED_TRAVELER", "actor_id": ids["owner"]}]


def test_signal_refresh_reuses_same_scene_and_keeps_provider_capture_on_wall_time(sim):
    from app.agent.signal_pipeline import refresh_demo_signals
    from app.db.models import ProviderObservation

    _, ids, _, factory, _, _, _ = sim
    _, run = start_scene(sim)
    db = factory()
    session = next(db)
    journey = session.get(Journey, ids["journey"])
    with clock.journey_business_time(session, journey.id):
        result = refresh_demo_signals(session, journey)
        assert execution_clock.now() == datetime.fromisoformat(run["virtual_now"])
    assert result.event_ids == (run["state"]["pending_event_id"],)
    assert result.created_event_ids == ()
    assert len(list(session.scalars(select(Event).where(Event.journey_id == journey.id)))) == 1
    observation = session.get(ProviderObservation, run["state"]["provider_observation_ids"][0])
    assert json.loads(observation.payload_json)["virtual_now"] == run["virtual_now"]
    assert (
        abs(
            (
                datetime.fromisoformat(observation.captured_at) - datetime.now(timezone.utc)
            ).total_seconds()
        )
        < 5
    )
    db.close()


def test_progress_ignores_other_event_agent_and_masks_unknown_tool(sim):
    client, ids, _, factory, headers, _, _ = sim
    path, run = start_scene(sim)
    db = factory()
    session = next(db)
    stamp = datetime.now(timezone.utc).isoformat()
    journey = session.get(Journey, ids["journey"])
    for event_id, name in [(run["state"]["pending_event_id"], "this"), (None, "other")]:
        mission = create_mission(
            session,
            journey,
            command="TEST_FIXTURE",
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
            model_key="DO_NOT_PROJECT",
            status="RUNNING",
            created_at=stamp,
            started_at=stamp,
        )
        session.add(agent)
        session.flush()
        session.add(
            AgentRunStep(
                id=str(uuid4()),
                run_id=agent.id,
                sequence_no=1,
                tool_name="DO_NOT_PROJECT",
                status="DO_NOT_PROJECT",
                created_at=stamp,
                arguments_json='{"key":"DO_NOT_PROJECT"}',
                result_json='{"error":"DO_NOT_PROJECT"}',
            )
        )
    session.commit()
    db.close()
    response = client.get(path + "/progress", headers=headers)
    assert response.status_code == 200
    assert "DO_NOT_PROJECT" not in response.text
    assert len(response.json()["agent_runs"]) == 1
    assert len(response.json()["steps"]) == 1
    assert response.json()["steps"][0]["tool_name"] == "unlisted_tool"
    assert response.json()["steps"][0]["status"] == "UNKNOWN"


@pytest.mark.parametrize("seed", [17, 409])
def test_two_days_two_stops_each_persist_completion(sim, seed):
    from datetime import timedelta

    from app.db.models import Activity

    client, ids, _, factory, headers, url, post = sim
    db = factory()
    session = next(db)
    originals = [session.get(Activity, aid) for aid in ids["activities"]]
    for index, original in enumerate(originals):
        original.sequence_no = index * 2 + 1
    session.flush()
    for index, original in enumerate(originals):
        session.add(
            Activity(
                id=str(uuid4()),
                plan_version_id=ids["plan"],
                sequence_no=index * 2 + 2,
                activity_type=original.activity_type,
                title="Second TEST_FIXTURE stop",
                place_id=original.place_id,
                start_at=(
                    datetime.fromisoformat(original.end_at) + timedelta(minutes=30)
                ).isoformat(),
                end_at=(
                    datetime.fromisoformat(original.end_at) + timedelta(minutes=90)
                ).isoformat(),
                travel_from_prev_min=10,
                estimated_cost_minor=0,
                currency="CNY",
                status="PLANNED",
                locked=False,
                metadata_json="{}",
                created_at=original.created_at,
                updated_at=original.updated_at,
            )
        )
    session.commit()
    db.close()
    run = post(url, {"seed": seed}).json()
    path = url + "/" + run["run_id"]
    response = post(path + "/advance", {"expected_sequence": 0, "minutes": 2880})
    assert response.status_code == 200, response.text
    completed = response.json()
    assert completed["status"] == "SIMULATED_COMPLETED"
    arrivals = [h for h in completed["history"] if h["event"] == "SIM_ARRIVAL"]
    assert len(arrivals) == 4
    assert len({datetime.fromisoformat(h["virtual_now"]).date() for h in arrivals}) == 2
    assert client.get(path, headers=headers).json() == completed
    # A new DB session reads the same durable state, independent of HTTP response memory.
    db = factory()
    session = next(db)
    saved = session.get(SimulationRun, run["run_id"])
    assert saved.status == "SIMULATED_COMPLETED"
    assert json.loads(saved.history_json) == completed["history"]
    assert session.get(Journey, ids["journey"]).status == "COMPLETED"
    db.close()
