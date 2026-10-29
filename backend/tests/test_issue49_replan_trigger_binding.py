"""Tool-level trigger binding checks for server-owned recovery missions."""

import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.agent import gateway as gateway_module
from app.agent.gateway import AgentToolGateway
from app.db.models import Journey, JourneyMission, ReplanProposal
from app.schemas import AgentToolCall


class FakeSession:
    def __init__(self, journey, mission):
        self.rows = {
            Journey: {journey.id: journey},
            JourneyMission: {mission.id: mission},
        }

    def get(self, model, identity):
        return self.rows.get(model, {}).get(str(identity))

    def add_row(self, model, row):
        self.rows.setdefault(model, {})[str(row.id)] = row


def _bound_task(*, server_recovery=True, mission_trigger=True):
    journey_id = str(uuid4())
    mission_id = str(uuid4())
    standing_mission_id = str(uuid4())
    trigger_id = str(uuid4())
    journey = SimpleNamespace(id=journey_id, traveler_id=str(uuid4()))
    resolved_intent = {}
    if server_recovery:
        resolved_intent["server_owned_recovery_context"] = {
            "journey_id": journey_id,
            "standing_mission_id": standing_mission_id,
            "recovery_mission_id": mission_id,
            "trigger_event_id": trigger_id,
        }
    mission = SimpleNamespace(
        id=mission_id,
        journey_id=journey_id,
        parent_mission_id=standing_mission_id if server_recovery else None,
        is_standing=False,
        trigger_event_id=trigger_id if mission_trigger else None,
        resolved_intent_json=json.dumps(resolved_intent),
        objective_codes_json="[]",
    )
    return journey, mission, trigger_id


def _request(journey, mission, *, trigger_event_id=None, proposal_id=None):
    return AgentToolCall(
        request_id="recovery-trigger-binding-" + uuid4().hex[:8],
        journey_id=UUID(journey.id),
        mission_id=UUID(mission.id),
        trigger_event_id=UUID(trigger_event_id) if trigger_event_id else None,
        proposal_id=UUID(proposal_id) if proposal_id else None,
    )


def _capture_event_selection(monkeypatch):
    seen = []

    def resolve(_session, journey_id, event_id=None):
        seen.append((journey_id, event_id))
        return None, [], "EVENT_SELECTION_REQUIRED"

    monkeypatch.setattr(gateway_module, "_resolve_actionable_event", resolve)
    return seen


def test_recovery_request_replan_defaults_to_mission_trigger_when_model_omits_it(monkeypatch):
    journey, mission, trigger_id = _bound_task()
    seen = _capture_event_selection(monkeypatch)

    result = AgentToolGateway(FakeSession(journey, mission)).request_replan(
        _request(journey, mission)
    )

    assert result["error"] == "EVENT_SELECTION_REQUIRED"
    assert seen == [(journey.id, UUID(trigger_id))]


def test_recovery_request_replan_rejects_explicit_trigger_conflict(monkeypatch):
    journey, mission, trigger_id = _bound_task()
    seen = _capture_event_selection(monkeypatch)
    conflicting_trigger_id = str(uuid4())
    assert conflicting_trigger_id != trigger_id

    with pytest.raises(HTTPException) as conflict:
        AgentToolGateway(FakeSession(journey, mission)).request_replan(
            _request(journey, mission, trigger_event_id=conflicting_trigger_id)
        )

    assert conflict.value.status_code == 409
    assert conflict.value.detail == "RECOVERY_TRIGGER_SCOPE_MISMATCH"
    assert seen == []


def test_non_recovery_mission_does_not_override_explicit_tool_trigger(monkeypatch):
    journey, mission, _bound_trigger_id = _bound_task(server_recovery=False)
    mission.trigger_event_id = str(uuid4())
    requested_trigger_id = str(uuid4())
    seen = _capture_event_selection(monkeypatch)

    result = AgentToolGateway(FakeSession(journey, mission)).request_replan(
        _request(journey, mission, trigger_event_id=requested_trigger_id)
    )

    assert result["error"] == "EVENT_SELECTION_REQUIRED"
    assert seen == [(journey.id, UUID(requested_trigger_id))]


def test_list_replans_for_recovery_mission_stays_on_bound_trigger(monkeypatch):
    journey, mission, trigger_id = _bound_task()
    seen = _capture_event_selection(monkeypatch)

    result = AgentToolGateway(FakeSession(journey, mission)).list_replans(
        _request(journey, mission)
    )

    assert result["error"] == "EVENT_SELECTION_REQUIRED"
    assert seen == [(journey.id, UUID(trigger_id))]


def test_list_replans_does_not_override_general_mission_trigger(monkeypatch):
    journey, mission, _bound_trigger_id = _bound_task(server_recovery=False)
    mission.trigger_event_id = str(uuid4())
    requested_trigger_id = str(uuid4())
    seen = _capture_event_selection(monkeypatch)

    result = AgentToolGateway(FakeSession(journey, mission)).list_replans(
        _request(journey, mission, trigger_event_id=requested_trigger_id)
    )

    assert result["error"] == "EVENT_SELECTION_REQUIRED"
    assert seen == [(journey.id, UUID(requested_trigger_id))]


def test_accept_recovery_rejects_old_event_proposal_before_policy_or_native_write(monkeypatch):
    journey, mission, bound_trigger_id = _bound_task()
    proposal = SimpleNamespace(
        id=str(uuid4()),
        journey_id=journey.id,
        trigger_event_id=str(uuid4()),
    )
    assert proposal.trigger_event_id != bound_trigger_id
    session = FakeSession(journey, mission)
    session.add_row(ReplanProposal, proposal)
    policy_calls = []

    def policy_read(*_args, **_kwargs):
        policy_calls.append(True)
        raise AssertionError("recovery proposal binding must be checked before policy")

    monkeypatch.setattr(gateway_module, "get_or_create_policy", policy_read)
    with pytest.raises(HTTPException) as conflict:
        AgentToolGateway(session).accept_replan(
            _request(journey, mission, proposal_id=proposal.id)
        )

    assert conflict.value.status_code == 409
    assert conflict.value.detail == "RECOVERY_PROPOSAL_TRIGGER_MISMATCH"
    assert policy_calls == []


def test_accept_recovery_with_bound_proposal_reaches_existing_policy_gate(monkeypatch):
    journey, mission, bound_trigger_id = _bound_task()
    proposal = SimpleNamespace(
        id=str(uuid4()),
        journey_id=journey.id,
        trigger_event_id=bound_trigger_id,
    )
    session = FakeSession(journey, mission)
    session.add_row(ReplanProposal, proposal)
    policy_calls = []

    class ExistingPolicyGateReached(Exception):
        pass

    def policy_read(_session, traveler_id):
        policy_calls.append(traveler_id)
        raise ExistingPolicyGateReached

    monkeypatch.setattr(gateway_module, "get_or_create_policy", policy_read)
    with pytest.raises(ExistingPolicyGateReached):
        AgentToolGateway(session).accept_replan(
            _request(journey, mission, proposal_id=proposal.id)
        )

    assert policy_calls == [journey.traveler_id]
