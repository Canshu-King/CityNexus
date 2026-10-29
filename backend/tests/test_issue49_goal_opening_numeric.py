"""Regression coverage for AMap numeric month/day opening spans.

The provider sentence and flattened envelope below are copied from the static extract at
C:/Users/仓鼠王/cn51/classroom-20261026-qa/supply-native-20261026/suzhou-museum-opening-source.json.
The fixture is embedded; tests do not read that local artifact or contact a provider.
The native preparation check uses the isolated test DB.
"""

import json
from uuid import uuid4

from sqlalchemy import select

from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: F401
from app.agent.goal_opening_date import (
    CLOSED_ON_DATE,
    DATE_SPECIFIC_UNKNOWN,
    OPEN_ON_DATE,
    TIME_OUTSIDE_WINDOW,
    verdict_for_date,
)
from app.agent.goal_place_identity import attach_canonical_places
from app.db.models import Activity, Journey, JourneyMission, Place
from app.db.session import SessionLocal


SUZHOU_OPENING_RAW = (
    "09/25-09/27 10:00–20:00开放 最晚进入19:00；09/30-10/06 10:00–20:00开放 最晚进入19:00；"
    "01/01-09/24 周二–周日 09:00–17:00开放 最晚进入16:00；"
    "09/28-09/29 周二–周日 09:00–17:00开放 最晚进入16:00；"
    "10/07-12/31 周二–周日 09:00–17:00开放 最晚进入16:00；"
    "01/01-09/24 周一 全天不开放；09/28-09/29 周一 全天不开放；"
    "10/07-12/31 周一 全天不开放；春节,劳动节,端午节 09:00–17:00开放；"
    "夜间开放时间另行公布。如本馆遇有重大活动或重要设备设施维修保养时，可根据需要临时闭馆，届时将告示公众。"
)

# Preserve the source envelope's flattened intervals alongside the exact sentence: the date reader must
# bind a visit to the numeric season in raw text instead of borrowing one of these all-week intervals.
SUZHOU_OPENING = {
    "status": "VERIFIED_PROVIDER",
    "source": "amap_business_opentime",
    "raw": SUZHOU_OPENING_RAW,
    "open": "10:00",
    "close": "20:00",
    "closure_notes": [
        "01/01-09/24 周一 全天不开放",
        "09/28-09/29 周一 全天不开放",
        "10/07-12/31 周一 全天不开放",
    ],
    "weekday_coverage": "UNRESOLVED",
    "intervals": [
        {"days": ["*"], "open": "10:00", "close": "20:00"},
        {"days": ["*"], "open": "10:00", "close": "20:00"},
        {"days": ["*"], "open": "01:00", "close": "09:00"},
        {"days": ["*"], "open": "09:00", "close": "17:00"},
        {"days": ["*"], "open": "09:00", "close": "17:00"},
        {"days": ["*"], "open": "07:00", "close": "12:00"},
        {"days": ["*"], "open": "09:00", "close": "17:00"},
        {"days": ["*"], "open": "01:00", "close": "09:00"},
        {"days": ["*"], "open": "07:00", "close": "12:00"},
        {"days": ["*"], "open": "09:00", "close": "17:00"},
    ],
}


def test_suzhou_numeric_season_and_weekday_rules_are_scoped_to_the_visit_date() -> None:
    saturday = verdict_for_date(
        SUZHOU_OPENING, "2026-12-05", arrival="2026-12-05T14:00:00+08:00"
    )
    assert saturday["verdict"] == OPEN_ON_DATE, saturday
    assert saturday["window"] == (9 * 60, 17 * 60), saturday

    monday = verdict_for_date(
        SUZHOU_OPENING, "2026-12-07", arrival="2026-12-07T14:00:00+08:00"
    )
    assert monday["verdict"] == CLOSED_ON_DATE, monday

    # In 2027 this special range includes Monday. It has no weekday restriction and owns a separate
    # 10:00–20:00 window, even though other seasons in the same sentence close Mondays.
    special_monday = verdict_for_date(
        SUZHOU_OPENING, "2027-09-27", arrival="2027-09-27T19:00:00+08:00"
    )
    assert special_monday["verdict"] == OPEN_ON_DATE, special_monday
    assert special_monday["window"] == (10 * 60, 20 * 60), special_monday


def test_suzhou_winter_arrival_does_not_borrow_the_other_seasons_evening_window() -> None:
    late = verdict_for_date(
        SUZHOU_OPENING, "2026-12-05", arrival="2026-12-05T18:00:00+08:00"
    )
    assert late["verdict"] == TIME_OUTSIDE_WINDOW, late
    assert late["window"] == (9 * 60, 17 * 60), late


def test_numeric_cross_year_range_does_not_fill_date_gaps_and_invalid_dates_stay_unknown() -> None:
    cross_year = {
        "status": "VERIFIED_PROVIDER",
        "raw": (
            "12/20-01/05 周一至周日 09:00–17:00；"
            "03/01-03/31 周一至周日 10:00–18:00"
        ),
        "intervals": [{"days": ["*"], "open": "09:00", "close": "18:00"}],
    }
    wrapped_season = verdict_for_date(
        cross_year, "2027-01-04", arrival="2027-01-04T14:00:00+08:00"
    )
    assert wrapped_season["verdict"] == OPEN_ON_DATE, wrapped_season
    assert wrapped_season["window"] == (9 * 60, 17 * 60), wrapped_season

    gap = verdict_for_date(
        cross_year, "2027-01-06", arrival="2027-01-06T14:00:00+08:00"
    )
    assert gap["verdict"] == DATE_SPECIFIC_UNKNOWN, gap

    invalid = verdict_for_date(
        cross_year, "2027-02-30", arrival="2027-02-30T14:00:00+08:00"
    )
    assert invalid["verdict"] == DATE_SPECIFIC_UNKNOWN, invalid


def test_notice_deference_keeps_the_existing_holiday_unknown_rule() -> None:
    deferred = {
        "status": "VERIFIED_PROVIDER",
        "raw": (
            "旺季4月11日至10月31日 周二至周日 08:30-17:00；"
            "淡季11月1日至3月31日 周二至周日 08:30-16:30；"
            "周一全天关闭；节假日营业时间以官方通知为准"
        ),
        "intervals": [{"days": ["*"], "open": "08:30", "close": "17:00"}],
    }
    holiday = verdict_for_date(
        deferred, "2026-10-01", arrival="2026-10-01T09:00:00+08:00"
    )
    assert holiday["verdict"] == DATE_SPECIFIC_UNKNOWN, holiday
    assert holiday["reason_code"] == "SOURCE_DEFERS_TO_NOTICE_FOR_A_HOLIDAY", holiday
    assert holiday["defers_to_notice"] is True, holiday


def test_numeric_weekday_windows_do_not_borrow_another_weekday_window() -> None:
    envelope = {
        "status": "VERIFIED_PROVIDER",
        "raw": (
            "12/01-12/31 周一 09:00–12:00；"
            "12/01-12/31 周二 14:00–17:00"
        ),
        "intervals": [{"days": ["*"], "open": "09:00", "close": "17:00"}],
    }
    monday_afternoon = verdict_for_date(
        envelope, "2026-12-07", arrival="2026-12-07T15:00:00+08:00"
    )
    assert monday_afternoon["verdict"] == TIME_OUTSIDE_WINDOW, monday_afternoon
    assert monday_afternoon["window"] == (9 * 60, 12 * 60), monday_afternoon


def test_lunar_holiday_only_hours_do_not_become_an_ordinary_daily_schedule() -> None:
    envelope = {
        "status": "VERIFIED_PROVIDER",
        "raw": "春节 09:00–17:00开放",
        "intervals": [{"days": ["*"], "open": "09:00", "close": "17:00"}],
    }
    ordinary_day = verdict_for_date(
        envelope, "2026-12-05", arrival="2026-12-05T14:00:00+08:00"
    )
    assert ordinary_day["verdict"] == DATE_SPECIFIC_UNKNOWN, ordinary_day


def test_invalid_or_incomplete_numeric_spans_do_not_fall_back_to_flattened_hours() -> None:
    for raw in (
        "13/01-13/31 周一至周日 09:00–17:00开放",
        "01/01-?? 周一至周日 09:00–17:00开放",
    ):
        envelope = {
            "status": "VERIFIED_PROVIDER",
            "raw": raw,
            "intervals": [{"days": ["*"], "open": "09:00", "close": "17:00"}],
        }
        verdict = verdict_for_date(
            envelope, "2026-12-05", arrival="2026-12-05T14:00:00+08:00"
        )
        assert verdict["verdict"] == DATE_SPECIFIC_UNKNOWN, (raw, verdict)


def test_native_prepare_uses_canonical_suzhou_source_without_a_false_opening_gap(signed_place) -> None:
    client, owner, _outsider, journey_id, *_ = signed_place
    visit_date = "2026-12-05"
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        journey.start_at = visit_date + "T08:00:00+08:00"
        journey.end_at = visit_date + "T22:00:00+08:00"
        session.commit()

    root = f"/api/v1/journeys/{journey_id}"
    created = client.post(root + "/agent/goal-tasks", headers=owner, json={
        "goal": "TEST_FIXTURE 2026-12-05 苏州博物馆",
        "model_consent": False,
        "online_research_consent": False,
    })
    assert created.status_code == 201, created.text
    task_id = created.json()["task_id"]
    draft = client.put(root + f"/agent/goal-tasks/{task_id}/draft", headers=owner, json={
        "expected_revision": 0,
        "days": [{"date": visit_date, "slots": [{
            "title": "苏州博物馆(本馆)", "time_of_day": "afternoon", "notes": "",
        }]}],
    })
    assert draft.status_code == 200, draft.text

    provider_object_id = "TESTFIX-ISSUE49-SUZHOU-" + uuid4().hex
    lead = {
        "id": f"amap:{provider_object_id}",
        "provider": "amap",
        "provider_object_id": provider_object_id,
        "name": "苏州博物馆(本馆)",
        "category": "museum",
        "latitude": 31.322948,
        "longitude": 120.627856,
        "coordinate_system": "GCJ02",
        "provider_provenance": "LIVE_PROVIDER",
        "region_status": "MATCHED",
    }
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        mission = session.get(JourneyMission, task_id)
        assert journey is not None and mission is not None
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        assert attach_canonical_places(session, journey, task, [lead])
        canonical_place_id = lead["canonical_place_id"]
        task["draft_artifact"]["days"][0]["slots"][0]["place_id"] = lead["id"]
        task["research_places"] = [lead]
        task["candidate_place_ids"] = [canonical_place_id]
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        canonical_place = session.get(Place, canonical_place_id)
        assert canonical_place is not None
        canonical_place.opening_hours_json = json.dumps(SUZHOU_OPENING, ensure_ascii=False)
        session.commit()

    prepared = client.post(
        root + f"/agent/goal-tasks/{task_id}/prepare-plan",
        headers={**owner, "Idempotency-Key": str(uuid4())},
        json={
            "expected_revision": 1,
            "schedule": [{
                "day_index": 0,
                "slot_index": 0,
                "start_time": "14:00",
                "end_time": "15:30",
            }],
        },
    )
    assert prepared.status_code == 201, prepared.text
    result = prepared.json()
    assert not any(gap["kind"] == "DATE_SPECIFIC_OPENING" for gap in result["gaps"]), result
    checks = result["opening_checks"]
    assert len(checks) == 1, checks
    assert checks[0]["verdict"] == OPEN_ON_DATE, checks
    assert checks[0]["window"] == [9 * 60, 17 * 60], checks

    with SessionLocal() as session:
        activity = session.scalar(select(Activity).where(
            Activity.plan_version_id == result["plan_version_id"]
        ))
        assert activity is not None
        stored = json.loads(activity.metadata_json or "{}").get("opening_on_date") or {}
    assert stored.get("verdict") == OPEN_ON_DATE, stored
    assert stored.get("window") == [9 * 60, 17 * 60], stored