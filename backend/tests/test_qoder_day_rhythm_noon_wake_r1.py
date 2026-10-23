"""ORD-0706 甲: the noon-wake rule has to be narrow, and its evidence has to agree with its number.

Codex's commit `fc5de6bf` taught the rhythm extractor to hear "睡到中午 / 正午才起" as an explicit
noon wake instead of lumping it into generic late-wake (which meant 10:30).  That is the right
product call, and this file is not a re-write of it -- these doors exist to keep the rule inside the
hole it was cut for:

  * a spoken clock still wins; a phrase may not overwrite a number the traveller said;
  * a phrase that did not decide the number may not appear as the evidence for that number;
  * every other late-wake phrasing keeps the number it had before this order, so the change is one
    step of a staircase and not a shift of the whole floor;
  * the late-night vocabulary that came in the same commit is checked both ways (new phrases answer,
    old phrases still answer), because a word list nobody reads is how a rule dies later.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.planning.day_rhythm import apply_day_rhythm, extract_day_rhythm

NOON = 12 * 60
GENERIC_LATE_WAKE = 10 * 60 + 30


def _activity(title: str, start: str, end: str, *, locked: bool = False, role: str = "ACTIVITY"):
    return SimpleNamespace(
        role=role, title=title, start_at=start, end_at=end, locked=locked, metadata={}, key=title
    )


def test_sleeping_until_noon_moves_the_wake_to_noon():
    rhythm = extract_day_rhythm("我们打算睡到中午再出门")

    assert rhythm is not None
    assert rhythm.wake_minute == NOON, rhythm
    assert rhythm.is_default is False
    assert "wake until noon" in rhythm.evidence, rhythm.evidence
    assert "late wake" in rhythm.evidence, rhythm.evidence


def test_the_noon_phrase_wins_in_each_shape_it_was_listed_in():
    for text in ("睡到正午", "中午才起", "正午醒", "中午起床"):
        rhythm = extract_day_rhythm(text)
        assert rhythm is not None, text
        assert rhythm.wake_minute == NOON, (text, rhythm.wake_minute)


def test_a_spoken_clock_is_not_overwritten_by_the_noon_phrase():
    """The traveller said nine o'clock.  A second-hand phrase may not move that number."""

    rhythm = extract_day_rhythm("九点起床，周末习惯睡到中午")

    assert rhythm is not None
    assert rhythm.wake_minute == 9 * 60, (rhythm.wake_minute, rhythm.evidence)


def test_evidence_does_not_claim_a_noon_wake_it_did_not_apply():
    """The narrower half of this order: an evidence line may not contradict the number it explains.

    Codex's version appended "wake until noon" whenever the phrase appeared, including when a clock
    had already decided the wake.  The answer that surfaces to the traveller would then say one thing
    while the schedule it came from did another.
    """

    rhythm = extract_day_rhythm("九点起床，周末习惯睡到中午")

    assert rhythm is not None
    assert "wake until noon" not in rhythm.evidence, rhythm.evidence


def test_every_other_late_wake_phrase_keeps_the_number_it_already_had():
    """One new stair, not a moved floor: the generic late-wake phrasing is untouched."""

    for text in ("睡到自然醒", "不爱早起", "起得很晚"):
        rhythm = extract_day_rhythm(text)
        assert rhythm is not None, text
        assert rhythm.wake_minute == GENERIC_LATE_WAKE, (text, rhythm.wake_minute)


def test_the_new_late_night_phrases_answer_and_the_old_ones_still_do():
    """Nightlife is carried only inside a rhythm that already has a sleep number.

    The extractor returns nothing when neither a wake nor a bed was decided (`day_rhythm.py`), so a
    lone "玩到凌晨" is not a rhythm -- that is the module's existing shape, and this door writes it
    down rather than pretending the flag can stand alone.
    """

    assert extract_day_rhythm("我们常常玩到凌晨") is None

    for text in ("我们常常玩到凌晨，第二天睡到中午", "活动到天亮再回去睡，中午才起"):
        rhythm = extract_day_rhythm(text)
        assert rhythm is not None, text
        assert rhythm.late_night is True, (text, rhythm.late_night)

    for text in ("夜宵要有，晚上很晚才睡", "夜市想逛，晚上很晚才睡"):
        rhythm = extract_day_rhythm(text)
        assert rhythm is not None, text
        assert rhythm.late_night is True, (text, rhythm.late_night)


def test_a_noon_wake_drops_the_optional_morning_and_keeps_the_noon_and_locked_rows():
    rhythm = extract_day_rhythm("睡到中午再出门")

    assert rhythm is not None
    before_noon = _activity("Morning walk", "2026-10-19T09:00:00+08:00", "2026-10-19T10:00:00+08:00")
    at_noon = _activity("Brunch", "2026-10-19T12:00:00+08:00", "2026-10-19T13:00:00+08:00")
    checked_in = _activity(
        "Hotel check-in", "2026-10-19T08:00:00+08:00", "2026-10-19T08:20:00+08:00",
        locked=True, role="ARRIVAL",
    )

    kept = apply_day_rhythm([before_noon, at_noon, checked_in], rhythm)

    assert [item.title for item in kept] == ["Brunch", "Hotel check-in"], [
        item.title for item in kept
    ]
