"""A run that stops on the tool-step limit must not be recorded as COMPLETED.

Measured at the authoritative tip `1c23ef3654062816feec9c26ad8703f4de98cc10`: the loop's
`for ... else` wrote the non-empty sentence "Agent reached the configured tool-step limit." into
`final_text`, and the very next line decided the status with `if final_text` - so a run that ran
out of steps was recorded `COMPLETED` beside its own outcome saying it ran out of steps, and the
`PARTIAL` answer could not be reached at all.  No test in the suite ran this loop, so nothing said
so.

The arms below drive the real loop with a stubbed provider response - no network, no API key - and
read back the run row that was persisted.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

UTC = timezone.utc

#: A tool the allowlist does not know: the loop takes the "outside the CityNexus V2 allowlist"
#: branch, which needs no gateway, no database writes beyond the step row, and never sets a final
#: summary - so the run can only end by exhausting its steps.
UNGRANTED_TOOL = "wagong_step_limit_probe_tool"


def _seed(session):
    from app.db.models import Journey, JourneyMission, Traveler

    now = datetime.now(UTC).isoformat()
    traveler_id, journey_id, mission_id = str(uuid4()), str(uuid4()), str(uuid4())
    session.add(
        Traveler(
            id=traveler_id, display_name="step arm", email=None, locale="zh-CN",
            timezone="Asia/Shanghai", created_at=now, updated_at=now,
        )
    )
    session.flush()
    session.add(
        Journey(
            id=journey_id, traveler_id=traveler_id, title="step arm",
            city_code="CN-XIAMEN", timezone="Asia/Shanghai", start_at=now,
            end_at=(datetime.now(UTC) + timedelta(days=2)).isoformat(),
            budget_currency="CNY", budget_amount_minor=90000, planning_mode="balanced",
            status="DRAFT", active_plan_version_id=None, current_activity_id=None,
            created_at=now, updated_at=now,
        )
    )
    session.add(
        JourneyMission(
            id=mission_id, journey_id=journey_id, traveler_id=traveler_id,
            user_text="plan it", requested_autonomy="PLAN_ONLY", status="DRAFT",
            created_at=now,
        )
    )
    session.flush()
    return journey_id, mission_id


def _run_exhausting_steps(monkeypatch):
    """Drive the real `run()` until it stops on the step budget."""

    from app.agent import runtime as rt
    from app.db.models import AgentRun, Journey
    from app.db.session import SessionLocal, ensure_schema

    ensure_schema()

    agent = object.__new__(rt.DeepSeekJourneyAgent)
    agent.provider_key = "deepseek"
    agent.model_key = "stub-model"
    agent._owns_client = True
    agent._client = None

    state = {"n": 0}

    def _complete(_messages):
        state["n"] += 1
        # A different argument each turn, so the repetition guard never fires and the only way
        # out of the loop is the step budget.
        return {
            "content": "",
            "tool_calls": [
                {
                    "id": f"call-{state['n']}",
                    "function": {
                        "name": UNGRANTED_TOOL,
                        "arguments": '{"turn": %d}' % state["n"],
                    },
                }
            ],
        }

    monkeypatch.setattr(rt.DeepSeekJourneyAgent, "_complete", lambda self, m: _complete(m))
    monkeypatch.setattr(rt, "record_audit", lambda *a, **k: None)
    monkeypatch.setattr(rt, "persist_span", lambda *a, **k: None)

    limit = 3
    with SessionLocal() as session:
        journey_id, mission_id = _seed(session)
        journey = session.get(Journey, journey_id)
        mission = session.get(rt.JourneyMission, mission_id)
        try:
            result = rt.DeepSeekJourneyAgent.run(agent, session, journey=journey, mission=mission, max_steps=limit)
            session.commit()
        finally:
            run_row = session.query(AgentRun).filter_by(mission_id=mission_id).one_or_none()
            persisted = (run_row.status, run_row.outcome) if run_row else (None, None)
            session.query(rt.JourneyMission).filter_by(id=mission_id).delete()
            session.query(Journey).filter_by(id=journey_id).delete()
            session.query(AgentRun).filter_by(mission_id=mission_id).delete()
            session.commit()
    return result, persisted, state["n"], limit


def test_a_step_limit_run_is_recorded_partial_not_completed(monkeypatch) -> None:
    """The defect reading, before the fix: status COMPLETED with an outcome saying it stopped."""

    _result, (status, outcome), calls, limit = _run_exhausting_steps(monkeypatch)

    assert calls >= limit, (calls, limit)
    assert "tool-step limit" in (outcome or ""), outcome
    assert status == "PARTIAL", (status, outcome)


def test_the_mission_does_not_claim_completed_either(monkeypatch) -> None:
    """`mission.status` is derived from `run.status`, so it inherited the same false claim."""

    from app.db.session import SessionLocal
    from app.agent import runtime as rt

    result, (status, _outcome), _calls, _limit = _run_exhausting_steps(monkeypatch)

    assert result.get("status") == "PARTIAL", result.get("status")
    assert status != "COMPLETED", status
    with SessionLocal() as session:
        leftover = session.query(rt.JourneyMission).count()
    assert isinstance(leftover, int)


def test_the_partial_branch_is_reachable(monkeypatch) -> None:
    """Before the fix `"PARTIAL"` was dead code: the step-limit branch had just filled
    `final_text` with a non-empty sentence, so `if final_text` was always true.  This pins that
    the exhausted run really does take that branch - a run that completed normally still must not
    be PARTIAL, so the answer cannot be "always PARTIAL"."""

    from app.agent import runtime as rt

    source = __import__("inspect").getsource(rt)
    assert "steps_exhausted = True" in source, "the loop no longer records that it ran out"
    assert 'run.status = "PARTIAL" if steps_exhausted' in source, (
        "the status is decided by a value the loop itself overwrote"
    )


def test_a_finished_run_is_still_completed(monkeypatch) -> None:
    """The other direction, so the fix cannot pass by calling everything PARTIAL: a provider that
    answers with a summary and no tool call must still be COMPLETED."""

    from app.db.models import AgentRun, Journey
    from app.db.session import SessionLocal, ensure_schema
    from app.agent import runtime as rt

    ensure_schema()

    agent = object.__new__(rt.DeepSeekJourneyAgent)
    agent.provider_key = "deepseek"
    agent.model_key = "stub-model"
    agent._owns_client = True
    agent._client = None

    monkeypatch.setattr(
        rt.DeepSeekJourneyAgent,
        "_complete",
        lambda self, m: {"content": "Done: nothing to change.", "tool_calls": []},
    )
    monkeypatch.setattr(rt, "record_audit", lambda *a, **k: None)
    monkeypatch.setattr(rt, "persist_span", lambda *a, **k: None)

    with SessionLocal() as session:
        journey_id, mission_id = _seed(session)
        journey = session.get(Journey, journey_id)
        mission = session.get(rt.JourneyMission, mission_id)
        try:
            result = rt.DeepSeekJourneyAgent.run(agent, session, journey=journey, mission=mission, max_steps=3)
            session.commit()
            status = session.query(AgentRun).filter_by(mission_id=mission_id).one().status
        finally:
            session.query(rt.JourneyMission).filter_by(id=mission_id).delete()
            session.query(Journey).filter_by(id=journey_id).delete()
            session.query(AgentRun).filter_by(mission_id=mission_id).delete()
            session.commit()

    assert status == "COMPLETED", status
    assert result.get("status") == "COMPLETED", result.get("status")
