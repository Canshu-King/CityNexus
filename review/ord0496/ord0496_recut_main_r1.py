"""ORD-0496 - re-cut the door's two additive blocks onto the CURRENT authoritative main.py.

Why this script exists rather than a hand merge: between my base `de341634d4dc30845d0c6ef98490bd33e41dd4b2`
and the tip I read (`c2bb95b8f4d78e6aacbb80773594020f1992f8a2`) someone converted
`backend/app/main.py` from LF to CRLF -- measured, not assumed: CR bytes go 0 -> 13,362 across those
22 commits, while `contracts/openapi.yaml` and `backend/tests/` stayed LF (CR=0 on both ends).  That
single-file flip is why `git merge-tree` reported the whole 26,581-line file as one conflict region:
every line differs, none of them semantically.

So the re-cut takes the TIP's bytes and re-inserts my two additive blocks with the tip's own line
ending, which keeps this lane's diff at +159/-0 instead of rewriting somebody else's 26k lines.  The
acceptance test is at the bottom: the rebuilt file must contain each of my markers exactly once, must
be uniformly CRLF, and the diff against the tip must add exactly the same number of lines the first
cut added.

Run from the worktree root with the project interpreter::

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0496/ord0496_recut_main_r1.py
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TARGET = ROOT / "backend/app/main.py"
BASE = "de341634d4dc30845d0c6ef98490bd33e41dd4b2"
CUT = "e5db371343accbb92539c81d442da81c6c47c155"
TIP = "c2bb95b8f4d78e6aacbb80773594020f1992f8a2"
REL = "backend/app/main.py"

IMPORT_HEAD = "from app.calendar_export import ("
ROUTE_HEAD = "# ORD-0496 slice 1: a trip's own schedule leaves this server as an RFC 5545 calendar."
ROUTE_TAIL = "# ORD-0476 slice 1: the trip footprint."
IMPORT_ANCHOR = "from app.concurrency_guards import journey_write_lock"
ROUTE_ANCHOR = (
    '@app.get("/api/v1/journeys/{journey_id}")\r\n'
    "def get_journey(journey_id: UUID, session: Session = Depends(get_session)):\r\n"
    '    return journey_schema(require(session, Journey, str(journey_id), "Journey"))\r\n'
)


def blob(rev: str) -> bytes:
    finished = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "blob", f"{rev}:{REL}"],
        capture_output=True,
    )
    assert finished.returncode == 0, finished.stderr.decode("utf-8", "replace")
    return finished.stdout


def main() -> int:
    cut = blob(CUT).decode("utf-8").replace("\r\n", "\n")
    tip_bytes = blob(TIP)
    tip = tip_bytes.decode("utf-8")

    # --- my two additive blocks, taken out of my own commit rather than retyped
    lines = cut.split("\n")
    start = lines.index(IMPORT_HEAD)
    end = next(i for i, line in enumerate(lines) if line == ")" and i > start)
    import_block = "\n".join(lines[start : end + 1]) + "\n"
    assert "ICS_MEDIA_TYPE" in import_block and "content_disposition" in import_block

    r_start = next(i for i, line in enumerate(lines) if line.startswith(ROUTE_HEAD))
    r_end = next(i for i, line in enumerate(lines) if line.startswith(ROUTE_TAIL) and i > r_start)
    route_block = "\n".join(lines[r_start:r_end]).rstrip("\n") + "\n\n\n"
    assert "def get_journey_calendar(" in route_block
    assert "_calendar_journey" in route_block and "CALENDAR_SOURCE_UNREADABLE" in route_block

    # --- the base file's own shape, so the re-cut is measured against what moved, not what I expect
    base = blob(BASE).decode("utf-8")
    assert base.count("\r") == 0, "the base was LF; if that stopped being true this script is wrong"
    assert tip.count("\r") > 10_000, "the tip no longer carries the CRLF flip this script is for"

    newline = "\r\n"
    assert tip.count("\n") == tip.count("\r\n"), "the tip file is mixed; report rather than splice"

    def to_crlf(text: str) -> str:
        return text.replace("\n", "\r\n")

    # --- splice at anchors that must be unique in the tip's file
    assert tip.count(IMPORT_ANCHOR) == 1, tip.count(IMPORT_ANCHOR)
    assert tip.count(ROUTE_ANCHOR) == 1, tip.count(ROUTE_ANCHOR)
    assert tip.count(ROUTE_TAIL) == 1, tip.count(ROUTE_TAIL)
    rebuilt = tip.replace(IMPORT_ANCHOR, to_crlf(import_block) + IMPORT_ANCHOR, 1)
    head, sep, tail = rebuilt.partition(ROUTE_TAIL)
    assert sep and rebuilt.index(ROUTE_ANCHOR) < rebuilt.index(ROUTE_TAIL), "the anchor pair moved"
    rebuilt = head.rstrip("\r\n") + "\r\n\r\n\r\n" + to_crlf(route_block) + sep + tail

    # --- the rebuilt file has to say the same things my first cut said, once each
    for marker in (IMPORT_HEAD, ROUTE_HEAD, "def get_journey_calendar(", "def _calendar_activities("):
        assert rebuilt.count(marker) == 1, (marker, rebuilt.count(marker))
    assert rebuilt.count("\r\n") == rebuilt.count("\n"), "splicing introduced a bare LF line"
    added = rebuilt.count("\n") - tip.count("\n")
    previous = cut.count("\n") - base.count("\n")
    assert added == previous, (added, previous)

    TARGET.write_bytes(rebuilt.encode("utf-8"))
    print(
        f"main.py rebuilt: tip_lines={tip.count(chr(10))} added={added} "
        f"same_as_first_cut={previous} cr_bytes={rebuilt.count(chr(13))}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
