from datetime import datetime, timezone

import pytest

from app.agent.journey_intent import (
    canonical_intent_dimension,
    intent_is_active,
    resolve_intent_scope,
    should_require_clarification,
)


NOW = datetime(2026, 10, 7, 2, 0, tzinfo=timezone.utc)


def test_rest_of_today_uses_journey_local_timezone():
    scope = resolve_intent_scope(
        scope_kind="REST_OF_TODAY",
        now=NOW,
        timezone_name="Asia/Tokyo",
    )
    assert scope.local_date == "2026-10-07"
    assert scope.ends_at == "2026-10-07T15:00:00+00:00"


def test_next_morning_is_future_scoped_not_immediately_active():
    scope = resolve_intent_scope(
        scope_kind="NEXT_MORNING",
        now=NOW,
        timezone_name="Asia/Tokyo",
    )
    assert scope.local_date == "2026-10-08"
    assert scope.starts_at == "2026-10-07T20:00:00+00:00"
    assert scope.ends_at == "2026-10-08T03:00:00+00:00"


def test_remaining_journey_may_span_overnight():
    scope = resolve_intent_scope(
        scope_kind="REMAINING_JOURNEY",
        now=NOW,
        timezone_name="Asia/Tokyo",
        journey_end_at="2026-10-10T09:00:00+00:00",
    )
    assert scope.ends_at == "2026-10-10T09:00:00+00:00"
    assert scope.local_date is None


def test_unknown_scope_fails_closed():
    with pytest.raises(ValueError, match="UNRESOLVED_INTENT_SCOPE"):
        resolve_intent_scope(
            scope_kind="SOMETIME",
            now=NOW,
            timezone_name="Asia/Tokyo",
        )


def test_expired_temporary_intent_is_not_active():
    assert intent_is_active(
        status="ACTIVE",
        starts_at="2026-10-06T00:00:00+00:00",
        ends_at="2026-10-07T01:59:59+00:00",
        now=NOW,
    ) is False


def test_active_temporary_intent_is_active_inside_scope():
    assert intent_is_active(
        status="ACTIVE",
        starts_at="2026-10-07T00:00:00+00:00",
        ends_at="2026-10-07T15:00:00+00:00",
        now=NOW,
    ) is True


def test_temporary_pace_and_walking_dimensions_are_not_global_preference_keys():
    assert canonical_intent_dimension(intent_kind="PACE") == "journey-intent:pace"
    assert canonical_intent_dimension(intent_kind="WALKING_LIMIT") == "journey-intent:walking"


def test_accessibility_need_is_not_flattened_to_soft_journey_intent():
    assert canonical_intent_dimension(intent_kind="ACCESSIBILITY_NEED") == "capability"


def test_ambiguous_goal_requires_clarification():
    assert should_require_clarification(
        confidence=0.9,
        scope_resolved=True,
        constraint_count=0,
        intent_kind="GENERAL_GOAL",
    ) is True


def test_grounded_bounded_intent_can_proceed():
    assert should_require_clarification(
        confidence=0.86,
        scope_resolved=True,
        constraint_count=2,
        intent_kind="WALKING_LIMIT",
    ) is False
