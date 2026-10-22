"""Reading a provider's opening sentence against the day the traveller is actually there.

Written from a real row, not a constructed one: the walked journey's own 故宫博物院 carries this AMap
sentence (trial/results/20261022_v3_human_chrome/walk62-departure-readback-1.txt shows the place rows the
candidate bound), whose parsed intervals say ``days: ["*"]`` while the prose says 周一全天关闭.  A plan
that reads those intervals as "open every day" would send a traveller to a closed museum.  These arms pin
what the date reader may say and what it must refuse to say.
"""

from app.agent.goal_opening_date import (
    CLOSED_ON_DATE,
    DATE_SPECIFIC_UNKNOWN,
    OPEN_ON_DATE,
    TIME_OUTSIDE_WINDOW,
    verdict_for_date,
)

# Verbatim shape of what the live provider handed over for one real Beijing museum.
AMAP_MUSEUM = {
    "status": "VERIFIED_PROVIDER",
    "source": "amap_business_opentime",
    "raw": ("旺季4月11日至10月31日 周二至周日 08:30-17:00 16:00停止售票；淡季11月1日至3月31日 周二至周日 "
            "08:30-16:30 15:30停止售票；周一全天关闭（期间营业时间以官方通知为准）"),
    "open": "08:30", "close": "17:00",
    "intervals": [{"days": ["*"], "open": "08:30", "close": "17:00"}, {"days": ["*"], "open": "08:30", "close": "16:30"}],
    "closure_notes": ["周一全天关闭"], "weekday_coverage": "UNRESOLVED",
}


def test_a_thursday_visit_to_a_monday_closed_museum_is_served() -> None:
    verdict = verdict_for_date(AMAP_MUSEUM, "2026-12-03", arrival="2026-12-03T09:00:00+08:00")
    assert verdict["verdict"] == OPEN_ON_DATE, verdict
    # The window it quotes is the provider's own, not the flattened pair the parser stored -- and for a
    # December Thursday the provider's own sentence is the 淡季 half: 「淡季11月1日至3月31日 周二至周日
    # 08:30-16:30」.  This line read (8*60+30, 17*60) until the reader bound each window to the calendar
    # span written in the same clause; quoting 旺季's 17:00 here would tell a traveller an 16:45 arrival
    # is fine when the source says the museum stops selling tickets at 15:30 that season.
    assert verdict["window"] == (8 * 60 + 30, 16 * 60 + 30), verdict
    assert verdict["defers_to_notice"] is True, verdict


def test_a_winter_arrival_is_measured_against_the_winter_hours_not_the_summer_ones() -> None:
    """The season is a bound, not decoration.

    A Thursday at 16:45 sits inside 旺季's 17:00 close and outside 淡季's 16:30; answering OPEN for
    December would be quoting the wrong half of the sentence.
    """

    winter = verdict_for_date(AMAP_MUSEUM, "2026-12-03", arrival="2026-12-03T16:45:00+08:00")
    assert winter["verdict"] == TIME_OUTSIDE_WINDOW, winter
    assert winter["window"] == (8 * 60 + 30, 16 * 60 + 30), winter
    summer = verdict_for_date(AMAP_MUSEUM, "2026-06-11", arrival="2026-06-11T16:45:00+08:00")
    assert summer["verdict"] == OPEN_ON_DATE, summer
    assert summer["window"] == (8 * 60 + 30, 17 * 60), summer


def test_the_same_museum_on_a_monday_is_closed_and_says_which_sentence_said_so() -> None:
    verdict = verdict_for_date(AMAP_MUSEUM, "2026-11-30", arrival="2026-11-30T09:00:00+08:00")
    assert verdict["verdict"] == CLOSED_ON_DATE, verdict
    assert verdict["reason_code"] == "SOURCE_SAYS_CLOSED_ON_THIS_DAY", verdict
    assert "周一全天关闭" in str(verdict["source_text"]), verdict


def test_a_weekday_the_sentence_neither_serves_nor_closes_is_not_read_as_served() -> None:
    envelope = {"status": "VERIFIED_PROVIDER", "raw": "周三至周五 10:00-18:00", "intervals": []}
    assert verdict_for_date(envelope, "2026-12-05", arrival="11:00")["verdict"] == CLOSED_ON_DATE


def test_arriving_after_the_stated_last_entry_is_its_own_answer() -> None:
    verdict = verdict_for_date(AMAP_MUSEUM, "2026-12-04", arrival="2026-12-04T18:30:00+08:00")
    assert verdict["verdict"] == TIME_OUTSIDE_WINDOW, verdict
    assert verdict["reason_code"] == "ARRIVES_OUTSIDE_THE_STATED_WINDOW", verdict


def test_a_plain_hours_sentence_with_no_day_rule_is_served_on_any_day() -> None:
    envelope = {"status": "VERIFIED_PROVIDER", "raw": "09:00-21:00",
                "intervals": [{"days": ["*"], "open": "09:00", "close": "21:00"}]}
    assert verdict_for_date(envelope, "2026-12-07", arrival="19:40")["verdict"] == OPEN_ON_DATE
    assert verdict_for_date(envelope, "2026-12-07", arrival="22:10")["verdict"] == TIME_OUTSIDE_WINDOW


def test_a_deferred_period_without_an_arrival_time_stays_unknown() -> None:
    """No hour to match means the only claim left is the provider's own hedge, so nothing is settled."""

    verdict = verdict_for_date(AMAP_MUSEUM, "2026-12-03")
    assert verdict["verdict"] == DATE_SPECIFIC_UNKNOWN, verdict
    assert verdict["reason_code"] == "SOURCE_DEFERS_TO_NOTICE", verdict


def test_unparsable_or_absent_text_is_never_read_as_open() -> None:
    assert verdict_for_date({"status": "RAW_UNPARSED", "raw": "营业时间见店内公告", "intervals": []},
                            "2026-12-03", arrival="09:00")["verdict"] == DATE_SPECIFIC_UNKNOWN
    assert verdict_for_date({"status": "UNKNOWN", "raw": None, "intervals": []},
                            "2026-12-03", arrival="09:00")["verdict"] == DATE_SPECIFIC_UNKNOWN
    assert verdict_for_date(AMAP_MUSEUM, "", arrival="09:00")["reason_code"] == "DATE_NOT_GIVEN"


def test_a_yearly_range_closes_only_when_the_clause_says_it_closes() -> None:
    """The range shape is shared by 旺季/淡季 statements and by real yearly closures.

    Reading a season range as a closure would close a museum for most of the year, so only a clause that
    also carries a closure word can put days out of service.
    """

    season_only = {"status": "VERIFIED_PROVIDER", "raw": "旺季4月11日至10月31日 周二至周日 08:30-17:00",
                   "intervals": [{"days": ["*"], "open": "08:30", "close": "17:00"}]}
    assert verdict_for_date(season_only, "2026-06-03", arrival="09:00")["verdict"] == OPEN_ON_DATE
    winter = verdict_for_date(season_only, "2026-12-03", arrival="09:00")
    # Not CLOSED_ON_DATE -- that was this arm's point and it still holds.  It is no longer OPEN either:
    # the sentence reserves its hours to 4月11日至10月31日, and the only thing that could make December
    # open is the parsed interval's ``days: ["*"]``, which is the flattening this module exists to refuse.
    assert winter["verdict"] == DATE_SPECIFIC_UNKNOWN, winter
    assert winter["reason_code"] == "SOURCE_SEASON_NOT_STATED_FOR_THIS_DAY", winter

    closed_range = {"status": "VERIFIED_PROVIDER", "raw": "1月1日至1月3日 闭馆；周二至周日 09:00-17:00",
                    "intervals": [{"days": ["*"], "open": "09:00", "close": "17:00"}]}
    assert verdict_for_date(closed_range, "2026-01-02", arrival="09:30")["verdict"] == CLOSED_ON_DATE
    assert verdict_for_date(closed_range, "2026-06-03", arrival="09:30")["verdict"] == OPEN_ON_DATE


def test_the_comma_joined_sentence_the_provider_actually_writes_is_read_by_season() -> None:
    """The unit above used 「；」 between the season and the closure; the live row uses 「，」.

    Joined that way, one clause carried both 淡季11月1日至3月31日 and 周一全天关闭, the clause said
    关闭, and the seasonal range was read as a closure for the whole winter -- a Thursday in December was
    reported as the museum being shut.  Splitting on the comma keeps the range and the weekly closure in
    separate clauses, which is how the sentence is meant to be read.
    """

    as_written = ("旺季4月1日至10月31日 周二至周日 08:30-17:00 16:00停止检票，淡季11月1日至3月31日 "
                  "周二至周日 08:30-16:30 15:30停止检票，周一全天关闭，节假日营业时间以官方通知为准")
    thursday = verdict_for_date({"raw": as_written}, "2026-12-03", arrival="2026-12-03T09:00:00+08:00")
    assert thursday["verdict"] == OPEN_ON_DATE, thursday
    assert thursday["window"] == (8 * 60 + 30, 16 * 60 + 30), thursday
    assert verdict_for_date({"raw": as_written}, "2026-12-07",
                            arrival="2026-12-07T09:00:00+08:00")["verdict"] == CLOSED_ON_DATE


def test_an_always_open_venue_that_states_its_bound_as_24_00_is_not_called_unanswered() -> None:
    """「周一至周日 00:00-24:00」 is a stated window, and 24:00 is its end, not an invalid hour.

    Dropping the pair made a street the provider says serves every hour look like a place nobody had
    answered for, and the reason code then claimed the sentence did not name any weekday when it names
    all seven -- the line printed beside it on the traveller's screen quoted that very sentence.
    """

    street = {"status": "VERIFIED_PROVIDER", "raw": "周一至周日 00:00-24:00", "intervals": []}
    evening = verdict_for_date(street, "2026-12-07", arrival="2026-12-07T19:00:00+08:00")
    assert evening["verdict"] == OPEN_ON_DATE, evening
    assert evening["window"] == (0, 24 * 60), evening
    # Without an hour to match there is nothing to settle, and the reason says which half is missing.
    no_hour = verdict_for_date(street, "2026-12-07")
    assert no_hour["verdict"] == DATE_SPECIFIC_UNKNOWN, no_hour
    assert no_hour["reason_code"] == "NO_ARRIVAL_GIVEN", no_hour
    no_bound = {"status": "VERIFIED_PROVIDER", "raw": "周一到周五有人值班", "intervals": []}
    assert verdict_for_date(no_bound, "2026-12-07", arrival="10:00")["reason_code"] == "NO_WINDOW_STATED"


def test_a_statutory_holiday_a_deferred_sentence_covers_is_not_claimed_open() -> None:
    """The weekday rule serves 10月1日; the same sentence says holidays follow an official notice.

    Only the three fixed dates are treated as holidays, because 春节/端午/中秋 move with the lunar
    calendar and no stored field says which year they fall in.
    """

    national_day = verdict_for_date(AMAP_MUSEUM, "2026-10-01", arrival="2026-10-01T09:00:00+08:00")
    assert national_day["verdict"] == DATE_SPECIFIC_UNKNOWN, national_day
    assert national_day["reason_code"] == "SOURCE_DEFERS_TO_NOTICE_FOR_A_HOLIDAY", national_day
    assert national_day["holiday"] == "国庆节", national_day
    # A venue whose sentence carries no hedge is not handed to a notice that was never written.
    plain = {"status": "VERIFIED_PROVIDER", "raw": "周二至周日 09:00-17:00", "intervals": []}
    assert verdict_for_date(plain, "2026-10-01", arrival="09:30")["verdict"] == OPEN_ON_DATE


# -------------------------------------------------------------------------- the same door as the traveller uses
#
# The unit reads above pin the reader itself.  These two walk the plan path the departure card calls, so
# the sentence below is about what the traveller sees, not about a function in isolation.

import json  # noqa: E402
from uuid import uuid4  # noqa: E402

from sqlalchemy import select  # noqa: E402
from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: E402,F401  (fixtures are imported on purpose)
from app.agent.goal_place_identity import attach_canonical_places  # noqa: E402
from app.db.models import Activity, Journey, JourneyMission, Place  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

LEAD = {"id": "amap:TESTFIX-OPENDATE-HALL", "provider": "amap", "provider_object_id": "TESTFIX-OPENDATE-HALL",
        "name": "TEST_FIXTURE 博物馆", "category": "museum", "latitude": 39.92, "longitude": 116.40,
        "coordinate_system": "GCJ02", "provider_provenance": "LIVE_PROVIDER", "region_status": "MATCHED"}


def _candidate_on(client, owner, journey_id, *, visit_date: str, arrival: str) -> tuple[str, str, list[dict], dict]:
    root = f"/api/v1/journeys/{journey_id}"
    with SessionLocal() as session:
        trip = session.get(Journey, journey_id)
        trip.start_at = visit_date + "T08:00:00+08:00"
        trip.end_at = visit_date + "T22:00:00+08:00"
        session.commit()
    task_id = client.post(root + "/agent/goal-tasks", headers=owner, json={
        "goal": "TEST_FIXTURE 上午看展", "model_consent": False, "online_research_consent": False}).json()["task_id"]
    draft = client.put(root + f"/agent/goal-tasks/{task_id}/draft", headers=owner, json={"expected_revision": 0,
        "days": [{"date": visit_date, "slots": [{"title": "TEST_FIXTURE 博物馆", "time_of_day": "morning",
                                                "notes": ""}]}]})
    assert draft.status_code == 200, draft.text
    with SessionLocal() as session:
        mission = session.get(JourneyMission, task_id)
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        lead = dict(LEAD)
        assert attach_canonical_places(session, session.get(Journey, journey_id), task, [lead])
        task["draft_artifact"]["days"][0]["slots"][0]["place_id"] = lead["id"]
        task["research_places"] = [lead]
        task["candidate_place_ids"] = [lead["canonical_place_id"]]
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        # The provider's own aggregate sentence, in the shape the live research leg stores it.
        row = session.get(Place, lead["canonical_place_id"])
        row.opening_hours_json = json.dumps({"status": "VERIFIED_PROVIDER", "source": "amap_business_opentime",
                                            "raw": AMAP_MUSEUM["raw"], "open": "08:30", "close": "17:00",
                                            "intervals": AMAP_MUSEUM["intervals"],
                                            "closure_notes": AMAP_MUSEUM["closure_notes"],
                                            "weekday_coverage": "UNRESOLVED"}, ensure_ascii=False)
        session.commit()
    answer = client.post(root + f"/agent/goal-tasks/{task_id}/prepare-plan",
                         headers={**owner, "Idempotency-Key": str(uuid4())},
                         json={"expected_revision": 1, "schedule": [{"day_index": 0, "slot_index": 0,
                                                                    "start_time": arrival, "end_time": "12:00"}]})
    assert answer.status_code == 201, answer.text
    plan_id = answer.json()["plan_version_id"]
    with SessionLocal() as session:
        row = session.scalar(select(Activity).where(Activity.plan_version_id == plan_id))
        # What the row itself carries is the part a later screen reads without re-asking anyone.
        stored = json.loads(row.metadata_json or "{}").get("opening_on_date") or {}
    return task_id, plan_id, answer.json()["gaps"], stored


def test_a_monday_at_a_monday_closed_museum_is_its_own_line_with_the_sentence_behind_it(signed_place) -> None:
    client, owner, outsider, journey_id, *_ = signed_place
    _task_id, _plan, gaps, stored = _candidate_on(client, owner, journey_id, visit_date="2026-11-30",
                                                  arrival="09:00")
    rows = [gap for gap in gaps if gap["kind"] == "DATE_SPECIFIC_OPENING"]
    assert len(rows) == 1, gaps
    assert rows[0]["resolution"] == "ASK_AGENT_TO_REPLAN_THE_DAY", rows
    assert rows[0]["detail"]["verdict"] == "CLOSED_ON_DATE", rows
    assert "周一全天关闭" in rows[0]["detail"]["source_text"], rows
    assert stored.get("verdict") == "CLOSED_ON_DATE", stored


def test_the_same_museum_on_a_thursday_at_half_past_nine_asks_for_nothing(signed_place) -> None:
    client, owner, outsider, journey_id, *_ = signed_place
    _task_id, _plan, gaps, stored = _candidate_on(client, owner, journey_id, visit_date="2026-12-03",
                                                  arrival="09:00")
    assert [gap["kind"] for gap in gaps] == ["ADMISSION_PRICE"], gaps
    assert stored.get("verdict") == "OPEN_ON_DATE", stored
