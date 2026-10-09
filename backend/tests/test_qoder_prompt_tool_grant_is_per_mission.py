"""The system prompt may not tell the model it has more tools than this mission grants.

Measured at the authoritative tip `bdee2fc3344168ce9b1e0228e53cdffb8c5ecd8c`: `_system_prompt`
opened with "Use only the eleven CityNexus tools supplied by the server" - a spelled-out constant
for a number that is not the mission's.  The server does hand eleven tool definitions to every
mission, but `build_mission_plan` grants five to a `PLAN_ONLY` one and the runtime refuses the
other six at call time, so a PLAN_ONLY model was given a premise the mission could not honour and
then blocked from acting on it.  The same prompt also said "do not accept or execute a mutating
action", so the two halves contradicted each other.

The prompt now reads both numbers from the same source that grants them.  An arm that only checked
"the word eleven is gone" would pass on a prompt that hardcoded "five" instead, so R4 compares the
stated grant against `mission_plan_for_model` itself.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest


@pytest.fixture(scope="module", autouse=True)
def _schema_present() -> None:
    """Create the schema in this process's isolated database.

    The suite's `CITYNEXUS_DATABASE_URL` points at a fresh temporary file, and the tables arrive
    with application startup; an arm that only ever opens `SessionLocal` would otherwise be
    reading a database that was never built.
    """

    from app.db.session import ensure_schema

    ensure_schema()


GRANT_SENTENCE = re.compile(
    r"Use only the (\d+) CityNexus tools this mission grants"
)
SUPPLIED_SENTENCE = re.compile(r"the server supplies (\d+) definitions")
REFUSED_SENTENCE = re.compile(r"refuses the (\d+) outside that grant")


def _prompt_for(autonomy: str) -> tuple[str, int, int]:
    """Build the real system prompt for one autonomy level on a throwaway row set.

    Returns the prompt text, the number of tools the plan grants and the number the server
    supplies, so the assertions compare what the model is told against what is actually granted -
    not against a second literal written in this file.
    """

    from app.agent.mission_plan import mission_plan_for_model
    from app.agent.runtime import _system_prompt, citynexus_tool_definitions
    from app.db.models import Journey, JourneyMission, Traveler
    from app.db.session import SessionLocal

    now = datetime.now(timezone.utc).isoformat()
    traveler_id, journey_id, mission_id = str(uuid4()), str(uuid4()), str(uuid4())
    supplied = len(citynexus_tool_definitions())
    try:
        with SessionLocal() as session:
            session.add(
                Traveler(
                    id=traveler_id, display_name="prompt arm", email=None, locale="zh-CN",
                    timezone="Asia/Shanghai", created_at=now, updated_at=now,
                )
            )
            session.flush()
            session.add(
                Journey(
                    id=journey_id, traveler_id=traveler_id, title="prompt arm",
                    city_code="CN-XIAMEN", timezone="Asia/Shanghai", start_at=now,
                    end_at=(datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                    budget_currency="CNY", budget_amount_minor=90000, planning_mode="balanced",
                    status="DRAFT", active_plan_version_id=None, current_activity_id=None,
                    created_at=now, updated_at=now,
                )
            )
            session.add(
                JourneyMission(
                    id=mission_id, journey_id=journey_id, traveler_id=traveler_id,
                    user_text="plan it", requested_autonomy=autonomy, status="DRAFT",
                    created_at=now,
                )
            )
            session.flush()
            mission = session.get(JourneyMission, mission_id)
            journey = session.get(Journey, journey_id)
            granted = len(mission_plan_for_model(mission).get("allowed_tools") or ())
            return _system_prompt(session, mission, journey), granted, supplied
    finally:
        with SessionLocal() as cleanup:
            cleanup.query(JourneyMission).filter_by(id=mission_id).delete()
            cleanup.query(Journey).filter_by(id=journey_id).delete()
            cleanup.query(Traveler).filter_by(id=traveler_id).delete()
            cleanup.commit()


# ------------------------------------------------------------------ R1: the PLAN_ONLY claim


def test_r1_a_plan_only_prompt_states_the_five_tools_it_actually_grants() -> None:
    """The before-fix reading: the prompt said "eleven" to a mission permitted five."""

    prompt, granted, supplied = _prompt_for("PLAN_ONLY")
    stated = GRANT_SENTENCE.search(prompt)

    assert stated is not None, "the prompt states no per-mission grant (one fixed figure for all)"
    assert int(stated.group(1)) == granted, (granted, stated.group(1), prompt[:200])
    assert granted < supplied, (granted, supplied)


def test_r1b_the_prompt_names_the_tools_it_will_refuse() -> None:
    """A grant narrower than the supply has to say what is withheld, or the model can only find
    out by being refused mid-run."""

    prompt, granted, supplied = _prompt_for("PLAN_ONLY")
    refused = REFUSED_SENTENCE.search(prompt)

    assert refused is not None, prompt[:300]
    assert int(refused.group(1)) == supplied - granted, (granted, supplied, refused.group(1))


def test_r1c_the_spelled_out_constant_is_gone() -> None:
    prompt, _granted, _supplied = _prompt_for("PLAN_ONLY")

    assert "eleven" not in prompt, prompt[:300]


# ------------------------------------------------------- R2: the full-grant level


def test_r2_a_fully_granted_mission_does_not_claim_a_remainder_to_refuse() -> None:
    """The other direction, so the fix cannot pass by always announcing withheld tools: when the
    mission holds every definition there is no 'rest', and naming one would be the same species
    of invention in miniature."""

    prompt, granted, supplied = _prompt_for("ASSISTED")
    stated = GRANT_SENTENCE.search(prompt)

    assert stated is not None, prompt[:200]
    assert int(stated.group(1)) == granted == supplied, (granted, supplied, stated.group(1))
    assert REFUSED_SENTENCE.search(prompt) is None, (
        "a mission granted everything still advertises tools it withholds"
    )


def test_r2b_an_autonomous_mission_reads_the_same_way() -> None:
    prompt, granted, supplied = _prompt_for("AUTONOMOUS")
    stated = GRANT_SENTENCE.search(prompt)

    assert int(stated.group(1)) == granted == supplied, (granted, supplied)


# ------------------------------------------- R3: it stays a claim about this mission


def test_r3_the_two_levels_do_not_answer_with_the_same_number() -> None:
    """One prompt sentence serving every mission was how the mismatch survived review: if both
    levels print the same figure, the figure is not coming from the grant."""

    plan_only, plan_only_granted, _ = _prompt_for("PLAN_ONLY")
    assisted, assisted_granted, _ = _prompt_for("ASSISTED")

    assert plan_only_granted != assisted_granted, (plan_only_granted, assisted_granted)
    assert (
        GRANT_SENTENCE.search(plan_only).group(1)
        != GRANT_SENTENCE.search(assisted).group(1)
    ), "both prompts state one grant, so it is not the mission's"


def test_r3b_the_grant_still_agrees_with_the_permission_the_runtime_enforces() -> None:
    """The prompt says the Gateway refuses the remainder; that is only honest if a PLAN_ONLY
    mission really is refused when it reaches for a mutating tool."""

    from app.agent.mission_plan import mission_plan_for_model

    prompt, _granted, _supplied = _prompt_for("PLAN_ONLY")
    refused_names = REFUSED_SENTENCE.search(prompt)
    assert refused_names is not None, prompt[:300]

    plan = mission_plan_for_model(
        type("_M", (), {
            "requested_autonomy": "PLAN_ONLY",
            "protected_activity_ids_json": "[]",
            "objective_codes_json": "[]",
        })()
    )
    granted = set(plan.get("allowed_tools") or ())
    assert "accept_replan" not in granted, granted
    assert "create_booking" not in granted, granted
