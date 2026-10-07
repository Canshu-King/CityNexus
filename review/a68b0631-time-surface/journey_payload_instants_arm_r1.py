"""Counter-arm for the journey payload's instants.

The gap this pins: `GET /api/v1/journeys/{id}` answered with `timezone` beside `start_at`/`end_at`
that were serialised from a bare local wall-clock column -- `2026-10-09T18:00:00`, no offset.  So the
payload named a zone and carried instants that carried none: the reader had no way to place the
moment, which is the same shape the execution clock answers for.

This arm reads the real `journey_schema` (only a stand-in row, no database) and asserts:
  * an instant in a payload must carry the offset its own `timezone` implies, or
  * the payload must say the zone was not honoured -- so an unplaceable moment is never presented as
    if it were placed.
"""
import sys

sys.path.insert(0, "D:/moodle/_qoder_rel_ord0447_wt/backend")

from app.services import journey_schema  # noqa: E402


class Row:
    id = "00000000-0000-4000-8000-000000000001"
    traveler_id = "00000000-0000-4000-8000-000000000002"
    title = "t"
    city_code = "CN-TIANJIN"
    timezone = "Asia/Shanghai"
    start_at = "2026-10-09T18:00:00"          # local wall-clock, no offset -- the shape in question
    end_at = "2026-10-11T15:00:00"
    budget_amount_minor = 1
    budget_currency = "CNY"
    planning_mode = "balanced"
    status = "PLANNED"
    active_plan_version_id = None
    current_activity_id = None
    aborted_at = None
    abort_reason = None


def payload(zone: str):
    row = type("Row", (Row,), {"timezone": zone})()
    s = journey_schema(row)
    return {"timezone": s.timezone,
            "honoured": getattr(s, "timezone_honoured", None),
            "start": s.start_at.isoformat(),
            "end": s.end_at.isoformat(),
            "start_has_offset": s.start_at.tzinfo is not None,
            "end_has_offset": s.end_at.tzinfo is not None}


def main() -> int:
    bad = []
    checks = 0

    good = payload("Asia/Shanghai")
    checks += 1
    if not good["start_has_offset"] or not good["end_has_offset"]:
        bad.append("a usable zone still serialised an instant with no offset: %s" % good["start"])
    if "+08:00" not in good["start"]:
        bad.append("the instant is not in the zone the payload names: %s (zone %s)"
                   % (good["start"], good["timezone"]))
    if good["honoured"] is not True:
        bad.append("a usable zone was reported as not honoured")

    ugly = payload("Mars/Phobos")
    checks += 1
    # Either the instants carry an offset, or the payload says the zone was not honoured.  On the
    # pre-fix bytes neither holds: naive instants and no flag at all.
    if not ugly["start_has_offset"] and ugly["honoured"] is not False:
        bad.append("the payload names zone %r beside an instant with no offset (%s) and does not say "
                   "the zone was not honoured -- the moment is presented as placed when it is not"
                   % (ugly["timezone"], ugly["start"]))

    print("journey payload instants: %d checks, %d bad" % (checks, len(bad)))
    for zone in ("Asia/Shanghai", "Mars/Phobos"):
        p = payload(zone)
        print("   timezone=%-16r honoured=%-5s start=%-28s offset=%s"
              % (p["timezone"], p["honoured"], p["start"], p["start_has_offset"]))
    if bad:
        print("\nARM BITES -- a payload names a zone its instants are not in:")
        for b in bad:
            print("   " + b)
        return 1
    print("\nARM_QUIET: every instant is either in the zone the payload names, or the payload says so.")
    return 0


if __name__ == "__main__":
    sys.exit(main())