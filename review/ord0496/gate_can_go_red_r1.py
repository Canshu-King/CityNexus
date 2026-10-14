"""Blank controls for ORD-0496 slice 3: does this test file actually bite, or is it green by habit?

Seventeen arms went green on the first run after the auth retrofit, which is the kind of green that
has to be doubted.  Each control below takes one product guarantee away, runs the whole file, and
writes back the bytes it read first -- no `git checkout`, no reformatting, so the tree is
byte-identical afterwards whether a control bit or not.

THE TARGETING LESSON, KEPT IN THE FILE BECAUSE IT COST A WHOLE RUN: the first cut anchored a tamper
on `    if "traveler_id" in request.query_params:` and on
`    return resolve_traveler_principal(request, session)`.  Both strings occur THREE times in
`main.py` (the shelf, calendar and footprint doors each carry their own copy), so
`replace(old, new, 1)` edited somebody else's door, the calendar arms stayed green, and the honest
reading of that output was "the control is stale", not "the guarantee does not matter".  Every anchor
below is asserted unique before it is used, and the two body-level anchors carry the calendar
function's own name so a neighbour's identical line cannot be hit by accident.

Run from `backend/`:
    PYTHONIOENCODING=utf-8 ..\\/..\\/..\\/CityNexus/.venv/Scripts/python.exe \\
        ../review/ord0496/gate_can_go_red_r1.py
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
MAIN = BACKEND / "app" / "main.py"
EXPORTER = BACKEND / "app" / "calendar_export.py"
TEST = "tests/test_qoder_ord0496_calendar_export.py"

OWNERSHIP_OLD = (
    "    journey = session.get(Journey, str(journey_id))\n"
    "    if journey is None or journey.traveler_id != principal.traveler_id:\n"
    "        raise _calendar_journey_not_found(journey_id)"
)
OWNERSHIP_NEW = (
    "    journey = session.get(Journey, str(journey_id))\n"
    "    if journey is None:\n"
    "        raise _calendar_journey_not_found(journey_id)"
)

# name -> (file, old, new, arm that must turn red)
CONTROLS = {
    "ownership_check_removed": (
        MAIN,
        OWNERSHIP_OLD,
        OWNERSHIP_NEW,
        "test_a_valid_credential_for_another_traveller_is_answered_exactly_like_a_missing_trip",
    ),
    "scope_param_guard_disabled": (
        MAIN,
        "def _calendar_scope_param(request: Request) -> None:",
        "def _calendar_scope_param(request: Request) -> None:\n"
        "    return  # CONTROL: the guard that refuses a caller-named traveller id is switched off",
        "test_a_request_that_names_another_traveller_in_the_query_is_refused_by_name",
    ),
    "door_reopened_to_anonymous": (
        MAIN,
        "def _calendar_principal(request: Request, session: Session):",
        "def _calendar_principal(request: Request, session: Session):\n"
        "    import types  # CONTROL\n"
        "    return types.SimpleNamespace(traveler_id=None)  # CONTROL: no credential asked for",
        "test_an_anonymous_export_is_refused_and_hands_out_no_calendar_bytes",
    ),
    "backslash_escaped_last": (
        EXPORTER,
        '        value.replace("\\\\", "\\\\\\\\")\n',
        "        value\n",
        "test_comma_semicolon_backslash_and_newline_are_escaped_and_survive_the_round_trip",
    ),
}

# The anonymous door only actually leaks if the ownership comparison is gone too.
PAIR_WITH = {"door_reopened_to_anonymous": "ownership_check_removed"}


def run_pytest() -> tuple[int, str]:
    process = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", TEST],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        # A curated env is not an option on Windows: without SYSTEMROOT et al the interpreter dies
        # inside pytest startup with WinError 10106, and `rc=1 failed=0` looks like a silent green.
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return process.returncode, process.stdout + process.stderr


def tally(out: str) -> tuple[list[str], str]:
    """The FAILED ids and the last summary line, or a shout when pytest never got that far."""

    reds = [l.split("::")[-1].strip() for l in out.splitlines() if l.startswith("FAILED")]
    summary = next((l for l in reversed(out.splitlines()) if (" passed" in l or " failed" in l)), "")
    return reds, summary or f"NO_SUMMARY tail={out.splitlines()[-3:]}"


def main() -> int:
    originals = {path: path.read_bytes() for path in {MAIN, EXPORTER}}
    baseline_code, baseline_out = run_pytest()
    _, baseline_summary = tally(baseline_out)
    print(f"BASELINE rc={baseline_code} {baseline_summary}")

    bites = 0
    ran = 0
    for name, (path, old, new, expected_arm) in CONTROLS.items():
        text = originals[path].decode("utf-8")
        hits = text.count(old)
        if hits != 1:
            print(f"CONTROL {name}: TARGET_NOT_UNIQUE hits={hits} -- control is stale, not passed")
            continue
        ran += 1
        tampered = text.replace(old, new, 1)
        mate = CONTROLS[PAIR_WITH[name]] if name in PAIR_WITH else None
        if mate is not None:
            tampered = tampered.replace(mate[1], mate[2], 1)
        path.write_text(tampered, encoding="utf-8", newline="")
        code, out = run_pytest()
        reds, summary = tally(out)
        bites_it = expected_arm in reds
        bites += bites_it
        print(
            f"CONTROL {name}: rc={code} {summary} "
            f"expected_red_arm_bit={'YES' if bites_it else 'NO'} names={reds}"
        )
        path.write_bytes(originals[path])

    for path, blob in originals.items():
        restored = hashlib.sha1(path.read_bytes()).hexdigest() == hashlib.sha1(blob).hexdigest()
        print(f"RESTORED {path.name} byte_identical={'YES' if restored else 'NO'}")
    code, out = run_pytest()
    _, summary = tally(out)
    print(f"AFTER_CONTROLS rc={code} {summary}")
    print(f"CONTROLS_RAN={ran} CONTROLS_THAT_BIT={bites}")
    return 0 if bites == ran == len(CONTROLS) else 1


if __name__ == "__main__":
    sys.exit(main())
