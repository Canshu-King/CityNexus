"""Which of the eleven refusal words had a screen reading on the line before this hand -- a denominator,
measured by reading the specs that are actually on the tip, not by remembering what lanes said.

For each copy key in `checkinCopy.ts` this looks for two independent words in the landed e2e specs:
the key name (an arm that imports or quotes the row) and the server's `reason_code` (an arm that drives
the door with that answer). A row matched by neither has never been put on a screen by the line's own
instruments, which is the gap this lane was sent to close.

Word-level hits are named, not judged: `frontend/e2e/**` is read as it stands at the checked-out tip.
"""
import glob
import io
import json
import os
import re
import subprocess
import time

WT = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt"
OUT = "%s/frontend/review/checkin-words-day24/receipts/which_rows_had_a_screen_reading_r1.json" % WT
KEYS = ["duplicateAt", "duplicateNoMoment", "activityUnknown", "activityNotInJourney", "placeUnknown",
        "targetRequired", "targetAmbiguous", "journeyInBin", "journeyUnknown", "unreachable",
        "unexpected"]
CODES = {
    "duplicateAt": "CHECKIN_DUPLICATE_STAMP",
    "duplicateNoMoment": "CHECKIN_DUPLICATE_STAMP",
    "activityUnknown": "CHECKIN_ACTIVITY_UNKNOWN",
    "activityNotInJourney": "CHECKIN_ACTIVITY_NOT_IN_JOURNEY",
    "placeUnknown": "CHECKIN_PLACE_UNKNOWN",
    "targetRequired": "CHECKIN_TARGET_REQUIRED",
    "targetAmbiguous": "CHECKIN_TARGET_AMBIGUOUS",
    "journeyInBin": "CHECKIN_JOURNEY_IN_RECYCLE_BIN",
    "journeyUnknown": "CHECKIN_JOURNEY_UNKNOWN",
}
OWN_SPEC = "qoder-e766b154-checkin-words-day24-r1.spec.ts"


def main():
    tip = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True,
                         text=True).stdout.strip()
    files = sorted(glob.glob("%s/frontend/e2e/**/*.ts" % WT, recursive=True))
    texts = {}
    for f in files:
        with io.open(f, encoding="utf-8", errors="replace") as handle:
            texts[os.path.relpath(f, WT).replace("\\", "/")] = handle.read()
    landed = {name: t for name, t in texts.items() if not name.endswith(OWN_SPEC)}

    rows = []
    for key in KEYS:
        code = CODES.get(key)
        by_key = sorted(n for n, t in landed.items()
                        if re.search(r"\b%s\b" % re.escape(key), t))
        by_code = sorted(n for n, t in landed.items()
                         if code and code in t)
        # A word hit in another feature's vocabulary is not this door being driven. The strict form
        # only counts a spec that is about this door: it names the door's reason_code, or its own file
        # name carries the check-in word.
        strict = sorted(n for n in set(by_key) | set(by_code)
                        if code and code in texts[n] or "checkin" in n.lower())
        rows.append({
            "copy_key": key, "reason_code": code or "CLIENT_STATE_NO_CODE",
            "specs_naming_the_key": by_key, "specs_sending_the_code": by_code,
            "had_a_screen_reading_before_this_hand": bool(by_key or by_code),
            "strict_door_own_spec_hits": strict,
            "strict_had_a_screen_reading_before_this_hand": bool(strict),
        })

    body = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "measured_against_tip": tip,
        "e2e_files_read": len(landed), "own_spec_excluded": OWN_SPEC,
        "rows": rows,
        "rows_never_driven_before_this_hand": sorted(r["copy_key"] for r in rows
                                                     if not r["had_a_screen_reading_before_this_hand"]),
        "rows_driven_before_this_hand": sorted(r["copy_key"] for r in rows
                                               if r["had_a_screen_reading_before_this_hand"]),
        "rows_driven_strictly_before_this_hand": sorted(r["copy_key"] for r in rows
                                                        if r["strict_had_a_screen_reading_before_this_hand"]),
        "limit": "word-level: a spec that drives a state without naming either the key or the code would "
        "read as never driven here",
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    printable = json.dumps(body, ensure_ascii=False).encode("ascii", "replace").decode("ascii")
    print(printable[:1500])
    print("WROTE %s bytes=%d" % (OUT, len(json.dumps(body, ensure_ascii=False).encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
