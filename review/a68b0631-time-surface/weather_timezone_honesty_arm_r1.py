"""Counter-arm: an unusable journey zone must not kill weather attribution.

The weather runtime used to turn a stored zone name it could not resolve into a
ValueError.  The caller (autorun) keeps only ``type(exc).__name__``, so the whole
capture degrades to the word "ValueError" and the reason is lost.  The clock
layer and the journey payload already answer this shape the other way: they
carry on and say the zone was not honoured.

This arm reads the real module from a tree root and exercises the two pure
functions that decide the outcome:

  1. ``_journey_timezone`` on an unusable name must return None, not raise.
  2. ``attribute_weather_fact_to_activity`` on that journey must return None,
     not raise -- the activity window is a wall clock that cannot be placed.
  3. Control: with a usable zone the same fact still attributes, so the arm is
     not just asserting "everything returns None".

Usage:
    python weather_timezone_honesty_arm_r1.py [tree-root]

The tree root defaults to the checkout this file lives in.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

FINDINGS: list[str] = []


def _import_runtime(root: Path):
    backend = root / "backend"
    if not (backend / "app" / "integrations" / "context" / "weather_runtime.py").is_file():
        raise SystemExit(f"no weather_runtime.py under {backend}")
    sys.path.insert(0, str(backend))
    os.chdir(backend)
    return importlib.import_module("app.integrations.context.weather_runtime")


def _entities(runtime, zone: str):
    journey = SimpleNamespace(timezone=zone)
    activity = SimpleNamespace(
        id="act-1",
        status="PLANNED",
        place_id="place-1",
        start_at="2026-10-10T15:00:00",
        end_at="2026-10-10T16:00:00",
    )
    place = SimpleNamespace(
        id="place-1",
        latitude=39.12,
        longitude=117.21,
        tags_json='["weather_sensitive"]',
    )
    fact = runtime.WeatherRiskFact(
        code="HEAVY_RAIN_RISK",
        severity="HIGH",
        at="2026-10-10T07:00:00+00:00",
        valid_until="2026-10-10T08:00:00+00:00",
        provider_key="open-meteo",
        evidence={"precipitation_probability": 90},
        scope=runtime.WeatherQueryScope("place-1", 39.12, 117.21),
    )
    return journey, activity, place, fact


def _call(label: str, fn):
    try:
        return fn(), None
    except Exception as exc:  # noqa: BLE001 - the arm judges the failure itself
        FINDINGS.append(f"{label}: raised {type(exc).__name__}: {exc}")
        return None, exc


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    runtime = _import_runtime(root)

    bad_journey, activity, place, fact = _entities(runtime, "Mars/Phobos")
    zone, _ = _call("unusable zone lookup", lambda: runtime._journey_timezone(bad_journey))
    if zone is not None:
        FINDINGS.append(f"unusable zone lookup returned {zone!r} instead of None")
    attribution, _ = _call(
        "attribution with an unusable zone",
        lambda: runtime.attribute_weather_fact_to_activity(
            journey=bad_journey, activity=activity, place=place, fact=fact
        ),
    )
    if attribution is not None:
        FINDINGS.append("attribution with an unusable zone returned a match instead of None")

    good_journey, activity, place, fact = _entities(runtime, "Asia/Shanghai")
    control, _ = _call(
        "attribution with a usable zone",
        lambda: runtime.attribute_weather_fact_to_activity(
            journey=good_journey, activity=activity, place=place, fact=fact
        ),
    )
    if control is None:
        FINDINGS.append("control: a usable zone no longer attributes the same fact")

    print(f"tree root        : {root}")
    print(f"unusable zone    : {zone!r}")
    print(f"bad-zone match   : {attribution!r}")
    print(f"control match    : {None if control is None else control.local_risk_start_at}")
    if FINDINGS:
        for finding in FINDINGS:
            print(f"FAILED {finding}")
        return 1
    print("PASS the unusable zone is named by the caller, not thrown as a generic error")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
