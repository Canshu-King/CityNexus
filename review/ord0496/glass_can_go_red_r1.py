"""Blank controls for the ORD-0496 glass gate: does the 390x844 export test bite, or is it green because nothing ever fails?

The first run of `qoder-ord0496-calendar-export-390x844.spec.ts` passed immediately
(`events=9 bytes=2879 door_events=9 anon_downloads=0`), and an immediately-green browser gate is the
weakest kind of evidence I have: it can be green because the download event fires for a file nobody
asked for, or because the assertion never reached the element it names.

Each control removes one load-bearing thing and re-runs the SAME spec against a fresh authoritative
stack (own run id, own `_*.db`, ports this run owns).  A control that does not turn the spec red is
reported as stale, never as passed.  Every file is restored to the bytes read at the start, whatever
happens in between -- these are edits to a tree that also holds committed work, so nothing here
touches git at all.

Run from anywhere:
    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0496/glass_can_go_red_r1.py
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
EXPORTER_TS = FRONTEND / "src/features/trip/calendarExport.ts"
SCREEN_TSX = FRONTEND / "src/features/trip/TripItinerary.tsx"
SPEC = "qoder-ord0496-calendar"
PORT_BASE = 4430

# name -> (file, old, new, one-line reason the spec must now fail)
CONTROLS = {
    "screen_stops_sending_the_credential": (
        EXPORTER_TS,
        "    response = await fetch(CALENDAR_PATH(journeyId), { headers: travelerAuthHeaders() });",
        "    response = await fetch(CALENDAR_PATH(journeyId), { headers: {} });",
        "the traveller's tap would then be an anonymous request, so the download the test waits for "
        "should never arrive",
    ),
    "notice_prints_a_raw_key": (
        SCREEN_TSX,
        '      setCalendarNotice(t("calendar.done", { events: answer.events }));',
        '      setCalendarNotice(t("calendar.deliberately_absent"));',
        "the test asserts the sentence is not a key name, so this must fail on that assertion",
    ),
    "button_loses_its_testid": (
        SCREEN_TSX,
        '            data-testid="calendar-export"\n',
        "",
        "the test presses that element by that name; a silent drop must not read as a pass",
    ),
}


def run_spec(run_id: str, port_offset: int) -> tuple[int, str]:
    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "CITYNEXUS_E2E_AUTHORITATIVE": "1",
        "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_E2E_PORT": str(PORT_BASE + port_offset),
        "CITYNEXUS_BACKEND_PORT": str(PORT_BASE + 600 + port_offset),
        "CITYNEXUS_PYTHON": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
        "CITYNEXUS_DATABASE_URL": f"sqlite:///D:/moodle/_qoder_fusion_import/_e2e_{run_id}.db",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_TRAVELER_AUTH_SECRET": "ord0496-glass-control-secret-0123456789abcdef",
    }
    env.pop("DEEPSEEK_API_KEY", None)  # authoritative mode refuses a live AI key in the environment
    process = subprocess.run(
        ["npx", "playwright", "test", "-g", SPEC, "--reporter=line"],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        shell=True,
        timeout=900,
    )
    # The raw output is kept, not just my reading of it: the first cut of this script called all three
    # controls GREEN while every one of them exited 1, and a reader bug is only auditable afterwards if
    # the bytes it mis-read are still around.
    log = ROOT.parent / f"_glass_ctl_{run_id}.log"
    log.write_text(process.stdout + process.stderr, encoding="utf-8", newline="\n")
    return process.returncode, process.stdout + process.stderr


TALLY = re.compile(r"^\s*(\d+) (passed|failed|flaky|skipped|did not run)", re.M)
KINDS = ("passed", "failed", "flaky", "skipped", "did not run")


def verdict(code: int, out: str) -> tuple[str, str]:
    """RED / GREEN / DID_NOT_RUN / READER_BROKEN, from EVERY count line plus the exit code.

    THE BUG THIS FUNCTION WAS WRITTEN TWICE FOR: Playwright's line reporter prints the setup project's
    `1 passed` and the chromium project's `1 failed` on SEPARATE lines, so "the last line that looks
    like a summary" names whichever project finished last -- which is how three genuinely red controls
    were first reported as green.  Same shape as the slice-2 reader fix in `QODER_RESULT.md` §7.1.
    An exit code that disagrees with the tallies is called out as READER_BROKEN rather than smoothed
    into either answer.
    """

    counts = dict.fromkeys(KINDS, 0)
    for number, kind in TALLY.findall(out):
        counts[kind] += int(number)
    tally_line = " ".join(f"{kind}={value}" for kind, value in sorted(counts.items()) if value)
    if not tally_line:
        return "DID_NOT_RUN", "no count line at all"
    red = counts["failed"] > 0 or counts["did not run"] > 0
    if red and code != 0:
        return "RED", tally_line
    if not red and code == 0:
        return "GREEN", tally_line
    return "READER_BROKEN", f"{tally_line} but rc={code}"


def main() -> int:
    originals = {path: path.read_bytes() for path in {EXPORTER_TS, SCREEN_TSX}}
    # A fresh run id per invocation: the run-stamped backend refuses to reopen a database that
    # already exists, so a fixed id would make the second run of this script refuse rather than fail.
    stamp = datetime.now().strftime("%H%M%S")
    bites = ran = 0
    try:
        # The reader's own blank control: nothing tampered, so the only honest answer is GREEN with the
        # setup project and the spec both counted.  Without this leg a reader that always said RED would
        # score 3/3 controls and look like the strongest evidence in the file.
        code, out = run_spec(f"slice3base{stamp}", 0)
        state, tally = verdict(code, out)
        print(f"BASELINE untampered: rc={code} {state} {tally}")
        if state != "GREEN":
            print("BASELINE_NOT_GREEN -- the reader or the stack is the problem, not the product; stopping")
            return 1
        for index, (name, (path, old, new, why)) in enumerate(CONTROLS.items()):
            text = originals[path].decode("utf-8")
            hits = text.count(old)
            if hits != 1:
                print(f"CONTROL {name}: TARGET_NOT_UNIQUE hits={hits} -- stale control, not a pass")
                continue
            ran += 1
            path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")
            code, out = run_spec(f"slice3ctl{stamp}{index}", index + 1)
            state, summary = verdict(code, out)
            bites += state == "RED"
            print(f"CONTROL {name}: rc={code} {state} summary={summary}")
            print(f"   expected because: {why}")
            if state == "DID_NOT_RUN":
                print("   tail: " + " | ".join(out.splitlines()[-6:]))
            path.write_bytes(originals[path])
            same = hashlib.sha1(path.read_bytes()).hexdigest() == hashlib.sha1(originals[path]).hexdigest()
            print(f"   restored={same}")
    finally:
        for path, blob in originals.items():
            if path.read_bytes() != blob:
                path.write_bytes(blob)
                print(f"FORCED_RESTORE {path.name}")
    print(f"CONTROLS_RAN={ran} CONTROLS_THAT_BIT={bites}")
    return 0 if bites == ran == len(CONTROLS) else 1


if __name__ == "__main__":
    sys.exit(main())
