"""ORD-0512 -- re-derive the mutant red sets from the logs already on disk.

The r2 harness printed `red_tests` empty because its own regex expected the file path and the line
number with a space between them; Playwright writes `file.ts:296:1 › title`. This reads the same logs
through the family diff's parser (the one that only counts the failure-summary block) so the published
report carries the per-case red sets rather than a paragraph of prose about them.

usage: python ord0512_mutant_redsets_r2.py <gen>      (gen = r1 | r2)
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ord0512_family_diff_r1 import reds, totals  # noqa: E402

GATE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/gate")
OUT = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/mutant")


def main() -> int:
    gen = sys.argv[1] if len(sys.argv) > 1 else "r2"
    report = {}
    for log in sorted(GATE.glob(f"ord0512{gen}m_*.log")):
        case = log.stem[len(f"ord0512{gen}m_"):]
        report[case] = {"totals": totals(str(log)), "red_tests": reds(str(log)), "log": str(log)}
    out = OUT / f"mutant_{gen}_red_sets.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1)[:1500].encode("ascii", "replace").decode())
    print(f"WROTE={out} CASES={len(report)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
