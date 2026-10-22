"""The screen must be able to tell "the Agent changed the schedule" from "the Agent said it did".

Measured on a real walk: after a traveller wrote 「11 月 2 日上午不去故宫了，改成天坛一带」 the Agent
answered 「明白，已把 Day1（11/2）上午从「故宫/天安门一带」改为「天坛一带」」 while the schedule on
screen still read 故宫/天安门. The sentence and the draft had both come from the server, but nothing
tied one to the other. These arms pin the pair the server now stores with every assistant message.
"""

from __future__ import annotations

import json
from uuid import uuid4

from app.agent import goal_tasks as goal_tasks_agent
from test_goal_tasks import _create, goal_scope  # noqa: F401  (fixture is imported on purpose)


def test_a_claim_that_never_wrote_the_draft_carries_an_unchanged_revision_receipt(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    created = _create(session, journey, member, max_model_turns=8, max_tool_calls=8)

    class ClaimOnlyAgent:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False

        def _complete(self, messages):
            return {"content": "TEST_FIXTURE 明白，已把 Day1 上午改为天坛一带，其余 slot 全部保留不动。"}

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: ClaimOnlyAgent())
    goal_tasks_agent.resume_goal_task(session, journey, member, created["task_id"])
    second = goal_tasks_agent.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="11 月 2 日上午不去故宫了，改成天坛一带，其他安排都别动。",
        message_id=str(uuid4()),
    )

    entry = second["conversation"][-1]
    assert entry["role"] == "assistant"
    # The words are the model's and stay untouched; the receipt beside them is computed by the server.
    assert entry["text"].startswith("TEST_FIXTURE 明白，已把 Day1 上午改为天坛一带")
    assert entry["draft_revision_before"] == entry["draft_revision_after"]
    assert entry["draft_revision_after"] == second["draft_artifact"]["revision"]


def test_the_turn_that_actually_saved_a_draft_reports_the_revision_it_moved(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    created = _create(session, journey, member, max_model_turns=8, max_tool_calls=8,
                      online_research_consent=True)

    class WriteThenSummarize:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False
        turn = 0

        def _complete(self, messages):
            self.turn += 1
            if self.turn == 1:
                return {"tool_calls": [{"id": "fixture-search-1", "function": {
                    "name": "discover_places", "arguments": json.dumps({"query": "TEST_FIXTURE 天坛"})}}]}
            if self.turn == 2:
                return {"tool_calls": [{"id": "fixture-write-1", "function": {
                    "name": "save_draft_itinerary", "arguments": json.dumps({"days": [{
                        "date": "2026-11-01", "slots": [{
                            "title": "TEST_FIXTURE 天坛一带", "time_of_day": "morning",
                            "place_id": "photon:node/123", "notes": "开放时间与票价待查证"}]}]})}}]}
            return {"content": "TEST_FIXTURE 已把 Day1 上午改为天坛一带"}

        _tool_allowlist = frozenset()

    def fixture_discovery(_session, _journey, task, **args):
        place = {"id": "photon:node/123", "name": "TEST_FIXTURE 天坛", "source_url": "https://www.openstreetmap.org/node/123"}
        task["research_places"] = [place]
        return {"tool": "discover_places", "status": "RESULTS", "places": [place], "http_status": 200}

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: WriteThenSummarize())
    monkeypatch.setattr(goal_tasks_agent, "discover_goal_places", fixture_discovery)
    result = goal_tasks_agent.resume_goal_task(session, journey, member, created["task_id"])

    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])
    entry = restored["conversation"][-1]
    assert entry["role"] == "assistant"
    assert [step["tool_name"] for step in restored["tool_steps"]] == ["discover_places", "save_draft_itinerary"]
    assert restored["draft_artifact"]["days"][0]["slots"][0]["place_id"] == "photon:node/123"
    assert entry["draft_revision_after"] == restored["draft_artifact"]["revision"]
    assert entry["draft_revision_after"] != entry["draft_revision_before"]


def test_a_refused_write_and_a_claiming_reply_stay_apart_on_the_receipt(goal_scope, monkeypatch):
    """The tool refuses a day outside the journey window; the sentence still says it saved.

    This is the exact shape of the walk defect: the reply is confident, the draft did not move. The
    receipt is what lets the screen say so without editing the model's words.
    """
    session, journey, member = goal_scope
    created = _create(session, journey, member, max_model_turns=8, max_tool_calls=8,
                      online_research_consent=True)

    class RefusedWriteThenClaim:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False
        turn = 0

        def _complete(self, messages):
            self.turn += 1
            if self.turn == 1:
                return {"tool_calls": [{"id": "p-search", "function": {
                    "name": "discover_places", "arguments": json.dumps({"query": "TEST_FIXTURE 天坛"})}}]}
            if self.turn == 2:
                return {"tool_calls": [{"id": "p-write", "function": {
                    "name": "save_draft_itinerary", "arguments": json.dumps({"days": [{
                        "date": "2026-11-02", "slots": [{
                            "title": "TEST_FIXTURE 天坛一带", "time_of_day": "morning",
                            "place_id": "photon:node/123", "notes": "待查证"}]}]})}}]}
            return {"content": "TEST_FIXTURE 已保存"}

    def fixture_discovery(_session, _journey, task, **args):
        place = {"id": "photon:node/123", "name": "TEST_FIXTURE 天坛", "source_url": "https://www.openstreetmap.org/node/123"}
        task["research_places"] = [place]
        return {"tool": "discover_places", "status": "RESULTS", "places": [place], "http_status": 200}

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: RefusedWriteThenClaim())
    monkeypatch.setattr(goal_tasks_agent, "discover_goal_places", fixture_discovery)
    goal_tasks_agent.resume_goal_task(session, journey, member, created["task_id"])
    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])
    step = restored["tool_steps"][-1]
    assert step["tool_name"] == "save_draft_itinerary"
    assert step["status"] == "FAILED"
    assert step["result"]["reason_code"] == "DRAFT_DATE_OUTSIDE_JOURNEY"
    assert restored["draft_artifact"]["revision"] == 0
    entry = restored["conversation"][-1]
    assert entry["text"] == "TEST_FIXTURE 已保存"
    assert entry["draft_revision_before"] == entry["draft_revision_after"] == 0


def test_a_round_that_only_describes_a_change_is_asked_once_to_actually_write_it(goal_scope, monkeypatch):
    """The traveller's sentence asked for a half-day change; a text-only answer is not one.

    Measured on a real Chrome journey: the Agent replied 「我会在已保存的草稿里把 11/3 下午这一格
    更新为…」 and the draft revision stayed where it was. The server now spends one already-approved
    turn telling the model to apply it, ask one concrete question, or say nothing needed changing.
    """
    session, journey, member = goal_scope
    created = _create(session, journey, member, max_model_turns=8, max_tool_calls=8,
                      online_research_consent=True)

    class SeedDraft:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False
        turn = 0

        def _complete(self, messages):
            self.turn += 1
            if self.turn == 1:
                return {"tool_calls": [{"id": "seed-search", "function": {
                    "name": "discover_places", "arguments": json.dumps({"query": "TEST_FIXTURE 古迹"})}}]}
            if self.turn == 2:
                return {"tool_calls": [{"id": "seed-write", "function": {
                    "name": "save_draft_itinerary", "arguments": json.dumps({"days": [{
                        "date": "2026-11-01", "slots": [{
                            "title": "TEST_FIXTURE 故宫一带", "time_of_day": "morning",
                            "place_id": "photon:node/123", "notes": "待核实"}]}]})}}]}
            return {"content": "TEST_FIXTURE 第一版已保存"}

    def fixture_discovery(_session, _journey, task, **args):
        place = {"id": "photon:node/123", "name": "TEST_FIXTURE 古迹", "source_url": "https://www.openstreetmap.org/node/123"}
        task["research_places"] = [place]
        return {"tool": "discover_places", "status": "RESULTS", "places": [place], "http_status": 200}

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: SeedDraft())
    monkeypatch.setattr(goal_tasks_agent, "discover_goal_places", fixture_discovery)
    goal_tasks_agent.resume_goal_task(session, journey, member, created["task_id"])
    session.expire_all()
    seeded = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])
    assert seeded["draft_artifact"]["revision"] == 1

    calls = []

    class DescribeThenWrite:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False

        def _complete(self, messages):
            calls.append([item["role"] for item in messages])
            if len(calls) == 1:
                return {"content": "TEST_FIXTURE 我会把上午这一格改成天坛一带"}
            if len(calls) == 2:
                assert calls[-1][-1] == "system", "the second turn must be the server's one nudge"
                return {"tool_calls": [{"id": "patch-1", "function": {"name": "replace_draft_slots", "arguments": json.dumps({
                    "date": "2026-11-01", "time_of_day": "morning",
                    "slots": [{"title": "TEST_FIXTURE 天坛一带", "time_of_day": "morning", "notes": "开放时间与票价待查证"}]})}}]}
            return {"content": "TEST_FIXTURE 已把上午这一格换成天坛一带"}

        _tool_allowlist = frozenset()

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: DescribeThenWrite())
    goal_tasks_agent.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="11 月 2 日上午改成天坛一带，其他都别动。", message_id=str(uuid4()),
    )
    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])

    assert len(calls) == 3, "one described change earns exactly one nudge, not a loop"
    assert restored["draft_artifact"]["days"][0]["slots"][0]["title"] == "TEST_FIXTURE 天坛一带"
    entry = restored["conversation"][-1]
    assert entry["draft_revision_before"] == 1
    assert entry["draft_revision_after"] == restored["draft_artifact"]["revision"] == 2
