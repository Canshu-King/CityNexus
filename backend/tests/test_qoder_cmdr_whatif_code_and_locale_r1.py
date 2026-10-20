"""What-if previews name their branch, and the reader gets the answer in their own language.

Why this exists: measured on the phone-shaped preview (412x915, interface in Chinese), the bubble under
the AI badge held the server's own English record -- "This is a hypothetical weather or closure
scenario only. It is not recorded as a real event; an explicit replan can capture current provider
evidence." -- while every label around it was Chinese. The payload sentence is legitimate as a server
record; it was simply never meant to be the thing a traveller reads.

So the split is pinned here in both directions: every preview branch names itself with
`explanation_code`, the reader-facing table covers exactly that vocabulary (no branch without a
sentence, no sentence without a branch), and an unnamed branch falls back to something true instead
of something empty.
"""

from __future__ import annotations

import re

import app.main as main_module
from app.integrations.ai.copilot_contract import (
    WHAT_IF_EXPLANATION_CODES,
    CopilotInterpretation,
    simulate_what_if,
)

_HAS_CJK = re.compile(r"[\u4e00-\u9fff]")


def _plan_context(*, activities: list[dict], commitments: list[dict], current: str | None) -> dict:
    return {
        "currency": "CNY",
        "current_activity_id": current,
        "plan": {
            "id": "plan-1",
            "version_no": 1,
            "status": "SELECTED",
            "cost_minor": 2000,
            "currency": "CNY",
            "activities": activities,
            "legs": [{"walking_min": 15}],
        },
        "commitments": commitments,
    }


_MUSEUM = {
    "id": "museum",
    "title": "Museum",
    "start_at": "2026-10-10T13:00:00+08:00",
    "end_at": "2026-10-10T15:00:00+08:00",
    "locked": False,
}
_CRUISE = {
    "id": "cruise",
    "title": "Cruise",
    "start_at": "2026-10-10T17:00:00+08:00",
    "end_at": "2026-10-10T18:00:00+08:00",
    "locked": False,
}
_PROTECTED_CRUISE = {
    "id": "cruise-commitment",
    "activity_id": "cruise",
    "protected": True,
    "scheduled_start_at": "2026-10-10T16:30:00+08:00",
}


def _branches() -> list[tuple[str, dict, str]]:
    """One reachable call per preview branch: (code, context, message)."""

    return [
        (
            "ABSORBS_WITHIN_OBSERVED_WINDOW",
            _plan_context(activities=[_MUSEUM], commitments=[_PROTECTED_CRUISE], current="museum"),
            "如果我延长 30 分钟会怎样？",
        ),
        (
            "NEXT_PROTECTED_WINDOW_WOULD_BE_CONSUMED",
            _plan_context(activities=[_MUSEUM], commitments=[_PROTECTED_CRUISE], current="museum"),
            "如果我延长 120 分钟会怎样？",
        ),
        (
            "PROTECTED_OR_LOCKED_TOUCHED",
            _plan_context(activities=[_MUSEUM, _CRUISE], commitments=[_PROTECTED_CRUISE], current="museum"),
            "在 Cruise 多待 30 分钟可以吗？",
        ),
        (
            "PROVIDER_BACKED_ALTERNATIVE_REQUIRED",
            _plan_context(activities=[_MUSEUM], commitments=[_PROTECTED_CRUISE], current="museum"),
            "能不能少走一点路？",
        ),
        (
            "HYPOTHETICAL_WEATHER_OR_CLOSURE",
            _plan_context(activities=[_MUSEUM], commitments=[_PROTECTED_CRUISE], current="museum"),
            "如果下午下雨，行程要怎么改？",
        ),
        (
            # A plan with nothing to stretch: the selector hands back None, and the preview says so.
            "NO_TARGET_SIMULATED",
            _plan_context(activities=[], commitments=[_PROTECTED_CRUISE], current=None),
            "如果我延长 30 分钟会怎样？",
        ),
    ]


def test_every_preview_branch_names_itself():
    seen = set()
    for expected_code, context, message in _branches():
        result = simulate_what_if(message, context)
        assert result["explanation_code"] == expected_code, (message, result["status"], result["explanation_code"])
        assert result["simulation_only"] is True
        assert str(result["explanation"]).strip(), expected_code
        seen.add(expected_code)

    # The vocabulary and the reachable branches are the same set: a code nobody can reach is dead, a
    # reachable branch nobody named is what produced the English bubble in the first place.
    assert seen == set(WHAT_IF_EXPLANATION_CODES), sorted(seen ^ set(WHAT_IF_EXPLANATION_CODES))


def test_reader_language_covers_exactly_the_named_branches():
    assert set(main_module._WHAT_IF_ANSWERS) == set(WHAT_IF_EXPLANATION_CODES)
    for code, (zh, en) in main_module._WHAT_IF_ANSWERS.items():
        assert _HAS_CJK.search(zh), code
        assert not _HAS_CJK.search(en), code
        assert zh.strip() and en.strip(), code
        # The old defect was the server sentence reaching the screen; no cell may be a copy of one.
        recorded = str(simulate_what_if("", {})["explanation"])
        assert zh != recorded and en != recorded, code


def test_a_chinese_reader_gets_chinese_for_every_branch():
    for expected_code, context, message in _branches():
        result = simulate_what_if(message, context)
        zh = main_module._what_if_answer_text(result, "zh")
        en = main_module._what_if_answer_text(result, "en")

        assert _HAS_CJK.search(zh), (expected_code, zh)
        assert not _HAS_CJK.search(en), (expected_code, en)
        # Neither language repeats the other, and neither is the server's own English record.
        assert zh != en
        assert zh != result["explanation"]
        assert en != result["explanation"], (expected_code, en)


def test_an_unnamed_branch_falls_back_to_something_true_not_empty():
    # Negative control, both halves: a code outside the vocabulary still says what the server said,
    # and a payload with neither code nor sentence still says the one thing every preview shares.
    recorded = main_module._what_if_answer_text(
        {"explanation_code": "SOME_BRANCH_NOBODY_DECLARED", "explanation": "Server recorded this."},
        "zh",
    )
    assert recorded == "Server recorded this."

    silent_zh = main_module._what_if_answer_text({}, "zh")
    silent_en = main_module._what_if_answer_text({}, "en")
    assert silent_zh == "这次只做了试算，行程没有改动。"
    assert silent_en == "This was a preview only; your trip is unchanged."
    assert _HAS_CJK.search(silent_zh) and not _HAS_CJK.search(silent_en)


def test_the_answer_helper_is_what_the_copilot_actually_uses():
    """The screen renders `_copilot_answer`; pin that it routes the preview through the table."""

    _, context, message = next(b for b in _branches() if b[0] == "HYPOTHETICAL_WEATHER_OR_CLOSURE")
    what_if = simulate_what_if(message, context)
    interpretation = CopilotInterpretation(
        intent="WHAT_IF",
        confidence=0.6,
        reason="pinned by this test",
        entities={},
        provider_key="deepseek",
        degraded=False,
    )

    answer = main_module._copilot_answer(interpretation, context, locale="zh", what_if=what_if)
    assert answer == main_module._WHAT_IF_ANSWERS["HYPOTHETICAL_WEATHER_OR_CLOSURE"][0]
    assert "hypothetical weather" not in answer

    english = main_module._copilot_answer(interpretation, context, locale="en", what_if=what_if)
    assert english == main_module._WHAT_IF_ANSWERS["HYPOTHETICAL_WEATHER_OR_CLOSURE"][1]


def _explain() -> CopilotInterpretation:
    return CopilotInterpretation(
        intent="EXPLAIN_PLAN",
        confidence=0.9,
        reason="pinned by this test",
        entities={},
        provider_key="deepseek",
        degraded=False,
    )


_PLAN = {
    "id": "plan-1",
    "version_no": 2,
    "status": "ACTIVE",
    "cost_minor": 2000,
    "currency": "CNY",
    "activities": [],
    "legs": [],
}


def test_the_plan_state_is_named_in_the_readers_own_words():
    """The screen used to print the column name and its value: `PlanVersion 2 (ACTIVE)`.

    Each status the tree actually writes has a word in both languages; the version number stays, and
    the internal token does not leak into a Chinese sentence.
    """

    vocabulary = {
        "ACTIVE": ("在用", "in use"),
        "SELECTED": ("已选定", "selected"),
        "CANDIDATE": ("候选", "candidate"),
        "REJECTED": ("未通过", "not passed"),
        "SUPERSEDED": ("已被取代", "superseded"),
        "EXPIRED": ("已过期", "expired"),
    }
    for status, (zh_word, en_word) in vocabulary.items():
        context = {"plan": {**_PLAN, "status": status}, "protected_commitments": [{"id": "c1"}]}
        zh = main_module._copilot_answer(_explain(), context, locale="zh")
        en = main_module._copilot_answer(_explain(), context, locale="en")

        assert "第 2 号方案" in zh, status
        assert zh_word in zh, status
        assert "PlanVersion" not in zh, status
        assert "plan version 2" in en, status
        assert en_word in en, status
        assert zh != en


def test_no_plan_selected_says_it_without_naming_a_column():
    context = {"plan": None, "protected_commitments": []}
    zh = main_module._copilot_answer(_explain(), context, locale="zh")
    en = main_module._copilot_answer(_explain(), context, locale="en")

    assert "还没有选定的方案" in zh
    assert "no selected plan" in en
    # The defect was an English phrase inside a Chinese sentence; keep both halves of the pin.
    assert "no selected PlanVersion" not in zh
    assert "PlanVersion" not in zh and "PlanVersion" not in en


def test_a_status_nobody_named_stays_visible_instead_of_being_invented():
    """Truth over prettiness: an unknown status is shown as it is, not re-labelled."""

    context = {"plan": {**_PLAN, "status": "WATSOEVER"}, "protected_commitments": []}
    zh = main_module._copilot_answer(_explain(), context, locale="zh")

    assert "WATSOEVER" in zh
    assert "第 2 号方案" in zh
    assert "在用" not in zh and "已选定" not in zh


def test_the_no_plan_notice_stops_reciting_the_machine():
    what_if = simulate_what_if(
        "如果下午下雨，行程要怎么改？", {"currency": "CNY", "plan": None, "commitments": []}
    )
    assert what_if["status"] == "NOT_SIMULATABLE_FROM_CURRENT_EVIDENCE"

    zh = main_module._copilot_answer(_explain(), {}, locale="zh", what_if=what_if)
    en = main_module._copilot_answer(_explain(), {}, locale="en", what_if=what_if)

    assert "还没有选定方案" in zh and "没有改动行程" in zh
    # The old sentence named two mechanisms the traveller cannot act on.
    assert "确定性门控" not in zh and "权威" not in zh
    assert "No plan is selected for this trip yet" in en
    assert zh != en


_CAMEL_CASE = re.compile(r"[A-Za-z][a-z]+[A-Z][A-Za-z]*")
# Capability codes are the second shape that leaked: measured on the phone screen, the preference
# branch answered `记下你的能力与偏好（MAX_WALKING_PER_LEG_M）…`. The code belongs in `entities`, not in
# a sentence addressed to a traveller.
_CODE_SHAPE = re.compile(r"[A-Z][A-Z0-9]*_[A-Z0-9_]+")
_INTERNAL_NAMES = ("TravelerTwin", "JourneyTwin", "PlanVersion", "ReplanDiff", "CityNexus", "Copilot")


def _interpretation(intent: str, entities: dict | None = None) -> CopilotInterpretation:
    return CopilotInterpretation(
        intent=intent,
        confidence=0.8,
        reason="pinned by this test",
        entities=entities or {},
        provider_key="deepseek",
        degraded=False,
    )


def _reader_branches() -> list[tuple[str, CopilotInterpretation, dict, str, str]]:
    """Every branch a traveller can land on, with the one fact each must still say out loud."""

    hard = {"capabilities": [{"code": "STEP_FREE", "severity": "HARD", "params": {}}]}
    soft = {"capabilities": [{"code": "QUIET_SPACE", "severity": "SOFT", "params": {}}]}
    return [
        ("DISCOVER", _interpretation("DISCOVER"), {}, "不会自己加进行程", "never added to your trip"),
        ("capability-hard", _interpretation("WHAT_IF", hard), {}, "要你先确认", "need your confirmation"),
        ("capability-soft", _interpretation("WHAT_IF", soft), {}, "不会自己改动你的偏好档案", "won't change your preference profile"),
        ("PREFERENCE_CHANGE", _interpretation("PREFERENCE_CHANGE"), {}, "明确确认更新偏好", "confirm the preference update"),
        ("REPLAN_REQUEST", _interpretation("REPLAN_REQUEST"), {}, "先过可行性核对", "pass the feasibility check"),
        ("VERIFY_FACT", _interpretation("VERIFY_FACT"), {}, "还没核实", "isn't verified yet"),
        ("PERSONAL_ASSISTANCE", _interpretation("PERSONAL_ASSISTANCE"), {}, "个人求助", "personal assistance"),
        ("unrouted", _interpretation("SOMETHING_ELSE"), {}, "没有可靠识别", "could not route"),
        (
            "EXPLAIN_PLAN",
            _interpretation("EXPLAIN_PLAN"),
            {"plan": _PLAN, "protected_commitments": []},
            "号方案",
            "plan version",
        ),
    ]


def test_no_sentence_addressed_to_a_traveller_names_one_of_our_own_objects():
    """A standing gate over the copilot's reader-facing sentences.

    These answers used to say things like `不会由 Copilot 静默修改 TravelerTwin` and name `CityNexus` as
    the party that must verify feasibility. The reassurance stays; the object names, the pipeline
    names and the self-justification do not. This walks every branch, both languages, so a future
    branch that leaks an identifier fails here rather than on a phone.
    """

    for label, interpretation, context, zh_fact, en_fact in _reader_branches():
        zh = main_module._copilot_answer(interpretation, context, locale="zh")
        en = main_module._copilot_answer(interpretation, context, locale="en")

        assert _HAS_CJK.search(zh), (label, zh)
        assert not _HAS_CJK.search(en), (label, en)
        assert zh_fact in zh, (label, zh)
        assert en_fact in en, (label, en)

        for name in _INTERNAL_NAMES:
            assert name not in zh, (label, name, zh)
            assert name not in en, (label, name, en)
        assert not _CAMEL_CASE.search(zh), (label, zh)
        assert not _CAMEL_CASE.search(en), (label, en)
        assert not _CODE_SHAPE.search(zh), (label, zh)
        assert not _CODE_SHAPE.search(en), (label, en)

    # The preview table is reader-facing too: no cell may carry an internal object name.
    for code, (zh, en) in main_module._WHAT_IF_ANSWERS.items():
        for name in _INTERNAL_NAMES:
            assert name not in zh and name not in en, (code, name)
        assert not _CAMEL_CASE.search(zh), code
        assert not _CAMEL_CASE.search(en), code
        assert not _CODE_SHAPE.search(zh), code
        assert not _CODE_SHAPE.search(en), code
