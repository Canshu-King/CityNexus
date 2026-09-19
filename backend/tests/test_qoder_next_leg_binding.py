"""ORD-0001: the Next leg is bound to a trustworthy Now, never to an index.

``_execution_truth`` used to pick the leg with ``legs[current_index]``.  Two legal
states push ``current_index`` to ``len(activities)`` - a stale cursor, and a
journey whose activities are all terminal - and in any plan that carries more legs
than activities (arrival/departure transfers do exactly that) the guard
``0 <= current_index < len(legs)`` is satisfied by an index that is past the end of
the *activities*.  The result was a projection with no Now, no Next, and a live
NextLeg: mode, ETA and leg id for a step the traveller is not standing at.

Mission 002 A says a stale projection must be empty in all three slots.  This file
pins the leg to the same evidence the rest of the projection needs - a resolved
Now - and keeps the two shapes that are allowed to show a leg:

  * a valid cursor with a successor (the leg is how you get there);
  * a valid cursor on the final activity (the leg is the transfer out of where the
    traveller actually is; there is no Next activity, and this is the behaviour the
    order prescribes, so it is pinned rather than left implicit).
"""

from __future__ import annotations

import pytest

from app.db.models import Activity, JourneyLeg
from app.operations.v9 import _execution_truth

_PLAN = "plan-v1"
# One leg more than activities: 3 stops, 4 transfers (arrival + 3 hops), which is
# the shape that used to leak.  Legs are indexable one past the last activity.
_ACTIVITY_COUNT = 3
_LEG_COUNT = 4


def _activity(index: int, *, status: str = "PENDING") -> Activity:
    return Activity(
        id=f"act-{index}",
        plan_version_id=_PLAN,
        sequence_no=index,
        activity_type="SIGHTSEE",
        title=f"Activity {index}",
        start_at=f"2026-10-10T{9 + index:02d}:00:00+08:00",
        end_at=f"2026-10-10T{10 + index:02d}:00:00+08:00",
        travel_from_prev_min=10,
        estimated_cost_minor=0,
        currency="CNY",
        status=status,
        locked=False,
        metadata_json="{}",
        created_at="2026-10-10T00:00:00+08:00",
        updated_at="2026-10-10T00:00:00+08:00",
    )


def _leg(index: int) -> JourneyLeg:
    return JourneyLeg(
        id=f"leg-{index}",
        journey_id="j1",
        plan_version_id=_PLAN,
        sequence_no=index,
        from_key=f"place-{index}",
        to_key=f"place-{index + 1}",
        mode="AUTO" if index >= _ACTIVITY_COUNT else "walk",
        depart_at="2026-10-10T09:00:00+08:00",
        arrive_at="2026-10-10T09:20:00+08:00",
        duration_min=20 + index,
        distance_m=900,
        cost_status="UNKNOWN",
        walking_min=15,
        transfers=0,
        reliability_score=0.0,
    )


def _activities(*, all_terminal: bool = False) -> list[Activity]:
    status = "COMPLETED" if all_terminal else "PENDING"
    return [_activity(index, status=status) for index in range(_ACTIVITY_COUNT)]


def _legs() -> list[JourneyLeg]:
    return [_leg(index) for index in range(_LEG_COUNT)]


@pytest.mark.parametrize(
    "cursor,expected_status",
    [("act-from-superseded-plan", "STALE"), (None, "ABSENT_FALLBACK")],
)
def test_no_trustworthy_now_projects_no_next_leg(cursor: str, expected_status: str) -> None:
    """(a) legs outnumber activities and there is no Now: every leg slot stays empty.

    ``None`` here is the finished-journey shape - the absent cursor falls back to the
    first pending activity, finds none, and lands past the end just like a stale
    cursor does.  Both used to hand out ``leg-3`` with mode AUTO and a real ETA.
    """
    activities = _activities(all_terminal=cursor is None)
    projection = _execution_truth(activities, _legs(), cursor)

    assert projection["cursor_status"] == expected_status
    assert projection["now_activity_id"] is None, (
        "the premise of this case is that nothing is a trustworthy Now: "
        f"{projection['now_activity_id']}"
    )
    assert projection["next_activity_id"] is None
    assert len(_legs()) > len(activities), (
        "the fixture stopped being the leaking shape; this case measures nothing"
    )
    assert projection["next_leg_id"] is None, (
        "a NextLeg was projected without a Now: "
        f"{projection['next_leg_id']} / {projection['next_mode']} / "
        f"{projection['next_eta_min']}"
    )
    assert projection["next_mode"] == "NONE"
    assert projection["next_eta_min"] == 0


def test_a_valid_cursor_with_a_successor_carries_its_next_state() -> None:
    """(b) VALID cursor plus a non-empty Next activity means Next has a state.

    The Edge and v10 surfaces read ``next_state`` to decide what to render; a
    projection that names a next activity without saying what state it is in gives
    them nothing to be correct with.
    """
    projection = _execution_truth(_activities(), _legs(), "act-1")

    assert projection["cursor_status"] == "VALID"
    assert projection["next_activity_id"] == "act-2"
    assert projection["next_state"], "a projected Next activity must carry its state"
    assert projection["next_state"] == "PENDING"
    assert projection["next_leg_id"] == "leg-1"
    assert projection["next_mode"] == "walk"
    assert projection["next_eta_min"] == 21


def test_the_final_activity_keeps_the_transfer_out_of_it_and_no_next_activity() -> None:
    """Pinned behaviour, not a new rule: Now is trustworthy, so its leg is real.

    The traveller is standing at the last stop and ``leg-2`` is the transfer away
    from it, while there is genuinely no next activity.  This is what the order's
    binding condition (a trustworthy Now) produces, so it is recorded here instead
    of being left to chance - if the product later decides a NextLeg requires a
    Next, this is the node that has to change on purpose.
    """
    projection = _execution_truth(_activities(), _legs(), "act-2")

    assert projection["cursor_status"] == "VALID"
    assert projection["now_activity_id"] == "act-2"
    assert projection["next_activity_id"] is None
    assert projection["next_state"] is None
    assert projection["next_leg_id"] == "leg-2"
    assert projection["next_mode"] == "walk"
    assert projection["next_eta_min"] == 22
