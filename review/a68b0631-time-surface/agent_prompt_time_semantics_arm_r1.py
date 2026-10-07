"""Counter-arm for the agent prompt's time semantics.

The gap this pins: the system prompt told the model the Journey ID, the Mission and the TravelerTwin,
and nothing about *what time it is* or *which zone the journey is in* -- while the agent reasons in
words like "now", "tonight" and "before arrival".  Every one of those was ambiguous, for the one
reader that acts on the answer.

This arm builds the real `_system_prompt` (only the three data helpers are stubbed; the string
building under test is the product's own) and asserts:
  * the prompt names the journey's time zone, and the moment it is acting in;
  * the moment's own offset agrees with the zone the prompt claims;
  * an unusable zone is SAID to be unusable, not quietly rendered as if it were honoured;
  * the journey window is present, so "before arrival" has something to be before.
"""
import sys
import types

sys.path.insert(0, "D:/moodle/_qoder_rel_ord0447_wt/backend")

import app.agent.runtime as runtime  # noqa: E402

runtime.refresh_snapshot = lambda *a, **k: {}
runtime.snapshot_payload = lambda *a, **k: {}
runtime.mission_payload = lambda m: {}

J = type("J", (), {})()
J.id = "J-1"
J.timezone = "Asia/Shanghai"
J.start_at = "2026-10-09T18:00:00+08:00"
J.end_at = "2026-10-11T15:00:00+08:00"
J.traveler_id = "T-1"
M = types.SimpleNamespace(trigger_event_id="E-1", requested_autonomy="PLAN_ONLY")


def prompt_for(zone: str) -> str:
    J.timezone = zone
    return runtime._system_prompt(None, M, J)


def main() -> int:
    bad = []
    checks = 0

    good = prompt_for("Asia/Shanghai")
    checks += 1
    if "Asia/Shanghai" not in good:
        bad.append("the prompt does not name the journey's time zone")
    if "Now (the moment you are acting in)" not in good:
        bad.append("the prompt does not say what moment the agent is acting in")
    if J.start_at not in good or J.end_at not in good:
        bad.append("the prompt does not carry the journey window, so 'before arrival' has no anchor")
    # the moment the prompt states must be in the zone it claims
    line = [l for l in good.split("\n") if l.startswith("Now (the moment")]
    if line and "+08:00" not in line[0]:
        bad.append("the prompt states a moment that is not in the zone it names: %s" % line[0][:120])

    bad_zone = prompt_for("Mars/Phobos")
    checks += 1
    if "could not be used" not in bad_zone and "unusable" not in bad_zone:
        bad.append("an unusable journey timezone is rendered without saying so")
    # and it must not imply the zone was honoured
    if "unusable" not in bad_zone:
        bad.append("the zone line does not mark the journey timezone unusable")
    # a moment in UTC must not be presented as +08:00
    moment_line = [l for l in bad_zone.split("\n") if l.startswith("Now (the moment")]
    if moment_line and "+08:00" in moment_line[0]:
        bad.append("an unusable zone still rendered a +08:00 moment: %s" % moment_line[0][:120])

    print("agent prompt time semantics: %d checks, %d bad" % (checks, len(bad)))
    for zone in ("Asia/Shanghai", "Mars/Phobos"):
        p = prompt_for(zone)
        for l in p.split("\n"):
            if any(k in l for k in ("Now (the moment", "Journey time zone", "Journey window")):
                print("   [%s] %s" % (zone, l.strip()[:120]))
    if bad:
        print("\nARM BITES -- the prompt does not place the agent in a moment:")
        for b in bad:
            print("   " + b)
        return 1
    print("\nARM_QUIET: the prompt says which moment it is, in which zone, and says so when the zone "
          "cannot be used.")
    return 0


if __name__ == "__main__":
    sys.exit(main())