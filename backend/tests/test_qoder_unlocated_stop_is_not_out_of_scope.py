"""A stop nobody located must not be dropped from a disruption as if a distance check cleared it.

Measured at the authoritative tip `95da0f272e870a566070dbaf5219411d6232460e`: `_within_scope`
returned False whenever the *activity* had no coordinate, and `_corroboration` turns that False
into `GEOSPATIAL_SCOPE_MISMATCH`, which `validate_impact_candidates` treats as a rejection.  So a
flood that the server had given a real coordinate and a 5 km radius was dropped for every stop the
planner had never located, as if the flood had been measured not to reach it.  The event's own
missing coordinate already answered True for the opposite reason - cannot rule it out, so do not
reject - and the two halves of one question were giving opposite verdicts.

`_within_scope` is now three-valued: True, False, or None for "cannot be told".  None is neither a
rejection nor a reference, and it is reported on the candidate so the screen can say the check
never happened.

These call the real functions with stand-in activity and event payloads, so what is asserted is
what the code emits rather than what it was asked to emit.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))


def _activity(latitude, longitude, *, place_id="place-old-town", title="Old Town Gate"):
    from app.intelligence.impact_contract import ImpactActivityContext

    start = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)
    return ImpactActivityContext(
        activity_id="act-1",
        sequence_no=1,
        title=title,
        activity_type="VISIT",
        place_id=place_id,
        place_name=title,
        place_category="attraction",
        latitude=latitude,
        longitude=longitude,
        start_at=start,
        end_at=start + timedelta(hours=2),
        status="PLANNED",
        locked=False,
        is_current=False,
        is_c4=False,
    )


#: The server said where the flood is and how far it reaches.
FLOOD = {"latitude": 39.124, "longitude": 117.205, "radius_m": 5000, "name": "flooding"}


def _unverified_token() -> str:
    """Lazy, so this file collects against an unmodified tree."""

    from app.intelligence import impact_validation

    return impact_validation.GEOSPATIAL_SCOPE_UNVERIFIABLE


def _run(latitude, longitude):
    """The real validator, one candidate, one activity - no network, no provider."""

    from app.intelligence.impact_contract import ImpactCandidate
    from app.intelligence.impact_validation import validate_impact_candidates

    return validate_impact_candidates(
        candidates=[
            ImpactCandidate(
                activity_id="act-1",
                impact_type="WEATHER_RISK",
                confidence=0.9,
            )
        ],
        activities=(_activity(latitude, longitude),),
        event_payload=FLOOD,
    )


# ------------------------------------------------------- R1: the three states exist


def test_r1_a_stop_with_no_coordinate_is_neither_inside_nor_ruled_out() -> None:
    """The before-fix reading: False, i.e. "the flood does not reach this stop"."""

    from app.intelligence.impact_validation import _within_scope

    assert _within_scope(_activity(None, None), FLOOD) is None
    # The other two states are unchanged, or the fix would be a different claim.
    assert _within_scope(_activity(39.13, 117.21), FLOOD) is True
    assert _within_scope(_activity(39.9, 117.9), FLOOD) is False


def test_r1b_a_missing_radius_is_also_cannot_tell_not_ruled_out() -> None:
    """The other False this function used to return, for the same reason."""

    from app.intelligence.impact_validation import _within_scope

    unreadable = {"latitude": 39.124, "longitude": 117.205, "radius_m": "wide"}

    assert _within_scope(_activity(39.13, 117.21), unreadable) is None


def test_r1c_an_event_with_no_geometry_still_cannot_rule_a_stop_out() -> None:
    """The pre-existing True, kept: the fix must not turn this into a rejection either."""

    from app.intelligence.impact_validation import _within_scope

    assert _within_scope(_activity(39.13, 117.21), {"name": "flooding"}) is True


# --------------------------------------- R2: what _corroboration does with each state


def test_r2_an_unlocated_stop_is_no_longer_rejected_for_being_out_of_scope() -> None:
    """The reading the traveller would have got: `GEOSPATIAL_SCOPE_MISMATCH`, i.e. rejected."""

    from app.intelligence.impact_validation import _corroboration

    refs, reasons, _strong, undecided = _corroboration(_activity(None, None), FLOOD)

    assert "GEOSPATIAL_SCOPE_MISMATCH" not in reasons, reasons
    assert reasons == (), reasons
    assert "event.payload.geo_scope" not in refs, refs
    assert undecided == (_unverified_token(),), undecided


def test_r2b_a_located_stop_outside_the_radius_is_still_rejected() -> None:
    """The other direction, so the fix cannot pass by never rejecting anything."""

    from app.intelligence.impact_validation import _corroboration

    _refs, reasons, _strong, undecided = _corroboration(_activity(39.9, 117.9), FLOOD)

    assert reasons == ("GEOSPATIAL_SCOPE_MISMATCH",), reasons
    assert undecided == (), undecided


def test_r2c_a_located_stop_inside_the_radius_still_counts_as_evidence() -> None:
    from app.intelligence.impact_validation import _corroboration

    refs, reasons, _strong, undecided = _corroboration(_activity(39.13, 117.21), FLOOD)

    assert "event.payload.geo_scope" in refs, refs
    assert reasons == (), reasons
    assert undecided == (), undecided


def test_r2d_an_unlocated_stop_never_reports_a_scope_mismatch_as_its_reason() -> None:
    """The whole chain in one reading, because the rejection happens at the caller."""

    from app.intelligence.impact_validation import validate_impact_candidates

    result = _run(None, None)

    assert "GEOSPATIAL_SCOPE_MISMATCH" not in result.reason_codes, result.reason_codes
    assert "act-1" not in result.rejected_activity_ids, result.rejected_activity_ids


# ------------------------------------------------------- R3: it is said out loud


def test_r3_the_check_that_could_not_run_is_named_on_the_candidate() -> None:
    """Silently dropping a check is how "unlocated" came to look like "cleared" in the first
    place, so the candidate carries the fact that it was never compared."""

    result = _run(None, None)

    candidates = result.candidates
    if not candidates:
        # Rejected for some other, unrelated reason - then there is nothing to be silent about,
        # but the scope mismatch still must not be the stated cause.
        assert "GEOSPATIAL_SCOPE_MISMATCH" not in result.reason_codes
        return
    for candidate in candidates:
        assert _unverified_token() in candidate.reason_codes, candidate.reason_codes


def test_r3b_a_located_stop_does_not_carry_the_unverified_note() -> None:
    result = _run(39.13, 117.21)

    for candidate in result.candidates:
        assert _unverified_token() not in candidate.reason_codes, candidate.reason_codes


# ------------------------------------------------------- R4: the shape cannot drift


def test_r4_every_corroboration_return_carries_four_values() -> None:
    """A new bucket means every early return has to say which bucket it belongs to; a branch
    that returns three would unpack-fail at runtime rather than quietly drop the signal."""

    import ast
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app" / "intelligence" / "impact_validation.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_corroboration"
    )
    returns = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Return) and node.value is not None
    ]
    assert returns, "no returns found to check"
    for node in returns:
        assert isinstance(node.value, ast.Tuple), ast.dump(node.value)
        assert len(node.value.elts) == 4, (
            ast.dump(node.value),
            "a branch of _corroboration does not say which of the four it belongs to",
        )