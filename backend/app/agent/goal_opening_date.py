"""Does this venue open on the day the traveller is actually there?

The shared opening-hours parser reads a provider's prose into intervals, and AMap's prose is aggregate:
「旺季4月11日至10月31日 周二至周日 08:30-17:00 16:00停止售票；淡季11月1日至3月31日 周二至周日
08:30-16:30 … 周一全天关闭；期间营业时间以官方通知为准」 flattens to ``days: ["*"]`` — a schedule that says
the故宫 opens every day, which it does not.  `goal_amap._amap_opening_envelope` already refuses to hide
that: it keeps the provider's own sentence and marks ``weekday_coverage=UNRESOLVED``.

This module is the other half: it reads that kept sentence *against the date the traveller picked*, and
answers one of four things, without ever inventing a window.

    OPEN_ON_DATE           the sentence says this weekday (and, when it names seasons, this calendar day)
                           is inside a window, and the arrival falls in it
    CLOSED_ON_DATE         the sentence closes this weekday, or the day sits in a stated yearly closure
    TIME_OUTSIDE_WINDOW    the day is served, but not at the hour the plan puts the traveller there
    DATE_SPECIFIC_UNKNOWN  the sentence cannot be resolved for this date -- including 「以官方通知为准」

A known answer only ever comes from the provider text that is already stored; nothing here queries a
calendar service, and an unresolved answer stays unresolved instead of quietly inheriting "every day".
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Mapping

OPEN_ON_DATE = "OPEN_ON_DATE"
CLOSED_ON_DATE = "CLOSED_ON_DATE"
TIME_OUTSIDE_WINDOW = "TIME_OUTSIDE_WINDOW"
DATE_SPECIFIC_UNKNOWN = "DATE_SPECIFIC_UNKNOWN"

# AMap writes the week in Chinese, and 周日/周天 both mean Sunday.
_WEEKDAY_ORDER = ("一", "二", "三", "四", "五", "六", "日")
_WEEKDAY_TO_INDEX = {name: index for index, name in enumerate(_WEEKDAY_ORDER)}
_WEEKDAY_TO_INDEX["天"] = 6
_TOKEN = r"(?:周|星期|礼拜)(" + "|".join(_WEEKDAY_ORDER) + r"|天)"
_RANGE = re.compile(_TOKEN + r"\s*(?:至|到|-|~|—|–)\s*" + _TOKEN)
_LIST = re.compile(_TOKEN)
_MONTH_DAY = re.compile(r"(?:(\d{1,2})\s*月)?\s*(\d{1,2})\s*[日号]")
_CLOCK = re.compile(r"(\d{1,2})[:：](\d{2})")
_CLOSE_MARKS = ("关闭", "闭馆", "休馆", "不开放", "不营业", "休息", "停开")
_DEFERS_TO_NOTICE = ("以官方通知为准", "以公告为准", "另行通知", "为准")
_HOLIDAY_MARKS = ("春节", "劳动节", "端午节", "中秋节", "国庆节", "元旦", "节假日", "假日")
# The three statutory holidays whose date does not move.  A sentence that ends 「节假日营业时间以官方
# 通知为准」 hands these days to an announcement nobody has stored, so on them the honest answer is
# unknown even when the weekday rule says the venue serves that weekday.  春节/端午/中秋 dates move with
# the lunar calendar and are deliberately not here -- inventing them would be the failure this whole
# module exists to refuse.
_FIXED_HOLIDAYS = {(1, 1): "元旦", (5, 1): "劳动节", (10, 1): "国庆节"}
_DATE_SPAN = re.compile(
    r"(\d{1,2}\s*月\s*\d{1,2}\s*[日号])\s*(?:至|到|-|–|—|~|～)\s*"
    r"(\d{1,2}\s*月\s*\d{1,2}\s*[日号])"
)
_NUMERIC_DATE_SPAN = re.compile(
    r"(?<!\d)(\d{1,2})\s*/\s*(\d{1,2})\s*(?:至|到|-|–|—|~|～)\s*"
    r"(\d{1,2})\s*/\s*(\d{1,2})(?!\d)"
)
_NUMERIC_DATE_SPAN_HINT = re.compile(r"(?<!\d)\d{1,2}\s*/\s*\d{1,2}\s*(?:至|到|-|–|—|~|～)")


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if len(text) == 10:
            return date.fromisoformat(text)
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _minutes_of(value: Any) -> int | None:
    """A clock time in minutes from midnight, from ``HH:MM`` or from an ISO stamp.

    ``24:00`` is a closing bound, not an hour: AMap writes an always-open street as 「00:00-24:00」 and
    dropping that pair made a venue which states its whole day look like a venue nobody answered for.
    It is accepted only as the end of a window -- a start of 24:00 or an arrival stamp at 24:00 is not a
    time anyone can be at a place.
    """

    text = str(value or "").strip()
    if not text:
        return None
    clock = _CLOCK.search(text)
    if clock:
        hour, minute = int(clock.group(1)), int(clock.group(2))
        if hour == 24 and minute == 0:
            return 24 * 60
        if hour <= 23 and minute <= 59:
            return hour * 60 + minute
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment.hour * 60 + moment.minute


def _month_day(token: str, year: int) -> date | None:
    match = _MONTH_DAY.search(token)
    if not match:
        return None
    month = int(match.group(1) or 0)
    day = int(match.group(2))
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _date_spans(clause: str, year: int) -> tuple[list[tuple[date, date]], bool]:
    """Read valid Chinese and month/day spans, also reporting malformed span syntax."""
    spans: list[tuple[date, date]] = []
    has_invalid_span = False
    for match in _DATE_SPAN.finditer(clause):
        first = _month_day(match.group(1), year)
        second = _month_day(match.group(2), year)
        if first is None or second is None:
            has_invalid_span = True
        else:
            spans.append((first, second))
    for match in _NUMERIC_DATE_SPAN.finditer(clause):
        first = _month_day(f"{match.group(1)}月{match.group(2)}日", year)
        second = _month_day(f"{match.group(3)}月{match.group(4)}日", year)
        if first is None or second is None:
            has_invalid_span = True
        else:
            spans.append((first, second))
    return spans, has_invalid_span


def _inside_span(day: date, first: date, second: date) -> bool:
    """Is the date inside a stated month-day span, including one that wraps the new year?

    「淡季11月1日至3月31日」 is written as first > second and means the union of both halves.
    """

    return first <= day <= second or first > second and (day >= first or day <= second)


def _served_weekdays(clause: str) -> set[int] | None:
    """The weekdays one clause speaks about, or None when it names none."""

    expanded: set[int] = set()
    rest = clause
    for match in _RANGE.finditer(clause):
        first, second = _WEEKDAY_TO_INDEX[match.group(1)], _WEEKDAY_TO_INDEX[match.group(2)]
        step = first
        while True:
            expanded.add(step)
            if step == second:
                break
            step = (step + 1) % 7
    if expanded:
        rest = _RANGE.sub(" ", rest)
    singles = {_WEEKDAY_TO_INDEX[name] for name in _LIST.findall(rest)}
    if not expanded and not singles:
        return None
    return expanded | singles


def _clauses(text: str) -> list[str]:
    """Split provider prose the way it is actually written.

    Measured consequence of splitting only on 「；」: AMap joins the 故宫 sentence with full-width commas
    -- 「淡季11月1日至3月31日 周二至周日 08:30-16:30 15:30停止检票，周一全天关闭，…」 -- so the seasonal
    date range and the weekly closure landed in one clause, the clause said 「关闭」, and 11月1日至3月31日
    was read as a yearly closure.  A traveller on a Thursday in December was told the museum was shut.
    The comma is a clause separator in this prose, so it separates them here.
    """

    return [part.strip() for part in re.split(r"[；;。，,\n]", text) if part.strip()]


def _window_in(clause: str) -> tuple[int, int] | None:
    """First ``HH:MM-HH:MM`` (or ``HH:MM~HH:MM``) pair inside a clause.

    The bounds come from `_minutes_of` so a closing 「24:00」 is a window end here exactly where it is
    one in the parsed-interval fallback below, instead of one arm of the same reader rejecting a
    sentence the other arm accepts.
    """

    times = _CLOCK.findall(clause)
    if len(times) < 2:
        return None
    pairs = [value for value in (_minutes_of(f"{hour}:{minute}") for hour, minute in times)
             if value is not None]
    if len(pairs) < 2:
        return None
    start, end = pairs[0], pairs[1]
    if start >= 24 * 60:
        return None
    return (start, end) if end >= start else (start, start)


def verdict_for_date(envelope: Mapping[str, Any], on: Any, *, arrival: Any = None) -> dict[str, Any]:
    """Answer for one venue, one calendar day, and (optionally) the hour the plan arrives."""

    day = _parse_date(on)
    if day is None:
        return {"verdict": DATE_SPECIFIC_UNKNOWN, "reason_code": "DATE_NOT_GIVEN", "source_text": None,
                "window": None, "weekday": None}
    weekday = day.weekday()
    text = str(envelope.get("raw") or "").strip()
    if not text:
        # No sentence to read: the caller's own status already says whether anybody asked.
        return {"verdict": DATE_SPECIFIC_UNKNOWN, "reason_code": "NO_SOURCE_TEXT", "source_text": None,
                "window": None, "weekday": weekday}

    closed_weekdays: set[int] = set()
    open_weekdays: set[int] = set()
    yearly_closed: list[tuple[date, date]] = []
    windows: list[tuple[int, int]] = []
    seasons: list[tuple[date, date, tuple[int, int], set[int] | None]] = []
    date_spans_seen = False
    holiday_hours_seen = False
    date_all_days = False
    defers = any(mark in text for mark in _DEFERS_TO_NOTICE)
    for clause in _clauses(text):
        served = _served_weekdays(clause)
        closes = any(mark in clause for mark in _CLOSE_MARKS)
        window = _window_in(clause)
        has_date_span = bool(_DATE_SPAN.search(clause) or _NUMERIC_DATE_SPAN_HINT.search(clause))
        date_spans_seen = date_spans_seen or has_date_span
        spans, invalid_span = _date_spans(clause, day.year)
        if has_date_span:
            if invalid_span or not spans:
                # An invalid or unresolved interval must not broaden its hours or weekday claim.
                continue
            spans = [(first, second) for first, second in spans if _inside_span(day, first, second)]
            if not spans:
                continue
        elif any(mark in clause for mark in _HOLIDAY_MARKS):
            # A holiday-only window has no calendar binding in this source text; never treat it as
            # the venue's ordinary schedule.
            holiday_hours_seen = holiday_hours_seen or window is not None
            continue
        if closes:
            if spans and served is None:
                # A date range only closes a day when the same clause says it closes something.  AMap
                # writes seasonal ranges in the same shape; a weekday clause narrows a closure to both
                # that date interval and the named weekday.
                yearly_closed.extend(spans)
            elif served is not None:
                closed_weekdays |= served
        elif window is not None and spans:
            # The hours belong to the span written in the same clause: 「淡季11月1日至3月31日 周二至周日
            # 08:30-16:30」.  Measured consequence of ignoring that binding, with the comma split above
            # in place -- a Thursday in December was checked against 旺季's 17:00 close, so an 16:45
            # arrival read as open when the source says the museum stops admitting at 16:30 that season.
            for first, second in spans:
                seasons.append((first, second, window, served))
            if served is None:
                date_all_days = True
            else:
                open_weekdays |= served
        elif window is not None:
            windows.append(window)
        if served is None:
            continue
        if closes:
            closed_weekdays |= served
        else:
            open_weekdays |= served

    inside_yearly = any(_inside_span(day, first, second) for first, second in yearly_closed)
    mentions_weekdays = bool(open_weekdays or closed_weekdays)
    # A closure that names the weekday wins over an interval that flattened to "every day": that is the
    # whole reason the provider sentence is kept next to the parsed one.
    if weekday in closed_weekdays or inside_yearly:
        # A yearly closure the source states (「1月1日至1月3日 闭馆」) takes the day out of service even
        # when the weekly sentence would otherwise serve it; only a clause that *says* it closes
        # something can set that range, which is what keeps 旺季/淡季 ranges from becoming closures.
        return {"verdict": CLOSED_ON_DATE, "reason_code": "SOURCE_SAYS_CLOSED_ON_THIS_DAY",
                "source_text": text[:400], "window": None, "weekday": weekday, "defers_to_notice": defers}
    if open_weekdays and weekday not in open_weekdays and not date_all_days:
        # The prose restricts service to other weekdays.  Saying "unknown" here would be softer than the
        # source, and saying "open" would be the flattening this module exists to refuse.
        return {"verdict": CLOSED_ON_DATE, "reason_code": "SOURCE_SERVES_OTHER_DAYS_ONLY",
                "source_text": text[:400], "window": None, "weekday": weekday, "defers_to_notice": defers}

    holiday = _FIXED_HOLIDAYS.get((day.month, day.day))
    if holiday is not None and defers:
        # Measured on the 故宫 sentence: the weekday rule serves a Thursday, so before this arm the
        # reader answered OPEN_ON_DATE for 10月1日 while the very same sentence says holidays follow an
        # official notice.  The date is the one thing the notice changes.
        return {"verdict": DATE_SPECIFIC_UNKNOWN, "reason_code": "SOURCE_DEFERS_TO_NOTICE_FOR_A_HOLIDAY",
                "source_text": text[:400], "window": None, "weekday": weekday, "defers_to_notice": True,
                "holiday": holiday}

    arrival_min = _minutes_of(arrival)
    candidates = [window for window in windows if window is not None]
    in_season = [window for first, second, window, served in seasons
                 if _inside_span(day, first, second) and (served is None or weekday in served)]
    if in_season:
        # The span the source wrote for this calendar day is the bound for this date; a window that
        # carries no span stays behind it as the venue's general hours.
        candidates = in_season + candidates
    elif (seasons or date_spans_seen or holiday_hours_seen) and not candidates:
        # Seasons are stated and none of them reaches this date: the sentence does not speak about the
        # day the traveller picked, and borrowing another season's hours would invent a window.
        return {"verdict": DATE_SPECIFIC_UNKNOWN, "reason_code": "SOURCE_SEASON_NOT_STATED_FOR_THIS_DAY",
                "source_text": text[:400], "window": None, "weekday": weekday, "defers_to_notice": defers}
    if not candidates and not date_spans_seen and not holiday_hours_seen:
        intervals = envelope.get("intervals") if isinstance(envelope.get("intervals"), list) else []
        for row in intervals:
            if not isinstance(row, Mapping):
                continue
            low, high = _minutes_of(row.get("open")), _minutes_of(row.get("close"))
            if low is not None and high is not None:
                candidates.append((low, high))
    if (date_all_days or (open_weekdays and weekday in open_weekdays)) and arrival_min is not None and candidates:
        if not any(low <= arrival_min <= high for low, high in candidates):
            return {"verdict": TIME_OUTSIDE_WINDOW, "reason_code": "ARRIVES_OUTSIDE_THE_STATED_WINDOW",
                    "source_text": text[:400], "window": candidates[0], "weekday": weekday,
                    "defers_to_notice": defers}
        return {"verdict": OPEN_ON_DATE, "reason_code": None, "source_text": text[:400],
                "window": candidates[0], "weekday": weekday, "defers_to_notice": defers}
    if defers and mentions_weekdays:
        # The sentence restricts days and at the same time hands the period over to an official notice
        # (「期间营业时间以官方通知为准」).  That is not a claim we may read as open.
        return {"verdict": DATE_SPECIFIC_UNKNOWN, "reason_code": "SOURCE_DEFERS_TO_NOTICE",
                "source_text": text[:400], "window": candidates[0] if candidates else None,
                "weekday": weekday, "defers_to_notice": True}
    if not mentions_weekdays:
        # Nothing in the sentence speaks about any weekday: the provider states hours and no day rule,
        # so the hours are what they are for this date too.
        if candidates and arrival_min is not None:
            if not any(low <= arrival_min <= high for low, high in candidates):
                return {"verdict": TIME_OUTSIDE_WINDOW, "reason_code": "ARRIVES_OUTSIDE_THE_STATED_WINDOW",
                        "source_text": text[:400], "window": candidates[0], "weekday": weekday,
                        "defers_to_notice": defers}
            return {"verdict": OPEN_ON_DATE, "reason_code": None, "source_text": text[:400],
                    "window": candidates[0], "weekday": weekday, "defers_to_notice": defers}
    # The day is served and the arrival still could not be placed.  Say which half is missing, read from
    # the sentence itself, because the traveller sees that sentence next to this line: 「周一至周日
    # 00:00-24:00」 names all seven days and states its bound only as 24:00, so answering
    # WEEKDAY_NOT_STATED for it contradicted the source text printed beside it.
    if not candidates:
        return {"verdict": DATE_SPECIFIC_UNKNOWN, "reason_code": "NO_WINDOW_STATED",
                "source_text": text[:400], "window": None, "weekday": weekday, "defers_to_notice": defers}
    if arrival_min is None:
        return {"verdict": DATE_SPECIFIC_UNKNOWN, "reason_code": "NO_ARRIVAL_GIVEN",
                "source_text": text[:400], "window": candidates[0], "weekday": weekday,
                "defers_to_notice": defers}
    return {"verdict": DATE_SPECIFIC_UNKNOWN, "reason_code": "SOURCE_NAMES_CLOSED_DAYS_ONLY",
            "source_text": text[:400], "window": candidates[0] if candidates else None,
            "weekday": weekday, "defers_to_notice": defers}
