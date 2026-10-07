"""An unnamed journey anchor must not become a place called "Arrival" on the traveller's plan.

Measured at the authoritative tip `2f4abb238a004a19fbde2bd3f998536dbe967ae9`: an anchor whose
row carries no `location` fell back to `kind.title()` in both `_anchor` implementations, so the
moment the traveller did give became the *name* of the place, and the two planners that build
node titles out of it wrote two stops called "Arrival" and "Departure" into `Place` rows and
`GraphNode`s - at coordinates invented around the city centre.  The role word is not somewhere
anyone can arrive at, and it is the one thing on every plan guaranteed to be there, so it is the
worst possible place for a fabrication.

These tests call the real production functions with a stand-in journey and no database rows, so
what is asserted is what the code emits rather than what it was asked to emit:

* R1 reads `_anchor` in both modules: a named anchor keeps its name, an unnamed one says null
  and marks the state, and the moment always answers;
* R2 runs the real `_structural_nodes` and reads the `Place` rows it writes: the titles are the
  honest ones, and a place the traveller did name is left exactly as it was;
* R3 pins the state onto the place metadata, so "we placed this for you" is distinguishable from
  "this is where you are going";
* R4 asserts the writers no longer store the role word, because that is where the fabrication
  enters the database rather than merely leaving it.

Reverting the product change leaves R1, R2 and R4 red with named assertions; R3 is left green on
purpose - it describes what an unnamed anchor already was before this change.
"""

from __future__ import annotations

import ast
from datetime import timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

TZ = timezone(timedelta(hours=8))


def _journey():
    from app.db.models import Journey

    return Journey(
        id="anchor-arm-journey",
        traveler_id="anchor-arm-traveler",
        title="anchor arm",
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


def _context(raw: str):
    from app.db.models import JourneyTripContext

    return JourneyTripContext(
        journey_id="anchor-arm-journey",
        arrival_anchor_json=raw,
        departure_anchor_json=raw,
        party_size=1,
        occupancy_json="{}",
        stay_budget_amount_minor=0,
        stay_budget_currency="CNY",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


class _RecordingSession:
    """The two things `_structural_nodes` does to the session, and nothing else."""

    def __init__(self) -> None:
        self.added = []

    def scalar(self, *_a, **_k):
        return None

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        return None


def _places_for(raw: str) -> list:
    from app.planning.authoritative_v12 import _anchor, _structural_nodes

    journey, context = _journey(), _context(raw)
    session = _RecordingSession()
    _structural_nodes(
        session=session,
        journey=journey,
        stay=None,
        ordered_days=[],
        day_count=1,
        places={},
        arrival=_anchor(context, journey, "arrival"),
        departure=_anchor(context, journey, "departure"),
        c4_ids=[],
        commitment_anchors={},
    )
    return session.added


def _unarmed_constants() -> dict[str, str]:
    """Resolved lazily so this file collects against an unmodified tree.

    A module-level import of a name the old tree does not have would turn the reverse-control
    run into one collection error, which says nothing about which requirement was unmet.
    """

    from app.core import temporal

    return {
        "arrival": temporal.ANCHOR_ARRIVAL_UNNAMED,
        "departure": temporal.ANCHOR_DEPARTURE_UNNAMED,
    }


# --------------------------------------------------------------------------- R1: the reader


def test_r1_an_unnamed_anchor_reads_null_and_says_it_was_never_named() -> None:
    from app.planning.authoritative_v12 import _anchor

    journey, context = _journey(), _context("{}")
    arrival = _anchor(context, journey, "arrival")

    assert arrival["location"] is None, arrival
    assert arrival["location_declared"] is False, arrival
    # The moment is the journey's own window and is never in doubt.
    assert arrival["at"] == journey.start_at, arrival


def test_r1b_both_modules_read_an_anchor_the_same_way() -> None:
    """Two implementations of one shape is how two answers get to exist."""

    from app.planning.authoritative_v12 import _anchor as planner_anchor
    from app.stay_mobility import _anchor as mobility_anchor

    journey, context = _journey(), _context("{}")
    for kind in ("arrival", "departure"):
        one = planner_anchor(context, journey, kind)
        other = mobility_anchor(context, journey, kind)
        assert one["location"] == other["location"] is None, (kind, one, other)
        assert one["location_declared"] == other["location_declared"] is False, (kind, one, other)


def test_r1c_a_place_the_traveller_named_is_left_exactly_as_it_was() -> None:
    from app.planning.authoritative_v12 import _anchor

    journey = _journey()
    context = _context('{"at": "2026-11-03T09:00:00+08:00", "location": "Beijing South Station"}')
    arrival = _anchor(context, journey, "arrival")

    assert arrival["location"] == "Beijing South Station", arrival
    assert arrival["location_declared"] is True, arrival


# ------------------------------------------------------------- R2: what reaches the plan


def test_r2_an_unnamed_anchor_is_not_written_into_a_place_as_arrival() -> None:
    """The reading the traveller would have got: `name='Arrival'` on a real row."""

    constants = _unarmed_constants()
    places = _places_for("{}")
    titles = {row.name for row in places}

    assert "Arrival" not in titles, titles
    assert "Departure" not in titles, titles
    assert constants["arrival"] in titles, titles
    assert constants["departure"] in titles, titles


def test_r2b_a_named_anchor_still_becomes_a_place_with_that_name() -> None:
    places = _places_for(
        '{"at": "2026-11-03T09:00:00+08:00", "location": "Tianjin Station"}'
    )
    titles = {row.name for row in places}

    assert titles == {"Tianjin Station"}, titles


def test_r2c_the_candidate_node_builder_uses_the_same_honest_titles() -> None:
    """The second planner.  Its titles were the role words too, so fixing one leaves the
    fabrication on screen for every journey that goes through it."""

    source = (BACKEND / "app" / "stay_mobility.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert 'title=arrival["location"]' not in source, (
        "the candidate node still titles itself from the raw anchor location"
    )
    assert 'title=departure["location"]' not in source, (
        "the candidate node still titles itself from the raw anchor location"
    )


# ------------------------------------------------------------------ R3: the honest state


def test_r3_the_place_says_whether_the_traveller_named_it_and_whether_it_was_located() -> None:
    """Describes what an unnamed anchor already was, so it is green in both states - it is here
    to keep the fix from pretending the placement is a location."""

    import json

    places = {row.category: row for row in _places_for("{}")}
    metadata = json.loads(places["arrival"].metadata_json)

    assert metadata["location_declared"] is False, metadata
    assert metadata["coordinates_declared"] is False, metadata


def test_r3b_a_named_but_unlocated_anchor_does_not_claim_surveyed_coordinates() -> None:
    import json

    places = {row.category: row for row in _places_for('{"location": "Tianjin Station"}')}
    metadata = json.loads(places["arrival"].metadata_json)

    assert metadata["location_declared"] is True, metadata
    assert metadata["coordinates_declared"] is False, metadata


# ----------------------------------------------------------------- R4: the writers


def test_r4_no_writer_stores_the_role_word_as_a_place_name() -> None:
    """The fabrication enters the database here, so this is the earliest point it can be
    stopped without reading anything back out."""

    for relative in ("app/stay_mobility.py", "app/operations/v9.py"):
        source = (BACKEND / relative).read_text(encoding="utf-8")
        ast.parse(source)
        for word in ('"location": "Arrival"', '"location": "Departure"'):
            assert word not in source, (relative, word)
        assert 'or "Arrival"' not in source, relative
        assert 'or "Departure"' not in source, relative