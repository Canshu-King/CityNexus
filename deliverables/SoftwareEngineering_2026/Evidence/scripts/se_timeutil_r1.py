"""Date reading helper for the Microsoft Project COM layer.

MEASURED ON THIS INSTALL, 2026-10-23, against the application's own grid:

    row 1   grid shows  完成时间 2026年9月9日
            task.Finish returns 2026-09-09 17:00, tzinfo TimeZoneInfo('GMT
            Standard Time')
    project grid shows  完成时间 2026年10月23日
            p.Finish    returns 2026-10-23 17:00, same tzinfo

pywin32 tags Project's Variant dates with a timezone name that is not this
machine's (+08). Running the value through astimezone() therefore pushed every
end-of-working-day value forward by eight hours, i.e. one whole calendar day for
anything at 17:00. The first version of this helper did exactly that, on the
reasonable-looking theory that a tz-aware value must be converted to local time.
It is wrong here, and it silently made every finish date in the evidence one day
later than the plan.

So the day is taken from the value exactly as Project returns it, which is what
the application displays. selftest() below pins the three shapes this has to keep
working; the build calls it before it reads anything.
"""
import datetime


def dstr(v):
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return ""
    try:
        s = str(v)
    except Exception:
        return ""
    if s.startswith("NaT") or not s[:4].isdigit():
        return ""
    try:
        return "%04d-%02d-%02d" % (v.year, v.month, v.day)
    except Exception:
        return s[:10]


def dur_hours(v):
    """Project stores duration in minutes; return whole working days.

    8 h per working day, so 480 minutes: a 3-day summary reads 1440 minutes and
    the grid says 3 个工作日.
    """
    try:
        return round(float(v) / 480.0, 2)
    except Exception:
        return None


def selftest():
    """Returns a list of failures; empty means the reader agrees with the grid."""
    bad = []
    try:
        import pywintypes                                    # noqa: F401
        from win32timezone import TimeZoneInfo
        for label, val, want in (
                ("end of working day",
                 datetime.datetime(2026, 9, 9, 17, 0,
                                   tzinfo=TimeZoneInfo("GMT Standard Time")),
                 "2026-09-09"),
                ("start of working day",
                 datetime.datetime(2026, 9, 7, 8, 0,
                                   tzinfo=TimeZoneInfo("GMT Standard Time")),
                 "2026-09-07"),
                ("plain string", "2026-10-02 00:00:00", "2026-10-02"),
                ("empty date", None, ""),
                ("duration to working days", 1440, 3.0)):
            got = dstr(val) if label != "duration to working days" else dur_hours(val)
            if got != want:
                bad.append("%s: got %r want %r" % (label, got, want))
    except Exception as exc:
        bad.append("selftest could not run: %s: %s" % (type(exc).__name__, exc))
    return bad


if __name__ == "__main__":
    fails = selftest()
    print("se_timeutil_r1 selftest: %s" % ("PASS" if not fails else "FAIL"))
    for f in fails:
        print("   ", f)
    raise SystemExit(0 if not fails else 1)
