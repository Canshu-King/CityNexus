"""Signed DRAFT GoalTask route contract; all trip data is TEST_FIXTURE."""

from uuid import uuid4

from test_bootstrap_place_facts import enabled_settings, signed_place


def test_signed_goal_task_create_restore_events_and_cancel(signed_place):
    client, owner_headers, outsider_headers, journey_id, *_ = signed_place
    base = f"/api/v1/journeys/{journey_id}/agent/goal-tasks"
    body = {
        "goal": "TEST_FIXTURE 两日行程：少走路，下午开始，兼顾古迹与本地饮食",
        "model_consent": True,
        "online_research_consent": True,
        "max_model_turns": 4,
        "max_tool_calls": 8,
    }

    assert client.post(base, json=body).status_code == 401
    created = client.post(base, headers=owner_headers, json=body)
    assert created.status_code == 201, created.text
    assert "no-store" in created.headers["cache-control"]
    task_id = created.json()["task_id"]
    assert created.json()["mode"] == "GOAL_PLANNING"
    assert created.json()["status"] == "ACCEPTED"
    assert created.json()["latest_run_id"] is None

    task_url = f"{base}/{task_id}"
    restored = client.get(task_url, headers=owner_headers)
    assert restored.status_code == 200, restored.text
    assert restored.json()["goal"] == body["goal"]
    assert restored.json()["status"] == "ACCEPTED"
    assert "no-store" in restored.headers["cache-control"]
    assert client.get(task_url, headers=outsider_headers).status_code == 403
    assert client.get(f"{base}/{uuid4()}", headers=owner_headers).status_code == 404

    events = client.get(f"{task_url}/events", headers=owner_headers)
    assert events.status_code == 200, events.text
    assert [event["event_type"] for event in events.json()["events"]] == ["TASK_ACCEPTED"]

    draft = restored.json()["draft_artifact"]
    draft["days"][0]["slots"] = [{"title": "TEST_FIXTURE 下午逛古城", "time_of_day": "afternoon", "notes": "待查路线"}]
    edit = {"expected_revision": draft["revision"], "days": draft["days"]}
    assert client.put(f"{task_url}/draft", headers=outsider_headers, json=edit).status_code == 403
    saved = client.put(f"{task_url}/draft", headers=owner_headers, json=edit)
    assert saved.status_code == 200, saved.text
    assert saved.json()["draft_artifact"]["days"][0]["slots"][0]["cost_status"] == "UNKNOWN"
    assert client.get(task_url, headers=owner_headers).json()["draft_artifact"]["revision"] == 1
    assert client.put(f"{task_url}/draft", headers=owner_headers, json=edit).status_code == 409

    cancelled = client.post(f"{task_url}/cancel", headers=owner_headers)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED"
    assert client.post(f"{task_url}/resume", headers=owner_headers, json={}).status_code == 409



def test_signed_same_task_chat_works_without_new_journey_and_hides_message_from_audit(signed_place):
    client, owner_headers, outsider_headers, journey_id, *_ = signed_place
    base = f"/api/v1/journeys/{journey_id}/agent/goal-tasks"
    created = client.post(base, headers=owner_headers, json={
        "goal": "TEST_FIXTURE 两日轻松旅行",
        "model_consent": False,
        "online_research_consent": False,
        "max_model_turns": 4,
        "max_tool_calls": 8,
    })
    assert created.status_code == 201, created.text
    task_id = created.json()["task_id"]
    message_id = str(uuid4())
    request = {"user_message": "TEST_FIXTURE 修改下午的景点，少走路", "message_id": message_id}
    assert client.post(f"{base}/{task_id}/resume", json=request).status_code == 401
    assert client.post(f"{base}/{task_id}/resume", headers=outsider_headers, json=request).status_code == 403
    sent = client.post(f"{base}/{task_id}/resume", headers=owner_headers, json=request)
    assert sent.status_code == 200, sent.text
    assert sent.json()["task_id"] == task_id
    assert sent.json()["status"] == "NEEDS_DECISION"
    assert sent.json()["conversation"][-1]["text"] == request["user_message"]
    assert sent.json()["conversation"][-1]["role"] == "user"
    assert client.post(f"{base}/{task_id}/resume", headers=owner_headers, json=request).status_code == 200
    restored = client.get(f"{base}/{task_id}", headers=owner_headers).json()
    assert len(restored["conversation"]) == 2
    assert restored["conversation"][1]["message_id"] == message_id
    events = client.get(f"{base}/{task_id}/events", headers=owner_headers).json()["events"]
    assert sum(item["event_type"] == "USER_MESSAGE_ADDED" for item in events) == 1
    assert request["user_message"] not in str(events)
