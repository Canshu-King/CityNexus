"""Counter-arm for the execution clock's zone honesty, measured on the PAYLOAD.

The defect this pins: `/api/v1/journeys/{id}/execution-clock` answered with `timezone` naming the
journey's zone beside a `now` that was in UTC whenever that zone could not be used.  The payload
contradicted itself and a reader had no way to place the moment.

`execution_clock.now()` is deliberately unchanged (other callers depend on it), so an arm pointed at
that method measures the wrong layer and reports quiet on both sides.  This arm therefore builds the
payload the way the endpoint does -- honouring the clock's zone report when it exists, falling back to
the old silent UTC path when it does not -- and asks one question of the result:

        is the instant in the zone THIS payload says it used?

Pre-fix the payload has no zone report, so "the zone it says it used" falls back to `timezone`,
which names `Mars/Phobos` beside a +00:00 instant, and the answer is no.  Post-fix the payload names
`UTC` and flags the journey's zone as not honoured, and the answer is yes.  Neither reading depends
on a symbol being present, so this arm fails on judgement rather than on an exception.
"""
import sys

sys.path.insert(0, "D:/moodle/_qoder_rel_ord0447_wt/backend")

from app.execution.clock import execution_clock  # noqa: E402

KNOWN_OFFSET = {"Asia/Shanghai": 8, "America/New_York": -4, "Europe/London": 1, "UTC": 0}
UNUSABLE = ["Mars/Phobos", "Not/AZone", "", None]


def payload(journey_timezone):
    """The endpoint's body, built exactly as the endpoint builds it."""
    if hasattr(execution_clock, "now_honest"):
        now, used_timezone, honoured = execution_clock.now_honest(journey_timezone or None)
        return {"now": now.isoformat(), "timezone": journey_timezone or None,
                "used_timezone": used_timezone, "timezone_honoured": honoured,
                "offset_minutes": int(now.utcoffset().total_seconds() // 60)}
    # the pre-fix endpoint: the instant silently, and the requested zone echoed verbatim
    now = execution_clock.now(journey_timezone or None)
    return {"now": now.isoformat(), "timezone": journey_timezone or None,
            "used_timezone": journey_timezone or None, "timezone_honoured": True,
            "offset_minutes": int(now.utcoffset().total_seconds() // 60)}


def main() -> int:
    bad = []
    checks = 0
    print("payload shape: %s" % sorted(payload("Asia/Shanghai")))

    for zone, hours in KNOWN_OFFSET.items():
        p = payload(zone)
        checks += 1
        if p["offset_minutes"] != hours * 60:
            bad.append("claims %s but the instant is %s min off it (%s)"
                       % (zone, p["offset_minutes"], p["now"]))
        if p["timezone_honoured"] is not True:
            bad.append("claims %s but reports the zone was NOT honoured" % zone)

    for zone in UNUSABLE:
        p = payload(zone)
        checks += 1
        used = p["used_timezone"]
        if used is None:
            continue
        expected = KNOWN_OFFSET.get(used)
        if expected is None:
            # The payload names a zone the clock could not have used.  On the pre-fix bytes this is
            # exactly the lie: `Mars/Phobos` beside a +00:00 instant.
            bad.append("names zone %r, which no offset here can justify, beside %s (%s min off)"
                       % (used, p["now"], p["offset_minutes"]))
        elif p["offset_minutes"] != expected * 60:
            bad.append("names %s but the instant is %s min off it (%s)"
                       % (used, p["offset_minutes"], p["now"]))

    print("execution-clock payload honesty: %d checks, %d bad" % (checks, len(bad)))
    for zone in list(KNOWN_OFFSET) + UNUSABLE:
        p = payload(zone)
        print("   asked=%-18r now=%-34s used=%-16r honoured=%-5s offset=%s"
              % (zone, p["now"], p["used_timezone"], p["timezone_honoured"], p["offset_minutes"]))
    if bad:
        print("\nARM BITES -- the payload does not say which zone its instant is in:")
        for b in bad:
            print("   " + b)
        return 1
    print("\nARM_QUIET: every payload places its instant in the zone it reports having used.")
    return 0


if __name__ == "__main__":
    sys.exit(main())