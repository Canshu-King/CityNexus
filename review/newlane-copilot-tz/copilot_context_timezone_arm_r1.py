"""Counter-arm for the copilot context's zone honesty.

The gap this pins: the dict `_copilot_context` builds for the copilot names a zone --
`"timezone": journey.timezone` -- and says nothing about whether that zone can be used.  The reader
of that dict is the model's prompt, which reasons in words like "now" and "tonight"; handed a zone
nothing can be placed in, it has no way to know the name is unusable, which is the shape
`execution_clock.now_honest` answers for the execution clock and `journey_schema` now answers for
the trip payload.

This arm reads the real `_copilot_context` (a stand-in trip and a session with no rows -- only the
one data helper that would need a database is stubbed) and then reads the real prompt context
`_copilot_fallback_or_ai` hands the model, and asserts:
  * the context says which zone it used and whether the named one was honoured, and
  * that pair survives into the prompt -- the one reader that acts on it.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "backend"))

import app.main as m  # noqa: E402


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _Session:
    """Enough of a Session for `_copilot_context` when the trip has no selected plan."""

    def get(self, *args, **kwargs):
        return None

    def scalars(self, *args, **kwargs):
        return _Rows([])


class _Journey:
    id = "00000000-0000-4000-8000-000000000001"
    traveler_id = "00000000-0000-4000-8000-000000000002"
    city_code = "CN-TIANJIN"
    budget_currency = "CNY"
    status = "PLANNED"
    current_activity_id = None
    active_plan_version_id = None
    timezone = "Asia/Shanghai"


def context_for(zone: str) -> dict:
    journey = type("Journey", (_Journey,), {"timezone": zone})()
    real = m.capability_payload
    m.capability_payload = lambda *a, **k: []
    try:
        return m._copilot_context(_Session(), journey)
    finally:
        m.capability_payload = real


def prompt_journey_block(payload: dict) -> dict:
    """The `journey` block of the prompt context the model is actually handed."""
    seen: dict = {}
    real_client, real_compile = m._deepseek_client, m.compile_semantic_envelope

    def capture(client, message, prompt_context):
        seen.update(prompt_context)
        return None

    m._deepseek_client = lambda *a, **k: object()
    m.compile_semantic_envelope = capture
    try:
        m._copilot_fallback_or_ai("what time is it now?", payload)
    finally:
        m._deepseek_client, m.compile_semantic_envelope = real_client, real_compile
    return seen.get("journey", {})


CASES = (
    ("Asia/Shanghai", True, "Asia/Shanghai"),
    ("Mars/Phobos", False, "UTC"),
)


def main() -> int:
    bad: list[str] = []
    checks = 0
    rows = []

    for zone, want_honoured, want_used in CASES:
        payload = context_for(zone)
        block = prompt_journey_block(payload)
        rows.append((zone, payload, block))

        checks += 1
        if "timezone_honoured" not in payload or "used_timezone" not in payload:
            bad.append(
                "the copilot context names zone %r and does not say which zone it used or whether "
                "the named one was honoured -- a usable zone and an unusable one are the same bytes "
                "to the reader" % zone
            )
        else:
            if payload["timezone_honoured"] is not want_honoured:
                bad.append(
                    "zone %r reported timezone_honoured=%r, expected %r"
                    % (zone, payload["timezone_honoured"], want_honoured)
                )
            if payload["used_timezone"] != want_used:
                bad.append(
                    "zone %r reported used_timezone=%r, expected %r"
                    % (zone, payload["used_timezone"], want_used)
                )

        checks += 1
        if (
            block.get("timezone_honoured") is not want_honoured
            or block.get("used_timezone") != want_used
        ):
            bad.append(
                "the prompt built from this context drops the honesty: its journey block says "
                "timezone_honoured=%r used_timezone=%r for zone %r"
                % (block.get("timezone_honoured"), block.get("used_timezone"), zone)
            )

    print("copilot context zone honesty: %d checks, %d bad" % (checks, len(bad)))
    for zone, payload, block in rows:
        print(
            "   zone=%-14r context(honoured=%-5s used=%-14r) prompt(honoured=%-5s used=%r)"
            % (
                zone,
                payload.get("timezone_honoured", "<absent>"),
                payload.get("used_timezone", "<absent>"),
                block.get("timezone_honoured", "<absent>"),
                block.get("used_timezone", "<absent>"),
            )
        )
    if bad:
        print("\nARM BITES -- the copilot context names a zone and does not say if it can be used:")
        for b in bad:
            print("   " + b)
        return 1
    print("\nARM_QUIET: the context and the prompt both say which zone was used, or that it could not be.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
