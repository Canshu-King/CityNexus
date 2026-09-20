"""ORD-0058 - Simulation Mode has to be a claim a process makes, not a route anyone can hit.

Three things are pinned here, one per door:

* `POST /api/v1/demo/reset` deletes 52 tables and previously needed no flag, env or auth.  With
  the switch off it must answer a named 403 **and delete nothing**, which is why the gate counts
  rows rather than trusting the status code;
* `GET /api/v1/demo/scene` is the one read that was missing: a client that wants a banner or a
  Today header had to call `new Date()` and so invented a second clock.  The gate asserts the
  reported moment is the seeded scenario's, not this machine's;
* the flagged `projection_now` inference is settled by measurement - a `?now=` without an offset
  used to reach a naive-vs-aware comparison, i.e. a 500 for a query-string detail, and now gets a
  named 422 while the offset-aware form keeps working (the control half of that gate).

The seed frozen-evidence TTL alignment is deliberately not covered by this file: it ships as its
own slice with the two regression sets the order names, because guessing there would weaken a
fail-closed gate on the frozen list.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.models import Activity, Journey, PlanVersion, Traveler
from app.db.session import SessionLocal
from app.main import app, demo_mode_enabled

client = TestClient(app)
TABLES = ("travelers", "journeys", "plan_versions", "activities")


def _counts() -> dict[str, int]:
    with SessionLocal() as session:
        return {
            "travelers": session.scalar(select(func.count(Traveler.id))) or 0,
            "journeys": session.scalar(select(func.count(Journey.id))) or 0,
            "plan_versions": session.scalar(select(func.count(PlanVersion.id))) or 0,
            "activities": session.scalar(select(func.count(Activity.id))) or 0,
        }


@pytest.fixture()
def _stage_on(monkeypatch) -> None:
    monkeypatch.setattr("app.main.demo_mode_enabled", lambda: True)
    assert client.post("/api/v1/demo/reset").status_code == 200


def _scene() -> dict:
    response = client.get("/api/v1/demo/scene")
    assert response.status_code == 200, response.text
    return response.json()


def _journey_in_scene() -> Journey:
    """Load the journey the scene itself named, so the gate cannot drift from the route."""

    scene = _scene()
    assert scene["journey_id"], scene
    with SessionLocal() as session:
        row = session.get(Journey, scene["journey_id"])
    assert row is not None, scene
    return row


def test_the_reset_route_is_closed_without_the_switch_and_deletes_nothing(monkeypatch) -> None:
    """The refusal has to be proven by the rows, not by the status code.

    A 403 that fires *after* `reset_all` would look identical to a good guard and still cost
    every traveller in the library.
    """

    monkeypatch.setattr("app.main.demo_mode_enabled", lambda: False)
    before = _counts()
    assert before["journeys"] > 0, "needs a populated library so deletion would be observable"
    response = client.post("/api/v1/demo/reset")
    assert response.status_code == 403, response.text
    body = response.json()["error"]
    assert body["code"] == "DEMO_MODE_REQUIRED", body
    assert body["message_key"] == "demo.reset_disabled", body
    assert body["details"]["flag"] == "CITYNEXUS_DEMO_MODE", body["details"]
    assert body["details"]["tables_protected"] is True, body["details"]
    assert _counts() == before, "a refused reset must not have touched a single row"


def test_the_same_call_is_allowed_once_the_process_claims_the_stage(_stage_on) -> None:
    """The guard discriminates on the flag and on nothing else."""

    response = client.post("/api/v1/demo/reset")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "reset"
    assert UUID(payload["traveler_id"]), payload
    assert _counts()["journeys"] > 0


def test_the_scene_read_reports_the_scenario_clock_and_not_this_machine(_stage_on) -> None:
    """`effective_now` must be the journey's own moment.

    If it ever becomes `Date.now()` on the server, the banner and Today header agree with the
    device instead of the scene, which is the disagreement this read exists to remove.
    """

    journey = _journey_in_scene()
    scene = _scene()
    assert scene["demo_mode"] is True, scene
    assert scene["journey_status"] == journey.status, (scene["journey_status"], journey.status)
    assert scene["journey_id"] == journey.id, (scene["journey_id"], journey.id)
    assert scene["basis"] in {"CURSOR", "JOURNEY_START"}, scene
    moment = datetime.fromisoformat(str(scene["effective_now"]))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    drift = abs((datetime.now(timezone.utc) - moment).total_seconds())
    assert drift > 86_400, f"the scene clock is within a day of wall time: {drift}s"
    assert scene["scene_start_at"] <= scene["scene_end_at"], scene
    assert scene["evidence_state"] in {"REFERENCED", "NO_FROZEN_EVIDENCE"}, scene


def test_the_scene_clock_moves_with_the_scenario_and_never_with_the_device(_stage_on) -> None:
    """Change the journey's window and the reported moment moves; wall time cannot make it move.

    The contract this read exists to provide: the scenario's clock is the answer.  A client
    that called `new Date()` would keep disagreeing with the seeded day no matter what the
    journey said, and the banner would look right while the plan underneath was elsewhere.
    """

    before = _scene()
    assert before["basis"] in {"CURSOR", "JOURNEY_START"}, before
    journey = _journey_in_scene()
    shifted = "2027-03-04T09:00:00+08:00"
    with SessionLocal() as session:
        row = session.get(Journey, journey.id)
        row.start_at = shifted
        row.end_at = "2027-03-06T18:00:00+08:00"
        session.commit()
    after = _scene()
    if after["basis"] == "JOURNEY_START":
        assert after["effective_now"] == shifted, after
    assert after["scene_start_at"] == shifted, after
    assert after["effective_now"] != before["effective_now"], (before, after)
    assert after["effective_now"] != datetime.now(timezone.utc).isoformat(), after


def test_a_naive_projection_instant_is_refused_by_name_instead_of_500(_stage_on) -> None:
    """The order's "measure it before you rely on it" item, plus its control half."""

    journey = _journey_in_scene()
    naive = client.get(f"/api/v1/journeys/{journey.id}/twin?now=2026-10-01T09:00")
    assert naive.status_code != 500, naive.text[:300]
    assert naive.status_code == 422, naive.text[:300]
    body = naive.json()["error"]
    assert body["code"] == "TWIN_NOW_OFFSET_REQUIRED", body
    assert body["message_key"] == "twin.now_offset_required", body
    assert body["details"]["offset_required"] is True, body["details"]
    aware = client.get(f"/api/v1/journeys/{journey.id}/twin?now=2026-10-01T09:00:00%2B08:00")
    assert aware.status_code == 200, aware.text[:300]
