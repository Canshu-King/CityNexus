"""Canonical Journey day/night semantics shared by planning and stay pricing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class JourneyTemporalShape:
    """Calendar dates and overnight boundaries touched by a Journey."""

    day_count: int
    night_count: int


# Named rather than inlined in the signature so an entry point can state the same window it
# enforces (ORD-0033: the create endpoint now rejects before it persists, and the rejection
# has to carry the limit the traveller can act on).  These are product rules, not tuning
# knobs - `V13_JOURNEY_DAYS_OUT_OF_BOUNDS` is raised against them, and a gate pins the
# values so shrinking them to make a test pass cannot be silent.
MIN_JOURNEY_DAYS = 1
MAX_JOURNEY_DAYS = 7


def derive_journey_temporal_shape(
    arrival_at: datetime,
    departure_at: datetime,
    *,
    min_day_count: int = MIN_JOURNEY_DAYS,
    max_day_count: int = MAX_JOURNEY_DAYS,
) -> JourneyTemporalShape:
    """Derive one calendar-date shape for every Journey consumer.

    A same-date Journey touches one calendar day and crosses no overnight
    boundary.  A departure on a later calendar date touches that many date
    boundaries plus the arrival date, so Oct 1 -> Oct 4 is 4 days / 3 nights.
    """

    if departure_at <= arrival_at:
        raise ValueError("V13_INVALID_ANCHOR_WINDOW")

    night_count = max(0, (departure_at.date() - arrival_at.date()).days)
    day_count = max(1, night_count + 1)
    if day_count < min_day_count or day_count > max_day_count:
        raise ValueError(f"V13_JOURNEY_DAYS_OUT_OF_BOUNDS:{day_count}")
    return JourneyTemporalShape(day_count=day_count, night_count=night_count)
