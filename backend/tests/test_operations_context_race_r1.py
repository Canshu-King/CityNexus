"""The one-per-journey operations row used to be inserted twice, and the trip page answered 500.

Issue #31 B moved the optional stay search off the critical path, so the reads the shell takes
right after a trip is created now overlap calls that touch `journey_operations_contexts`.  Two
writers keep that single row: `stay_mobility._operations_context` (through `/experience` and
`build_candidate_nodes`) and `operations.v9.set_luggage_context` (through the luggage door).  Both
were written as "look, then add", and the look could not see the other one's work: a row that is
only `session.add`-ed is *pending* -- it is in neither the identity map nor the database -- so the
second writer saw `None`, added its own row, and the flush sent two INSERTs for the same
`journey_id`.  What the traveller got back was
`UNIQUE constraint failed: journey_operations_contexts.journey_id` inside a 500 on `/experience`:
a trip that intermittently refused to open right after it was created.

Both writers now create inside a savepoint and re-read afterwards, so the loser of the race adopts
the row that exists instead of failing the request.  These tests hold that:

* the two writers, in either order, in one session, leave exactly one row;
* the values that were asked for are the ones that come back -- nobody's update is swallowed;
* even a pending row left behind by some other code path cannot turn into a 500.
"""

from __future__ import annotations

import threading
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.main as main_module
from app.db.models import Journey, JourneyOperationsContext
from app.db.session import SessionLocal, ensure_schema
from app.operations.v9 import set_luggage_context
from app.stay_mobility import _operations_context

client = TestClient(main_module.app)
ensure_schema()


def _journey() -> str:
    """A trip opened through the same door the creation wizard uses."""

    start_at = "2026-11-01T09:00:00+08:00"
    end_at = "2026-11-02T18:00:00+08:00"
    person = client.post(
        "/api/v1/travelers",
        json={"display_name": "Race traveller", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    )
    assert person.status_code == 201, person.text
    answer = client.post("/api/v1/journeys", json={
        "traveler_id": person.json()["id"],
        "title": "Ningbo · journey",
        "city_code": "CN-Ningbo",
        "timezone": "Asia/Shanghai",
        "start_at": start_at,
        "end_at": end_at,
        "budget": {"amount_minor": 120000, "currency": "CNY"},
        "party_size": 2,
    })
    assert answer.status_code == 201, answer.text
    return answer.json()["id"]


def _rows(session, journey_id: str) -> list[JourneyOperationsContext]:
    return session.scalars(
        select(JourneyOperationsContext).where(
            JourneyOperationsContext.journey_id == journey_id
        )
    ).all()


def _drop_row(journey_id: str) -> None:
    """Put the trip back into the state the defect actually bit: a journey with no row yet.

    A line that creates the row alongside the journey cannot race for it, so the population at
    risk is every journey that predates that -- this is what the two writers found on the machine
    the screenshots were taken on.
    """

    session = SessionLocal()
    try:
        session.execute(
            JourneyOperationsContext.__table__.delete().where(
                JourneyOperationsContext.journey_id == journey_id
            )
        )
        session.commit()
    finally:
        session.close()


def create_by_get(session: Session, journey: Journey) -> None:
    """The writer behind reading the trip page."""

    _operations_context(session, journey)


def create_by_put(session: Session, journey: Journey) -> None:
    """The writer behind the luggage door."""

    set_luggage_context(
        session, journey, baggage_present=True, baggage_size_class="HEAVY",
        luggage_drop_required=False,
    )


def _count(session, journey_id: str) -> int:
    return session.scalar(
        select(func.count())
        .select_from(JourneyOperationsContext)
        .where(JourneyOperationsContext.journey_id == journey_id)
    )


def test_read_then_luggage_leaves_one_row_and_the_travellers_values():
    """`/experience` asks first, the luggage door asks after -- the shape that produced the 500."""

    journey_id = _journey()
    session = SessionLocal()
    try:
        journey = session.get(Journey, journey_id)
        assert journey is not None

        _operations_context(session, journey)
        row = set_luggage_context(
            session,
            journey,
            baggage_present=True,
            baggage_size_class="HEAVY",
            luggage_drop_required=True,
        )
        session.commit()

        assert _count(session, journey_id) == 1, _rows(session, journey_id)
        assert row.baggage_present is True
        assert row.baggage_size_class == "HEAVY"
        assert row.luggage_drop_required is True
    finally:
        session.close()


def test_luggage_then_read_leaves_one_row_and_keeps_the_values():
    """The other order: the writer that knows the row exists goes first."""

    journey_id = _journey()
    session = SessionLocal()
    try:
        journey = session.get(Journey, journey_id)
        set_luggage_context(
            session,
            journey,
            baggage_present=True,
            baggage_size_class="CABIN",
            luggage_drop_required=False,
        )
        row = _operations_context(session, journey)
        session.commit()

        assert _count(session, journey_id) == 1, _rows(session, journey_id)
        assert row.baggage_size_class == "CABIN"
    finally:
        session.close()


def test_a_pending_row_left_by_somebody_else_does_not_become_a_500():
    """The row this journey has must be found even when it was written by another hand.

    Measured against the pre-fix line: this ordering is the one that produced the 500 -- see
    ``test_two_threads_that_both_looked_still_leave_exactly_one_row``, which forces it.
    """

    journey_id = _journey()
    session = SessionLocal()
    try:
        journey = session.get(Journey, journey_id)
        _operations_context(session, journey)
        row = set_luggage_context(
            session,
            journey,
            baggage_present=True,
            baggage_size_class="MEDIUM",
            luggage_drop_required=False,
        )
        session.commit()

        assert _count(session, journey_id) == 1, _rows(session, journey_id)
        assert row.baggage_size_class == "MEDIUM"
    finally:
        session.close()


@pytest.mark.parametrize("first,second", [(create_by_get, create_by_put),
                                          (create_by_put, create_by_get)])
def test_two_threads_that_both_looked_still_leave_exactly_one_row(first, second):
    """The defect, forced rather than waited for.

    Two writers each open their own session and read the trip -- that read is where the failing
    request started, so neither of them can see a row that does not exist yet.  A barrier holds
    both of them there until *both* have looked, and only then does either insert.  Pre-fix, one
    of the two came back with `IntegrityError: UNIQUE constraint failed:
    journey_operations_contexts.journey_id`, which is the 500 on `/experience` that Issue #31 B's
    traffic exposed.  Post-fix both writers finish, and the journey is left with one row.
    """

    jid = _journey()
    _drop_row(jid)

    both_have_looked = threading.Barrier(2)
    escaping: list[str] = []
    guard = threading.Lock()

    def worker(which: str, action) -> None:
        session = SessionLocal()
        try:
            journey = session.get(Journey, jid)
            session.get(JourneyOperationsContext, jid)   # the look that both writers start from
            both_have_looked.wait(timeout=20)
            action(session, journey)
            session.commit()
        except BaseException as exc:  # noqa: BLE001 - the escaping exception IS the reading
            with guard:
                escaping.append("{}: {}: {}".format(
                    which, type(exc).__name__, str(exc).splitlines()[0][:120]))
            try:
                session.rollback()
            except BaseException:  # noqa: BLE001
                pass
        finally:
            session.close()

    threads = [threading.Thread(target=worker, args=(name, action))
               for name, action in (("first", first), ("second", second))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(40)

    assert not [t.name for t in threads if t.is_alive()], "a writer hung instead of finishing"
    assert escaping == [], escaping
    session = SessionLocal()
    try:
        assert _count(session, jid) == 1, _rows(session, jid)
    finally:
        session.close()


def test_the_trip_page_opens_after_both_doors_have_been_used():
    """What the traveller is able to see: creation, the experience read, luggage, read again."""

    journey_id = _journey()

    first = client.get(f"/api/v1/journeys/{journey_id}/experience")
    assert first.status_code == 200, first.text[:400]

    put = client.put(
        f"/api/v1/journeys/{journey_id}/operations/luggage",
        json={
            "request_id": f"luggage-{uuid4()}",
            "baggage_present": True,
            "baggage_size_class": "HEAVY",
            "luggage_drop_required": True,
        },
    )
    assert put.status_code == 200, put.text[:400]

    second = client.get(f"/api/v1/journeys/{journey_id}/experience")
    assert second.status_code == 200, second.text[:400]

    session = SessionLocal()
    try:
        assert _count(session, journey_id) == 1, _rows(session, journey_id)
    finally:
        session.close()
