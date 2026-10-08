"""Counter-arm for the two v9 device-facing moments.

The gap this pins: the last site in the time-domain sweep.  `operations/v9.py` carried two moments
into payloads a device reads (often offline) using `execution_clock.now(journey.timezone)`, which
silently falls back to UTC when the zone cannot be used -- so a payload named a zone and carried a
moment from another one, with the reader having no way to tell:

  * `refresh_offline_snapshot` serialises `reference_at` (the window this snapshot is valid for), and
  * the edge reconciliation response serialises `time` (the journey's now).

Both readers are devices that act on "now", and an unusable zone is silently presented as honoured
-- the shape `now_honest` answers for the execution clock, and the trip payload, the two model
contexts and the experience payload now answer.

This arm reads the real `refresh_offline_snapshot` and the real edge-reconcile function, and asserts
each payload says which zone its moment is in, or that the zone could not be used.
"""
from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "backend"))

import app.operations.v9 as v9  # noqa: E402
from app.db.models import OfflineJourneySnapshot, Journey  # noqa: E402


class _Rows:
    """A session that answers "no rows" for every read and swallows the writes.

    `refresh_offline_snapshot` and `edge_snapshot` only read; the one row that must exist is the
    snapshot being updated, which is passed in.
    """

    def __init__(self, rows=None):
        self._rows = list(rows or [])

    def all(self):
        return []

    def scalar(self, *a, **k):
        return None

    def scalars(self, *a, **k):
        return self

    def get(self, model, key, *a, **k):
        for row in self._rows:
            if isinstance(row, model):
                return row
        return None

    def flush(self):
        pass

    def add(self, row):
        self._rows.append(row)


class _Session(_Rows):
    pass


class _Journey:
    id = "00000000-0000-4000-8000-000000000001"
    traveler_id = "00000000-0000-4000-8000-000000000002"
    active_plan_version_id = None
    current_activity_id = None
    timezone = "Asia/Shanghai"
    status = "ACTIVE"


def journey(zone: str):
    return type("Journey", (_Journey,), {"timezone": zone})()


def offline_payload(zone: str) -> dict:
    existing = OfflineJourneySnapshot(
        journey_id=_Journey.id,
        sequence=0,
        valid_until="2026-10-01T00:00:00",
        payload_json="{}",
        provider_freshness_json="{}",
        updated_at="2026-10-01T00:00:00",
    )
    session = _Session([existing])
    row = v9.refresh_offline_snapshot(session, journey(zone))
    return json.loads(row.payload_json)

def edge_response(zone: str) -> dict:
    # `edge_snapshot` reads Commitment / Event / GuardianRun via scalars; our session returns a
    # dummy row for each, which the device-facing fields tolerate.  The device needs journey_id, and
    # the session must return the journey for that id.
    device = type(
        "EdgeDevice",
        (),
        {
            "journey_id": _Journey.id,
            "status": "ACTIVE",
            "last_sequence": 0,
            "updated_at": "2026-10-01T00:00:00",
        },
    )()
    journey_row = journey(zone)
    session = _Session([journey_row, type("C4", (), {})()])
    # `get(Journey, id)` must return the journey row, not the dummy.
    session.get = lambda model, key, *a, **k: journey_row if model is Journey else None
    return v9.edge_snapshot(session, device)


CASES = ("Asia/Shanghai", "Mars/Phobos")
SITES = (("offline reference_at", offline_payload), ("edge time", edge_response))


def main() -> int:
    bad: list[str] = []
    checks = 0
    rows = []

    for site, build in SITES:
        for zone in CASES:
            b = build(zone)
            rows.append((site, zone, b))
            checks += 1
            if "timezone_honoured" not in b or "used_timezone" not in b:
                bad.append(
                    "%s names a zone (%r) and does not say which zone its moment is in -- a usable "
                    "zone and an unusable one are the same bytes to the device" % (site, zone)
                )
                continue
            want_honoured = zone != "Mars/Phobos"
            if b["timezone_honoured"] is not want_honoured:
                bad.append(
                    "%s reported timezone_honoured=%r for zone %r, expected %r"
                    % (site, b["timezone_honoured"], zone, want_honoured)
                )

    print("v9 device-facing moments: %d checks, %d bad" % (checks, len(bad)))
    for site, zone, b in rows:
        print(
            "   %-22s timezone=%s honoured=%s used=%s"
            % (
                site,
                zone,
                b.get("timezone_honoured", "<absent>"),
                b.get("used_timezone", "<absent>"),
            )
        )
    if bad:
        print("\nARM BITES -- a device-facing moment names a zone and does not say if it can be used:")
        for x in bad:
            print("   " + x)
        return 1
    print("\nARM_QUIET: both device-facing moments say which zone was used, or that it could not be.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
