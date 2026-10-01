"""ORD-0518 -- where do the two folds the screen would have to reproduce part company?

`journeyOrderVerdict.ts` wants to re-check the door's `TITLE` order in the browser.  The server sorts
on Python's `str.casefold()` (`backend/app/main.py`, `_JOURNEY_TIER_KEYS`); the screen has only
JavaScript's `toLowerCase()`.  The screen may claim "checked row by row" only for titles where those
two operations answer the same thing, so the deny-list it uses has to come from a measurement of every
code point, not from a guess about which letters are "exotic".

This script is one half of that measurement.  For every code point except the surrogate range it asks
Python what `casefold` returns, and writes the answers as JSON for `fold_diff_browser_vs_server_r1.cjs` to
compare against `String.prototype.toLowerCase`.  Both files are kept so the list can be re-derived
instead of re-invented.

    D:/moodle/CityNexus/backend/.venv/Scripts/python.exe review/ord0518/fold_casefold_server_r1.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fold_casefold_server_r1.json"

MAX_CODE_POINT = 0x10FFFF
SURROGATE_FIRST, SURROGATE_LAST = 0xD800, 0xDFFF


def main() -> int:
    answers = {}
    for code_point in range(MAX_CODE_POINT + 1):
        if SURROGATE_FIRST <= code_point <= SURROGATE_LAST:
            continue
        character = chr(code_point)
        folded = character.casefold()
        # Only the cases worth transporting: where casefold changes the character at all, or where it
        # is one of the forms that are not simply the lowercase of the same letter.
        if folded != character:
            answers[str(code_point)] = folded
    OUT.write_text(json.dumps(answers, ensure_ascii=False), encoding="utf-8")
    # The count is the reading, so it has to survive a GBK console.
    print(len(answers))
    print(OUT.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
