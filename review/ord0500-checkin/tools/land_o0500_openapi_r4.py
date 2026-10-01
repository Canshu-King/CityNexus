"""ORD-0500 r4 -- land the contract line the rebase dropped, and say what caught it.

My r4 landing carried `backend/app/main.py`, the CSS merge and the carriers; the frontend patch carried
`checkins.ts` + `TripItinerary.tsx`; neither brought `contracts/openapi.yaml`.  Nothing complained
until my own arm ran: `test_the_name_is_written_into_the_hand_contract_too` reads the hand contract for
the name the door answers with and reported FAILED (15 passed / 1 failed) on the candidate.  A name
the app says and the contract does not is exactly the drift that arm exists to catch -- the arm was
right and my landing was wrong.

The description here is a folded YAML scalar, so the edit is the scalar's first two lines, anchored
inside the check-in path item (this batch added 95 lines to the file elsewhere) and asserted to match
exactly once.  It aborts if the name is already present, so re-running cannot double it.
"""
import hashlib
import os

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(LANE, "wt19", "contracts", "openapi.yaml")
NL = chr(10)
OLD = NL.join([
    "          description: >-",
    "            error.reason_code = CHECKIN_ACTIVITY_UNKNOWN / CHECKIN_PLACE_UNKNOWN -- no row of that",
])
NEW = NL.join([
    "          description: >-",
    "            error.reason_code = CHECKIN_JOURNEY_UNKNOWN / CHECKIN_ACTIVITY_UNKNOWN /",
    "            CHECKIN_PLACE_UNKNOWN -- no row of that",
])

text = open(PATH, encoding="utf-8").read()
if "CHECKIN_JOURNEY_UNKNOWN" in text:
    print("already landed")
    raise SystemExit(0)
start = text.index("  /journeys/{journey_id}/checkins:")
stop = text.index(NL + "  /", start + 10)
section = text[start:stop]
if section.count(OLD) != 1:
    raise SystemExit("ABORT_SECTION_ANCHOR %d" % section.count(OLD))
text = text[:start] + section.replace(OLD, NEW) + text[stop:]
open(PATH, "w", encoding="utf-8", newline="\n").write(text)
raw = open(PATH, "rb").read()
print("openapi.yaml bytes=%d CR=%d sha256=%s name_hits=%d" % (
    len(raw), raw.count(b"\r"), hashlib.sha256(raw).hexdigest()[:16],
    raw.decode("utf-8").count("CHECKIN_JOURNEY_UNKNOWN")))
