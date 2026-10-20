"""Classroom mode: when no provider can answer, keep moving with a labelled estimate.

The strict product contract stops at `UNKNOWN`.  That is right for a live deployment --
a number nobody measured must not become a feasibility decision -- and it is also what
freezes a coursework demo the moment Photon, Overpass, Valhalla or a search engine is
not configured.

One switch resolves that tension: `CITYNEXUS_CLASSROOM_MODE=true`.  When it is on, the
dead ends below answer with an estimate instead of nothing:

  * the on-demand route session falls back to the mock provider's blanket default
    instead of refusing to capture a pair that has no explicit matrix cell;
  * `mission_route_snapshot` reports a modelled ETA when the edge was never acquired;
  * `discover_source_leads` / `research_place_sources` report the angles worth looking
    at when no web provider is configured;
  * the live-context watcher reports whether the planned interval would fit a
    category-typical opening window when the place has no qualified hours.

Three rules keep the estimates from laundering themselves into truth:

  1. every estimate carries `authority="MODEL_ESTIMATE"` and `authority_eligible=False`,
     so the hard feasibility gate (`main.hard_minutes`) rejects it unchanged -- the
     switch loosens *display*, never the gate;
  2. every estimate carries the `basis` that produced it (a table of same-city
     heuristics, not a measurement), so a reviewer can see how the number was made;
  3. nothing is invented as *evidence*.  No coordinates, no fake URLs, no cost figure
     a provider never returned.  An estimate is a modelling step, and it says so.

With the switch off (the default) every path in this module is inert and the strict
behaviour and its tests are untouched.
"""

from __future__ import annotations

from typing import Any

from app.core import config

AUTHORITY = "MODEL_ESTIMATE"

#: minutes of the day, `[open, close]`, per provider category family.
_CATEGORY_WINDOWS: tuple[tuple[tuple[str, ...], int, int, str], ...] = (
    (("museum", "gallery", "art"), 9 * 60, 17 * 60, "museum-typical 09:00-17:00"),
    (("park", "garden", "nature", "landmark", "monument"), 6 * 60, 20 * 60, "open-site-typical 06:00-20:00"),
    (
        ("attraction", "tourist", "theme", "zoo", "aquarium", "observatory"),
        9 * 60,
        18 * 60,
        "ticketed-attraction-typical 09:00-18:00",
    ),
    (("restaurant", "food", "cafe", "coffee", "bar", "dining"), 11 * 60, 22 * 60, "dining-typical 11:00-22:00"),
    (("shopping", "mall", "store", "market", "shop"), 10 * 60, 22 * 60, "retail-typical 10:00-22:00"),
    (
        ("theatre", "theater", "cinema", "concert", "entertainment", "nightlife"),
        18 * 60,
        24 * 60,
        "evening-venue-typical 18:00-24:00",
    ),
    (("hotel", "hostel", "accommodation", "transport", "transit", "station", "airport"), 0, 24 * 60, "always-open"),
)
_DEFAULT_WINDOW = (9 * 60, 17 * 60, "category-unknown default 09:00-17:00")

#: minutes per kilometre, plus a fixed per-trip overhead, per mobility mode family.
_MODE_RATES: tuple[tuple[tuple[str, ...], float, int, str], ...] = (
    (("walk", "foot", "pedestrian"), 12.8, 0, "4.7 km/h walking pace"),
    (("bike", "cycl", "scooter"), 4.0, 0, "15 km/h cycling pace"),
    (("car", "drive", "taxi", "ride"), 2.5, 5, "24 km/h urban driving plus 5 min curb time"),
    (
        ("transit", "bus", "metro", "subway", "train", "tram"),
        5.0,
        9,
        "6 min for the line, 3 min per transfer, 9 min wait",
    ),
)
_DEFAULT_RATE = (5.0, 9, "transit-typical pace")

#: minutes assumed for a trip whose distance nobody measured.
_UNMEASURED_TRIP_MINUTES = {
    "walk": 20,
    "bike": 8,
    "car": 15,
    "transit": 25,
}


def classroom_mode() -> bool:
    """Read the switch at call time so a deployment (or a test) can flip it."""

    return bool(getattr(config.settings, "classroom_mode", False))


def estimate(payload: dict[str, Any]) -> dict[str, Any]:
    """Stamp one estimate block with the authority markers every caller must carry."""

    stamped = {
        "status": "ESTIMATED_CLASSROOM",
        "authority": AUTHORITY,
        "authority_eligible": False,
        "provider": "classroom-heuristic",
    }
    stamped.update(payload)
    return stamped


def estimated_hours(category: Any) -> dict[str, Any]:
    """A category-typical opening window, used only when the place has no qualified hours."""

    token = str(category or "").strip().casefold()
    open_minutes, close_minutes, basis = _DEFAULT_WINDOW
    for keys, low, high, reason in _CATEGORY_WINDOWS:
        if any(key in token for key in keys):
            open_minutes, close_minutes, basis = low, high, reason
            break
    return estimate(
        {
            "kind": "opening_hours",
            "open_minutes": open_minutes,
            "close_minutes": close_minutes,
            "open": f"{open_minutes // 60:02d}:{open_minutes % 60:02d}",
            "close": f"{close_minutes // 60:02d}:{close_minutes % 60:02d}",
            "category": token or None,
            "basis": basis,
        }
    )


def window_fit(window: dict[str, Any], *, start_minutes: int, end_minutes: int) -> str:
    """Would the planned interval sit inside the estimated window?

    `OVERNIGHT` means the venue window runs past midnight (or the activity does), so a
    plain minute comparison cannot decide it and the answer says so instead of guessing.
    """

    low = int(window.get("open_minutes") or 0)
    high = int(window.get("close_minutes") or 0)
    if high <= low or high >= 24 * 60 or end_minutes <= start_minutes:
        return "OVERNIGHT_UNDECIDABLE"
    if start_minutes < low:
        return "EARLY_OF_WINDOW"
    if end_minutes > high:
        return "LATE_OF_WINDOW"
    return "INSIDE_ESTIMATED_WINDOW"


def estimated_route(*, mode: Any, distance_m: Any = None) -> dict[str, Any]:
    """A modelled travel time for one mode, from a pace table and the known distance.

    When `distance_m` is absent the figure is a typical intra-city trip length for that
    mode, and `basis` names that assumption rather than hiding it.
    """

    token = str(mode or "TRANSIT").strip().casefold()
    per_km, overhead, pace_basis = _DEFAULT_RATE
    for keys, rate, pad, reason in _MODE_RATES:
        if any(key in token for key in keys):
            per_km, overhead, pace_basis = rate, pad, reason
            break
    metres = None
    try:
        if distance_m is not None:
            metres = float(distance_m)
    except (TypeError, ValueError):
        metres = None
    family = next(
        (name for name in ("walk", "bike", "car", "transit") if name in token),
        "transit",
    )
    if metres is not None and metres > 0:
        duration_min = round(metres / 1000.0 * per_km + overhead)
        basis = f"{pace_basis} over {round(metres)} m"
        distance_basis = "STORED_DISTANCE"
    else:
        duration_min = _UNMEASURED_TRIP_MINUTES[family]
        basis = f"{pace_basis} over an assumed {duration_min}-min intra-city trip"
        distance_basis = "NO_MEASURED_DISTANCE"
    return estimate(
        {
            "kind": "route_eta",
            "mode": token.upper(),
            "duration_min": duration_min,
            "distance_m": None if metres is None else round(metres),
            "distance_basis": distance_basis,
            "basis": basis,
        }
    )


def estimated_search_angles(*, region: str, topic: str) -> dict[str, Any]:
    """No web provider is configured: name the angles instead of inventing results.

    This is deliberately *not* a list of URLs.  A fabricated link is worse than none,
    because the next step cannot tell it apart from a captured page.
    """

    return estimate(
        {
            "kind": "source_angles",
            "region": region,
            "topic": topic,
            "angles": [
                f"{topic} {region} official site",
                f"{topic} {region} opening hours",
                f"{topic} {region} ticket price",
                f"{topic} {region} how to get there",
            ],
            "leads_captured": 0,
            "basis": "no web provider configured; query shapes derived from the public region and topic",
        }
    )


def classroom_note(result: dict[str, Any], *, estimate_key: str = "estimate") -> dict[str, Any]:
    """Attach the standing caveat so a consumer cannot read the block as a fact."""

    if estimate_key in result:
        result["estimate_note"] = (
            "MODEL_ESTIMATE: a classroom heuristic, not a provider measurement. "
            "It is refused by the hard feasibility gate and must not be shown as verified."
        )
    return result
