from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.agent.mission import compile_mission
from app.integrations.ai.copilot_contract import (
    classify_copilot_message,
    disruption_event_type,
)
from app.planning.authoritative_v12 import ComposeNode, _schedule_nodes
from app.planning.day_rhythm import apply_day_rhythm, extract_day_rhythm


LATE_START_SCENARIO = (
    "情侣晚间活动到凌晨，次日睡到中午再慢慢出门，不排上午活动、少走路；"
    "真实下雨才用室内备选；地点营业时间/开放状态未知时先询问或标未知。"
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


def _compile_mission_without_activity_resolution(command: str, monkeypatch):
    monkeypatch.setattr("app.agent.mission._resolve_protected_activities", lambda *_args: ())
    journey = SimpleNamespace(budget_currency="CNY", active_plan_version_id=None)
    return compile_mission(
        None,
        journey,
        command,
        requested_autonomy="PLAN_ONLY",
    )


def test_rain_contingent_indoor_backup_is_not_a_current_weather_report(monkeypatch) -> None:
    spec = _compile_mission_without_activity_resolution(LATE_START_SCENARIO, monkeypatch)

    assert spec.preferences["indoor_backup_if_raining"] is True
    assert "PREFER_INDOOR" not in spec.objective_codes
    assert "weather_state" not in spec.preferences
    capability_codes = {item["code"] for item in spec.capabilities}
    assert "MAX_WALKING_PER_LEG_M" in capability_codes
    assert "INDOOR_PREFERRED" not in capability_codes
    assert "MINIMIZE_WALKING" in spec.objective_codes

    conditional = "真实下雨才用室内备选"
    assert classify_copilot_message(conditional).intent == "PREFERENCE_CHANGE"
    assert disruption_event_type(conditional) is None
    assert classify_copilot_message("现在下雨").intent == "DISRUPTION_REPORT"
    assert disruption_event_type("现在下雨") == "WEATHER"


def test_unknown_opening_hours_fail_closed_in_authoritative_schedule() -> None:
    date = "2026-10-19"
    nodes = [
        ComposeNode(
            "arrival",
            "Arrival",
            "ARRIVAL",
            0,
            0,
            "arrival",
            0,
            datetime.fromisoformat(f"{date}T08:00:00+08:00"),
            datetime.fromisoformat(f"{date}T08:20:00+08:00"),
        ),
        ComposeNode(
            "unknown-place",
            "Unknown place",
            "ACTIVITY",
            0,
            0,
            "unknown-place",
            0,
            datetime.fromisoformat(f"{date}T09:00:00+08:00"),
            datetime.fromisoformat(f"{date}T10:00:00+08:00"),
        ),
        ComposeNode(
            "departure",
            "Departure",
            "DEPARTURE",
            0,
            0,
            "departure",
            0,
            datetime.fromisoformat(f"{date}T18:00:00+08:00"),
            datetime.fromisoformat(f"{date}T18:20:00+08:00"),
        ),
    ]
    place = SimpleNamespace(
        id="unknown-place",
        metadata_json='{"cost_minor":0,"cost_status":"KNOWN","duration_min":45}',
        opening_hours_json="",
    )
    selected_modes = {
        ("arrival", "unknown-place"): SimpleNamespace(duration_min=15),
        ("unknown-place", "departure"): SimpleNamespace(duration_min=15),
    }

    for opening_hours, expected_code in (
        ('{"status":"UNKNOWN"}', "V13_OPENING_STATUS_UNKNOWN"),
        (
            '{"status":"UNKNOWN","open":"09:00","close":"18:00"}',
            "V13_OPENING_STATUS_UNKNOWN",
        ),
        ('{"status":"CLOSED"}', "V13_PLACE_CLOSED"),
    ):
        place.opening_hours_json = opening_hours
        with pytest.raises(ValueError, match=f"{expected_code}:unknown-place"):
            _schedule_nodes(
                nodes,
                [["unknown-place"]],
                {"unknown-place": place},
                selected_modes,
                SimpleNamespace(),
                {"at": f"{date}T08:00:00+08:00"},
                {"at": f"{date}T18:00:00+08:00"},
                day_count=1,
                stay=None,
            )
