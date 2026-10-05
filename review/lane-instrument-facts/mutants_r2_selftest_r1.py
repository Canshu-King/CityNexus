"""Give the new INVALID judgement its own discriminating run.

`cmdr0204_mutants_r2.py` added a third row shape, `INVALID_no_summary`, so that a run which produced no
parseable evidence can no longer be scored as green or red.  A judgement shape that never fired is
exactly the kind of lock that bites nobody, so this script fires it deliberately:

  leg 1  the r1 malformed call: `list("<node id>")` -- one argument per character;
         expected: shape == INVALID_no_summary   (this is r1's R4 row, reproduced on purpose)
  leg 2  the same call with the selection normalised the r2 way;
         expected: a real shape (GREEN, with no mutation applied)

No product or test bytes are touched: leg 2 runs the clean module with no mutant.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

SPEC = importlib.util.spec_from_file_location(
    "m2", r"D:/moodle/_qoder_seed_ord0489/run/cmdr0204_mutants_r2.py")
m2 = importlib.util.module_from_spec(SPEC)
assert m2.__spec__ is not None and SPEC.loader is not None
SPEC.loader.exec_module(m2)

NODE = f"{m2.RCITY}::{m2.CITY_NODE}"


def main() -> int:
    malformed = list(NODE)                      # what r1's caller effectively passed
    print(f"leg1 malformed argv length = {len(malformed)} args (one per character of the node id)")
    row1 = m2.run(m2.RCITY, malformed, m2.CITY_NODE)
    print(f"leg1 shape={row1['shape']} exit={row1['exit']} summary={row1['summary']!r}")

    print(f"\nleg2 normalised argv = ['{NODE}'] (one argument)")
    row2 = m2.run(m2.RCITY, [NODE], m2.CITY_NODE)
    print(f"leg2 shape={row2['shape']} exit={row2['exit']} summary={row2['summary']!r}")

    ok = row1["shape"] == "INVALID_no_summary" and row2["shape"] in ("GREEN",)
    print("\nVERDICT", "INVALID_LEG_BITES" if ok else "INVALID_LEG_DID_NOT_BITE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
