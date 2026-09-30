"""ORD-0500 r3 -- re-land the footprint door's journey refusal on the LF generation.

ORD-0532 converted `backend/app/main.py` to LF and pinned it with `.gitattributes`, which is why this
is two small text edits instead of the whole-file reconciliation that bounced two rebases.

Edit one: `_checkin_journey_read` fell through the shared `require()`, which answers
`Journey <uuid> was not found` with `details: null` and no reason_code at both footprint doors.  The
anchor is searched inside that function, because `require(session, Journey, ...)` is a pattern this
file uses at several doors, so a whole-file count of one would be an accident rather than a check.
Edit two: the POST door's 404 description names the new code, because a refusal a consumer cannot
look up in the contract is a refusal it cannot code against.
"""
import hashlib

PATH = "wt16/backend/app/main.py"
NL = chr(10)
text = open(PATH, encoding="utf-8", newline="").read()

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

lines = text.split(NL)
starts = [i for i, line in enumerate(lines) if line.startswith("def _checkin_journey_read")]
if len(starts) != 1:
    raise SystemExit("ABORT_FUNCTION_NOT_UNIQUE %r" % starts)
start = starts[0]
hits = [i for i in range(start, start + 60) if lines[i].strip() == OLD_CALL]
if len(hits) != 1:
    raise SystemExit("ABORT_CALL_ANCHOR %r" % hits)
lines[hits[0]:hits[0] + 1] = NEW_CALL.split(NL)
text = NL.join(lines)
if text.count(OLD_DOC) != 1:
    raise SystemExit("ABORT_DOC_ANCHOR %d" % text.count(OLD_DOC))
text = text.replace(OLD_DOC, NEW_DOC)

open(PATH, "w", encoding="utf-8", newline="").write(text)
raw = open(PATH, "rb").read()
print("LANDED bytes=%d CR=%d LF=%d sha256=%s" % (
    len(raw), raw.count(b"\r"), raw.count(b"\n"), hashlib.sha256(raw).hexdigest()[:16]))
print("CHECKIN_JOURNEY_UNKNOWN x%d" % raw.decode("utf-8").count("CHECKIN_JOURNEY_UNKNOWN"))
