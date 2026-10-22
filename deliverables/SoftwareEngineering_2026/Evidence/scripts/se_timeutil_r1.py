"""Date reading helper for the Microsoft Project COM layer.

pywin32 hands back Project's Variant dates as tz-aware UTC datetimes, so
`str(task.Finish)[:10]` on a machine at UTC+8 silently returns the previous
day. Every date this build reports goes through dstr() instead.
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
        if getattr(v, "tzinfo", None) is not None:
            v = v.astimezone()
        elif " " in s or "T" in s:
            v = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
            if v.tzinfo is not None:
                v = v.astimezone()
        return v.strftime("%Y-%m-%d")
    except Exception:
        return s[:10]


def dur_hours(v):
    """Project stores duration in minutes; return whole working days."""
    try:
        return round(float(v) / 4800.0, 2)
    except Exception:
        return None
