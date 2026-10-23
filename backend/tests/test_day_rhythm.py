from __future__ import annotations

from types import SimpleNamespace

from app.planning.day_rhythm import apply_day_rhythm, extract_day_rhythm


LATE_START_SCENARIO = (
    "成年情侣晚间活动到凌晨，次日睡到中午再慢慢出门，不排上午活动、少走路；"
    "若午后下雨给室内备选；地点营业时间/开放状态未知时先询问或标未知。"
)


def test_explicit_noon_wake_filters_optional_morning_without_inventing_place_facts() -> None:
    rhythm = extract_day_rhythm(LATE_START_SCENARIO)

    assert rhythm is not None
    assert rhythm.wake_minute == 12 * 60
    assert rhythm.is_default is False
    assert rhythm.late_night is True
    assert rhythm.evidence == ("late wake", "wake until noon", "late-night activity")
    assert not any(
        token in " ".join(rhythm.evidence)
        for token in ("营业", "开放", "weather", "opening")
    )

    morning = SimpleNamespace(
        role="ACTIVITY",
        title="Morning activity",
        start_at="2026-10-19T09:00:00+08:00",
        end_at="2026-10-19T10:00:00+08:00",
        locked=False,
        metadata={},
    )
    afternoon = SimpleNamespace(
        role="ACTIVITY",
        title="Afternoon activity",
        start_at="2026-10-19T13:00:00+08:00",
        end_at="2026-10-19T14:00:00+08:00",
        locked=False,
        metadata={},
    )
    protected = SimpleNamespace(
        role="ARRIVAL",
        title="Protected arrival",
        start_at="2026-10-19T10:00:00+08:00",
        end_at="2026-10-19T10:20:00+08:00",
        locked=True,
        metadata={},
    )

    assert apply_day_rhythm([morning, afternoon, protected], rhythm) == [afternoon, protected]
