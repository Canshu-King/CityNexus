"""ORD-0500 r3 -- the call site Q64's ruler is actually complaining about.

Measured on this generation, tip first: `ui_exposure_taint_ast_r7b.cjs --tree` answers 6 cells over
307 modules on the tip and 10 over 308 on my r2 tree, with the extra four landing on
`src/features/access/AccessPanel.tsx` and `src/features/studio/PlanVersionHistoryPanel.tsx` -- two
files this order never opens.  The path it followed was mine: `facts.existingStampedAt` comes out of
the server's response body, and I handed it to `formatV8Date`, a helper exported from
`frontend/src/lib/v8Formatting` that those two panels also call.  The ruler weighs paths, not file
ownership, so once a shared helper carries upstream text every other caller of it loses its claim of
"this one only ever renders device-side words".

The order offers two shapes and this is the second one: the screen renders the instant itself, in the
module that only this screen imports, so a body value never enters a helper another surface depends
on.  The output shape is the one travellers already read on these surfaces (month/day, 24-hour,
locale-specific), which is what the shared helper does.
"""
import hashlib

COPY = "wt16/frontend/src/features/checkin/checkinCopy.ts"
ITIN = "wt16/frontend/src/features/trip/TripItinerary.tsx"
NL = chr(10)

LOCAL_RENDERER = NL.join([
    "",
    "/**",
    " * The instant of the stamp that won, as this screen's own words render it.",
    " *",
    " * Deliberately not the shared date helper (`frontend/src/lib/v8Formatting`), which the access",
    " * panel and the plan-version history panel also call: the value coming in here was read out of",
    " * the server's response body, and ORD-0500 measured that routing a body value through that one",
    " * helper costs those two surfaces their exemption -- the exposure ruler follows the path, so it",
    " * then claims a cell at every other caller of the helper.  This module is imported by the",
    " * itinerary screen and by nothing else, so the path ends here.",
    " *",
    " * An instant the door did not send renders as an empty string, and the caller falls back to the",
    " * sentence that says so without a moment; nothing here invents a time.",
    " */",
    "export function formatStampedMoment(value?: string | null, zh = false): string {",
    "  if (!value) return \"\";",
    "  const stamp = new Date(value);",
    "  if (Number.isNaN(stamp.getTime())) return \"\";",
    "  return new Intl.DateTimeFormat(zh ? \"zh-CN\" : \"en-GB\", {",
    "    month: \"numeric\",",
    "    day: \"numeric\",",
    "    hour: \"2-digit\",",
    "    minute: \"2-digit\",",
    "    hour12: false,",
    "  }).format(stamp);",
    "}",
    "",
])

copy = open(COPY, encoding="utf-8", newline="").read()
if "formatStampedMoment" in copy:
    raise SystemExit("ABORT_RENDERER_ALREADY_LANDED")
open(COPY, "w", encoding="utf-8", newline="").write(copy.rstrip(chr(10)) + LOCAL_RENDERER)

itin = open(ITIN, encoding="utf-8", newline="").read()
OLD_CALL = "wordsFor(CHECKIN_COPY.duplicateAt, zh, { moment: formatV8Date(facts.existingStampedAt, locale) })"
NEW_CALL = "wordsFor(CHECKIN_COPY.duplicateAt, zh, { moment: formatStampedMoment(facts.existingStampedAt, zh) })"
OLD_IMPORT_LINE = 'import { formatV8Date } from "../../lib/v8Formatting";' + NL
if itin.count(OLD_CALL) != 1:
    raise SystemExit("ABORT_CALL_SITE %d" % itin.count(OLD_CALL))
itin = itin.replace(OLD_CALL, NEW_CALL)
if itin.count(OLD_IMPORT_LINE) != 1:
    raise SystemExit("ABORT_IMPORT_LINE %d" % itin.count(OLD_IMPORT_LINE))
itin = itin.replace(OLD_IMPORT_LINE, "")
# my own module already carries wordsFor/CHECKIN_COPY; extend that import with the new name
old_from = 'CHECKIN_REFUSAL_COPY,' + NL
if itin.count(old_from) != 1:
    raise SystemExit("ABORT_MY_IMPORT_BLOCK %d" % itin.count(old_from))
itin = itin.replace(old_from, old_from + "  formatStampedMoment," + NL)
open(ITIN, "w", encoding="utf-8", newline="").write(itin)

for path in (COPY, ITIN):
    raw = open(path, "rb").read()
    print("%s bytes=%d CR=%d sha256=%s" % (path.split("/")[-1], len(raw), raw.count(b"\r"),
                                           hashlib.sha256(raw).hexdigest()[:16]))
print("formatV8Date left in the screen:", open(ITIN, encoding="utf-8").read().count("formatV8Date"))
