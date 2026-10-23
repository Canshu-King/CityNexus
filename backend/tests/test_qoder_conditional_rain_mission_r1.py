"""ORD-0707 甲: "室内 only if it rains" is a contingency, not an indoor-preferred journey.

Measured on the tip before this order, "我们想睡到中午再出门，若午后下雨给室内备选" produced
`PREFER_INDOOR` plus an `INDOOR_PREFERRED` capability -- the planner was told the traveller wants
indoor places, when the traveller only said what to do if it rains.  These doors hold both sides:
the contingency still has to be remembered (it is a real instruction), and an actual indoor
preference must keep working exactly as it did.
"""

from __future__ import annotations

import pytest

from app.agent import mission
from app.agent.mission import _indoor_rain_preferences, compile_mission

CONDITIONAL = "我们想睡到中午再出门，若午后下雨给室内备选"
PLAIN = "我们只想要室内的地方，少走一点路"
BARE_RAIN = "下午可能会下雨"


@pytest.fixture(autouse=True)
def _no_protection_lookup():
    """`compile_mission` may hit the database for protected rows; these doors are about wording."""

    original = mission._resolve_protected_activities
    mission._resolve_protected_activities = lambda *_args, **_kwargs: ()
    yield
    mission._resolve_protected_activities = original


def _spec(command: str):
    return compile_mission(None, object(), command, requested_autonomy="AUTONOMOUS")


def _codes(spec) -> list[str]:
    return [str(item.get("code")) for item in (spec.capabilities or ())]


def test_a_rain_contingency_no_longer_marks_the_whole_journey_indoor():
    spec = _spec(CONDITIONAL)

    assert "PREFER_INDOOR" not in spec.objective_codes, spec.objective_codes
    assert "indoor" not in spec.preferences, spec.preferences
    assert spec.preferences.get("indoor_backup_if_raining") is True, spec.preferences
    assert "INDOOR_PREFERRED" not in _codes(spec), _codes(spec)


def test_a_real_indoor_preference_still_marks_the_journey_indoor():
    spec = _spec(PLAIN)

    assert "PREFER_INDOOR" in spec.objective_codes, spec.objective_codes
    assert spec.preferences.get("indoor") is True, spec.preferences
    assert "indoor_backup_if_raining" not in spec.preferences, spec.preferences
    assert "INDOOR_PREFERRED" in _codes(spec), _codes(spec)


def test_both_kinds_in_one_sentence_keep_both_readings():
    spec = _spec("我们偏爱室内的地方，另外要是下雨就再找室内备选")

    assert "PREFER_INDOOR" in spec.objective_codes, spec.objective_codes
    assert spec.preferences.get("indoor") is True, spec.preferences
    assert spec.preferences.get("indoor_backup_if_raining") is True, spec.preferences
    assert "INDOOR_PREFERRED" in _codes(spec), _codes(spec)


def test_a_bare_rain_mention_behaves_exactly_as_it_did_before():
    """This order fixes the conditional misread; it does not touch what rain alone used to mean."""

    spec = _spec(BARE_RAIN)

    assert "PREFER_INDOOR" in spec.objective_codes, spec.objective_codes
    assert "indoor_backup_if_raining" not in spec.preferences, spec.preferences


def test_the_clause_splitter_answers_both_ways_in_each_language():
    assert _indoor_rain_preferences("indoor if it rains in the afternoon") == (True, False)
    assert _indoor_rain_preferences("we want indoor places only") == (False, True)
    assert _indoor_rain_preferences("博物馆关门了") == (False, False)
    assert _indoor_rain_preferences("不要室内的地方，就去户外") == (False, False)


def test_the_contingency_is_still_a_day_rhythm_reading_of_the_same_sentence():
    """The rain sentence above also carries "睡到中午": the two rules must not eat each other."""

    spec = _spec(CONDITIONAL)

    assert spec.preferences.get("day_rhythm", {}).get("wake_hhmm") == "12:00", spec.preferences
