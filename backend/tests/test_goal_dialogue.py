"""Conversation/choice and open-ended research controls; no external requests."""
import json
from uuid import uuid4
from app.agent import goal_tasks
from test_goal_tasks import goal_scope


def create(scope, **extra):
    session, journey, member = scope
    return goal_tasks.create_goal_task(session, journey, member, goal="周末想去看看广州，先给我几个方向",
        model_consent=True, online_research_consent=True, max_model_turns=1, max_tool_calls=0,
        interaction_mode="DISCUSS", unlimited_research=True, **extra)


def test_discussion_asks_a_real_question_and_choice_continues_same_task(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    task = create(goal_scope)
    class Agent:
        provider_key = model_key = "TEST_FIXTURE"
        def _complete(self, messages):
            assert "discussing a trip" in str(messages)
            return {"tool_calls": [{"id": "question", "function": {"name": "ask_traveler", "arguments": json.dumps({
                "question": "这次更想轻松看江景，还是逛博物馆？", "options": [
                    {"label": "江边休息", "description": "少走路，多留休息时间"},
                    {"label": "博物馆慢逛", "description": "室内为主，先比较展馆"}]})}}]}
    def agent(tools):
        assert tools == {"ask_traveler", "inspect_journey"}
        return Agent()
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", agent)
    result = goal_tasks.resume_goal_task(session, journey, member, task["task_id"])
    assert result["status"] == "NEEDS_DECISION"
    assert len(result["pending_question"]["options"]) == 2
    assert result["conversation"][-1]["role"] == "assistant"
    assert result["usage"]["tool_calls"] == 1  # beyond the old zero-tool cap
    restored = goal_tasks.read_goal_task(session, journey, member, task["task_id"])
    assert restored["pending_question"] == result["pending_question"]
    class Reply:
        provider_key = model_key = "TEST_FIXTURE"
        def _complete(self, _): return {"content": "好，按江边休息来考虑。可以先比较珠江两岸的地点，你点开始研究后我再去查。"}
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda _: Reply())
    result = goal_tasks.resume_goal_task(session, journey, member, task["task_id"],
        user_message="江边休息", message_id=uuid4(), interaction_mode="DISCUSS", unlimited_research=True)
    assert result["task_id"] == task["task_id"] and result["pending_question"] is None
    assert result["usage"]["model_turns"] == 2  # beyond the old one-turn cap
    assert result["conversation"][-2]["text"] == "江边休息"
    assert not any(day["slots"] for day in result["draft_artifact"]["days"])


def test_discussion_does_not_dispatch_a_research_tool(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    task = create(goal_scope)
    class Agent:
        provider_key = model_key = "TEST_FIXTURE"
        turn = 0
        def _complete(self, _):
            self.turn += 1
            if self.turn > 1: return {"content": "先聊聊你的喜好。"}
            return {"tool_calls": [{"id": "blocked", "function": {"name": "discover_places", "arguments": "{}"}}]}
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda _: Agent())
    monkeypatch.setattr(goal_tasks, "discover_goal_places", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("discussion must not search")))
    result = goal_tasks.resume_goal_task(session, journey, member, task["task_id"])
    assert not result["research_places"]
    result = goal_tasks.read_goal_task(session, journey, member, task["task_id"])
    assert result["tool_steps"][0]["status"] == "BLOCKED"


def test_explicit_research_switch_preserves_conversation_and_opens_tools(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    task = create(goal_scope)
    class Agent:
        provider_key = model_key = "TEST_FIXTURE"
        turn = 0
        def _complete(self, _):
            self.turn += 1
            if self.turn > 1: return {"content": "已读取你这趟行程，继续按商量好的方向安排。"}
            return {"tool_calls": [{"id": "read", "function": {"name": "inspect_journey", "arguments": "{}"}}]}
    def agent(tools):
        assert "discover_places" in tools
        return Agent()
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", agent)
    result = goal_tasks.resume_goal_task(session, journey, member, task["task_id"],
        user_message="按江边休息的方向开始研究", message_id=uuid4(), interaction_mode="RESEARCH", unlimited_research=True)
    assert result["interaction_mode"] == "RESEARCH" and result["budget"]["unlimited"]
    assert result["usage"]["model_turns"] == 2 and result["usage"]["tool_calls"] == 1
