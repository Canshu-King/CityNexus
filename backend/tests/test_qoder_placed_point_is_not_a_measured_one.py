"""A point this planner placed around the city centre must not read as one anybody measured.

Measured at the authoritative tip `2f4abb238a004a19fbde2bd3f998536dbe967ae9`: an anchor carrying no
coordinate was given one invented around the city centre (`center_lat - 0.015` and friends), and
`_distance_minutes` turns a pair of points into minutes on the traveller's plan while
`_solve_day_assignment` sorts the days on that number.  Probed on the real functions: a placed
arrival to a real POI came out as 590 minutes, against 3 minutes when both points sit at the same
placed point - so an unmeasured coordinate was deciding how far apart two stops were, and the
`Place` row it was written into said nothing about that.

`Place.coordinate_system` already answers "what system is the stored geometry in"; its sibling
`source_coordinate_system` answers "what did a provider actually hand us", and a point this
planner invented came from no provider at all.  These tests pin that the two are no longer the
same value, and that a measured anchor is untouched.

They call the real functions with a stand-in journey and a recording session, so what is asserted
is what the code emits rather than what it was asked to emit.
"""

from __future__ import annotations

import ast
import json
from datetime import timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=8))


def _journey():
    from app.db.models import Journey

    return Journey(
        id="coord-arm-journey",
        traveler_id="coord-arm-traveler",
        title="coordinate arm",
        city_code="CN-TIANJIN",
        timezone="Asia/Shanghai",
        start_at="2026-11-03T09:00:00+08:00",
        end_at="2026-11-05T17:00:00+08:00",
        budget_currency="CNY",
        budget_amount_minor=90000,
        planning_mode="balanced",
        status="DRAFT",
        active_plan_version_id=None,
        current_activity_id=None,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def _anchor(location: str | None, latitude=None, longitude=None) -> dict:
    from app.db.models import JourneyTripContext

    return {
        "at": "2026-11-03T09:00:00+08:00",
        "location": location,
        "latitude": latitude,
        "longitude": longitude,
    }


class _RecordingSession:
    def __init__(self) -> None:
        self.added = []

    def scalar(self, *_a, **_k):
        return None

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        return None


def _places_for(anchor: dict) -> list:
    from app.planning.authoritative_v12 import _structural_nodes

    session = _RecordingSession()
    _structural_nodes(
        session=session,
        journey=_journey(),
        stay=None,
        ordered_days=[],
        day_count=1,
        places={},
        arrival=anchor,
        departure=dict(anchor),
        c4_ids=[],
        commitment_anchors={},
    )
    return session.added


def _placed_marker() -> str:
    """Lazy, so this file collects against an unmodified tree."""

    from app.planning import authoritative_v12

    return authoritative_v12.COORDINATE_PLACED_BY_PLANNER


# --------------------------------------------------------- R1: the row says which it is


def test_r1_a_point_the_planner_placed_does_not_claim_a_provider_measured_it() -> None:
    """The before-fix reading: `source_coordinate_system` NULL, exactly like a measured point."""

    places = {row.category: row for row in _places_for(_anchor("Beijing South Station"))}

    for category, row in places.items():
        assert row.source_coordinate_system == _placed_marker(), (category, row.source_coordinate_system)


def test_r1b_the_metadata_says_the_same_thing_in_the_shape_readers_already_parse() -> None:
    places = {row.category: json.loads(row.metadata_json) for row in _places_for(_anchor(None))}

    for category, metadata in places.items():
        assert metadata["coordinates_declared"] is False, (category, metadata)


# ------------------------------------------------- R2: a measured coordinate is untouched


def test_r2_an_anchor_that_came_with_a_coordinate_is_left_as_it_was() -> None:
    places = {row.category: row for row in _places_for(_anchor("Beijing South Station", 39.9, 116.4))}

    for category, row in places.items():
        assert row.latitude == 39.9 and row.longitude == 116.4, (category, row.latitude, row.longitude)
        assert row.source_coordinate_system is None, (category, row.source_coordinate_system)
        assert json.loads(row.metadata_json)["coordinates_declared"] is True, category


def test_r2b_a_measured_coordinate_is_never_relabelled_even_when_the_place_is_new() -> None:
    """The other direction, so the fix cannot pass by labelling every row."""

    places = _places_for(_anchor("Tianjin Station", 39.13, 117.2))
    assert all(row.source_coordinate_system is None for row in places), places


# ------------------------------------------- R3: the number this actually feeds is real


def test_r3_the_minutes_a_placed_point_produces_are_still_derived_not_declared() -> None:
    """Why the marking matters: the real `_distance_minutes` turns two points into minutes, and
    those minutes are what `_solve_day_assignment` sorts the days on.  A placed point next to a
    real one reads as a very long walk, so a reader with no way to tell the two apart prices the
    traveller's day on a number nobody measured."""

    from datetime import datetime

    from app.planning.authoritative_v12 import ComposeNode, _city_center, _distance_minutes

    center_lat, center_lon = _city_center(_journey())
    start = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)

    def node(key: str, lat: float, lon: float) -> ComposeNode:
        return ComposeNode(
            key=key,
            title=key,
            role="ACTIVITY",
            latitude=lat,
            longitude=lon,
            place_id=key,
            day_index=0,
            start_at=start,
            end_at=start + timedelta(minutes=30),
        )

    placed = node("placed", center_lat - 0.015, center_lon - 0.02)
    real_poi = node("poi", center_lat + 0.9, center_lon + 1.1)

    minutes = _distance_minutes(placed, real_poi)
    assert minutes > 60, minutes
    # And the same two points at the same place read as the floor, which is what makes the
    # fabricated one indistinguishable from a measured short hop.
    assert _distance_minutes(placed, node("same", center_lat - 0.015, center_lon - 0.02)) <= 5


# ------------------------------------------------------ R4: the writer cannot drift back


def test_r4_both_planners_mark_a_placed_anchor_point() -> None:
    """`stay_mobility.build_candidate_nodes` places points the same way, and the planner is the
    one that writes the `Place` rows - so the marking has to exist where the row is written, and
    the second placer has to be the reason it cannot be forgotten there."""

    planner = (BACKEND / "app" / "planning" / "authoritative_v12.py").read_text(encoding="utf-8")
    ast.parse(planner)
    assert "COORDINATE_PLACED_BY_PLANNER" in planner
    assert "coordinate_origin=" in planner
    # Both anchors take the decision independently: neither may inherit the other's answer.
    assert planner.count("COORDINATE_PLACED_BY_PLANNER if") == 2, (
        "one of the two anchors stopped declaring where its point came from"
    )

    mobility = (BACKEND / "app" / "stay_mobility.py").read_text(encoding="utf-8")
    ast.parse(mobility)
    assert 'center.get("latitude"' in mobility, "the second placer no longer places points"
