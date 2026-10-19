"""TEST_FIXTURE models exercise autonomous progress inside one approved run."""
import json
from test_goal_tasks import goal_scope, _create
from app.agent import goal_tasks


def test_first_grounded_batch_is_saved_after_text_only_early_finish(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    created = _create(session, journey, member, online_research_consent=True, max_model_turns=4)
    class Agent:
        provider_key = model_key = "TEST_FIXTURE"
        turn = 0
        def _complete(self, messages):
            self.turn += 1
            if self.turn == 1:
                name, args = "discover_places", {"query": "TEST_FIXTURE museum"}
            elif self.turn == 2:
                return {"content": "TEST_FIXTURE 我找到了地点"}
            elif self.turn == 3:
                assert "no editable draft" in messages[-1]["content"]
                name, args = "save_draft_itinerary", {"days": [{"date": "2026-11-01", "slots": [{
                    "title": "TEST_FIXTURE 文化地点", "time_of_day": "afternoon", "place_id": "photon:node/123"}]}]}
            else:
                return {"content": "TEST_FIXTURE 已存草案"}
            return {"tool_calls": [{"id": f"fixture-{self.turn}", "function": {"name": name, "arguments": json.dumps(args)}}]}
    def discover(_session, _journey, task, **_args):
        lead = {"id": "photon:node/123", "name": "TEST_FIXTURE museum"}
        task["research_places"] = [lead]
        return {"status": "RESULTS", "places": [lead]}
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda *_: Agent())
    monkeypatch.setattr(goal_tasks, "discover_goal_places", discover)
    result = goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    assert result["task_id"] == created["task_id"]
    assert result["usage"]["model_turns"] == 4
    assert result["draft_artifact"]["days"][0]["slots"][0]["place_id"] == "photon:node/123"


def test_provider_zero_does_not_advertise_terminal_state_mid_run(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    created = _create(session, journey, member, online_research_consent=True, max_model_turns=3)
    class Agent:
        provider_key = model_key = "TEST_FIXTURE"
        turn = 0
        def _complete(self, messages):
            self.turn += 1
            if self.turn == 1:
                return {"tool_calls": [{"id": "fixture-zero", "function": {"name": "discover_places", "arguments": '{"query":"TEST_FIXTURE zero"}'}}]}
            assert goal_tasks.read_goal_task(session, journey, member, created["task_id"])["status"] == "WORKING"
            assert json.loads(messages[-1]["content"])["status"] == "NO_RESULTS"
            return {"content": "TEST_FIXTURE 暂无来源结果"}
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda *_: Agent())
    monkeypatch.setattr(goal_tasks, "discover_goal_places", lambda *_a, **_k: {"status": "NO_RESULTS", "places": []})
    result = goal_tasks.resume_goal_task(session, journey, member, created["task_id"])
    assert result["status"] == "PARTIAL_READY"
    assert result["usage"]["model_turns"] == 2
