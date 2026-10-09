"""Counter-arm for the two model-facing contexts that name a zone.

The gap this pins: the same shape the copilot context was fixed for, one layer out.  Two dicts that
go to a model name a zone -- `"timezone": journey.timezone` -- and say nothing about whether that
zone can be used:

  * `build_discovery_context` hands the model the journey window beside the zone that is supposed to
    place it, and reasons about "before arrival" in words;
  * `build_impact_context` hands the model the event that happened and the zone the journey is in,
    and reasons about which activities it touches.

Neither reader can tell an unusable zone from a usable one, and an unusable zone is silently
presented as if honoured -- the shape `execution_clock.now_honest` answers for the clock,
`journey_schema` for the trip payload and `_copilot_context` for the copilot.

This arm reads both real functions (stand-in trip and event, session with no rows, only the data
helpers stubbed) and asserts each context says which zone it used and whether the named one was
honoured.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "backend"))

import app.integrations.discovery.orchestration as orch  # noqa: E402
import app.intelligence.impact_resolver as resolver  # noqa: E402

# The data helpers both functions call would need a database; they are not what is under test.
orch.refresh_snapshot = lambda session, traveler_id: None
orch.snapshot_payload = lambda snapshot: {}
orch.journey_memory_payload = lambda session, journey: {}
orch._preference_payload = lambda session, journey: []


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _Session:
    def scalars(self, *args, **kwargs):
        return _Rows([])


class _Journey:
    id = "00000000-0000-4000-8000-000000000001"
    traveler_id = "00000000-0000-4000-8000-000000000002"
    city_code = "CN-TIANJIN"
    budget_amount_minor = 1
    budget_currency = "CNY"
    status = "PLANNED"
    current_activity_id = None
    timezone = "Asia/Shanghai"
    # The columns in question: bare local wall-clock, no offset.
    start_at = "2026-10-09T18:00:00"
    end_at = "2026-10-11T15:00:00"


class _Event:
    id = "00000000-0000-4000-8000-000000000003"
    event_type = "CLOSURE"
    severity = "MAJOR"
    occurred_at = "2026-10-09T20:00:00"
    provider_key = "user-command"
    provenance = "USER_REPORT"
    payload_json = "{}"


def journey(zone: str):
    return type("Journey", (_Journey,), {"timezone": zone})()


def discovery_block(zone: str) -> dict:
    payload = orch.build_discovery_context(
        _Session(), journey(zone), goal="find dinner", anchors=[], weather={}
    )
    return payload["journey"]


def impact_block(zone: str) -> dict:
    context, _ = resolver.build_impact_context(
        event=_Event(),
        journey=journey(zone),
        activities=[],
        places_by_id={},
    )
    return context["journey"]


SITES = (
    ("build_discovery_context", discovery_block),
    ("build_impact_context", impact_block),
)

CASES = (
    ("Asia/Shanghai", True, "Asia/Shanghai"),
    ("Mars/Phobos", False, "UTC"),
)


def main() -> int:
    bad: list[str] = []
    checks = 0
    rows = []

    for site, build in SITES:
        for zone, want_honoured, want_used in CASES:
            block = build(zone)
            rows.append((site, zone, block))
            checks += 1
            if "timezone_honoured" not in block or "used_timezone" not in block:
                bad.append(
                    "%s names zone %r and does not say which zone it used or whether the named "
                    "one was honoured -- a usable zone and an unusable one are the same bytes to "
                    "the model" % (site, zone)
                )
                continue
            if block["timezone_honoured"] is not want_honoured:
                bad.append(
                    "%s reported timezone_honoured=%r for zone %r, expected %r"
                    % (site, block["timezone_honoured"], zone, want_honoured)
                )
            if block["used_timezone"] != want_used:
                bad.append(
                    "%s reported used_timezone=%r for zone %r, expected %r"
                    % (site, block["used_timezone"], zone, want_used)
                )

    print("model context zone honesty: %d checks, %d bad" % (checks, len(bad)))
    for site, zone, block in rows:
        print(
            "   %-24s zone=%-14r honoured=%-5s used=%r"
            % (
                site,
                zone,
                block.get("timezone_honoured", "<absent>"),
                block.get("used_timezone", "<absent>"),
            )
        )
    if bad:
        print("\nARM BITES -- a model-facing context names a zone and does not say if it can be used:")
        for b in bad:
            print("   " + b)
        return 1
    print("\nARM_QUIET: both model-facing contexts say which zone was used, or that it could not be.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
