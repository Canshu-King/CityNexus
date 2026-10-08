"""A headcount nobody stated must not become a party of one downstream.

`_context()` creates a `journey_trip_contexts` row the moment the stay flow runs, and the
`party_size` column is NOT NULL DEFAULT 1. Reading that column alone therefore reports one
traveller for a trip whose headcount was never asked, and that number was then divided by,
written into offer snapshots, and handed to accommodation suppliers. These arms assert the
three-state reading: a stored headcount is only a fact when a traveller declared it.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.core.temporal import derive_budget_reference
from app.stay_mobility import declared_party_size


def _context(**overrides):
    values = {
        "party_size": 1,
        "occupancy_json": '{"adults": 1}',
        "stay_budget_declared": None,
        "party_size_declared": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_a_lazy_row_claims_no_headcount():
    # What `_context()` now writes: the column's own floor, flagged as nobody's answer.
    assert declared_party_size(_context(party_size_declared=False)) is None


def test_an_asked_and_emptied_row_claims_no_headcount():
    assert declared_party_size(_context(party_size_declared=False)) is None


def test_a_declared_headcount_is_the_fact_it_is():
    assert declared_party_size(_context(party_size=3, party_size_declared=True)) == 3


def test_a_legacy_row_keeps_its_stored_number():
    # A row written before the column existed may hold a headcount a traveller really typed,
    # so NULL must not discard it - the same reason ORD-0355 keeps a NULL stay budget.
    assert declared_party_size(_context(party_size=4, party_size_declared=None)) == 4


def test_per_person_stays_unanswered_without_a_headcount():
    result = derive_budget_reference(
        budget_amount_minor=50_000,
        day_count=2,
        budget_currency="CNY",
        party_size=None,
    )

    assert result.party_size is None
    assert result.per_person_per_day_minor is None
    assert result.per_day_minor == 25_000


def test_per_person_is_divided_by_a_declared_headcount():
    result = derive_budget_reference(
        budget_amount_minor=50_000,
        day_count=2,
        budget_currency="CNY",
        party_size=3,
    )

    assert result.party_size == 3
    assert result.per_person_per_day_minor == 8_333


def test_an_undeclared_budget_does_not_invent_a_headcount_either():
    result = derive_budget_reference(
        budget_amount_minor=None,
        day_count=2,
        budget_currency="CNY",
        party_size=None,
    )

    assert result.party_size is None
    assert result.available is False
