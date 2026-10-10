"""Counter-arm for the stay offer's check-in window zone honesty.

The gap this pins -- measured, not assumed.  `_at_on_day` places a hotel's local wall-clock
check-in/check-out in the *journey's* zone.  When that zone cannot be used it fell back to the
anchor's own offset, and `except Exception: zone = None` made the fallback silent.  On the tip's
bytes, with an anchor stored as `2026-10-09T18:00:00+00:00` and a `14:00` check-in asked for:

    usable zone  -> check_in 2026-10-10T06:00:00+00:00
    broken zone  -> check_in 2026-10-09T14:00:00+00:00      (sixteen hours away, a different day)
    no zone      -> check_in 2026-10-09T14:00:00+00:00      (byte-identical to the broken zone)

Those two instants are then compared as `arrival_at < check_in_at` to decide whether a stay reads as
a conflict, and they are what the traveller is shown as the check-in line.  So a zone nobody can use
was silently moving a money-relevant day, and nothing downstream could tell it apart from a journey
that never named a zone at all.

The fix records the verdict where the window is written (`evidence.check_window_timezone_honoured`,
which the read surface already passes through verbatim) and narrows the swallow to the zone errors it
actually means.

This arm runs the real `capture_accommodation_offers` (a stand-in journey, a session with no rows;
only the helpers that would need a database are stubbed), so it reads what the door actually writes.
On the tip's bytes the flag is absent in both arms and the arm exits 1.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "backend"))

import app.stay_mobility as sm  # noqa: E402

ANCHOR_AT = "2026-10-09T18:00:00+00:00"
DEPARTURE_AT = "2026-10-12T11:00:00+00:00"
NIGHTS = 2

# Only the helpers that would need a database or a provider are stubbed; the window arithmetic and
# the evidence write -- the things under test -- stay real.
sm._context = lambda session, journey: type(
    "Ctx",
    (),
    {
        "party_size": 2,
        "id": journey.id,
        "occupancy_json": "{}",
        "arrival_anchor_json": "{}",
        "departure_anchor_json": "{}",
        "stay_budget_declared": None,
        "stay_budget_amount_minor": None,
        "stay_budget_currency": None,
    },
)()
sm._anchor = lambda context, journey, kind: {
    "at": ANCHOR_AT if kind == "arrival" else DEPARTURE_AT
}
sm._nights = lambda context, journey: NIGHTS
sm._operations_context = lambda session, journey: None
sm.city_fixture = lambda city_code: {"stays": []}


class _Draft:
    external_offer_id = "offer-1"
    property_name = "Test Hotel"
    latitude = 39.0
    longitude = 117.0
    coordinate_crs = "WGS84"
    room_type = "double"
    nightly_amount_minor = 10000
    refundable = True
    luggage_drop = {"available": True}
    evidence_confidence = 0.9


class _Provider:
    provider_key = "stub-provider"
    provenance = "STUB"

    def discover(self, *, city_code, party_size, nights):
        return [_Draft()]


class _Rows:
    def all(self):
        return []


class _Session:
    def scalars(self, *a, **k):
        return _Rows()

    def scalar(self, *a, **k):
        return None

    def get(self, *a, **k):
        return None

    def add(self, row):
        pass

    def flush(self):
        pass


class _Journey:
    id = "00000000-0000-4000-8000-000000000001"
    traveler_id = "00000000-0000-4000-8000-000000000002"
    city_code = "CN-TIANJIN"
    timezone = "Asia/Shanghai"
    budget_amount_minor = 100000
    budget_currency = "CNY"
    status = "PLANNED"
    start_at = ANCHOR_AT
    end_at = DEPARTURE_AT


def offer(zone):
    journey = type("Journey", (_Journey,), {"timezone": zone})()
    real_provider = sm.CapturedAccommodationProvider
    sm.CapturedAccommodationProvider = _Provider
    sm.OsmAccommodationProvider = _Provider
    try:
        rows = sm.capture_accommodation_offers(_Session(), journey, attempts_out=[])
    finally:
        sm.CapturedAccommodationProvider = real_provider
    return rows[0]


def evidence_of(row):
    import json

    return json.loads(row.evidence_json)


GOOD = "Asia/Shanghai"
BAD = "Mars/Phobos"


def main() -> int:
    bad = []
    checks = 0

    good_row = offer(GOOD)
    bad_row = offer(BAD)
    good_ev = evidence_of(good_row)
    bad_ev = evidence_of(bad_row)

    good_in = datetime.fromisoformat(good_row.check_in_at)
    bad_in = datetime.fromisoformat(bad_row.check_in_at)
    shift = good_in - bad_in

    # 1. The shift is real, not cosmetic -- the premise the whole finding rests on.
    checks += 1
    if shift.total_seconds() == 0:
        bad.append("a broken zone produced the same check-in as a usable one -- the finding this "
                   "cell delivers against is not reproducible on these bytes")

    # 2. The flag exists on both arms.
    for zone, ev in ((GOOD, good_ev), (BAD, bad_ev)):
        checks += 1
        if "check_window_timezone_honoured" not in ev:
            bad.append("offer captured with zone %r records no check_window_timezone_honoured -- "
                       "the fallback is silent and the reader cannot tell a placed window from an "
                       "unplaced one" % zone)

    # 3. And it disagrees between the arms -- a constant would be as good as no flag.
    checks += 1
    if good_ev.get("check_window_timezone_honoured") == bad_ev.get(
        "check_window_timezone_honoured"
    ):
        bad.append("usable and unusable zones carry the same honoured value (%r) -- the flag does "
                   "not state the thing it is there to state"
                   % good_ev.get("check_window_timezone_honoured"))

    checks += 1
    if good_ev.get("check_window_timezone_honoured") is not True:
        bad.append("a usable zone was recorded as not honoured")
    checks += 1
    if bad_ev.get("check_window_timezone_honoured") is not False:
        bad.append("an unusable zone was recorded as honoured")

    # 4. The broken zone and "never named a zone" must now be tellable apart.
    checks += 1
    no_zone_ev = evidence_of(offer(None))
    if no_zone_ev.get("check_window_timezone_honoured") is not False:
        bad.append("no zone at all is not recorded as unhonoured either")
    checks += 1
    if bad_in == datetime.fromisoformat(offer(None).check_in_at) and (
        bad_ev.get("check_window_timezone_honoured")
        == no_zone_ev.get("check_window_timezone_honoured")
        and bad_ev.get("journey_timezone") == no_zone_ev.get("journey_timezone")
    ):
        bad.append("a broken zone and no zone are still identical bytes including the flag -- the "
                   "two facts the fallback erased have not been separated")

    print("stay offer check-in window zone honesty: %d checks, %d bad" % (checks, len(bad)))
    print("   usable zone  -> check_in=%s honoured=%s" % (good_row.check_in_at,
                                                          good_ev.get("check_window_timezone_honoured")))
    print("   broken zone  -> check_in=%s honoured=%s  shift=%s"
          % (bad_row.check_in_at, bad_ev.get("check_window_timezone_honoured"), shift))
    print("   no zone      -> honoured=%s" % no_zone_ev.get("check_window_timezone_honoured"))
    if bad:
        print("\nARM BITES -- an unusable zone moves the traveller's check-in day and says nothing:")
        for item in bad:
            print("   " + item)
        return 1
    print("\nARM_QUIET: the window's verdict is recorded with the window, and the two facts stay apart.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
