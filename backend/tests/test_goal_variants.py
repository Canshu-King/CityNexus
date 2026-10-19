"""TEST_FIXTURE alternatives retain source scope and leave the selected draft alone."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.agent.goal_variants import save_draft_variants, variant_definition

@pytest.fixture
def context():
    journey = SimpleNamespace(start_at="2026-11-01T09:00:00+08:00",end_at="2026-11-02T21:00:00+08:00")
    task = {"research_places": [{"id":"amap:fixture-a","provider_provenance":"LIVE_PROVIDER","region_status":"MATCHED"}],
        "draft_artifact":{"revision":5,"days":[{"date":"2026-11-01","slots":[{"title":"TEST_FIXTURE 保留原稿"}]}]},
        "research_routes":[],"candidate_place_ids":[]}
    variants=[{"id":key,"title":"TEST_FIXTURE "+key,"comparison":"TEST_FIXTURE 来源地点比较，票价待查", "days":[
        {"date":"2026-11-01","slots":[{"title":"TEST_FIXTURE 文化地点","time_of_day":"afternoon","place_id":"amap:fixture-a"}]}]}
        for key in ("relaxed","budget","local")]
    return journey,task,variants

def test_variant_save_preserves_main_draft_and_unknowns(context):
    journey,task,variants=context;original=deepcopy(task["draft_artifact"])
    result=save_draft_variants(journey,task,variants)
    assert len(result["variants"])==3 and task["draft_artifact"]==original
    assert result["variants"][0]["source_place_ids"]==["amap:fixture-a"]
    assert result["variants"][0]["artifact"]["days"][0]["slots"][0]["cost_status"]=="UNKNOWN"
    assert result["variants"][0]["unknown_summary"]==["营业时间与票价待查"]

@pytest.mark.parametrize("kind",["foreign","date","duplicate","empty","conflict"])
def test_invalid_variant_does_not_publish_partial_output(context,kind):
    journey,task,variants=context
    if kind=="foreign": variants[1]["days"][0]["slots"][0]["place_id"]="OTHER_OWNER_PLACE"
    if kind=="date": variants[1]["days"][0]["date"]="2029-01-01"
    if kind=="duplicate": variants[1]["id"]="relaxed"
    if kind=="empty": variants[1]["days"][0]["slots"]=[]
    if kind=="conflict": task["research_places"][0]["region_status"]="CONFLICT"
    with pytest.raises(HTTPException):save_draft_variants(journey,task,variants)
    assert "draft_variants" not in task

def test_variant_tool_schema_is_bounded():
    schema=variant_definition()["function"]["parameters"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["variants"]["maxItems"]==3


def test_variant_tool_is_dispatched_and_restored_without_online_permission(goal_scope, monkeypatch):
    import json
    from app.agent import goal_tasks
    from test_goal_tasks import _create
    session,journey,member=goal_scope
    created=_create(session,journey,member,max_model_turns=3)
    mission=session.get(goal_tasks.JourneyMission,created["task_id"])
    intent=json.loads(mission.intent_json)
    intent["goal_task"]["candidate_place_ids"]=["TEST_FIXTURE canonical-place"]
    mission.intent_json=json.dumps(intent);session.commit()
    class Agent:
        provider_key=model_key="TEST_FIXTURE"
        turn=0
        def _complete(self,messages):
            self.turn+=1
            if self.turn>1:return {"content":"TEST_FIXTURE 已保存两个备选"}
            variants=[{"id":key,"title":"TEST_FIXTURE "+key,"comparison":"TEST_FIXTURE 待查费用", "days":[
                {"date":"2026-11-01","slots":[{"title":"TEST_FIXTURE 文化地点","time_of_day":"afternoon","place_id":"TEST_FIXTURE canonical-place"}]}]}
                for key in ("relaxed","local")]
            return {"tool_calls":[{"id":"fixture-variants","function":{"name":"save_draft_variants","arguments":json.dumps({"variants":variants})}}]}
    monkeypatch.setattr(goal_tasks,"_new_goal_agent",lambda *_:Agent())
    goal_tasks.resume_goal_task(session,journey,member,created["task_id"])
    session.expire_all()
    result=goal_tasks.read_goal_task(session,journey,member,created["task_id"])
    assert len(result["draft_variants"])==2
    assert result["tool_steps"][0]["result"]["status"]=="VARIANTS_SAVED"
    assert result["draft_artifact"]["revision"]==0

from test_goal_tasks import goal_scope
