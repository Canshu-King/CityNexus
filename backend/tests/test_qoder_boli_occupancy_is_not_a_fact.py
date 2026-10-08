"""An occupancy nobody stated must not be stored as one adult.

`_context()` creates a `journey_trip_contexts` row the first time the stay flow runs, and
three of the values it writes came from nobody: `party_size=1`, `stay_budget_amount_minor=0`
and `occupancy={"adults": 1}`. The first two now carry a declared flag or an honest empty
shape. Occupancy was left behind, so a trip with no recorded headcount still reads back
"1 adult" and that object is forwarded verbatim in `trip.occupancy`.

These arms read the stored row back with plain SQLite, because a value that survives only
inside the request object says nothing about what the product kept.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.models import Journey, JourneyTripContext, Traveler
from app.db.session import SessionLocal
from app.main import app
from app.stay_mobility import _context

client = TestClient(app)
TZ = timezone(timedelta(hours=8))
START = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)


def _traveler() -> str:
    traveler_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="boli occupancy probe",
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return traveler_id


def _journey_without_trip_context(*, party_size: int | None) -> str:
    """A journey row with no `journey_trip_contexts` row, so the lazy branch is reachable."""

    journey_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(
            Journey(
                id=journey_id,
                traveler_id=_traveler(),
                title="boli occupancy probe",
                city_code="CN-XIAMEN",
                timezone="Asia/Shanghai",
                start_at=START.isoformat(),
                end_at=(START + timedelta(days=2, hours=8)).isoformat(),
                budget_currency="CNY",
                budget_amount_minor=90_000,
                planning_mode="balanced",
                status="DRAFT",
                active_plan_version_id=None,
                current_activity_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    if party_size is not None:
        # A headcount the traveller did give, stored the way the real door stores it.
        _store_declared_party_size(journey_id, party_size)
    return journey_id


def _store_declared_party_size(journey_id: str, party_size: int) -> None:
    """Write the context row a traveller answering the headcount question would have."""

    from app.db.models import JourneyTripContext

    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(
            JourneyTripContext(
                journey_id=journey_id,
                arrival_anchor_json="{}",
                departure_anchor_json="{}",
                party_size=party_size,
                occupancy_json=json.dumps({"adults": party_size}),
                stay_budget_amount_minor=0,
                stay_budget_currency="CNY",
                stay_budget_declared=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()


def _stored_occupancy(journey_id: str) -> dict:
    """`journey_trip_contexts.occupancy_json` for this trip, read with plain SQLite."""

    from conftest import RESOLVED_TEST_DATABASE

    path = Path(RESOLVED_TEST_DATABASE.replace("sqlite:///", "", 1))
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT occupancy_json FROM journey_trip_contexts WHERE journey_id = ?",
            (journey_id,),
        ).fetchone()
    assert row is not None, f"no journey_trip_contexts row for journey_id={journey_id}"
    return json.loads(row[0])


def test_the_lazy_row_records_no_adults() -> None:
    journey_id = _journey_without_trip_context(party_size=None)

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        session.add(_context(session, journey))
        session.commit()

    assert _stored_occupancy(journey_id) == {}


def test_a_recorded_headcount_keeps_its_occupancy() -> None:
    """The required negative case: an occupancy a traveller gave must survive untouched."""

    journey_id = _journey_without_trip_context(party_size=2)

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        assert _context(session, journey).occupancy_json == '{"adults": 2}'

    assert _stored_occupancy(journey_id) == {"adults": 2}


def test_the_lazy_row_is_what_creates_that_row() -> None:
    """Pins that this arm is reading the lazy branch and not a pre-existing row."""

    journey_id = _journey_without_trip_context(party_size=None)

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        assert session.get(JourneyTripContext, journey_id) is None, (
            "this journey already has a context row, so _context would not take the lazy branch"
        )
        row = _context(session, journey)
        assert session.get(JourneyTripContext, journey_id) is not None
        # The row this call invented carries nobody's answer.
        assert json.loads(row.occupancy_json) == {}
        session.commit()