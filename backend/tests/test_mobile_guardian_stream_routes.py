"""Signed Guardian stream reads; all records in these tests are TEST_FIXTURE."""
from uuid import uuid4
from sqlalchemy import select, func
from app.db.models import Event, GuardianRun, GuardianPulse, ProviderCall
from app.db.session import SessionLocal
from test_bootstrap_place_facts import enabled_settings, signed_place


def test_guardian_stream_signed_owner_read_is_private_and_read_only(signed_place):
    client, owner, outsider, journey_id, *_ = signed_place
    path = f"/api/v1/journeys/{journey_id}/guardian/stream"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=outsider).status_code == 403
    models = (Event, GuardianRun, GuardianPulse, ProviderCall)
    with SessionLocal() as session:
        before = [session.scalar(select(func.count()).select_from(model)) for model in models]
    result = client.get(path, headers=owner)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["journey_id"] == journey_id
    assert data["status"] == "WATCH_NOT_RUNNING"
    assert data["stream"] == [] and data["recovery_epoch"] is None
    assert "no-store" in result.headers["cache-control"]
    assert "Authorization" in result.headers["vary"]
    assert client.get(path + f"?mission_id={uuid4()}", headers=owner).status_code == 404
    with SessionLocal() as session:
        after = [session.scalar(select(func.count()).select_from(model)) for model in models]
    assert before == after


def test_goal_runtime_can_read_guardian_without_online_research(goal_scope, monkeypatch):
    import json
    from app.agent import goal_tasks
    from test_goal_tasks import _create
    session, journey, member = goal_scope
    created = _create(session, journey, member, max_model_turns=3)
    seen = []
    class Agent:
        provider_key = model_key = "TEST_FIXTURE"
        turn = 0
        def _complete(self, messages):
            self.turn += 1
            if self.turn == 1:
                return {"tool_calls": [{"id": "fixture-guardian", "function": {
                    "name": "read_guardian_stream", "arguments": "{}"}}]}
            seen.extend(messages)
            return {"content": "TEST_FIXTURE 尚无守护检查记录"}
    def agent_factory(allowed):
        assert "read_guardian_stream" in allowed
        return Agent()
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", agent_factory)
    goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    restored = goal_tasks.read_goal_task(session, journey, member, created["task_id"])
    step = restored["tool_steps"][0]
    assert step["tool_name"] == "read_guardian_stream"
    assert step["result"]["status"] == "WATCH_NOT_RUNNING"
    assert step["result"]["acquisition_attempted"] is False
    assert "WATCH_NOT_RUNNING" in json.dumps(seen)
    assert journey.status == "DRAFT" and journey.active_plan_version_id is None


from test_goal_tasks import goal_scope
