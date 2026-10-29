"""Two draft doors, two names: what a refused save tells the traveller to do next (2026-10-22).

Measured on the live stack first -- see `trial/results/20261022_V3_AGENT_DRAFT_DOOR_RECEIPT.txt`:
both doors answered `409` / `CONFLICT` and differed only inside `error.message`, which the browser
cannot read, because `citynexus.ts` builds `CityNexusApiError.message` as
"CityNexus API <status>: <path>".  The screen therefore showed "the draft version changed" for a save
that was actually refused because the Agent's turn was still running, and named the wrong next step.

These arms pin the reason code the client is meant to read (ORD-0101).  The assistant leg is
TEST_FIXTURE: no provider is called, and the door under test is the product's own.
"""
import pytest
from fastapi import HTTPException

from test_bootstrap_place_facts import enabled_settings, signed_place
from test_goal_tasks import _create, goal_scope
from app.agent import goal_tasks

DRAFT_SLOT = {"title": "TEST_FIXTURE 湖边慢走", "time_of_day": "afternoon", "notes": ""}


def _put_draft(client, owner, root, task_id, expected_revision):
    return client.put(f"{root}/agent/goal-tasks/{task_id}/draft", headers=owner, json={
        "expected_revision": expected_revision,
        "days": [{"date": "2026-11-01", "slots": [DRAFT_SLOT]}]})


def _new_task(client, owner, root):
    created = client.post(f"{root}/agent/goal-tasks", headers=owner, json={
        "goal": "TEST_FIXTURE 下午慢逛", "model_consent": False, "online_research_consent": False})
    assert created.status_code == 201, created.text
    return created.json()["task_id"]


def test_a_stale_revision_is_named_as_the_version_door(signed_place):
    client, owner, _outsider, journey_id, *_ = signed_place
    root = f"/api/v1/journeys/{journey_id}"
    task_id = _new_task(client, owner, root)
    assert _put_draft(client, owner, root, task_id, 0).status_code == 200

    refused = _put_draft(client, owner, root, task_id, 0)
    assert refused.status_code == 409, refused.text
    error = refused.json()["error"]
    assert error["code"] == "CONFLICT"
    assert error["reason_code"] == "DRAFT_CHANGED_RELOAD"


def test_the_prepare_door_names_the_same_reason(signed_place):
    """The version door has a second writer; a screen that reads one name must not need two."""
    client, owner, _outsider, journey_id, *_ = signed_place
    root = f"/api/v1/journeys/{journey_id}"
    task_id = _new_task(client, owner, root)
    assert _put_draft(client, owner, root, task_id, 0).status_code == 200

    refused = client.post(f"{root}/agent/goal-tasks/{task_id}/prepare-plan",
                          headers={**owner, "Idempotency-Key": "fixture-prepare-door"}, json={
                              "expected_revision": 0,
                              "schedule": [{"day_index": 0, "slot_index": 0,
                                            "start_time": "14:00", "end_time": "15:00"}]})
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["reason_code"] == "DRAFT_CHANGED_RELOAD"


def test_a_save_during_a_running_turn_is_named_as_the_running_door(goal_scope, monkeypatch):
    session, journey, member = goal_scope
    created = _create(session, journey, member, max_model_turns=2)
    task_id = created["task_id"]
    seen = {}

    class Agent:
        provider_key = model_key = "TEST_FIXTURE"
        turn = 0

        def _complete(self, messages):
            self.turn += 1
            if self.turn == 1:
                # anti-vacuity: the door can only be reached while this turn really is in flight
                seen["status"] = goal_tasks.read_goal_task(session, journey, member, task_id)["status"]
                with pytest.raises(HTTPException) as caught:
                    goal_tasks.update_goal_draft(session, journey, member, task_id,
                                                 days=[{"date": "2026-11-01", "slots": [DRAFT_SLOT]}],
                                                 expected_revision=0)
                seen["http_status"] = caught.value.status_code
                seen["reason_code"] = getattr(caught.value, "reason_code", None)
                return {"content": "TEST_FIXTURE 这一轮问一句就结束"}
            return {"content": "TEST_FIXTURE 结束"}

    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda *_: Agent())
    goal_tasks.resume_goal_task(session, journey, member, task_id)
    assert seen["status"] == "WORKING"
    assert seen["http_status"] == 409
    assert seen["reason_code"] == "DRAFT_RESEARCH_RUNNING"

    # the same save is accepted once the turn has settled, so the refusal was about the turn
    settled = goal_tasks.read_goal_task(session, journey, member, task_id)
    assert settled["status"] != "WORKING"
    goal_tasks.update_goal_draft(session, journey, member, task_id,
                                 days=[{"date": "2026-11-01", "slots": [DRAFT_SLOT]}],
                                 expected_revision=settled["draft_artifact"]["revision"])
    assert goal_tasks.read_goal_task(session, journey, member, task_id)["draft_artifact"]["revision"] == 1
