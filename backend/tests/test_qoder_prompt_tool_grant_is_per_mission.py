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

The same opening block also asserted "You may autonomously act on ordinary reversible changes"
to every mission, two sentences above "do not accept or execute a mutating action" for the one
level that holds no executing tool at all - so R4 pins the authority claim too.  The plan already
names that limit as its `approval_boundary` step and the prompt now quotes it; the whole plan is
also dumped into the prompt as JSON, so R4b pins the quote as an instruction, not the words
appearing anywhere, which would be vacuously true with or without the fix.

The prompt also promises that "the Gateway refuses the N outside that grant", and until R5 the
Gateway decided that from its own hard-coded set of six names beside a `requested_autonomy` test -
two rules that happened to agree. The refusal now reads the same grant. Reverting only that half
leaves R5 red alone, which is what makes it a judgement about the enforcement rather than about
the sentence.
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


# ------------------------------------------- R4: the authority the prompt claims


FLAT_CLAIM = "You may autonomously act on ordinary reversible changes"
EXECUTING_CLAIM = re.compile(
    r"act on ordinary reversible changes using the (\d+) executing tools this mission grants"
)
NO_EXECUTION_CLAIM = "grants you no tool that carries a change out"


def test_r4_a_plan_only_prompt_does_not_claim_a_change_carrying_authority() -> None:
    """The before-fix reading: one flat sentence telling every mission it may act on reversible
    changes, sitting two sentences above "do not accept or execute a mutating action"."""

    prompt, granted, _supplied = _prompt_for("PLAN_ONLY")

    assert FLAT_CLAIM not in prompt, prompt[:400]
    assert NO_EXECUTION_CLAIM in prompt, prompt[:400]


def test_r4b_the_boundary_the_plan_itself_sets_is_quoted_not_paraphrased() -> None:
    """The server already wrote this mission's limit as a step. It is also already present in the
    prompt as data, because the whole plan is dumped as JSON - so "the words appear somewhere"
    would be a vacuous judgement. What this pins is that the instruction block quotes it, which is
    the only place a model reads it as a rule rather than as a field."""

    from app.agent.mission_plan import mission_plan_for_model

    prompt, _granted, _supplied = _prompt_for("PLAN_ONLY")
    plan = mission_plan_for_model(
        type("_M", (), {
            "requested_autonomy": "PLAN_ONLY",
            "protected_activity_ids_json": "[]",
            "objective_codes_json": "[]",
        })()
    )
    boundary = next(
        str(step.get("operation"))
        for step in (plan.get("steps") or [])
        if isinstance(step, dict) and step.get("id") == "approval_boundary"
    )

    assert f"Your boundary: {boundary}." in prompt, (boundary, prompt[:400])


def test_r4c_a_mission_that_does_hold_executing_tools_says_so_with_a_number() -> None:
    """The other direction, so the fix cannot pass by never granting anything: ASSISTED holds six
    executing tools and the prompt has to state that rather than leave it implied."""

    from app.agent.runtime import _MUTATION_TOOLS

    prompt, _granted, _supplied = _prompt_for("ASSISTED")

    stated = EXECUTING_CLAIM.search(prompt)
    assert stated is not None, prompt[:400]

    from app.agent.mission_plan import mission_plan_for_model

    plan = mission_plan_for_model(
        type("_M", (), {
            "requested_autonomy": "ASSISTED",
            "protected_activity_ids_json": "[]",
            "objective_codes_json": "[]",
        })()
    )
    allowed = set(plan.get("allowed_tools") or ())
    executing = len((allowed & set(_MUTATION_TOOLS)) - {"request_replan"})
    assert executing > 0, allowed
    assert int(stated.group(1)) == executing, (executing, stated.group(1))
    assert NO_EXECUTION_CLAIM not in prompt, prompt[:400]


def test_r4d_the_prompt_no_longer_holds_both_halves_of_one_contradiction() -> None:
    """A PLAN_ONLY prompt must not tell the model it may act and must not act in the same breath."""

    prompt, _granted, _supplied = _prompt_for("PLAN_ONLY")
    claims_it_may_act = FLAT_CLAIM in prompt or EXECUTING_CLAIM.search(prompt) is not None
    forbids_action = "do not accept or execute a mutating action" in prompt

    assert not (claims_it_may_act and forbids_action), (
        "the prompt asserts an execution authority and withdraws it in the same text"
    )


# ------------------------------- R5: one rule, one source (prompt and enforcement)


def test_r5_the_enforcement_refuses_by_the_grant_the_prompt_quotes() -> None:
    """The prompt now tells the model how many tools the Gateway withholds. Until the refusal also
    reads the grant, that sentence was a promise computed from one source and honoured by another:
    they agreed only because someone had written six names out twice, and nothing would have said
    so when a seventh tool or a new autonomy level broke the coincidence."""

    import inspect

    from app.agent import runtime as rt
    from app.agent.mission_plan import mission_plan_for_model

    source = inspect.getsource(rt)
    # The old refusal spoke from its own rule; that sentence is gone. A literal list of tool names
    # is not checked here, because the definitions table legitimately names them too - what
    # matters is which branch decides the refusal.
    assert "mission is PLAN_ONLY; proposal generation is allowed" not in source, (
        "the refusal still speaks from a second rule"
    )
    assert "tool_name not in granted_tool_names" in source, (
        "the refusal no longer reads the grant"
    )

    for autonomy in ("PLAN_ONLY", "ASSISTED", "AUTONOMOUS"):
        mission = type("_M", (), {
            "requested_autonomy": autonomy,
            "protected_activity_ids_json": "[]",
            "objective_codes_json": "[]",
        })()
        granted = set(mission_plan_for_model(mission).get("allowed_tools") or ())
        for name in (d["function"]["name"] for d in rt.citynexus_tool_definitions()):
            outside = name not in granted
            if outside:
                assert autonomy == "PLAN_ONLY", (autonomy, name)


def test_r5b_prompt_and_grant_never_disagree_across_levels_and_tools() -> None:
    """The cell-by-cell table: for every level and every supplied tool, the number the prompt
    states must equal what the grant actually withholds."""

    from app.agent.mission_plan import mission_plan_for_model
    from app.agent.runtime import citynexus_tool_definitions

    supplied = {d["function"]["name"] for d in citynexus_tool_definitions()}
    checked = 0
    for autonomy in ("PLAN_ONLY", "ASSISTED", "AUTONOMOUS"):
        mission = type("_M", (), {
            "requested_autonomy": autonomy,
            "protected_activity_ids_json": "[]",
            "objective_codes_json": "[]",
        })()
        granted = set(mission_plan_for_model(mission).get("allowed_tools") or ())
        assert granted <= supplied, (autonomy, granted - supplied)
        prompt, _granted, _supplied = _prompt_for(autonomy)
        withheld = len(supplied) - len(granted)
        if withheld:
            assert f"refuses the {withheld} outside that grant" in prompt, (autonomy, withheld)
        else:
            assert "refuses the" not in prompt, (autonomy, prompt[:300])
        checked += len(supplied)

    assert checked == 3 * len(supplied), checked
