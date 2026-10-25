from types import SimpleNamespace

from app.simulation.coverage import summarize_activity_coverage


def activity(
    activity_id,
    start_at,
    place_id,
    *,
    status="PLANNED",
    activity_type="SIGHTSEE",
    metadata_json=None,
):
    return SimpleNamespace(
        id=activity_id,
        start_at=start_at,
        place_id=place_id,
        activity_type=activity_type,
        status=status,
        metadata_json=metadata_json or "{}",
        title=activity_id,
    )


def test_two_days_each_have_two_named_places():
    rows = summarize_activity_coverage(
        [
            activity("d1-a", "2026-12-03T09:00:00+08:00", "place-a"),
            activity("d1-b", "2026-12-03T14:00:00+08:00", "place-b"),
            activity("d2-a", "2026-12-04T09:00:00+08:00", "place-c"),
            activity("d2-b", "2026-12-04T14:00:00+08:00", "place-d"),
        ],
        [],
        journey_timezone="Asia/Shanghai",
    )

    assert [row["date"] for row in rows] == ["2026-12-03", "2026-12-04"]
    assert [row["distinct_place_count"] for row in rows] == [2, 2]
    assert [row["missing_for_target"] for row in rows] == [0, 0]
    assert rows[0]["named_activity_ids"] == ["d1-a", "d1-b"]


def test_repeated_place_counts_once_but_keeps_both_activity_ids():
    rows = summarize_activity_coverage(
        [
            activity("morning", "2026-12-03T09:00:00+08:00", "same-place"),
            activity("afternoon", "2026-12-03T14:00:00+08:00", "same-place"),
        ],
        [],
        journey_timezone="Asia/Shanghai",
    )

    assert rows[0]["distinct_place_count"] == 1
    assert rows[0]["distinct_place_ids"] == ["same-place"]
    assert rows[0]["named_activity_ids"] == ["morning", "afternoon"]
    assert rows[0]["missing_for_target"] == 1


def test_placeholder_and_free_time_do_not_count_as_named_places():
    rows = summarize_activity_coverage(
        [
            activity(
                "research-placeholder",
                "2026-12-03T11:00:00+08:00",
                None,
                activity_type="FREE_TIME",
                metadata_json='{"preparation_gaps":["PLACE_REQUIRED"]}',
            ),
            activity(
                "ordinary-free-time",
                "2026-12-03T15:00:00+08:00",
                None,
                activity_type="FREE_TIME",
            ),
            activity(
                "free-time-with-place",
                "2026-12-03T15:30:00+08:00",
                "place-ignored-for-free-time",
                activity_type="FREE_TIME",
            ),
            activity("unnamed-sightsee", "2026-12-03T16:00:00+08:00", None),
        ],
        [],
        journey_timezone="Asia/Shanghai",
    )

    assert rows[0]["distinct_place_count"] == 0
    assert rows[0]["named_activity_ids"] == []
    assert rows[0]["placeholder_count"] == 2
    assert rows[0]["placeholder_activity_ids"] == [
        "research-placeholder",
        "unnamed-sightsee",
    ]
    assert rows[0]["missing_for_target"] == 2


def test_run_completions_are_separate_from_inherited_completed_activities():
    rows = summarize_activity_coverage(
        [
            activity("before-run", "2026-12-03T09:00:00+08:00", "old-place", status="COMPLETED"),
            activity("during-run", "2026-12-03T14:00:00+08:00", "new-place", status="COMPLETED"),
        ],
        ["during-run"],
        journey_timezone="Asia/Shanghai",
    )

    assert rows[0]["run_completed_place_count"] == 1
    assert rows[0]["run_completed_activity_ids"] == ["during-run"]
    assert rows[0]["inherited_completed_place_count"] == 1
    assert rows[0]["inherited_completed_activity_ids"] == ["before-run"]


def test_aware_utc_timestamps_group_by_journey_local_date():
    rows = summarize_activity_coverage(
        [
            activity("late-d1", "2026-12-03T15:59:00Z", "place-a"),
            activity("early-d2", "2026-12-03T16:01:00Z", "place-b"),
        ],
        [],
        journey_timezone="Asia/Shanghai",
    )

    assert [row["date"] for row in rows] == ["2026-12-03", "2026-12-04"]
    assert rows[0]["named_activity_ids"] == ["late-d1"]
    assert rows[1]["named_activity_ids"] == ["early-d2"]


def test_required_empty_date_is_reported_with_full_target_gap():
    rows = summarize_activity_coverage(
        [
            activity("d2-a", "2026-12-04T09:00:00+08:00", "place-a"),
            activity("d2-b", "2026-12-04T14:00:00+08:00", "place-b"),
        ],
        [],
        journey_timezone="Asia/Shanghai",
        required_dates=["2026-12-03", "2026-12-04"],
    )

    assert [row["date"] for row in rows] == ["2026-12-03", "2026-12-04"]
    assert rows[0]["distinct_place_count"] == 0
    assert rows[0]["named_activity_ids"] == []
    assert rows[0]["missing_for_target"] == 2
    assert rows[1]["distinct_place_count"] == 2
    assert rows[1]["missing_for_target"] == 0
