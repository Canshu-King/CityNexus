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


def test_the_round_that_saved_the_draft_reports_it_even_when_it_ends_on_a_question(goal_scope, monkeypatch):
    """A question that closes a saving round must not read as "nothing happened".

    Measured on a real Chrome journey: the research round saved six arrangements (revision 0 to 1)
    and ended by asking which ancient site to prefer. The screen said 「这条回复没有改动日程（版本 1）」
    right next to a schedule that had just appeared, because the question stamped both halves of the
    receipt with the revision of the moment it was written.
    """
    session, journey, member = goal_scope
    created = _create(session, journey, member, max_model_turns=8, max_tool_calls=8,
                      online_research_consent=True)

    class WriteThenAsk:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False
        turn = 0

        def _complete(self, messages):
            self.turn += 1
            if self.turn == 1:
                return {"tool_calls": [{"id": "q-search", "function": {
                    "name": "discover_places", "arguments": json.dumps({"query": "TEST_FIXTURE 古迹"})}}]}
            if self.turn == 2:
                return {"tool_calls": [{"id": "q-write", "function": {
                    "name": "save_draft_itinerary", "arguments": json.dumps({"days": [{
                        "date": "2026-11-01", "slots": [{
                            "title": "TEST_FIXTURE 故宫一带", "time_of_day": "morning",
                            "place_id": "photon:node/123", "notes": "待核实"}]}]})}}]}
            return {"tool_calls": [{"id": "q-ask", "function": {"name": "ask_traveler", "arguments": json.dumps({
                "question": "TEST_FIXTURE 第一天上午的主古迹你想优先哪个方向？\"}]",
                "options": [{"label": "天坛\"", "description": "园林式、较省力"},
                            {"label": "颐和园", "description": "湖园结合，稍远"}]})}}]}

    def fixture_discovery(_session, _journey, task, **args):
        place = {"id": "photon:node/123", "name": "TEST_FIXTURE 古迹", "source_url": "https://www.openstreetmap.org/node/123"}
        task["research_places"] = [place]
        return {"tool": "discover_places", "status": "RESULTS", "places": [place], "http_status": 200}

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: WriteThenAsk())
    monkeypatch.setattr(goal_tasks_agent, "discover_goal_places", fixture_discovery)
    goal_tasks_agent.resume_goal_task(session, journey, member, created["task_id"])
    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])

    assert restored["draft_artifact"]["revision"] == 1
    entry = restored["conversation"][-1]
    assert entry["draft_revision_before"] == 0
    assert entry["draft_revision_after"] == 1
    # The envelope punctuation the walk measured is gone, and the traveller's own sentence shape stays.
    assert entry["text"] == "TEST_FIXTURE 第一天上午的主古迹你想优先哪个方向？"
    assert restored["pending_question"]["options"][0]["label"] == "天坛"


def test_a_traveller_sentence_keeps_its_own_punctuation_and_loses_the_envelope():
    """The residue rule is narrow on purpose: ASCII envelope characters at the very end, nothing else."""
    from app.agent.goal_dialogue import plain_traveller_text

    assert plain_traveller_text("第二天下午想在哪片水域散步？\"}]") == "第二天下午想在哪片水域散步？"
    assert plain_traveller_text("第一天上午的主古迹你想优先哪个方向？（这决定小吃片区）\"") == (
        "第一天上午的主古迹你想优先哪个方向？（这决定小吃片区）")
    # Ordinary copy a traveller or a model would really write is left alone, every character of it.
    for kept in ("已把 Day1 上午改为天坛一带。", "预算 ¥500/人", "要不要早上八点出发", "什刹海（后海）"):
        assert plain_traveller_text(kept) == kept
    assert plain_traveller_text(None) == ""


def test_a_question_that_reports_a_change_that_never_happened_is_sent_back_once(goal_scope, monkeypatch):
    """The shape the real walk produced: a tool call, not a sentence, so the text-only nudge missed it.

    Measured on a real Edge journey: the traveller wrote 「11 月 3 日下午…改成什刹海边一家咖啡馆坐着，
    其他安排都别动」 and the Agent ended the round with ask_traveler whose own text read
    「收到，按你说的改：…其余安排原封不动」 while the draft stayed at revision 1. A round that reports
    finished work must either do that work or say plainly that nothing changed yet.
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
                return {"tool_calls": [{"id": "c-search", "function": {
                    "name": "discover_places", "arguments": json.dumps({"query": "TEST_FIXTURE 古迹"})}}]}
            if self.turn == 2:
                return {"tool_calls": [{"id": "c-write", "function": {
                    "name": "save_draft_itinerary", "arguments": json.dumps({"days": [{
                        "date": "2026-11-01", "slots": [{
                            "title": "TEST_FIXTURE 湖边散步", "time_of_day": "afternoon",
                            "place_id": "photon:node/123", "notes": "待核实"}]}]})}}]}
            return {"content": "TEST_FIXTURE 草稿已存"}

    def fixture_discovery(_session, _journey, task, **args):
        place = {"id": "photon:node/123", "name": "TEST_FIXTURE 古迹", "source_url": "https://www.openstreetmap.org/node/123"}
        task["research_places"] = [place]
        return {"tool": "discover_places", "status": "RESULTS", "places": [place], "http_status": 200}

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: SeedDraft())
    monkeypatch.setattr(goal_tasks_agent, "discover_goal_places", fixture_discovery)
    goal_tasks_agent.resume_goal_task(session, journey, member, created["task_id"])

    seen = []

    def question_args(**extra):
        return json.dumps({"question": extra.get("question"), "options": [
            {"label": "A", "description": "甲"}, {"label": "B", "description": "乙"}]})

    class ClaimThenWrite:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False

        def _complete(self, messages):
            seen.append([item["role"] for item in messages])
            if len(seen) == 1:
                return {"tool_calls": [{"id": "c-claim", "function": {"name": "ask_traveler", "arguments": question_args(
                    question="TEST_FIXTURE 收到，按你说的改：下午从湖边散步换成咖啡馆坐着，其余安排原封不动。要哪家咖啡馆？")}}]}
            if len(seen) == 2:
                assert seen[-1][-1] == "system", "the claiming question must be sent back once"
                return {"tool_calls": [{"id": "c-patch", "function": {"name": "replace_draft_slots", "arguments": json.dumps({
                    "date": "2026-11-01", "time_of_day": "afternoon",
                    "slots": [{"title": "TEST_FIXTURE 什刹海边咖啡馆坐着", "time_of_day": "afternoon", "notes": "店名待定"}]})}}]}
            return {"tool_calls": [{"id": "c-ask", "function": {"name": "ask_traveler", "arguments": question_args(
                question="TEST_FIXTURE 下午这一格已经换成咖啡馆坐着，还没有改动别的。你想靠窗还是院子里？")}}]}

        _tool_allowlist = frozenset()

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: ClaimThenWrite())
    goal_tasks_agent.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="11 月 3 日下午不去湖边走路了，改成什刹海边一家咖啡馆坐着，其他安排都别动。",
        message_id=str(uuid4()),
    )
    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])

    assert len(seen) == 3, "one claiming question earns one send-back, not a loop"
    slot = restored["draft_artifact"]["days"][0]["slots"][0]
    assert slot["title"] == "TEST_FIXTURE 什刹海边咖啡馆坐着"
    assert restored["draft_artifact"]["revision"] == 2
    # The question the traveller is left with reports the truth: the change is now actually saved.
    assert restored["pending_question"]["question"].startswith("TEST_FIXTURE 下午这一格已经换成咖啡馆坐着")


def test_a_round_that_changes_the_subject_is_sent_back_to_the_requested_edit(goal_scope, monkeypatch):
    """The second measured shape: a question that claims nothing and simply drops the request.

    Same sentence twice on two browsers: 「11 月 3 日下午…改成什刹海边一家咖啡馆坐着，其他安排都别动」
    and the Agent answered with a comparison of morning monuments. Nothing was claimed, so the wording
    check could not see it; the traveller's own request is what says a half-day was meant to move.
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
                return {"tool_calls": [{"id": "s-search", "function": {
                    "name": "discover_places", "arguments": json.dumps({"query": "TEST_FIXTURE 古迹"})}}]}
            if self.turn == 2:
                return {"tool_calls": [{"id": "s-write", "function": {
                    "name": "save_draft_itinerary", "arguments": json.dumps({"days": [{
                        "date": "2026-11-01", "slots": [
                            {"title": "TEST_FIXTURE 湖边散步", "time_of_day": "afternoon",
                             "place_id": "photon:node/123", "notes": "待核实"},
                            {"title": "TEST_FIXTURE 故宫一带", "time_of_day": "morning",
                             "notes": "地点待核实"}]}]})}}]}
            return {"content": "TEST_FIXTURE 草稿已存"}

    def fixture_discovery(_session, _journey, task, **args):
        place = {"id": "photon:node/123", "name": "TEST_FIXTURE 古迹", "source_url": "https://www.openstreetmap.org/node/123"}
        task["research_places"] = [place]
        return {"tool": "discover_places", "status": "RESULTS", "places": [place], "http_status": 200}

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: SeedDraft())
    monkeypatch.setattr(goal_tasks_agent, "discover_goal_places", fixture_discovery)
    goal_tasks_agent.resume_goal_task(session, journey, member, created["task_id"])

    turns = []

    class DeflectThenApply:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False

        def _complete(self, messages):
            turns.append(messages[-1]["role"])
            if len(turns) == 1:
                return {"tool_calls": [{"id": "s-deflect", "function": {"name": "ask_traveler", "arguments": json.dumps({
                    "question": "TEST_FIXTURE 上午的古迹你想看哪个方向？",
                    "options": [{"label": "故宫", "description": "体量大"}, {"label": "天坛", "description": "园林式"}]})}}]}
            if len(turns) == 2:
                assert turns[-1] == "system", "a dropped request is put back in front of the Agent once"
                return {"tool_calls": [{"id": "s-apply", "function": {"name": "replace_draft_slots", "arguments": json.dumps({
                    "date": "2026-11-01", "time_of_day": "afternoon",
                    "slots": [{"title": "TEST_FIXTURE 什刹海边咖啡馆坐着", "time_of_day": "afternoon", "notes": "店名待定"}]})}}]}
            return {"content": "TEST_FIXTURE 下午这一格已换成咖啡馆坐着，上午没有动。"}

        _tool_allowlist = frozenset()

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: DeflectThenApply())
    goal_tasks_agent.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="11 月 3 日下午不去湖边走路了，改成什刹海边一家咖啡馆坐着，其他安排都别动。",
        message_id=str(uuid4()),
    )
    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])

    assert len(turns) == 3
    titles = {slot["title"] for day in restored["draft_artifact"]["days"] for slot in day["slots"]}
    assert "TEST_FIXTURE 什刹海边咖啡馆坐着" in titles
    assert "TEST_FIXTURE 故宫一带" in titles, "the unrelated half-day must survive the edit"
    assert restored["draft_artifact"]["revision"] == 2
    assert restored["conversation"][-1]["draft_revision_before"] == 1

def test_a_plain_question_without_a_claim_is_left_alone(goal_scope, monkeypatch):
    """The send-back must not fire on a round that only asks, or every first reply costs a turn."""
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
                return {"tool_calls": [{"id": "n-search", "function": {
                    "name": "discover_places", "arguments": json.dumps({"query": "TEST_FIXTURE 古迹"})}}]}
            if self.turn == 2:
                return {"tool_calls": [{"id": "n-write", "function": {
                    "name": "save_draft_itinerary", "arguments": json.dumps({"days": [{
                        "date": "2026-11-01", "slots": [{
                            "title": "TEST_FIXTURE 故宫一带", "time_of_day": "morning",
                            "place_id": "photon:node/123", "notes": "待核实"}]}]})}}]}
            return {"content": "TEST_FIXTURE 草稿已存"}

    def fixture_discovery(_session, _journey, task, **args):
        place = {"id": "photon:node/123", "name": "TEST_FIXTURE 古迹", "source_url": "https://www.openstreetmap.org/node/123"}
        task["research_places"] = [place]
        return {"tool": "discover_places", "status": "RESULTS", "places": [place], "http_status": 200}

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: SeedDraft())
    monkeypatch.setattr(goal_tasks_agent, "discover_goal_places", fixture_discovery)
    goal_tasks_agent.resume_goal_task(session, journey, member, created["task_id"])

    calls = []

    class AskOnly:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False

        def _complete(self, messages):
            calls.append(len(messages))
            return {"tool_calls": [{"id": "n-ask", "function": {"name": "ask_traveler", "arguments": json.dumps({
                "question": "TEST_FIXTURE 第二天上午想去人少的园子还是寺院？",
                "options": [{"label": "天坛", "description": "露天，步行多"}, {"label": "雍和宫", "description": "殿宇，院子紧凑"}]})}}]}

        _tool_allowlist = frozenset()

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: AskOnly())
    goal_tasks_agent.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="第二天上午有什么推荐？", message_id=str(uuid4()),
    )
    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])

    assert len(calls) == 1, "a question that claims nothing is the traveller's to answer right away"
    assert restored["status"] == "NEEDS_DECISION"
    assert restored["pending_question"]["question"] == "TEST_FIXTURE 第二天上午想去人少的园子还是寺院？"
    assert restored["draft_artifact"]["revision"] == 1



def _seed_two_slot_draft(goal_scope, monkeypatch, goal_tasks_agent):
    """Put a saved draft on the task so the follow-up rounds have something to edit."""
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
                return {"tool_calls": [{"id": "m-search", "function": {
                    "name": "discover_places", "arguments": json.dumps({"query": "TEST_FIXTURE 古迹"})}}]}
            if self.turn == 2:
                return {"tool_calls": [{"id": "m-write", "function": {
                    "name": "save_draft_itinerary", "arguments": json.dumps({"days": [{
                        "date": "2026-11-01", "slots": [
                            {"title": "TEST_FIXTURE 湖边散步", "time_of_day": "afternoon",
                             "place_id": "photon:node/123", "notes": "待核实"},
                            {"title": "TEST_FIXTURE 故宫一带", "time_of_day": "morning",
                             "notes": "地点待核实"}]}]})}}]}
            return {"content": "TEST_FIXTURE 草稿已存"}

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
    return session, journey, member, created


class TextOnly:
    provider_key = model_key = "TEST_FIXTURE"
    _owns_client = False

    def _complete(self, messages):
        return {"content": "TEST_FIXTURE 好"}

    _tool_allowlist = frozenset()


def test_a_typed_edit_request_is_not_left_in_discussion_mode(goal_scope, monkeypatch):
    """The chat dock labels every typed follow-up DISCUSS, and discussion may not touch the schedule.

    Measured on a real Edge journey: the traveller wrote 「11 月 3 日下午…改成什刹海边一家咖啡馆坐着，
    其他安排都别动」 and the Agent answered 「已按你最新要求调整…」 in 20 seconds. The stored round was
    still interaction_mode=DISCUSS, whose own instruction says do not change or save an itinerary -- so
    the only thing left for the model to do was to say it.
    """
    session, journey, member, created = _seed_two_slot_draft(goal_scope, monkeypatch, goal_tasks_agent)
    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: TextOnly())
    goal_tasks_agent.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="11 月 3 日下午不去湖边走路了，改成什刹海边一家咖啡馆坐着，其他安排都别动。",
        message_id=str(uuid4()), interaction_mode="DISCUSS",
    )
    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])
    assert restored["interaction_mode"] == "RESEARCH"


def test_a_typed_question_about_the_trip_stays_a_discussion(goal_scope, monkeypatch):
    """The flip must follow the instruction, not any sentence that happens to mention a day."""
    session, journey, member, created = _seed_two_slot_draft(goal_scope, monkeypatch, goal_tasks_agent)
    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: TextOnly())
    goal_tasks_agent.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="第二天下午一般几点天黑？", message_id=str(uuid4()), interaction_mode="DISCUSS",
    )
    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])
    assert restored["interaction_mode"] == "DISCUSS"


def test_versions_asked_for_in_words_are_put_back_until_they_exist(goal_scope, monkeypatch):
    """The comparison screen only exists when the task holds versions, not when prose lists them.

    Measured twice: 「按轻松少走、省钱、本地特色三种想法各出一版，让我三选一」 came back as three
    paragraphs and the on-screen counts for the variant tabs and cards stayed at zero -- because a
    typed message ran as a discussion round, where the version tool is not even offered, and the
    round was then allowed to end with words.
    """
    session, journey, member = goal_scope
    created = _create(session, journey, member, max_model_turns=8, max_tool_calls=8,
                      online_research_consent=True)

    def fixture_discovery(_session, _journey, task, **args):
        place = {"id": "photon:node/123", "name": "TEST_FIXTURE 古迹", "source_url": "https://www.openstreetmap.org/node/123"}
        task["research_places"] = [place]
        task["candidate_place_ids"] = ["photon:node/123"]
        return {"tool": "discover_places", "status": "RESULTS", "places": [place], "http_status": 200}

    class SeedDraft:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False
        turn = 0

        def _complete(self, messages):
            self.turn += 1
            if self.turn == 1:
                return {"tool_calls": [{"id": "v-search", "function": {
                    "name": "discover_places", "arguments": json.dumps({"query": "TEST_FIXTURE 古迹"})}}]}
            if self.turn == 2:
                return {"tool_calls": [{"id": "v-write", "function": {
                    "name": "save_draft_itinerary", "arguments": json.dumps({"days": [{
                        "date": "2026-11-01", "slots": [{
                            "title": "TEST_FIXTURE 古迹半天", "time_of_day": "morning",
                            "place_id": "photon:node/123", "notes": "待核实"}]}]})}}]}
            return {"content": "TEST_FIXTURE 草稿已存"}

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: SeedDraft())
    monkeypatch.setattr(goal_tasks_agent, "discover_goal_places", fixture_discovery)
    goal_tasks_agent.resume_goal_task(session, journey, member, created["task_id"])

    rounds = []

    def variant_arguments() -> str:
        day = [{"date": "2026-11-01", "slots": [{
            "title": "TEST_FIXTURE 古迹半天", "time_of_day": "morning",
            "place_id": "photon:node/123", "notes": "待核实"}]}]
        # Only the three ids the tool itself declares (relaxed / budget / local) can be published;
        # a free-letter id is refused, and a refused call is exactly what used to leave the screen empty.
        return json.dumps({"variants": [
            {"id": "relaxed", "title": "TEST_FIXTURE 轻松少走", "comparison": "少走路，半天一个点", "days": day},
            {"id": "budget", "title": "TEST_FIXTURE 省钱", "comparison": "只买大门票", "days": day}]})

    class ProseThenVariants:
        provider_key = model_key = "TEST_FIXTURE"
        _owns_client = False

        def _complete(self, messages):
            rounds.append(messages[-1]["role"])
            if len(rounds) == 1:
                return {"content": "TEST_FIXTURE 轻松少走版……；省钱版……（三选一）"}
            if len(rounds) == 2:
                assert rounds[-1] == "system", "a prose answer to a request for versions is put back once"
                return {"tool_calls": [{"id": "v-variants", "function": {
                    "name": "save_draft_variants", "arguments": variant_arguments()}}]}
            return {"content": "TEST_FIXTURE 两版都存好了，你想选哪一版？"}

        _tool_allowlist = frozenset()

    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: ProseThenVariants())
    goal_tasks_agent.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="按轻松少走、省钱、本地特色三种想法各出一版，让我三选一。",
        message_id=str(uuid4()), interaction_mode="RESEARCH",
    )
    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])

    assert len(rounds) == 3
    step = [item for item in restored["tool_steps"] if item["tool_name"] == "save_draft_variants"]
    assert len(step) == 1 and step[0]["status"] == "COMPLETED", step
    assert step[0]["result"]["status"] == "VARIANTS_SAVED", step[0]["result"]
    assert [item["title"] for item in restored["draft_variants"]] == ["TEST_FIXTURE 轻松少走", "TEST_FIXTURE 省钱"]
    assert [item["id"] for item in restored["draft_variants"]] == ["relaxed", "budget"]
    assert restored["draft_variants"][0]["unknown_summary"], "an unpublished price stays an unknown"


def test_a_versions_request_is_not_left_in_discussion_mode(goal_scope, monkeypatch):
    """Discussion mode does not even offer save_draft_variants, so the request must not stay there."""
    session, journey, member, created = _seed_two_slot_draft(goal_scope, monkeypatch, goal_tasks_agent)
    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: TextOnly())
    goal_tasks_agent.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="按轻松少走和省钱两种想法各出一版，让我三选一。",
        message_id=str(uuid4()), interaction_mode="DISCUSS",
    )
    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])
    assert restored["interaction_mode"] == "RESEARCH"


def test_a_blank_trip_keeps_researching_when_the_dock_sends_a_plain_followup(goal_scope, monkeypatch):
    """A blank trip has nothing to discuss, so a typed follow-up must not collapse the tool set.

    Measured on the 430 walk: after 「不选了，直接按现在的方向开始研究」 the next typed message carried
    the chat dock's default DISCUSS, the stored mode went back to DISCUSS, and the model's
    discover_places call answered TOOL_NOT_ALLOWED -- research_places stayed empty and the draft had no
    slots, so the trip could never reach a candidate. Only a draft that already has slots may fall back
    to discussion for a plain question (test_a_typed_question_about_the_trip_stays_a_discussion).
    """
    session, journey, member = goal_scope
    created = _create(session, journey, member, max_model_turns=8, max_tool_calls=8,
                      online_research_consent=True)
    monkeypatch.setattr(goal_tasks_agent, "_new_goal_agent", lambda *_: TextOnly())
    goal_tasks_agent.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="按已经定下的方向开始研究，不用再问我", message_id=str(uuid4()),
        interaction_mode="RESEARCH",
    )
    goal_tasks_agent.resume_goal_task(
        session, journey, member, created["task_id"],
        user_message="再补一个故宫附近的咖啡店", message_id=str(uuid4()), interaction_mode="DISCUSS",
    )
    session.expire_all()
    restored = goal_tasks_agent.read_goal_task(session, journey, member, created["task_id"])
    assert restored["interaction_mode"] == "RESEARCH"
