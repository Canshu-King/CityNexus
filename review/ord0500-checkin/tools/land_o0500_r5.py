"""ORD-0500 r4 -- re-land the whole write-set on tip 514b397f, where ORD-0530 also wrote.

The sequencer's conflict was real and it is in this family: ORD-0530 (footprints by day) appended 40
lines to `frontend/src/features/checkin/footprint.css`, the same tail my 31-line stop-row block sits
at, so the merge cannot decide an order for two additive blocks.  That is resolved here by hand: both
blocks are kept, theirs first (it was there first on this line), mine after it, and the tool aborts if
either block is already present so a re-run cannot double it.

The other three edits are anchored, each asserted to match exactly once:
  * `backend/app/main.py` -- the journey leg of both footprint doors names its refusal (2 edits),
    and this file is LF now, so the edit is 14 added / 2 deleted and not a whole-file collision.
  * `contracts/openapi.yaml` -- the POST door's 404 description says the name it answers with.
Frontend logic (`checkins.ts`, `TripItinerary.tsx`) and the carriers land by patch, which was checked
against this tip before running.
"""
import hashlib
import os
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
TREE = sys.argv[1] if len(sys.argv) > 1 else "wt22"
NL = chr(10)
ROOT = os.path.join(LANE, TREE)
MAIN = os.path.join(ROOT, "backend", "app", "main.py")
CSS = os.path.join(ROOT, "frontend", "src", "features", "checkin", "footprint.css")
SPEC = os.path.join(ROOT, "contracts", "openapi.yaml")
SRC_MAIN = os.path.join(LANE, "wt19", "backend", "app", "main.py")
SRC_CSS = os.path.join(LANE, "wt19", "frontend", "src", "features", "checkin", "footprint.css")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def tail_block(path, marker):
    text = open(path, encoding="utf-8", newline="").read()
    i = text.index(marker)
    return text[i:]


# --- footprint.css: keep both blocks, theirs then mine -----------------------------------------
tip_css = open(CSS, encoding="utf-8", newline="").read()
marker = "/* ORD-0500"
if marker in tip_css:
    raise SystemExit("ABORT_MY_CSS_BLOCK_ALREADY_PRESENT")
mine = tail_block(SRC_CSS, marker)
if "cn-footprints__day" not in tip_css:
    raise SystemExit("ABORT_ORD0530_CSS_NOT_ON_THIS_SIDE")
open(CSS, "w", encoding="utf-8", newline="").write(tip_css.rstrip(NL) + NL + NL + mine.rstrip(NL) + NL)

# --- backend/app/main.py: two anchored edits, LF preserved --------------------------------------
OLD_CALL = 'journey = require(session, Journey, str(journey_id), "Journey")'
NEW_CALL = NL.join([
    "    # ORD-0500: this leg used to fall through to `require()`, which answers",
    '    # "Journey <uuid> was not found" -- an id printed into a traveller\'s sentence, with',
    "    # `details: null` and no `reason_code`, at both footprint doors.  The door has a name for",
    "    # this case, so it says it, and the identity stays out of the prose.",
    "    journey = session.get(Journey, str(journey_id))",
    "    if journey is None:",
    "        raise _share_refusal(",
    "            404,",
    '            "This server has no such trip, so nothing was stamped or read.",',
    '            "CHECKIN_JOURNEY_UNKNOWN",',
    '            {"field": "journey_id"},',
    "        )",
])
OLD_DOC = '            "description": "error.reason_code = CHECKIN_ACTIVITY_UNKNOWN / CHECKIN_PLACE_UNKNOWN"'
NEW_DOC = NL.join([
    '            "description": "error.reason_code = CHECKIN_JOURNEY_UNKNOWN / "',
    '            "CHECKIN_ACTIVITY_UNKNOWN / CHECKIN_PLACE_UNKNOWN"',
])
text = open(MAIN, encoding="utf-8", newline="").read()
if "CHECKIN_JOURNEY_UNKNOWN" in text:
    raise SystemExit("ABORT_MAIN_ALREADY_LANDED")
lines = text.split(NL)
starts = [i for i, line in enumerate(lines) if line.startswith("def _checkin_journey_read")]
if len(starts) != 1:
    raise SystemExit("ABORT_FUNCTION_NOT_UNIQUE %r" % starts)
hits = [i for i in range(starts[0], starts[0] + 60) if lines[i].strip() == OLD_CALL]
if len(hits) != 1:
    raise SystemExit("ABORT_CALL_ANCHOR %r" % hits)
lines[hits[0]:hits[0] + 1] = NEW_CALL.split(NL)
text = NL.join(lines)
if text.count(OLD_DOC) != 1:
    raise SystemExit("ABORT_DOC_ANCHOR %d" % text.count(OLD_DOC))
open(MAIN, "w", encoding="utf-8", newline="").write(text.replace(OLD_DOC, NEW_DOC))

# --- carriers and new files: copied byte for byte from the r3 tree ------------------------------
for rel in ["backend/tests/test_qoder_ord0500_journey_refusal.py",
            "frontend/src/features/checkin/checkinCopy.ts",
            "frontend/e2e/qoder-ord0500-checkin-truth.spec.ts",
            "frontend/playwright.ord0500-checkin.config.ts"]:
    src = os.path.join(LANE, "wt19", rel)
    dst = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(open(src, "rb").read())

print("landed on", TREE)
for rel in ["backend/app/main.py", "frontend/src/features/checkin/footprint.css",
            "frontend/src/features/checkin/checkinCopy.ts"]:
    raw = open(os.path.join(ROOT, rel), "rb").read()
    print("  %-52s bytes=%7d CR=%5d sha256=%s" % (rel.split("/")[-1], len(raw), raw.count(b"\r"),
                                                  sha(os.path.join(ROOT, rel))[:16]))
print("  main.py vs the r3 tree identical bytes?",
      open(MAIN, "rb").read() == open(SRC_MAIN, "rb").read())
print("  CHECKIN_JOURNEY_UNKNOWN x%d, cn-footprints__day x%d, ORD-0500 css x%d" % (
    open(MAIN, encoding="utf-8").read().count("CHECKIN_JOURNEY_UNKNOWN"),
    open(CSS, encoding="utf-8").read().count("cn-footprints__day"),
    open(CSS, encoding="utf-8").read().count("/* ORD-0500")))
