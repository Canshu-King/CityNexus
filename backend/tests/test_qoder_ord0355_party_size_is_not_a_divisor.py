"""ORD-0355's shape applied to the headcount: an undeclared party size must stop being a divisor.

Measured at the authoritative tip `b1e392758fe3f8f1fa1e6b12f670d882dde6533f`: a trip POSTed
without the `party_size` key reached `journey_trip_contexts.party_size` as the column's own
`NOT NULL DEFAULT 1`, that 1 became the divisor of the declared budget, and the experience read
answered `per_person_per_day_minor = 10000` with `reason = null` - an invented divisor reported as
a complete answer, with no caveat anywhere on the screen.  ORD-0355 removed exactly this shape
for `stay_budget_amount_minor`; the headcount was the remaining member of the same family.

These tests pin the four requirements and refuse the shortcuts that would pass them vacuously:

* R1 is judged by reading `journey_trip_contexts` back with raw SQL - naming table, column and
  row - because a value that only survives inside the request object proves nothing about what
  the product stored;
* R2 asserts on the trip body the code actually builds, for declared / undeclared / legacy, and
  above all that the per-person figure is *absent* rather than computed from the server's default;
* R3 pins the reported reason to a code whose sentence names the missing headcount, and keeps
  the daily half - which is the traveller's own budget over their own trip - still stated;
* R4 runs the additive migration against a database built with the *old* DDL and checks that the
  pre-existing row is still there, still holding the number it held, and reading as "never asked".

A lane cannot pass R2 by leaving `derive_budget_reference` alone and filtering at the edge: R3
calls the function directly, so the clamp has to be gone there too.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.temporal import derive_budget_reference
from app.db.models import JourneyTripContext
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)
TZ = timezone(timedelta(hours=8))
START = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)
END = datetime(2026, 11, 4, 20, 0, tzinfo=TZ)

#: The pre-change DDL, quoted so the migration is exercised against the shape this column had
#: to be added to - not against whatever the current models happen to emit.
LEGACY_DDL = """
CREATE TABLE journeys (
    id TEXT PRIMARY KEY,
    traveler_id TEXT NOT NULL,
    title TEXT NOT NULL,
    city_code TEXT NOT NULL,
    timezone TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    budget_currency TEXT NOT NULL,
    budget_amount_minor INTEGER NOT NULL CHECK (budget_amount_minor >= 0),
    planning_mode TEXT NOT NULL DEFAULT 'balanced',
    status TEXT NOT NULL,
    active_plan_version_id TEXT,
    current_activity_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE journey_trip_contexts (
    journey_id TEXT PRIMARY KEY REFERENCES journeys(id) ON DELETE CASCADE,
    arrival_anchor_json TEXT NOT NULL DEFAULT '{}',
    departure_anchor_json TEXT NOT NULL DEFAULT '{}',
    party_size INTEGER NOT NULL DEFAULT 1 CHECK (party_size >= 1),
    occupancy_json TEXT NOT NULL DEFAULT '{}',
    stay_budget_amount_minor INTEGER NOT NULL DEFAULT 0 CHECK (stay_budget_amount_minor >= 0),
    stay_budget_currency TEXT NOT NULL DEFAULT 'CNY',
    stay_budget_declared INTEGER CHECK (stay_budget_declared IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

INSERT INTO journeys (id, traveler_id, title, city_code, timezone, start_at, end_at,
                      budget_currency, budget_amount_minor, status, created_at, updated_at)
VALUES ('legacy-journey', 'legacy-traveler', 'before the headcount column', 'CN-XIAMEN',
        'Asia/Shanghai', '2026-11-03T09:00:00+08:00', '2026-11-05T17:00:00+08:00', 'CNY', 90000,
        'DRAFT', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00');
INSERT INTO journey_trip_contexts (journey_id, party_size, stay_budget_amount_minor,
                                   stay_budget_currency, created_at, updated_at)
VALUES ('legacy-journey', 4, 6000, 'CNY', '2026-01-01T00:00:00+00:00',
        '2026-01-01T00:00:00+00:00');
"""


def declared_reason():
    """Resolved lazily so the whole file still collects against an unmodified tree.

    A module-level import would turn the before-fix run into one collection error, which
    proves nothing about which requirement was unmet - the ORD-0355 file above this one is
    written the same way for the same reason.
    """

    from app.core import temporal

    return temporal.UNAVAILABLE_PARTY_UNKNOWN


def party_size_body(context):  # noqa: N802 - mirrors the production symbol name
    """Resolved lazily so the readings still run on an unmigrated tree.

    A module-level import would turn the before-fix run into one collection error, which
    proves nothing about which requirement was unmet.
    """

    from app import stay_mobility as module

    return module.party_size_body(context)


def _traveler() -> str:
    return client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()["traveler_id"]


def demo_reset_headers():
    from demo_stage import demo_reset_headers as build

    return build()


def _create(traveler: str, *, with_party: bool) -> str:
    payload = {
        "traveler_id": traveler,
        "title": "headcount probe",
        "city_code": "CNX-DEMO",
        "timezone": "Asia/Shanghai",
        "start_at": START.isoformat(),
        "end_at": END.isoformat(),
        "budget": {"amount_minor": 20000, "currency": "CNY"},
        "planning_mode": "balanced",
    }
    if with_party:
        payload["party_size"] = 3
    response = client.post("/api/v1/journeys", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _trip_of(journey_id: str) -> dict:
    response = client.get(f"/api/v1/journeys/{journey_id}/experience")
    assert response.status_code == 200, response.text
    return response.json()["trip"]


# ------------------------------------------------------------------ R1: what is stored


def test_r1_a_request_without_a_headcount_is_stored_as_never_asked_not_as_one() -> None:
    """The column is read back with raw SQL: table, column and row named out loud."""

    from app.db.session import engine

    journey_id = _create(_traveler(), with_party=False)
    with engine.connect() as connection:
        row = connection.exec_driver_sql(
            "SELECT party_size, party_size_declared FROM journey_trip_contexts"
            " WHERE journey_id = ?",
            (journey_id,),
        ).fetchone()

    assert row is not None, ("journey_trip_contexts has no row for this journey", journey_id)
    assert int(row[1]) == 0, (
        "a request that never mentioned party_size was recorded as asked-and-said-something",
        row,
    )


def test_r2a_asking_for_a_headcount_records_it_as_declared() -> None:
    """The opposite case, so the fix cannot pass by refusing to record anything at all."""

    from app.db.session import engine

    journey_id = _create(_traveler(), with_party=True)
    with engine.connect() as connection:
        row = connection.exec_driver_sql(
            "SELECT party_size, party_size_declared FROM journey_trip_contexts"
            " WHERE journey_id = ?",
            (journey_id,),
        ).fetchone()

    assert row is not None, journey_id
    assert int(row[0]) == 3 and int(row[1]) == 1, row


# -------------------------------------------------- R2: what leaves the process, per shape


def test_r2b_the_trip_body_does_not_dress_the_servers_own_default_as_a_headcount() -> None:
    """The before-fix reading, kept as the thing that must never come back."""

    trip = _trip_of(_create(_traveler(), with_party=False))

    assert trip["party_size"] is None, trip
    assert trip["party_size_declared"] is False, trip


def test_r2c_a_declared_headcount_still_leaves_as_a_number() -> None:
    trip = _trip_of(_create(_traveler(), with_party=True))

    assert trip["party_size"] == 3, trip
    assert trip["party_size_declared"] is True, trip


def test_r2d_a_legacy_row_keeps_the_number_it_held_and_says_it_cannot_vouch_for_it() -> None:
    """NULL is *unknown*, not "not declared": the stored number may be one a traveller typed
    before this column existed, so it keeps travelling - with the state that says so."""

    journey_id = _create(_traveler(), with_party=True)
    with SessionLocal() as session:
        row = session.get(JourneyTripContext, journey_id)
        row.party_size_declared = None
        session.commit()

    body = party_size_body(row)
    assert body["declared"] is None, body
    assert body["party_size"] == 3, body

    trip = _trip_of(journey_id)
    assert trip["party_size"] == 3, trip
    assert trip["party_size_declared"] is None, trip


def test_r2e_the_per_person_figure_is_absent_rather_than_divided_by_one() -> None:
    """The defect in the shape the traveller would have read it in."""

    reference = _trip_of(_create(_traveler(), with_party=False))["budget_reference"]

    assert reference["per_person_per_day_minor"] is None, reference
    assert reference["party_size"] is None, reference


# -------------------------------------------------- R3: the reported reason, called directly


def test_r3_the_function_itself_declines_the_per_person_step() -> None:
    """Called directly so a fix that only filters at the projection edge cannot pass: before the
    change this returned `per_person_per_day_minor = 10000` with `reason = None`."""

    result = derive_budget_reference(
        day_count=2, budget_amount_minor=20000, budget_currency="CNY", party_size=None
    )

    assert result.per_person_per_day_minor is None, result
    assert result.party_size is None, result
    assert result.reason == declared_reason(), result
    assert result.available is False, result


def test_r3b_the_daily_half_is_still_stated_because_it_is_a_true_number() -> None:
    """`available: false` must not take the whole allowance off the screen: the daily figure is
    the traveller's own budget over their own trip, and discarding it to avoid printing an
    invented divisor is the other half of the same lie."""

    result = derive_budget_reference(
        day_count=2, budget_amount_minor=20000, budget_currency="CNY", party_size=None
    )

    assert result.per_day_minor == 10000, result


def test_r3c_a_declared_headcount_is_unaffected() -> None:
    for size, expected in ((1, 20000), (2, 10000), (4, 5000)):
        result = derive_budget_reference(
            day_count=2, budget_amount_minor=40000, budget_currency="CNY", party_size=size
        )
        assert result.available is True, result
        assert result.per_person_per_day_minor == expected, result
        assert result.reason is None, result


# ------------------------------------------------------- R4: the migration is additive


def test_r4_migrating_an_old_database_leaves_its_row_and_its_number_alone(tmp_path) -> None:
    """The old DDL, one row, then the additive migration: the row survives and reads as unknown.

    This store is a `tmp_path` file created by this test and deleted with it.  No shared
    database was opened, and none of `_live.db` / `_preview.db` was named by any code path.
    """

    from app.db.session import ensure_schema, make_engine

    database = tmp_path / "_ord0355_party_legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(LEGACY_DDL)

    before = sqlite3.connect(database).execute(
        "SELECT name FROM pragma_table_info('journey_trip_contexts')"
    ).fetchall()
    assert ("party_size_declared",) not in before, before

    engine = make_engine(f"sqlite:///{database.as_posix()}")
    ensure_schema(engine)
    ensure_schema(engine)

    after = sqlite3.connect(database).execute(
        "SELECT name, \"notnull\", dflt_value FROM pragma_table_info('journey_trip_contexts')"
        " WHERE name IN ('party_size_declared','party_size')"
    ).fetchall()
    columns = {str(row[0]): row for row in after}
    assert "party_size_declared" in columns, sorted(columns)
    # Additive: nullable, no default.  A DEFAULT 0 would have converted every historical row into
    # "asked, and said one", which is the fabrication this change removes.
    assert int(columns["party_size_declared"][1]) == 0, columns
    assert columns["party_size_declared"][2] is None, columns
    # The column it shares the table with came out of the migration unchanged.
    assert int(columns["party_size"][1]) == 1, columns
    assert columns["party_size"][2] == "1", columns

    with sqlite3.connect(database) as connection:
        legacy = connection.execute(
            "SELECT party_size, party_size_declared FROM journey_trip_contexts"
            " WHERE journey_id = 'legacy-journey'"
        ).fetchone()
    assert legacy == (4, None), legacy
    engine.dispose()