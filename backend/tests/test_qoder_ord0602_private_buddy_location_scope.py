"""ORD-0602 - a private buddy-handoff position must not enter the shared Journey projection.

Measured on the authoritative tip `b68f381712abd9207b5ecd7625d18d0883838459`: the active-plan
read in `backend/app/stay_mobility.py` asked for the newest `location_observations` row of the
journey and nothing else

```python
.where(LocationObservation.journey_id == journey.id)
```

while the representative branch `gpt/revolution-r33-open-world-journey-adaptation` (pinned at
`a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9`) filters one source out of it.  That source is
`BUDDY_HANDOFF_ROUTE_PRIVATE`: a route a traveller hands to a buddy, which is the most recent
position on the trip by construction, so the unfiltered read returns *exactly* the row the
handoff made private and serves it to every consumer of the stay projection.

Four arms, and the third one is what stops this from being an over-block:

* A1 the newest row is private and an older ordinary row exists -> the projection carries the
  ordinary row, coordinates included;
* A2 the only row is private -> the projection reports no position at all, rather than the
  private one;  the row is shown to exist first, so a missing fixture cannot look like a fix;
* A3 a journey with only ordinary observations still gets its position -> filtering private
  rows must not narrow what an ordinary trip sees;
* A4 the same answer through a real served GET route, read off the response body, because a
  function that only this file calls would not be a wiring.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.models import Journey, LocationObservation, PlanVersion, Traveler
from app.db.session import SessionLocal, ensure_schema
from app.main import app
from app.stay_mobility import _active_plan_payload

client = TestClient(app)
TZ = timezone(timedelta(hours=8))
START = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)

#: The ordinary source the model defaults to (`backend/app/db/models.py`, column `source`).
ORDINARY_SOURCE = "FOREGROUND_WEB"

#: Two places far enough apart that a leak cannot be mistaken for rounding.
PUBLIC_LAT, PUBLIC_LON = 24.4501, 118.3020
PRIVATE_LAT, PRIVATE_LON = 31.2304, 121.4737

ensure_schema()


def _private_source() -> str:
    """Read the scope constant off the module that filters with it.

    Deliberately not a top-of-file import: on a generation whose read path carries no filter,
    `from app.execution.location_scope import ...` aborts collection for the whole module and
    the run reports an import error instead of which requirement is unmet.  Resolved here, the
    failure names the symbol the read path is expected to carry.
    """

    from app import stay_mobility as module

    value = getattr(module, "PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE", None)
    assert value is not None, (
        "app/stay_mobility.py carries no PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE, so the active-plan "
        "location read has nothing to filter the handed-off route out with"
    )
    return str(value)


def _journey() -> str:
    traveler_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="ORD-0602 probe",
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    created = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": traveler_id,
            "title": "ORD-0602",
            "city_code": "CN-XIAMEN",
            "timezone": "Asia/Shanghai",
            "start_at": START.isoformat(),
            "end_at": (START + timedelta(days=2, hours=8)).isoformat(),
            "budget": {"amount_minor": 90000, "currency": "CNY"},
            "planning_mode": "balanced",
        },
    )
    assert created.status_code == 201, created.text
    journey_id = str(created.json()["id"])

    # `_active_plan_payload` returns None for a journey with no active plan, so the projection
    # under test only exists once a plan version is attached to the trip.
    with SessionLocal() as session:
        plan = PlanVersion(
            id=str(uuid4()),
            journey_id=journey_id,
            version_no=1,
            planning_mode="balanced",
            status="ACTIVE",
            source="INITIAL",
            total_cost_minor=120000,
            currency="CNY",
            estimated_duration_min=240,
            created_at=now,
        )
        session.add(plan)
        journey = session.get(Journey, journey_id)
        assert journey is not None
        journey.active_plan_version_id = plan.id
        session.commit()
    return journey_id


def _add_location(journey_id: str, *, source: str, captured_at: str, latitude: float,
                  longitude: float) -> None:
    with SessionLocal() as session:
        session.add(
            LocationObservation(
                id=str(uuid4()),
                journey_id=journey_id,
                latitude=latitude,
                longitude=longitude,
                accuracy_m=12.0,
                captured_at=captured_at,
                source=source,
            )
        )
        session.commit()


def _payload(journey_id: str) -> dict:
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        body = _active_plan_payload(session, journey)
    assert body is not None, "no active-plan projection for journey %s" % journey_id
    return body


def _stored_sources(journey_id: str) -> list[str]:
    """What the table actually holds for this trip, before any read path touches it."""

    from sqlalchemy import select

    with SessionLocal() as session:
        return [
            str(row)
            for row in session.scalars(
                select(LocationObservation.source).where(
                    LocationObservation.journey_id == journey_id
                )
            ).all()
        ]


def test_private_newest_position_does_not_reach_the_active_plan_projection() -> None:
    """A1: the handoff row is the newest one, and the projection must show the ordinary row."""

    journey_id = _journey()
    private = _private_source()
    _add_location(journey_id, source=ORDINARY_SOURCE, captured_at="2026-11-03T01:00:00+08:00",
                  latitude=PUBLIC_LAT, longitude=PUBLIC_LON)
    _add_location(journey_id, source=private, captured_at="2026-11-03T09:30:00+08:00",
                  latitude=PRIVATE_LAT, longitude=PRIVATE_LON)
    assert sorted(_stored_sources(journey_id)) == sorted([ORDINARY_SOURCE, private])

    user_location = _payload(journey_id)["user_location"]
    assert user_location is not None, (
        "the trip has an ordinary %s observation and the projection reported no position: the "
        "private-source filter dropped more rows than it names" % ORDINARY_SOURCE
    )
    assert user_location["source"] == ORDINARY_SOURCE, (
        "active_plan.user_location.source came back %r: the newest location_observations row is "
        "the handed-off private one, so the read reached it" % user_location["source"]
    )
    assert (user_location["latitude"], user_location["longitude"]) == (PUBLIC_LAT, PUBLIC_LON), (
        "active_plan.user_location is %.4f,%.4f - that is the private handoff coordinate, not the "
        "ordinary observation at %.4f,%.4f"
        % (
            user_location["latitude"],
            user_location["longitude"],
            PUBLIC_LAT,
            PUBLIC_LON,
        )
    )


def test_a_journey_whose_only_position_is_private_reports_no_position() -> None:
    """A2: with nothing ordinary to fall back to, the projection says absent instead of leaking."""

    journey_id = _journey()
    private = _private_source()
    _add_location(journey_id, source=private, captured_at="2026-11-03T09:30:00+08:00",
                  latitude=PRIVATE_LAT, longitude=PRIVATE_LON)
    assert _stored_sources(journey_id) == [private], (
        "the fixture did not store the private row, so a None below would prove nothing"
    )

    user_location = _payload(journey_id)["user_location"]
    assert user_location is None, (
        "the only location_observations row for this trip is source=%r and the projection served "
        "%r" % (private, dict(user_location or {}).get("source"))
    )


def test_an_ordinary_trip_still_gets_its_position() -> None:
    """A3: the filter must be a scope, not a shrink - an ordinary trip reads exactly as before."""

    journey_id = _journey()
    _add_location(journey_id, source=ORDINARY_SOURCE, captured_at="2026-11-03T07:15:00+08:00",
                  latitude=PUBLIC_LAT, longitude=PUBLIC_LON)
    assert _stored_sources(journey_id) == [ORDINARY_SOURCE]

    user_location = _payload(journey_id)["user_location"]
    assert user_location is not None, (
        "a journey with one %s observation and no private row lost its position" % ORDINARY_SOURCE
    )
    assert user_location["source"] == ORDINARY_SOURCE
    assert (user_location["latitude"], user_location["longitude"]) == (PUBLIC_LAT, PUBLIC_LON)


def test_the_served_stay_options_response_carries_the_filtered_position() -> None:
    """A4: the same answer out of a route the client actually calls."""

    journey_id = _journey()
    private = _private_source()
    _add_location(journey_id, source=ORDINARY_SOURCE, captured_at="2026-11-03T01:00:00+08:00",
                  latitude=PUBLIC_LAT, longitude=PUBLIC_LON)
    _add_location(journey_id, source=private, captured_at="2026-11-03T09:30:00+08:00",
                  latitude=PRIVATE_LAT, longitude=PRIVATE_LON)

    response = client.get("/api/v1/journeys/%s/stay-options" % journey_id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["active_plan"] is not None, response.text
    user_location = body["active_plan"]["user_location"]
    assert user_location is not None, (
        "GET /api/v1/journeys/{id}/stay-options answered active_plan.user_location = null while "
        "an ordinary %s observation is stored for the trip" % ORDINARY_SOURCE
    )
    assert user_location["source"] == ORDINARY_SOURCE, (
        "the served active_plan.user_location.source is %r: a consumer of the stay route receives "
        "the handed-off private position" % user_location["source"]
    )
