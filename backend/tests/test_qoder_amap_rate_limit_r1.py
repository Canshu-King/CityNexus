"""The freeze asks a rate-limited hop once more, and asks a quota-limited hop not at all.

Why this is worth a test: the provider refuses the fourth, fifth and sixth of a burst with infocode 10021
CUQPS_HAS_EXCEEDED_THE_LIMIT and answers the same hop a second later (measured in
trial/results/20261022_v3_human_chrome/amap-burst-infocode-2.txt:2 against :3).  Before this change that
momentary refusal reached the traveller as 「地图服务今天的查询次数已经用完」 and the hop stayed unmeasured,
which is what held a plan at 4/5 frozen.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.agent import goal_route_freeze
from app.db.models import Place

_OK = {"status": "ROUTE_READY", "reason_code": None, "provider_call_id": "call-walk-1",
       "route": {"distance_m": 1400, "duration_seconds": 1200}}
_RATE = {"status": "PROVIDER_UNAVAILABLE", "reason_code": "AMAP_RATE_LIMITED", "route": None}
_QUOTA = {"status": "PROVIDER_UNAVAILABLE", "reason_code": "AMAP_QUOTA_EXCEEDED", "route": None}


class _Client:
    def __init__(self, answers):
        self._answers = list(answers)
        self.asks = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def walking(self, start, end):
        self.asks += 1
        return self._answers.pop(0) if self._answers else dict(_QUOTA)

    def transit(self, start, end, city_code, date=None, time=None):  # pragma: no cover - must not be reached
        raise AssertionError("the transport door must not be asked about an access refusal")


class _Session:
    def add(self, *args, **kwargs):
        raise AssertionError("the receipt writer is stubbed in these tests")


def _places():
    return (Place(id="p-from", name="景山公园", latitude=39.926, longitude=116.396),
            Place(id="p-to", name="南锣鼓巷", latitude=39.937, longitude=116.403))


@pytest.fixture
def _no_sleep(monkeypatch):
    monkeypatch.setattr(goal_route_freeze.time, "sleep", lambda seconds: None)


def _run(monkeypatch, answers):
    client = _Client(answers)
    monkeypatch.setattr(goal_route_freeze, "_client", lambda: client)
    monkeypatch.setattr(goal_route_freeze, "_receipt",
                        lambda session, operation, arguments, result: dict(result))
    monkeypatch.setattr(goal_route_freeze, "settings", SimpleNamespace(amap_web_key="stub-key-never-used"))
    origin, destination = _places()
    task = {"public_queries": [], "route_refusals": {}, "research_routes": []}
    arrival = datetime(2026, 12, 5, 3, 0, tzinfo=timezone.utc)
    return task, client, goal_route_freeze._measure_now(_Session(), task, origin, destination, arrival)


def test_a_rate_limited_hop_is_asked_again_and_freezes_when_the_second_answer_arrives(monkeypatch, _no_sleep):
    task, client, row = _run(monkeypatch, [dict(_RATE), dict(_OK)])
    assert client.asks == 2, "the momentary refusal should be asked once more"
    assert row is not None and row["mode"] == "WALK", row
    assert task["route_refusals"] == {}, task["route_refusals"]


def test_a_hop_still_refused_after_the_pause_is_reported_as_refused_and_not_reached_a_third_time(monkeypatch, _no_sleep):
    task, client, row = _run(monkeypatch, [dict(_RATE), dict(_RATE)])
    assert client.asks == 2, "one repeat, never a loop"
    assert row is None
    assert [entry for entry in task["route_refusals"].values()] == ["AMAP_RATE_LIMITED"]


def test_a_daily_quota_refusal_is_not_asked_again_and_does_not_open_the_transport_door(monkeypatch, _no_sleep):
    task, client, row = _run(monkeypatch, [dict(_QUOTA)])
    assert client.asks == 1, "a spent allowance is not recovered by repeating the question"
    assert row is None
    assert list(task["route_refusals"].values()) == ["AMAP_QUOTA_EXCEEDED"]
