"""Counter-arm for the experience payload's journey window.

The gap this pins: `experience_payload` -- the body of `GET /journeys/{id}/experience`, and of
`/stay-options` and `/multiday` -- echoed `"timezone": journey.timezone` beside `start_at` and
`end_at` that were the bare local wall-clock columns, `2026-10-09T18:00:00`, no offset at all.  So
the payload named a zone and carried a window that named none, and every screen reading it had to
place those two instants itself against a zone it could not check -- the same shape the trip
payload was fixed for.

This arm reads the real `experience_payload` (a stand-in trip and a session with no rows -- only the
helpers that would need a database are stubbed) and asserts:
  * the window instants carry the offset the named zone implies, or
  * the payload says the zone was not honoured -- so an unplaceable window is never presented as if
    it were placed.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "backend"))

import app.stay_mobility as sm  # noqa: E402
from app.db.models import JourneyOperationsContext  # noqa: E402

# The data helpers `experience_payload` calls would need a database; they are not under test here.
sm._context = lambda session, journey: type(
    "Ctx",
    (),
    {
        "party_size": 1,
        "occupancy_json": "{}",
        "trip_id": journey.id,
        "id": journey.id,
        "arrival_anchor_json": "{}",
        "departure_anchor_json": "{}",
        "stay_budget_declared": None,
        "stay_budget_amount_minor": None,
        "stay_budget_currency": None,
    },
)()
# `JourneyOperationsContext` is a real SQLAlchemy model, so build a real row rather than a
# stand-in with hand-picked attributes -- a fake here would silently grow fields.
sm._operations_context = lambda session, journey: JourneyOperationsContext(
    journey_id=journey.id,
    baggage_present=False,
    baggage_size_class="NONE",
    luggage_drop_required=False,
    constraints_json="{}",
    created_at="2026-10-01T00:00:00",
    updated_at="2026-10-01T00:00:00",
)
sm.planning_preference_items = lambda session, traveler_id, journey_id: []
sm.refresh_snapshot = lambda session, traveler_id: None
sm.snapshot_payload = lambda snapshot: {}
sm._anchor = lambda context, journey, kind: None


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _Session:
    def scalars(self, *args, **kwargs):
        return _Rows([])


class _Journey:
    id = "00000000-0000-4000-8000-000000000001"
    traveler_id = "00000000-0000-4000-8000-000000000002"
    title = "t"
    city_code = "CN-TIANJIN"
    budget_amount_minor = 10000
    budget_currency = "CNY"
    status = "PLANNED"
    active_plan_version_id = None
    timezone = "Asia/Shanghai"
    # The columns in question: bare local wall-clock, no offset.
    start_at = "2026-10-09T18:00:00"
    end_at = "2026-10-11T15:00:00"


def _offset(zone: str) -> timedelta:
    return datetime(2026, 10, 9, tzinfo=ZoneInfo(zone)).utcoffset()


def block(zone: str) -> dict:
    journey = type("Journey", (_Journey,), {"timezone": zone})()
    return sm.experience_payload(_Session(), journey)["journey"]


CASES = ("Asia/Shanghai", "Mars/Phobos")


def main() -> int:
    bad: list[str] = []
    checks = 0
    rows = []

    for zone in CASES:
        b = block(zone)
        rows.append((zone, b))
        checks += 1

        start, end = b.get("start_at"), b.get("end_at")
        # The payload must either place the window, or say the zone was not honoured.  On the pre-fix
        # bytes neither held: bare wall-clock strings and no flag at all.  "Placed" means the value
        # carries its offset -- a string with one, or a datetime whose tzinfo is set -- because that
        # is what FastAPI serialises into an offset-bearing instant on the wire.
        placed = isinstance(start, str) and ("+" in start or start.endswith("Z"))
        placed = placed or (isinstance(start, datetime) and start.tzinfo is not None)
        honoured = b.get("timezone_honoured")
        if not placed and honoured is not False:
            bad.append(
                "the payload names zone %r beside a window that is not placed (%r .. %r) and does "
                "not say the zone was not honoured -- the window is presented as placed when it is "
                "not" % (zone, start, end)
            )

        checks += 1
        if zone == "Asia/Shanghai":
            if not placed:
                bad.append("a usable zone still serialised a window with no offset: %r" % start)
            elif isinstance(start, datetime) and start.utcoffset() != _offset(zone):
                bad.append(
                    "the window is not in the zone the payload names: %r (zone %s)" % (start, zone)
                )
            if honoured is not True:
                bad.append("a usable zone was reported as not honoured (%r)" % (honoured,))

        checks += 1
        if "used_timezone" not in b:
            bad.append("the payload has no used_timezone -- it names a zone and not what it became")

    print("experience payload window: %d checks, %d bad" % (checks, len(bad)))
    for zone, b in rows:
        print(
            "   timezone=%-14r honoured=%-5s used=%-14r start=%r"
            % (
                zone,
                b.get("timezone_honoured", "<absent>"),
                b.get("used_timezone", "<absent>"),
                b.get("start_at"),
            )
        )
    if bad:
        print("\nARM BITES -- the experience payload names a zone its window is not in:")
        for x in bad:
            print("   " + x)
        return 1
    print("\nARM_QUIET: the window is either in the zone the payload names, or the payload says so.")
    return 0


if __name__ == "__main__":
    sys.exit(main())